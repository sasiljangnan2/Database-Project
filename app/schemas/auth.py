"""예정 API 계약의 요청·응답 모델. 이 파일을 구현과 함께 갱신한다."""

from __future__ import annotations

from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import APIModel, PatchModel


class Register(APIModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128, repr=False)
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=30)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Login(APIModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class Token(APIModel):
    access_token: str = Field(min_length=1)
    token_type: Literal["bearer"]
    expires_in: int = Field(ge=1, strict=True)


class User(APIModel):
    id: int = Field(ge=1, strict=True)
    email: EmailStr
    name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    role: Literal["MEMBER", "ADMIN"]
    is_active: bool = Field(strict=True)


class UserPatch(PatchModel):
    name: str = Field(default=None, min_length=1, max_length=100)
    phone: str = Field(default=None, min_length=1, max_length=30)


class PasswordChange(APIModel):
    current_password: str = Field(min_length=1, max_length=128, repr=False)
    new_password: str = Field(min_length=10, max_length=128, repr=False)


class AdminUserPatch(PatchModel):
    is_active: bool = Field(strict=True)
