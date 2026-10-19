from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import create_app

# These pin the full error envelope once. Other tests only check status and code.


def test_domain_error_shape(client):
    response = client.get(f"/books/{ObjectId()}")

    assert response.json() == {"code": "book_not_found", "detail": "Book not found"}


def test_validation_error_shape(client):
    response = client.get("/books/invalid_id")

    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "detail": "Request validation failed",
        "errors": [
            {"loc": ["path", "book_id"], "msg": "Value error, Invalid ObjectId"}
        ],
    }


def test_unknown_route_uses_error_shape(client):
    response = client.get("/nope")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "detail": "Not Found"}


def test_unexpected_error_returns_500_without_leaking_details():
    app = create_app()

    @app.get("/boom")
    async def boom():
        raise RuntimeError("database password is hunter2")

    # Not entering the client as a context manager skips the lifespan, so no
    # MongoDB connection is opened.
    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.json() == {"code": "internal_error", "detail": "Internal error"}
