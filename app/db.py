from typing import Annotated

from fastapi import Depends, Request
from pymongo import IndexModel
from pymongo.asynchronous.database import AsyncDatabase


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db


Database = Annotated[AsyncDatabase, Depends(get_db)]


async def create_indexes(db: AsyncDatabase) -> None:
    # Filter field first, then _id: list queries filter on one field and page
    # sorted by _id, so the index returns matches already in order.
    await db.books.create_indexes(
        [
            IndexModel([(field, 1), ("_id", 1)])
            for field in ("authors.id", "publisher", "tags")
        ]
    )
