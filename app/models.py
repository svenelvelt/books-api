from datetime import datetime
from typing import Annotated

from bson import ObjectId
from pydantic import AfterValidator, BaseModel, BeforeValidator, Field


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