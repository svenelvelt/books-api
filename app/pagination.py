from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel
from pymongo.asynchronous.collection import AsyncCollection


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int


@dataclass(frozen=True)
class Pagination:
    page: int
    limit: int

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.limit


def _pagination(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Pagination:
    return Pagination(page=page, limit=limit)


PageParams = Annotated[Pagination, Depends(_pagination)]


async def paginate[T: BaseModel](
    collection: AsyncCollection, query: dict, pagination: Pagination, model: type[T]
) -> Page[T]:
    """Run `query` sorted by _id and return one page with the total match count."""
    cursor = (
        collection.find(query).sort("_id").skip(pagination.skip).limit(pagination.limit)
    )
    return Page(
        items=[model.model_validate(document) async for document in cursor],
        total=await collection.count_documents(query),
        page=pagination.page,
        limit=pagination.limit,
    )
