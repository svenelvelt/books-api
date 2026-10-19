import pytest


@pytest.fixture(autouse=True)
def _clean_db(mongo_db):
    # Every integration test starts with empty collections. Documents are
    # deleted but collections and indexes stay, so there is no per-test startup.
    for name in mongo_db.list_collection_names():
        mongo_db[name].delete_many({})
