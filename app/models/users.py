import enum
from uuid6 import uuid6
from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.session import Base


class ROLE(enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid6)
    github_id = Column(String(255), nullable=False, unique=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    avatar_url = Column(String(255), nullable=False)
    role = Column(Enum(ROLE), nullable=False, default=ROLE.ANALYST)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    refresh_tokens = relationship("RefreshToken", back_populates="user")
