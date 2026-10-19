from datetime import date, datetime
from typing import Annotated

from bson import ObjectId
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)


def _stringify_object_id(value: object) -> object:
    return str(value) if isinstance(value, ObjectId) else value


def _check_object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return value


# Accepts an ObjectId (from MongoDB) or its 24-char hex string (from clients)
# and always yields the string form.
ObjectIdStr = Annotated[
    str,
    BeforeValidator(_stringify_object_id),
    AfterValidator(_check_object_id),
]


class AuthorRef(BaseModel):
    id: ObjectIdStr
    name: str


class Book(BaseModel):
    id: ObjectIdStr = Field(validation_alias="_id")
    title: str
    publisher: str
    authors: list[AuthorRef]
    pages: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int


class BookCreate(BaseModel):
    title: str
    publisher: str
    author_ids: list[ObjectIdStr]
    pages: int
    tags: list[str] = []


class BookUpdate(BaseModel):
    title: str | None = None
    publisher: str | None = None
    author_ids: list[ObjectIdStr] | None = None
    pages: int | None = None
    tags: list[str] | None = None

    # Fields are optional so clients can send only what changes, but a field
    # that is sent must not be null. Field validators only run on sent fields.
    @field_validator("*")
    @classmethod
    def _reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("must not be null")
        return value

    @model_validator(mode="after")
    def _reject_empty(self) -> "BookUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self


class AuthorWithBookCount(BaseModel):
    id: ObjectIdStr = Field(validation_alias="_id")
    name: str
    birth_date: date | None
    book_count: int
