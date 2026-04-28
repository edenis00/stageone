from fastapi import APIRouter, Depends, status, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.profiles import (
    ProfileCreate,
    ProfileSuccessResponse,
    ProfileListResponse,
    ProfileFilterParams,
    SortBy,
    Order
)
from app.services.profiles import ProfileService
from app.api.dependencies.deps import get_current_user
from app.api.dependencies.rbac import Rolechecker
from app.models.users import ROLE


router = APIRouter()


@router.post(
    "/profiles",
    response_model=ProfileSuccessResponse,
)
async def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    current_user=Depends(Rolechecker(ROLE.ADMIN)),
):
    service = ProfileService(db)
    result = await service.create_profile(payload)

    return result


@router.get("/profiles", response_model=ProfileListResponse)
def get_all_profiles(
    filters: ProfileFilterParams = Depends(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProfileService(db)
    result = service.list_profiles(**filters.model_dump())  
    
    return result


@router.get("/profiles/search")
def search_profiles(
    q: str,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
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
def get_profile_by_id(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProfileService(db)
    result = service.get_profile(profile_id)
    
    return result


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(Rolechecker(ROLE.ADMIN)),
):
    service = ProfileService(db)
    result = service.delete_profile(profile_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profiles/export")
def export_profile(
    format: str = "csv",
    gender: str | None = None,
    age_group: str | None = None,
    country_id: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    sort_by: SortBy | None = None,
    order: Order | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if format != "csv":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Only CSV format supported"},
        )
    
    service = ProfileService(db)
    
    csv_buffer, filename = service.export_profile_to_csv(
        gender=gender,
        age_group=age_group,
        country_id=country_id,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        order=order,
    )
    
    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )