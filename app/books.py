from datetime import UTC, datetime
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.db import Database
from app.models import Book, BookCreate, ObjectIdStr, Page

router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(
    db: Database,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[Book]:
    cursor = db.books.find().sort("_id").skip((page - 1) * limit).limit(limit)
    return Page(
        items=[Book.model_validate(book) async for book in cursor],
        total=await db.books.count_documents({}),
        page=page,
        limit=limit,
    )


@router.get("/{book_id}")
async def get_book(db: Database, book_id: ObjectIdStr) -> Book:
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return Book.model_validate(book)


@router.post("", status_code=201)
async def create_book(db: Database, book_create: BookCreate) -> Book:
    author_ids = [ObjectId(author_id) for author_id in book_create.author_ids]
    names = {
        author["_id"]: author["name"]
        async for author in db.authors.find({"_id": {"$in": author_ids}}, {"name": 1})
    }
    missing = [str(author_id) for author_id in author_ids if author_id not in names]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Unknown author ids: {', '.join(missing)}"
        )

    now = datetime.now(UTC)
    # MongoDB stores milliseconds, so truncate to return what a later GET returns.
    now = now.replace(microsecond=now.microsecond // 1000 * 1000)
    book = book_create.model_dump(exclude={"author_ids"}) | {
        "authors": [
            {"id": author_id, "name": names[author_id]} for author_id in author_ids
        ],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.books.insert_one(book)
    return Book.model_validate(book | {"_id": result.inserted_id})
