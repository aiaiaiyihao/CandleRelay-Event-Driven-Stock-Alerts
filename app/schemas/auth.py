import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[1-9]\d{7,14}$")


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip().lower()
        if EMAIL_PATTERN.fullmatch(normalized):
            return normalized
        phone = re.sub(r"[\s()-]", "", normalized)
        if PHONE_PATTERN.fullmatch(phone):
            return phone
        raise ValueError("Enter a valid email address or phone number")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identifier: str
    identifier_type: str
    created_at: datetime
