from datetime import UTC, date, datetime
from typing import Annotated, Literal

from bson import ObjectId
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


def _stringify_object_id(value: object) -> object:
    return str(value) if isinstance(value, ObjectId) else value


def _check_object_id(value: str) -> str:
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    # Canonical lowercase form, so case variants of one id compare equal.
    return str(ObjectId(value))


def _reject_duplicates(values: list) -> list:
    if len(set(values)) != len(values):
        raise ValueError("must not contain duplicates")
    return values


def _drop_duplicates(values: list) -> list:
    return list(dict.fromkeys(values))


# Accepts an ObjectId (from MongoDB) or its 24-char hex string (from clients)
# and always yields the string form.
ObjectIdStr = Annotated[
    str,
    BeforeValidator(_stringify_object_id),
    AfterValidator(_check_object_id),
]


# The 500-character cap bounds input size; it is not meant as a business rule.
Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
# Strict so JSON true or "12" is rejected instead of silently coerced.
Pages = Annotated[int, Field(strict=True, gt=0, le=100_000)]
AuthorIds = Annotated[
    list[ObjectIdStr], Field(min_length=1), AfterValidator(_reject_duplicates)
]
Tags = Annotated[list[Text], AfterValidator(_drop_duplicates)]


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


class BookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Text
    publisher: Text
    author_ids: AuthorIds
    pages: Pages
    tags: Tags = []


class BookUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Text | None = None
    publisher: Text | None = None
    author_ids: AuthorIds | None = None
    pages: Pages | None = None
    tags: Tags | None = None

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


def _reject_future(value: date | None) -> date | None:
    if value is not None and value > datetime.now(UTC).date():
        raise ValueError("must not be in the future")
    return value


class AuthorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Text
    birth_date: Annotated[date | None, AfterValidator(_reject_future)] = None


class Author(BaseModel):
    id: ObjectIdStr = Field(validation_alias="_id")
    name: str
    birth_date: date | None


class AuthorWithBookCount(Author):
    book_count: int


class PublisherWithAveragePages(BaseModel):
    publisher: str
    average_pages: float


class HealthStatus(BaseModel):
    status: Literal["ok"]
