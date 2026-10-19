from bson import ObjectId
from fastapi import APIRouter

from app.db import Database
from app.errors import AuthorNotFound
from app.models import Book, ObjectIdStr, Page
from app.pagination import PageParams, paginate

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/{author_id}/books")
async def list_author_books(
    db: Database,
    author_id: ObjectIdStr,
    pagination: PageParams,
) -> Page[Book]:
    oid = ObjectId(author_id)
    if await db.authors.find_one({"_id": oid}) is None:
        raise AuthorNotFound

    return await paginate(db.books, {"authors.id": oid}, pagination, Book)
