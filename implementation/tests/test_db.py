from __future__ import annotations

import pytest

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = create_database(tmp_path / "lab.db")
    return SQLiteAdapter(db_path)


def test_search_filters_ordering_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters={"cohort": "A1"},
        columns=["id", "name", "cohort"],
        order_by="name",
        limit=1,
        offset=0,
    )

    assert result["count"] == 1
    assert result["rows"][0]["name"] == "An Nguyen"
    assert result["rows"][0]["cohort"] == "A1"


def test_search_supports_comparison_filter(adapter):
    result = adapter.search(
        "enrollments",
        filters=[{"column": "score", "operator": ">=", "value": 90}],
        columns=["student_id", "course_id", "score"],
        order_by="score",
        descending=True,
    )

    assert [row["score"] for row in result["rows"]] == [95.0, 93.0, 91.0]


def test_insert_returns_inserted_payload(adapter):
    result = adapter.insert(
        "students",
        {
            "name": "Lan Hoang",
            "email": "lan.hoang@example.edu",
            "cohort": "A3",
            "status": "active",
        },
    )

    assert result["inserted"]["id"] > 0
    assert result["inserted"]["email"] == "lan.hoang@example.edu"


def test_aggregate_count_by_group(adapter):
    result = adapter.aggregate("students", "count", group_by="cohort")

    assert {"group_key": "A1", "value": 2} in result["rows"]
    assert {"group_key": "B1", "value": 2} in result["rows"]


def test_aggregate_average(adapter):
    result = adapter.aggregate("enrollments", "avg", column="score")

    assert round(result["rows"][0]["value"], 2) == 85.56


def test_schema_lists_columns(adapter):
    schema = adapter.get_database_schema()

    assert "students" in schema
    assert any(column["name"] == "cohort" for column in schema["students"])


@pytest.mark.parametrize(
    "operation",
    [
        lambda db: db.search("missing_table"),
        lambda db: db.search("students", columns=["missing_column"]),
        lambda db: db.search("students", filters=[{"column": "cohort", "operator": "regex", "value": "A"}]),
        lambda db: db.insert("students", {}),
        lambda db: db.aggregate("students", "median", column="id"),
        lambda db: db.aggregate("students", "avg", column="name"),
    ],
)
def test_invalid_requests_raise_clear_validation_errors(adapter, operation):
    with pytest.raises(ValidationError) as exc_info:
        operation(adapter)

    assert str(exc_info.value)
