import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models import BookCreate, BookUpdate

AUTHOR_ID = str(ObjectId())

VALID_BOOK = {
    "title": "Learning Python",
    "publisher": "O'Reilly Media",
    "author_ids": [AUTHOR_ID],
    "pages": 1648,
    "tags": ["Python"],
}

# Rules shared by BookCreate and BookUpdate: (changes, field the error points at).
INVALID_FIELDS = [
    ({"title": ""}, "title"),
    ({"title": "   "}, "title"),
    ({"title": "x" * 501}, "title"),
    ({"publisher": "  "}, "publisher"),
    ({"pages": 0}, "pages"),
    ({"pages": -5}, "pages"),
    ({"pages": 100_001}, "pages"),
    ({"pages": 2**63}, "pages"),
    ({"pages": True}, "pages"),
    ({"pages": "12"}, "pages"),
    ({"author_ids": []}, "author_ids"),
    ({"author_ids": [AUTHOR_ID, AUTHOR_ID]}, "author_ids"),
    ({"author_ids": ["not-an-id"]}, "author_ids"),
    ({"tags": [" "]}, "tags"),
    ({"tags": ["x" * 501]}, "tags"),
    ({"titel": "Typo"}, "titel"),
]


def error_fields(exc: ValidationError) -> set:
    return {error["loc"][0] for error in exc.errors()}


def test_book_create_accepts_valid_book():
    book = BookCreate.model_validate(VALID_BOOK)

    assert book.model_dump() == VALID_BOOK


@pytest.mark.parametrize("changes, field", INVALID_FIELDS)
def test_book_create_rejects_invalid_field(changes, field):
    with pytest.raises(ValidationError) as exc:
        BookCreate.model_validate(VALID_BOOK | changes)

    assert error_fields(exc.value) == {field}


@pytest.mark.parametrize("changes, field", INVALID_FIELDS)
def test_book_update_rejects_invalid_field(changes, field):
    with pytest.raises(ValidationError) as exc:
        BookUpdate.model_validate(changes)

    assert error_fields(exc.value) == {field}


@pytest.mark.parametrize("field", ["title", "publisher", "author_ids", "pages"])
def test_book_create_requires_field(field):
    data = {key: value for key, value in VALID_BOOK.items() if key != field}

    with pytest.raises(ValidationError) as exc:
        BookCreate.model_validate(data)

    assert error_fields(exc.value) == {field}


def test_book_create_defaults_tags_to_empty():
    data = {key: value for key, value in VALID_BOOK.items() if key != "tags"}

    assert BookCreate.model_validate(data).tags == []


def test_text_fields_are_stripped():
    book = BookCreate.model_validate(
        VALID_BOOK | {"title": "  Learning Python ", "tags": [" Python "]}
    )

    assert book.title == "Learning Python"
    assert book.tags == ["Python"]


def test_duplicate_tags_are_dropped_keeping_order():
    book = BookCreate.model_validate(
        VALID_BOOK | {"tags": ["Python", "Learning", "Python"]}
    )

    assert book.tags == ["Python", "Learning"]


def test_author_ids_are_normalized_so_case_variants_count_as_duplicates():
    upper = AUTHOR_ID.upper()

    assert BookCreate.model_validate(
        VALID_BOOK | {"author_ids": [upper]}
    ).author_ids == [AUTHOR_ID]
    with pytest.raises(ValidationError):
        BookCreate.model_validate(VALID_BOOK | {"author_ids": [AUTHOR_ID, upper]})


def test_book_update_accepts_a_single_field():
    update = BookUpdate.model_validate({"pages": 10})

    assert update.model_dump(exclude_unset=True) == {"pages": 10}


@pytest.mark.parametrize("field", ["title", "publisher", "author_ids", "pages", "tags"])
def test_book_update_rejects_null(field):
    with pytest.raises(ValidationError) as exc:
        BookUpdate.model_validate({field: None})

    assert error_fields(exc.value) == {field}


def test_book_update_rejects_empty_body():
    with pytest.raises(ValidationError):
        BookUpdate.model_validate({})
