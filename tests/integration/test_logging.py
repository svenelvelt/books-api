import logging
import re

from fastapi.testclient import TestClient

from app.main import create_app


def access_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "app.access"]


def test_response_carries_a_generated_request_id(client):
    response = client.get("/health/live")

    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_valid_incoming_request_id_is_kept(client):
    response = client.get("/health/live", headers={"X-Request-ID": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


def test_unsafe_incoming_request_id_is_replaced(client):
    for unsafe in ["x" * 201, "has space", "<script>"]:
        response = client.get("/health/live", headers={"X-Request-ID": unsafe})

        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_each_request_is_logged_once_with_its_fields(client, caplog):
    caplog.set_level(logging.INFO, logger="app.access")

    response = client.get("/books", params={"title": "secret"})

    [record] = access_records(caplog)
    assert record.fields == {
        "method": "GET",
        "path": "/books",  # without the query string
        "status": 200,
        "duration_ms": record.fields["duration_ms"],
    }
    assert record.fields["duration_ms"] >= 0
    assert record.request_id == response.headers["x-request-id"]


def test_unexpected_error_is_logged_as_500(caplog):
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    caplog.set_level(logging.INFO, logger="app.access")
    TestClient(app, raise_server_exceptions=False).get("/boom")

    [record] = access_records(caplog)
    assert record.fields["status"] == 500


def test_successful_health_checks_are_not_logged(client, caplog, unreachable_db):
    caplog.set_level(logging.INFO, logger="app.access")

    client.get("/health/live")  # 200
    client.get("/health/ready")  # 503

    assert [r.fields["path"] for r in access_records(caplog)] == ["/health/ready"]
