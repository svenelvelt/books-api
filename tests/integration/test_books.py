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


def test_get_book_returns_book(client, insert_book):
    created = datetime(2017, 1, 12, tzinfo=UTC)
    book = insert_book(created_at=created, updated_at=created)
    author = book["authors"][0]

    response = client.get(f"/books/{book['_id']}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(book["_id"]),
        "title": book["title"],
        "publisher": book["publisher"],
        "authors": [{"id": str(author["id"]), "name": author["name"]}],
        "pages": book["pages"],
        "tags": book["tags"],
        "created_at": "2017-01-12T00:00:00Z",
        "updated_at": "2017-01-12T00:00:00Z",
    }


def test_list_books_paginates_in_insertion_order(client, insert_book):
    for title in ["A", "B", "C"]:
        insert_book(title=title)

    first = client.get("/books", params={"page": 1, "limit": 2})
    second = client.get("/books", params={"page": 2, "limit": 2})

    assert first.status_code == 200
    assert [book["title"] for book in first.json()["items"]] == ["A", "B"]
    assert [book["title"] for book in second.json()["items"]] == ["C"]
    assert {k: v for k, v in second.json().items() if k != "items"} == {
        "total": 3,
        "page": 2,
        "limit": 2,
    }


def test_create_book_embeds_authors(client, mongo_db, insert_author):
    author = insert_author(name="Mark Lutz")

    response = client.post(
        "/books",
        json={
            "title": "Learning Python",
            "publisher": "O'Reilly Media",
            "author_ids": [str(author["_id"])],
            "pages": 1648,
            "tags": ["Python"],
        },
    )

    assert response.status_code == 201
    book = response.json()
    assert book["authors"] == [{"id": str(author["_id"]), "name": "Mark Lutz"}]
    assert mongo_db.books.find_one()["authors"][0]["id"] == author["_id"]
    assert book["created_at"] == book["updated_at"]
    assert client.get(f"/books/{book['id']}").json() == book


def test_create_book_with_unknown_author_returns_422(client, mongo_db):
    unknown = ObjectId()
    response = client.post(
        "/books",
        json={"title": "x", "publisher": "y", "pages": 1, "author_ids": [str(unknown)]},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": f"Unknown author ids: {unknown}"}
    assert mongo_db.books.count_documents({}) == 0
