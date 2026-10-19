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


def test_list_books_filters_by_title_case_insensitive_substring(client, insert_book):
    for title in ["Learning Python", "Fluent PYTHON", "Clean Code"]:
        insert_book(title=title)

    response = client.get("/books", params={"title": "python"})

    assert response.status_code == 200
    body = response.json()
    assert [book["title"] for book in body["items"]] == [
        "Learning Python",
        "Fluent PYTHON",
    ]
    assert body["total"] == 2


def test_list_books_filters_by_any_author_name(client, insert_book):
    insert_book(
        title="Learning Python", authors=[{"id": ObjectId(), "name": "Mark Lutz"}]
    )
    insert_book(
        title="Architecture Patterns",
        authors=[
            {"id": ObjectId(), "name": "Harry Percival"},
            {"id": ObjectId(), "name": "Bob Gregory"},
        ],
    )

    by_first = client.get("/books", params={"author": "mark"}).json()
    by_coauthor = client.get("/books", params={"author": "gregory"}).json()

    assert [book["title"] for book in by_first["items"]] == ["Learning Python"]
    assert [book["title"] for book in by_coauthor["items"]] == ["Architecture Patterns"]


def test_list_books_combines_author_and_title_filters(client, insert_book):
    mark = {"id": ObjectId(), "name": "Mark Lutz"}
    insert_book(title="Learning Python", authors=[mark])
    insert_book(title="Programming Python", authors=[mark])
    insert_book(title="Learning Go", authors=[{"id": ObjectId(), "name": "Jon Bodner"}])

    response = client.get("/books", params={"author": "Mark", "title": "Learning"})

    assert [book["title"] for book in response.json()["items"]] == ["Learning Python"]


def test_list_books_requires_all_given_tags(client, insert_book):
    insert_book(title="A", tags=["Python", "Learning"])
    insert_book(title="B", tags=["Python"])
    insert_book(title="C", tags=["Go", "Learning"])

    one_tag = client.get("/books", params={"tags": "Python"}).json()
    two_tags = client.get("/books", params={"tags": ["Python", "Learning"]}).json()

    assert [book["title"] for book in one_tag["items"]] == ["A", "B"]
    assert [book["title"] for book in two_tags["items"]] == ["A"]
    assert two_tags["total"] == 1


def test_list_books_treats_filter_input_as_literal_text(client, insert_book):
    insert_book(title="C++ Primer")
    insert_book(title="CCC")

    response = client.get("/books", params={"title": "C++"})

    assert [book["title"] for book in response.json()["items"]] == ["C++ Primer"]


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
