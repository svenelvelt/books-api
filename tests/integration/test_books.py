from datetime import UTC, datetime

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

def test_get_book_returns_book(client, mongo_db):
    author_id = ObjectId()
    book_id = mongo_db.books.insert_one({
        "title": "Learning Python",
        "publisher": "O'Reilly Media",
        "authors": [{"id": author_id, "name": "Mark Lutz"}],
        "pages": 1648,
        "tags": ["Python", "Development", "Learning"],
        "created_at": datetime(2017, 1, 12, tzinfo=UTC),
        "updated_at": datetime(2017, 1, 12, tzinfo=UTC),
    }).inserted_id

    response = client.get(f"/books/{book_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(book_id),
        "title": "Learning Python",
        "publisher": "O'Reilly Media",
        "authors": [{"id": str(author_id), "name": "Mark Lutz"}],
        "pages": 1648,
        "tags": ["Python", "Development", "Learning"],
        "created_at": "2017-01-12T00:00:00Z",
        "updated_at": "2017-01-12T00:00:00Z",
    }

def test_create_book_embeds_authors(client, mongo_db):
    author_id = mongo_db.authors.insert_one({"name": "Mark Lutz", "birth_date": None}).inserted_id

    response = client.post("/books", json={
        "title": "Learning Python",
        "publisher": "O'Reilly Media",
        "author_ids": [str(author_id)],
        "pages": 1648,
        "tags": ["Python"],
    })

    assert response.status_code == 201
    book = response.json()
    assert book["authors"] == [{"id": str(author_id), "name": "Mark Lutz"}]
    assert book["created_at"] == book["updated_at"]
    assert client.get(f"/books/{book['id']}").json() == book
