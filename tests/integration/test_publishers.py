from tests.helpers import assert_error


def test_average_pages_for_publisher(client, insert_book):
    insert_book(publisher="O'Reilly Media", pages=100)
    insert_book(publisher="O'Reilly Media", pages=201)
    insert_book(publisher="Manning", pages=1000)

    response = client.get("/publishers/O'Reilly Media/average_pages")

    assert response.status_code == 200
    assert response.json() == {
        "publisher": "O'Reilly Media",
        "average_pages": 150.5,
    }


def test_average_pages_for_unknown_publisher_returns_404(client, insert_book):
    insert_book(publisher="Manning")

    response = client.get("/publishers/Unknown Press/average_pages")

    assert_error(response, 404, "publisher_not_found")


def test_average_pages_matches_publisher_name_exactly(client, insert_book):
    insert_book(publisher="O'Reilly Media")

    response = client.get("/publishers/o'reilly media/average_pages")

    assert_error(response, 404, "publisher_not_found")


def test_average_pages_is_rounded_to_two_decimals(client, insert_book):
    for pages in [100, 100, 101]:
        insert_book(publisher="Manning", pages=pages)

    response = client.get("/publishers/Manning/average_pages")

    assert response.json()["average_pages"] == 100.33
