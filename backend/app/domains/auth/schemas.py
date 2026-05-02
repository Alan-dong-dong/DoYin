from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domains.users.schemas import UserProfile


class RegisterRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email is required.")
        return normalized

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Username is required.")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email is required.")
        return normalized


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserProfile

