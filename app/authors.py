from bson import ObjectId
from fastapi import APIRouter

from app.db import Database
from app.errors import AuthorNotFound
from app.models import AuthorWithBookCount, Book, ObjectIdStr, Page
from app.pagination import PageParams, paginate

router = APIRouter(prefix="/authors", tags=["authors"])


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
