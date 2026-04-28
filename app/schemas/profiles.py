from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime

from uuid import UUID

from typing import List

from enum import Enum

from fastapi import Query


class ProfileCreate(BaseModel):
    name: str


class ProfileSchema(BaseModel):

    id: UUID
    name: str
    gender: str
    gender_probability: float
    sample_size: int
    age: int
    age_group: str
    country_id: str
    country_name: str | None = None
    country_probability: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):

        return dt.isoformat().replace("+00:00", "Z")


class ProfileSuccessResponse(BaseModel):
    status: str

    message: str | None = None

    data: ProfileSchema


class ProfileListResponse(BaseModel):
    status: str
    page: int
    limit: int
    total: int
    total_pages: int
    links: dict
    data: List[ProfileSchema]


class SortBy(str, Enum):
    age = "age"
    created_at = "created_at"
    gender_probability = "gender_probability"


class Order(str, Enum):
    asc = "asc"
    desc = "desc"


class ProfileFilterParams(BaseModel):
    gender: str | None = None
    age_group: str | None = None
    country_id: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    min_gender_probability: float | None = None
    min_country_probability: float | None = None
    sort_by: SortBy | None = None
    order: Order | None = None
    page: int = Query(default=1, ge=1)
    limit: int = Query(default=10, ge=1, le=100)
