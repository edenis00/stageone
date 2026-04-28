import re
import asyncio
import httpx
import csv
import io
import pycountry
from fastapi import Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.profiles import Profile
from app.db.session import get_db
from app.schemas.profiles import ProfileCreate, SortBy, Order, ProfileSchema
from app.core.config import settings


GENDERIZE_URL = settings.GENDERIZE_URL
AGIFY_URL = settings.AGIFY_URL
NATIONALIZE_URL = settings.NATIONALIZE_URL


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def error_message(self, code, message):
        return JSONResponse(
            status_code=code,
            content={
                "status": "error",
                "message": message,
            },
        )

    async def fetch_external_data(self, name: str):
        async with httpx.AsyncClient() as client:
            try:
                gender_res = await client.get(GENDERIZE_URL, params={"name": name})
                gender_res.raise_for_status()
                gender_data = gender_res.json()
            except Exception:
                return self.error_message(
                    code=502, message="Genderize returned an invalid response"
                )

            try:
                age_res = await client.get(AGIFY_URL, params={"name": name})
                age_res.raise_for_status()
                age_data = age_res.json()
            except Exception:
                return self.error_message(
                    code=502, message="Agify returned an invalid response"
                )

            try:
                country_res = await client.get(NATIONALIZE_URL, params={"name": name})
                country_res.raise_for_status()
                country_data = country_res.json()
            except Exception:
                return self.error_message(
                    code=502, message="Nationalize returned an invalid response"
                )

            return gender_data, age_data, country_data

    async def create_profile(self, payload: ProfileCreate):
        name = payload.name.strip().lower()

        if not name:
            return self.error_message(code=400, message="Missing or empty name")

        existing_profile = self.db.query(Profile).filter(Profile.name == name).first()
        if existing_profile:
            return {
                "status": "success",
                "message": "Profile already exists",
                "data": existing_profile,
            }

        api_result = await self.fetch_external_data(name)
        if isinstance(api_result, JSONResponse):
            return api_result

        gender, age, country = api_result

        if gender.get("gender") is None or gender.get("count") == 0:
            return self.error_message(
                code=502, message="Genderize returned an invalid response"
            )

        if age.get("age") is None:
            return self.error_message(
                code=502, message="Agify returned an invalid response"
            )
        countries = country.get("country")
        if not countries or len(countries) == 0:
            return self.error_message(
                code=502, message="Nationalize returned an invalid response"
            )

        best_country = max(countries, key=lambda x: x["probability"])
        country_code = best_country["country_id"]
        country_obj = pycountry.countries.get(alpha_2=country_code)
        country_name = country_obj.name if country_obj else country_code

        age_value = age["age"]
        age_group = ""

        if age_value <= 12:
            age_group = "child"

        elif age_value <= 19:
            age_group = "teenager"

        elif age_value <= 59:
            age_group = "adult"

        else:
            age_group = "senior"

        new_profile = Profile(
            name=name,
            gender=gender["gender"],
            gender_probability=gender["probability"],
            sample_size=gender["count"],
            age=age_value,
            age_group=age_group,
            country_id=country_code,
            country_name=country_name,
            country_probability=best_country["probability"],
        )

        self.db.add(new_profile)
        try:
            self.db.commit()
            self.db.refresh(new_profile)
            return {"status": "success", "data": new_profile}
        except Exception as e:
            self.db.rollback()
            print(f"DEBUG ERROR: {e}")
            return self.error_message(code=500, message=str(e))

    def get_profile(self, id: str):

        profile = self.db.query(Profile).filter(Profile.id == id).first()

        if not profile:
            return self.error_message(code=404, message="Profile not found")

        return {"status": "success", "data": profile}

    def list_profiles(
        self,
        gender: str | None = None,
        age_group: str | None = None,
        country_id: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        min_gender_probability: float | None = None,
        min_country_probability: float | None = None,
        sort_by: SortBy | None = None,
        order: Order | None = None,
        page: int = 1,
        limit: int = 10,
    ):

        query = self.db.query(Profile)

        if gender:
            query = query.filter(Profile.gender.ilike(gender))

        if country_id:
            query = query.filter(Profile.country_id.ilike(country_id))

        if age_group:
            query = query.filter(Profile.age_group.ilike(age_group))

        if country_id:
            query = query.filter(Profile.country_id.ilike(country_id))

        if min_age:
            query = query.filter(Profile.age >= min_age)

        if max_age:
            query = query.filter(Profile.age <= max_age)

        if min_gender_probability:
            query = query.filter(Profile.gender_probability >= min_gender_probability)

        if min_country_probability:
            query = query.filter(Profile.country_probability >= min_country_probability)

        if sort_by:
            sorted_fields = {
                "age": Profile.age,
                "created_at": Profile.created_at,
                "gender_probability": Profile.gender_probability,
            }

            column = sorted_fields.get(sort_by)

            if column is not None:
                if order == "desc":
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())

        total = query.count()

        limit = max(10, min(limit, 50))

        offset = (page - 1) * limit

        profiles = query.offset(offset).limit(limit).all()

        profiles = [ProfileSchema.model_validate(p) for p in profiles]
        
        total_pages = (total + limit - 1) // limit

        return {
            "status": "success",
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "links": {
                "self": f"/api/profiles?page={page}&limit={limit}",
                "next": f"/api/profiles?page={page + 1}&limit={limit}" if (page *  limit)  < total else None,
                "prev": f"/api/profiles?page={page - 1}&limt={limit}" if page > 1 else None,
            },
            "data": profiles,
        }

    def delete_profile(self, id: str):

        profile = self.db.query(Profile).filter(Profile.id == id).first()

        if not profile:
            return self.error_message(code=404, message="Profile not found")

        self.db.delete(profile)
        self.db.commit()

        return {"status": "success", "message": "Profile deleted"}

    def natural_query(self, query: str):
        q = query.lower()
        filters = {}

        if "male" in q or "males" in q:
            filters["gender"] = "male"

        if "female" in q or "females" in q:
            filters["gender"] = "female"
        
        if "child" in q or "children" in q:
            filters["age_group"] = "child"

        if "teenager" in q or "teenagers" in q:
            filters["age_group"] = "teenager"

        if "adult" in q or "adults" in q:
            filters["age_group"] = "adult"

        if "young" in q:
            filters["min_age"] = 16
            filters["max_age"] = 24
        
        if "senior" in q:
            filters["age_group"] = "senior"

        match = re.search(r"above (\d+)", q)
        if match:
            filters["min_age"] = int(match.group(1))

        match = re.search(r"below (\d+)", q)
        if match:
            filters["max_age"] = int(match.group(1))

        for country in pycountry.countries:
            if country.name.lower() in q:
                filters["country_id"] = country.alpha_2
                break

        if not filters:
            return None

        return filters

    def export_profile_to_csv(
        self,
        gender: str | None = None,
        age_group: str | None = None,
        country_id: str | None = None,
        min_age: int | None = None,
        max_age: int | None = None,
        sort_by=None,
        order=None,
    ):
        query = self.db.query(Profile)
        
        if gender:
            query = query.filter(Profile.gender.ilike(gender))

        if country_id:
            query = query.filter(Profile.country_id.ilike(country_id))

        if age_group:
            query = query.filter(Profile.age_group.ilike(age_group))

        if min_age:
            query = query.filter(Profile.age >= min_age)

        if max_age:
            query = query.filter(Profile.age <= max_age)

        if sort_by:
            sorted_fields = {
                "age": Profile.age,
                "created_at": Profile.created_at,
                "gender_probability": Profile.gender_probability,
            }

            column = sorted_fields.get(sort_by)

            if column is not None:
                query = query.order_by(column.desc() if order == "desc" else column.asc())

        profiles = query.all()
        
        # Csv buffer
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([            
            "id",
            "name",
            "gender",
            "gender_probability",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "country_probability",
            "created_at",
        ])
        
        for p in profiles:
            writer.writerow([
                p.id,
                p.name,
                p.gender,
                p.gender_probability,
                p.age,
                p.age_group,
                p.country_id,
                p.country_name,
                p.country_probability,
                p.created_at,
            ])
    
        output.seek(0)
        
        filename = f"profiles_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
        
        return output, filename