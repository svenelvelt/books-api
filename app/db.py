from typing import Annotated

from fastapi import Depends, Request
from pymongo import IndexModel
from pymongo.asynchronous.database import AsyncDatabase


def get_db(request: Request) -> AsyncDatabase:
    return request.app.state.db


Database = Annotated[AsyncDatabase, Depends(get_db)]


async def create_indexes(db: AsyncDatabase) -> None:
    await db.books.create_indexes(
        [IndexModel("authors.id"), IndexModel("publisher"), IndexModel("tags")]
    )
