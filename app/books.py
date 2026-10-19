import re
from datetime import UTC, datetime
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Query, Request, Response
from pymongo import ReturnDocument

from app.db import Database
from app.errors import BookNotFound, UnknownAuthors
from app.models import Book, BookCreate, BookUpdate, ObjectIdStr
from app.pagination import Page, PageParams, paginate

router = APIRouter(prefix="/books", tags=["books"])


def _now() -> datetime:
    now = datetime.now(UTC)
    # MongoDB stores milliseconds, so truncate to return what a later GET returns.
    return now.replace(microsecond=now.microsecond // 1000 * 1000)


def _contains(text: str) -> dict:
    return {"$regex": re.escape(text), "$options": "i"}


def build_book_filter(
    title: str | None = None,
    author: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    query = {}
    if title:
        query["title"] = _contains(title)
    if author:
        query["authors.name"] = _contains(author)
    if tags:
        query["tags"] = {"$all": tags}
    return query


@router.get("")
async def list_books(
    db: Database,
    pagination: PageParams,
    title: str | None = None,
    author: str | None = None,
    tags: Annotated[list[str] | None, Query()] = None,
) -> Page[Book]:
    query = build_book_filter(title=title, author=author, tags=tags)
    return await paginate(db.books, query, pagination, Book)


@router.get("/{book_id}")
async def get_book(db: Database, book_id: ObjectIdStr) -> Book:
    book = await db.books.find_one({"_id": ObjectId(book_id)})
    if book is None:
        raise BookNotFound
    return Book.model_validate(book)


async def _embed_authors(db: Database, author_ids: list[str]) -> list[dict]:
    """Look up the authors and return the {id, name} refs that books embed."""
    ids = [ObjectId(author_id) for author_id in author_ids]
    names = {
        author["_id"]: author["name"]
        async for author in db.authors.find({"_id": {"$in": ids}}, {"name": 1})
    }
    missing = [str(author_id) for author_id in ids if author_id not in names]
    if missing:
        raise UnknownAuthors(missing)
    return [{"id": author_id, "name": names[author_id]} for author_id in ids]


@router.post("", status_code=201)
async def create_book(
    db: Database, book_create: BookCreate, request: Request, response: Response
) -> Book:
    authors = await _embed_authors(db, book_create.author_ids)
    now = _now()
    book = book_create.model_dump(exclude={"author_ids"}) | {
        "authors": authors,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.books.insert_one(book)
    book_id = str(result.inserted_id)
    response.headers["Location"] = request.url_for("get_book", book_id=book_id).path
    return Book.model_validate(book | {"_id": result.inserted_id})


@router.delete("/{book_id}", status_code=204)
async def delete_book(db: Database, book_id: ObjectIdStr) -> None:
    result = await db.books.delete_one({"_id": ObjectId(book_id)})
    if result.deleted_count == 0:
        raise BookNotFound


@router.patch("/{book_id}")
async def update_book(
    db: Database, book_id: ObjectIdStr, book_update: BookUpdate
) -> Book:
    changes = book_update.model_dump(exclude_unset=True)
    if "author_ids" in changes:
        changes["authors"] = await _embed_authors(db, changes.pop("author_ids"))
    book = await db.books.find_one_and_update(
        {"_id": ObjectId(book_id)},
        {"$set": changes | {"updated_at": _now()}},
        return_document=ReturnDocument.AFTER,
    )
    if book is None:
        raise BookNotFound
    return Book.model_validate(book)
