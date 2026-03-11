from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    email: str
    display_name: str
    preferred_locale: str | None = None
    created_at: datetime | None = None


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    display_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    preferred_locale: str | None = Field(default=None, max_length=16)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class AuthSessionResponse(BaseModel):
    token: str
    profile: UserProfile

