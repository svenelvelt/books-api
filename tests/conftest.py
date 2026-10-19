import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.config import Settings
from app.main import create_app

TEST_SETTINGS = Settings(mongodb_database="books_test")


@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(TEST_SETTINGS.mongodb_uri)
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
