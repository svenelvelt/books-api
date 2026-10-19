from datetime import UTC, datetime, time

from bson import ObjectId
from fastapi import APIRouter, Request, Response

from app.db import Database
from app.errors import AuthorNotFound
from app.models import Author, AuthorCreate, AuthorWithBookCount, Book, ObjectIdStr
from app.pagination import Page, PageParams, paginate

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("/{author_id}")
async def get_author(db: Database, author_id: ObjectIdStr) -> Author:
    author = await db.authors.find_one({"_id": ObjectId(author_id)})
    if author is None:
        raise AuthorNotFound
    return Author.model_validate(author)


@router.get("/{author_id}/books")
async def list_author_books(
    db: Database,
    author_id: ObjectIdStr,
    pagination: PageParams,
) -> Page[Book]:
    oid = ObjectId(author_id)
    if await db.authors.find_one({"_id": oid}, {"_id": 1}) is None:
        raise AuthorNotFound

    return await paginate(db.books, {"authors.id": oid}, pagination, Book)


@router.get("")
async def list_authors(
    db: Database, pagination: PageParams
) -> Page[AuthorWithBookCount]:
    pipeline = [
        {"$sort": {"_id": 1}},
        {"$skip": pagination.skip},
        {"$limit": pagination.limit},
        {
            "$lookup": {
                "from": "books",
                "localField": "_id",
                "foreignField": "authors.id",
                "pipeline": [{"$count": "n"}],
                "as": "counts",
            }
        },
        {"$set": {"book_count": {"$ifNull": [{"$first": "$counts.n"}, 0]}}},
        {"$unset": "counts"},
    ]
    items = [
        AuthorWithBookCount.model_validate(a)
        async for a in await db.authors.aggregate(pipeline)
    ]
    total = await db.authors.count_documents({})

    return Page(items=items, total=total, page=pagination.page, limit=pagination.limit)


@router.post("", status_code=201)
async def create_author(
    db: Database, author_create: AuthorCreate, request: Request, response: Response
) -> Author:
    author = author_create.model_dump()
    if author["birth_date"] is not None:
        # MongoDB has no date-only type, so store midnight UTC.
        author["birth_date"] = datetime.combine(author["birth_date"], time(), UTC)
    result = await db.authors.insert_one(author)
    author_id = str(result.inserted_id)
    response.headers["Location"] = request.url_for(
        "get_author", author_id=author_id
    ).path
    return Author.model_validate(author | {"_id": result.inserted_id})
