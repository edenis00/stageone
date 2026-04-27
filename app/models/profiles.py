from uuid6 import uuid7
from sqlalchemy import Column, String, Integer, Float, DateTime, UUID
from datetime import datetime, timezone
from app.db.session import Base

class Profile(Base):
    __tablename__ = "profile"
    
    id = Column(UUID, primary_key=True, default=uuid7)
    name = Column(String(255), unique=True, index=True)
    gender = Column(String)
    gender_probability = Column(Float)
    sample_size = Column(Integer)
    age = Column(Integer)
    age_group = Column(String(255))
    country_id = Column(String(10))
    country_name = Column(String(255))
    country_probability = Column(Float)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    ) 
