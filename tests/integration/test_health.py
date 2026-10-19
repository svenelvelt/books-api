import time

import pytest
from pymongo import AsyncMongoClient

from app.config import Settings
from tests.helpers import assert_error


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


def test_liveness_returns_ok(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ok_when_database_is_reachable(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_503_quickly_when_database_is_unreachable(
    client, unreachable_db
):
    started = time.monotonic()
    response = client.get("/health/ready")

    assert_error(response, 503, "database_unavailable")
    assert time.monotonic() - started < 2


def test_liveness_does_not_depend_on_the_database(client, unreachable_db):
    assert client.get("/health/live").status_code == 200


def test_database_timeout_defaults_to_five_seconds():
    assert Settings().mongodb_timeout_ms == 5000
