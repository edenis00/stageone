from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.profiles import ProfileCreate, ProfileSuccessResponse, ProfileListResponse
from app.services.profiles import ProfileService


router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.post("/", response_model=ProfileSuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate, response: Response, db: Session = Depends(get_db)):
    service = ProfileService(db)
    result = await service.create_profile(payload)
    if result.get("message") == "Profile already exists":
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED
        
    return result


@router.get("/", response_model=ProfileListResponse)
def get_all_profiles(db: Session = Depends(get_db)):
    service = ProfileService(db)
    return service.list_profiles()


@router.get("/{profile_id}", response_model=ProfileSuccessResponse)
def get_profile_by_id(profile_id: str, db: Session = Depends(get_db)):
    service = ProfileService(db)
    return service.get_profile(profile_id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: str, db: Session = Depends(get_db)):
    service = ProfileService(db)
    return service.delete_profile(profile_id)
