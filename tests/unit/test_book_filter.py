import re

import pytest

from app.books import build_book_filter


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"title": None, "author": None, "tags": None, "publisher": None},
        {"title": ""},
        {"publisher": ""},
    ],
)
def test_no_filters_match_everything(kwargs):
    assert build_book_filter(**kwargs) == {}


def test_title_is_a_case_insensitive_substring_match():
    assert build_book_filter(title="Python") == {
        "title": {"$regex": "Python", "$options": "i"}
    }


def test_regex_characters_are_escaped():
    pattern = build_book_filter(title="C++ (2nd ed.)")["title"]["$regex"]

    assert re.fullmatch(pattern, "C++ (2nd ed.)")
    assert not re.search(pattern, "CCC (2nd edX)")


def test_author_matches_embedded_author_names():
    assert build_book_filter(author="Mark") == {
        "authors.name": {"$regex": "Mark", "$options": "i"}
    }


def test_publisher_is_an_exact_match():
    # Exact, unlike title and author, so the publisher index can serve it.
    assert build_book_filter(publisher="O'Reilly Media") == {
        "publisher": "O'Reilly Media"
    }


def test_tags_must_all_match():
    assert build_book_filter(tags=["Python", "Learning"]) == {
        "tags": {"$all": ["Python", "Learning"]}
    }


def test_filters_combine():
    assert build_book_filter(title="Learning", author="Mark", tags=["Python"]) == {
        "title": {"$regex": "Learning", "$options": "i"},
        "authors.name": {"$regex": "Mark", "$options": "i"},
        "tags": {"$all": ["Python"]},
    }
