from datetime import UTC, datetime

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.config import Settings
from app.main import create_app

TEST_SETTINGS = Settings(mongodb_database="books_test")


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(TEST_SETTINGS.mongodb_uri, tz_aware=True)
    client.drop_database(TEST_SETTINGS.mongodb_database)
    yield client[TEST_SETTINGS.mongodb_database]
    client.drop_database(TEST_SETTINGS.mongodb_database)
    client.close()


@pytest.fixture(scope="session")
def app_client(mongo_db):
    with TestClient(create_app(TEST_SETTINGS)) as client:
        yield client


@pytest.fixture
def client(app_client, mongo_db):
    # Clear documents but keep collections and indexes, so each test is isolated
    # without paying for a full startup per test.
    for name in mongo_db.list_collection_names():
        mongo_db[name].delete_many({})
    return app_client


@pytest.fixture
def insert_author(mongo_db):
    def insert(**overrides):
        author = {"name": "Mark Lutz", "birth_date": None} | overrides
        mongo_db.authors.insert_one(author)
        return author

    return insert


@pytest.fixture
def insert_book(mongo_db):
    # Inserts straight into MongoDB, bypassing the API, and returns the stored
    # document (with _id) so tests can build their expectations from it.
    def insert(**overrides):
        book = {
            "title": "Learning Python",
            "publisher": "O'Reilly Media",
            "authors": [{"id": ObjectId(), "name": "Mark Lutz"}],
            "pages": 1648,
            "tags": ["Python"],
            "created_at": datetime(2017, 1, 12, tzinfo=UTC),
            "updated_at": datetime(2017, 1, 12, tzinfo=UTC),
        } | overrides
        mongo_db.books.insert_one(book)
        return book

    return insert
