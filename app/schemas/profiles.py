from pydantic import BaseModel, ConfigDict
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

class ProfileSuccessResponse(BaseModel):
    status: str
    message: str | None = None
    data: ProfileSchema

class ProfileListResponse(BaseModel):
    status: str
    count: int
    data: List[ProfileSchema]