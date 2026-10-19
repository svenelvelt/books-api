from typing import Annotated

from bson import ObjectId
from pydantic import AfterValidator, BeforeValidator


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
