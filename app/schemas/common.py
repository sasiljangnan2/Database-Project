from datetime import UTC, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def database_times_are_utc(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @field_validator("*", mode="after")
    @classmethod
    def require_time_zone(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("일시 문자열에는 시간대를 포함해야 합니다.")
        return value


class PatchModel(APIModel):
    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("수정할 필드를 하나 이상 지정해야 합니다.")
        return self


class ErrorDetail(APIModel):
    field: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ErrorContent(APIModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: list[ErrorDetail]


class Error(APIModel):
    error: ErrorContent


class Health(APIModel):
    status: Literal["ok"]
    scope: Literal["process"]


class Message(APIModel):
    message: str = Field(min_length=1)


Item = TypeVar("Item")


class Page(APIModel, Generic[Item]):
    items: list[Item]
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
