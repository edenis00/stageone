from fastapi import APIRouter, Depends, status, Response

from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from app.db.session import get_db

from app.schemas.profiles import (
    ProfileCreate,
    ProfileSuccessResponse,
    ProfileListResponse,
    SortBy,
    Order,
)

from app.services.profiles import ProfileService


router = APIRouter()


@router.post(
    "/profiles",
    response_model=ProfileSuccessResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    payload: ProfileCreate, response: Response, db: Session = Depends(get_db)
):

    service = ProfileService(db)

    result = await service.create_profile(payload)

    if isinstance(result, JSONResponse):
        return result

    if result.get("message") == "Profile already exists":

        response.status_code = status.HTTP_200_OK

    else:

        response.status_code = status.HTTP_201_CREATED

    return result


@router.get("/profiles", response_model=ProfileListResponse)
def get_all_profiles(
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
    db: Session = Depends(get_db),
):

    service = ProfileService(db)

    result = service.list_profiles(
        gender=gender,
        age_group=age_group,
        country_id=country_id,
        min_age=min_age,
        max_age=max_age,
        min_gender_probability=min_gender_probability,
        min_country_probability=min_country_probability,
        sort_by=sort_by,
        order=order,
        page=page,
        limit=limit,
    )

    if isinstance(result, JSONResponse):
        return result
    return result


@router.get("/profiles/search")
def search_profiles(
    q: str, page: int = 1, limit: int = 10, db: Session = Depends(get_db)
):
    if not q or q.strip() == (""):
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Missing search query",
            },
        )

    service = ProfileService(db)
    filters = service.natural_query(q)

    if not filters:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Unable to interpret query",
            },
        )

    return service.list_profiles(**filters, page=page, limit=limit)


@router.get("/profiles/{profile_id}", response_model=ProfileSuccessResponse)
def get_profile_by_id(profile_id: str, db: Session = Depends(get_db)):

    service = ProfileService(db)

    result = service.get_profile(profile_id)

    if isinstance(result, JSONResponse):
        return result
    return result


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):

    service = ProfileService(db)

    result = service.delete_profile(profile_id)

    if isinstance(result, JSONResponse):
        return result

    return Response(status_code=status.HTTP_204_NO_CONTENT)
