from bson import ObjectId

from tests.helpers import assert_error


def test_author_books_returns_only_that_authors_books(
    client, insert_author, insert_book
):
    mark = insert_author(name="Mark Lutz")
    mark_ref = {"id": mark["_id"], "name": "Mark Lutz"}
    insert_book(title="Learning Python", authors=[mark_ref])
    insert_book(
        title="Fluent Python", authors=[{"id": ObjectId(), "name": "Luciano Ramalho"}]
    )
    insert_book(title="Programming Python", authors=[mark_ref])

    response = client.get(f"/authors/{mark['_id']}/books")

    assert response.status_code == 200
    body = response.json()
    assert [b["title"] for b in body["items"]] == [
        "Learning Python",
        "Programming Python",
    ]
    assert body["total"] == 2


def test_unknown_author_returns_404(client):
    response = client.get(f"/authors/{ObjectId()}/books")
    assert_error(response, 404, "author_not_found")


def test_author_without_books_returns_empty_page(client, insert_author):
    author = insert_author()

    response = client.get(f"/authors/{author['_id']}/books")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_co_authored_book_is_listed_for_each_author(client, insert_author, insert_book):
    harry = insert_author(name="Harry Percival")
    bob = insert_author(name="Bob Gregory")
    insert_book(
        title="Architecture Patterns",
        authors=[
            {"id": harry["_id"], "name": "Harry Percival"},
            {"id": bob["_id"], "name": "Bob Gregory"},
        ],
    )

    for author in (harry, bob):
        response = client.get(f"/authors/{author['_id']}/books")
        titles = [book["title"] for book in response.json()["items"]]
        assert titles == ["Architecture Patterns"]


def test_author_books_with_invalid_id_returns_422(client):
    response = client.get("/authors/invalid_id/books")

    error = assert_error(response, 422, "validation_error")["errors"][0]
    assert error["loc"] == ["path", "author_id"]
