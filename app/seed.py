"""Load the challenge's sample books into an empty database.

Run with: uv run python -m app.seed
"""

from datetime import datetime

from pymongo import MongoClient
from pymongo.database import Database

from app.config import Settings

# The sample data from the challenge, as given. Its integer ids are left out
# because the API uses ObjectIds, and "author" is converted into author
# documents with embedded references.
SAMPLE_BOOKS = [
    {
        "title": "Learning Python",
        "publisher": "O'Reilly Media",
        "author": "Mark Lutz",
        "pages": 1648,
        "created_at": "2017-01-12T00:00:00+03:00",
        "tags": ["Python", "Development", "Learning"],
        "updated_at": "2017-01-12T00:00:00+03:00",
    },
    {
        "title": "Architecture Patterns with Python",
        "publisher": "O'Reilly Media",
        "author": "Harry Percival, Bob Gregory",
        "pages": 304,
        "tags": ["Python", "Development", "Functional Programming"],
        "created_at": "2017-01-12T00:00:00+03:00",
        "updated_at": "2017-01-12T00:00:00+03:00",
    },
]


def _author_names(sample: dict) -> list[str]:
    return [name.strip() for name in sample["author"].split(",")]


def seed(db: Database) -> bool:
    """Insert the sample data. Returns False, changing nothing, if data exists."""
    if db.books.find_one({}, {"_id": 1}) or db.authors.find_one({}, {"_id": 1}):
        return False

    names = list(dict.fromkeys(n for book in SAMPLE_BOOKS for n in _author_names(book)))
    result = db.authors.insert_many([{"name": n, "birth_date": None} for n in names])
    author_ids = dict(zip(names, result.inserted_ids, strict=True))

    db.books.insert_many(
        [
            {
                "title": sample["title"],
                "publisher": sample["publisher"],
                "authors": [
                    {"id": author_ids[name], "name": name}
                    for name in _author_names(sample)
                ],
                "pages": sample["pages"],
                "tags": sample["tags"],
                "created_at": datetime.fromisoformat(sample["created_at"]),
                "updated_at": datetime.fromisoformat(sample["updated_at"]),
            }
            for sample in SAMPLE_BOOKS
        ]
    )
    return True


def main() -> None:
    settings = Settings()
    client = MongoClient(settings.mongodb_uri, tz_aware=True)
    try:
        if seed(client[settings.mongodb_database]):
            print(f"Seeded {len(SAMPLE_BOOKS)} sample books.")
        else:
            print("Database already has data; nothing seeded.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
