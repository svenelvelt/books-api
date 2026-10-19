from app.seed import seed


def test_seed_loads_the_sample_books_with_their_authors(client, mongo_db):
    assert seed(mongo_db) is True

    books = client.get("/books").json()["items"]
    assert [
        (book["title"], [author["name"] for author in book["authors"]])
        for book in books
    ] == [
        ("Learning Python", ["Mark Lutz"]),
        ("Architecture Patterns with Python", ["Harry Percival", "Bob Gregory"]),
    ]
    authors = client.get("/authors").json()["items"]
    assert [(author["name"], author["book_count"]) for author in authors] == [
        ("Mark Lutz", 1),
        ("Harry Percival", 1),
        ("Bob Gregory", 1),
    ]


def test_seed_keeps_the_sample_timestamps_in_utc(client, mongo_db):
    seed(mongo_db)

    book = client.get("/books", params={"title": "Learning Python"}).json()["items"][0]
    # The sample says 2017-01-12T00:00:00+03:00.
    assert book["created_at"] == "2017-01-11T21:00:00Z"
    assert book["updated_at"] == "2017-01-11T21:00:00Z"


def test_seed_does_nothing_when_data_exists(mongo_db, insert_author):
    insert_author(name="Existing Author")

    assert seed(mongo_db) is False
    assert mongo_db.books.count_documents({}) == 0
    assert mongo_db.authors.count_documents({}) == 1


def test_seed_twice_does_not_duplicate(mongo_db):
    seed(mongo_db)
    seed(mongo_db)

    assert mongo_db.books.count_documents({}) == 2
    assert mongo_db.authors.count_documents({}) == 3
