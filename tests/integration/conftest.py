import pytest
from pymongo import AsyncMongoClient


@pytest.fixture(autouse=True)
def _clean_db(mongo_db):
    # Every integration test starts with empty collections. Documents are
    # deleted but collections and indexes stay, so there is no per-test startup.
    for name in mongo_db.list_collection_names():
        mongo_db[name].delete_many({})


@pytest.fixture
def unreachable_db(client, monkeypatch):
    """Simulate MongoDB going away after startup: nothing listens on port 1."""
    unreachable = AsyncMongoClient(
        "mongodb://localhost:1", serverSelectionTimeoutMS=100
    )
    monkeypatch.setattr(client.app.state, "db", unreachable["books_test"])
    yield
    # Close on the app's event loop, where the client was used.
    client.portal.call(unreachable.close)
