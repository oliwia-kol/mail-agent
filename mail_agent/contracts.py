from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Recipient = Literal[
    "human-resources@example.com",
    "help-desk@example.com",
    "it@example.com",
    "kadry@example.com",
    "other@example.com",
]


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("message")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Wpisz treść wiadomości. Same odstępy nie wystarczą.")
        return value


class SendEmailArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    recipient: Recipient


class RouteResponse(BaseModel):
    request_id: str
    recipient: Recipient
    status: Literal["smtp_accepted"] = "smtp_accepted"
