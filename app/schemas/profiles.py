from pydantic import BaseModel, ConfigDict, field_serializer
from datetime import datetime
from uuid import UUID
from typing import List


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
    country_probability: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat().replace("+00:00", "Z")


class ProfileListSchema(BaseModel):
    id: UUID
    name: str
    gender: str
    age: int
    age_group: str
    country_id: str

    model_config = ConfigDict(from_attributes=True)


class ProfileSuccessResponse(BaseModel):
    status: str
    message: str | None = None
    data: ProfileSchema


class ProfileListResponse(BaseModel):
    status: str
    count: int
    data: List[ProfileListSchema]
