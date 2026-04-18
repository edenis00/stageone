from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.profiles import (
    ProfileCreate,
    ProfileSuccessResponse,
    ProfileListResponse,
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

    # If the service returned a JSONResponse (error), return it directly
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
    country_id: str | None = None,
    age_group: str | None = None,
    db: Session = Depends(get_db),
):
    service = ProfileService(db)
    result = service.list_profiles(
        gender=gender, country_id=country_id, age_group=age_group
    )
    if isinstance(result, JSONResponse):
        return result
    return result


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
