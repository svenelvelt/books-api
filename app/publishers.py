from fastapi import APIRouter

from app.db import Database
from app.errors import PublisherNotFound
from app.models import PublisherWithAveragePages

router = APIRouter(prefix="/publishers", tags=["publishers"])


@router.get("/{publisher_name}/average_pages")
async def get_average_pages_for_publisher(
    db: Database, publisher_name: str
) -> PublisherWithAveragePages:
    pipeline = [
        {"$match": {"publisher": publisher_name}},
        {"$group": {"_id": None, "average_pages": {"$avg": "$pages"}}},
        {"$set": {"average_pages": {"$round": ["$average_pages", 2]}}},
    ]
    results = await (await db.books.aggregate(pipeline)).to_list()

    if not results:
        raise PublisherNotFound

    return PublisherWithAveragePages(
        publisher=publisher_name, average_pages=results[0]["average_pages"]
    )
