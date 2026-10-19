from bson import ObjectId


def test_get_unknown_book_return_404(client):
    response = client.get(f"/books/{ObjectId()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Book not found"}


def test_get_invalid_book_id_return_422(client):
    response = client.get("/books/invalid_id")

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["path", "book_id"]
    assert "ObjectId" in error["msg"]
