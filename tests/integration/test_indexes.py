import pytest
from bson import ObjectId

from app.books import build_book_filter


def test_startup_creates_book_indexes(client, mongo_db):
    keys = {
        tuple(index["key"]) for index in mongo_db.books.index_information().values()
    }

    assert {
        (("authors.id", 1), ("_id", 1)),
        (("publisher", 1), ("_id", 1)),
        (("tags", 1), ("_id", 1)),
    } <= keys


def winning_plan_stages(mongo_db, query: dict) -> list[tuple[str, str | None]]:
    # The same shape as a list endpoint: filter, sort by _id, one page.
    explain = mongo_db.command(
        "explain",
        {"find": "books", "filter": query, "sort": {"_id": 1}, "limit": 20},
        verbosity="queryPlanner",
    )
    stages = []
    plan = explain["queryPlanner"]["winningPlan"]
    plan = plan.get("queryPlan", plan)
    while plan:
        stages.append((plan["stage"], plan.get("indexName")))
        plan = plan.get("inputStage")
    return stages


@pytest.mark.parametrize(
    "query, index",
    [
        ({"authors.id": ObjectId()}, "authors.id_1__id_1"),
        (build_book_filter(publisher="Manning"), "publisher_1__id_1"),
        (build_book_filter(tags=["Python"]), "tags_1__id_1"),
    ],
)
def test_filtered_pages_come_sorted_from_the_index(
    client, mongo_db, insert_book, query, index
):
    for _ in range(5):
        insert_book()

    stages = winning_plan_stages(mongo_db, query)

    assert ("IXSCAN", index) in stages
    # A SORT stage would mean every match is fetched and sorted in memory.
    assert "SORT" not in [stage for stage, _ in stages]
