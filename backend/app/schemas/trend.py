from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.trend import TrendCategory, TrendStatus


def non_blank(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("must not be blank")
    return stripped


class AliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=200)

    _normalize_alias_input = field_validator("alias")(non_blank)


class AliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trend_id: UUID
    alias: str
    created_at: datetime


class TrendCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: TrendCategory = TrendCategory.OTHER
    description: str | None = Field(default=None, max_length=5000)
    aliases: list[str] = Field(default_factory=list, max_length=50)

    _normalize_name_input = field_validator("name")(non_blank)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("aliases")
    @classmethod
    def validate_aliases(cls, values: list[str]) -> list[str]:
        return [non_blank(value) for value in values]


class TrendRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: TrendCategory
    description: str | None
    status: TrendStatus
    created_at: datetime
    updated_at: datetime
    aliases: list[AliasRead]

