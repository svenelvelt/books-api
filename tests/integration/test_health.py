import time

from pymongo.errors import OperationFailure

from app.config import Settings
from tests.helpers import assert_error


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


def test_readiness_returns_503_for_other_database_errors(client, monkeypatch):
    # E.g. wrong credentials: MongoDB is reachable but refuses the command.
    # Regular endpoints treat such errors as bugs (500); readiness must not.
    class RefusingDatabase:
        async def command(self, name):
            raise OperationFailure("Authentication failed.", code=18)

    monkeypatch.setattr(client.app.state, "db", RefusingDatabase())

    assert_error(client.get("/health/ready"), 503, "database_unavailable")


def test_liveness_does_not_depend_on_the_database(client, unreachable_db):
    assert client.get("/health/live").status_code == 200


def test_database_timeout_defaults_to_five_seconds():
    assert Settings().mongodb_timeout_ms == 5000
