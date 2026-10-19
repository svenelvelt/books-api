def test_startup_creates_book_indexes(client, mongo_db):
    keys = {
        tuple(index["key"]) for index in mongo_db.books.index_information().values()
    }

    assert {
        (("authors.id", 1),),
        (("publisher", 1),),
        (("tags", 1),),
    } <= keys
