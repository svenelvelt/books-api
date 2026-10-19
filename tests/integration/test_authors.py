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
