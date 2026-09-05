"""The YAML is the human-owned half of the context pipeline. These tests hold it
to the only two things a machine can check: that it parses into the declared
shape, and that the columns it names are the columns BigQuery actually has.

Whether a description is TRUE is a review question, not a test question. What a
test can stop is a description attached to a column that does not exist, which
would be invisible until an agent read a prompt describing a phantom field.
"""
from __future__ import annotations

import pytest
from google.cloud import bigquery

from mining_agents.config import settings
from scripts.semantics import (
    MIN_DESCRIPTION_CHARS,
    TableSemantics,
    agent_tables,
    load_semantics,
)


@pytest.fixture(scope="module")
def semantics() -> dict[str, TableSemantics]:
    return load_semantics()


@pytest.fixture(scope="module")
def live_columns() -> dict[str, set[str]]:
    """Top-level column names per table, straight from BigQuery."""
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    sql = f"""
        SELECT table_name, field_path
        FROM `{s.project_id}.{s.dataset}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`
        WHERE NOT CONTAINS_SUBSTR(field_path, '.')
    """
    found: dict[str, set[str]] = {}
    for row in client.query(sql).result():
        found.setdefault(f"{s.dataset}.{row['table_name']}", set()).add(row["field_path"])
    assert found, "INFORMATION_SCHEMA returned no columns at all; the rest of this file would pass vacuously"
    return found


def test_agent_tables_is_the_25_table_surface():
    tables = agent_tables()
    assert len(tables) == 25, (
        f"the catalog now declares {len(tables)} distinct tables, not 25. "
        "The plan's six MECE sections were sized against 25 — re-derive them "
        f"before continuing. Tables: {sorted(tables)}"
    )
    for table in tables:
        assert table.startswith("mining_data."), (
            f"{table!r} is not in mining_data; the annotate and build scripts "
            "assume a single dataset"
        )


def test_yaml_parses_and_declares_only_agent_tables(semantics):
    assert semantics, "load_semantics() returned nothing"
    unknown = set(semantics) - agent_tables()
    assert not unknown, f"described but read by no agent: {sorted(unknown)}"


def test_every_described_column_exists_in_bigquery(semantics, live_columns):
    assert semantics, "no tables described yet; this test would pass vacuously"
    for table, entry in semantics.items():
        assert table in live_columns, f"{table} is described but not in BigQuery"
        phantom = set(entry.columns) - live_columns[table]
        assert not phantom, (
            f"{table}: described columns that do not exist: {sorted(phantom)}"
        )


def test_each_described_table_is_described_completely(semantics, live_columns):
    """Partial coverage of a table is worse than none: the agent cannot tell
    which of the columns in front of it were reviewed."""
    assert semantics, "no tables described yet; this test would pass vacuously"
    for table, entry in semantics.items():
        missing = live_columns[table] - set(entry.columns)
        assert not missing, f"{table}: columns present in BigQuery but undescribed: {sorted(missing)}"


_LONG = "a description comfortably over the minimum length"
_SHORT = "x" * (MIN_DESCRIPTION_CHARS - 1)


def test_a_short_table_description_is_refused():
    # The column description here is deliberately valid, so the table
    # description is the only thing that can raise. The original form of this
    # test passed a table description of exactly MIN_DESCRIPTION_CHARS -- which
    # the validator accepts, the bound being `<` -- next to a short column, and
    # so proved nothing about the table description at all.
    with pytest.raises(ValueError):
        TableSemantics.model_validate(
            {"description": _SHORT, "columns": {"a": _LONG}}
        )


def test_a_short_column_description_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate(
            {"description": _LONG, "columns": {"a": _SHORT}}
        )


def test_a_description_of_exactly_the_minimum_length_is_accepted():
    # Pins the boundary the two tests above straddle, so that tightening the
    # bound from `<` to `<=` cannot pass silently.
    at_bound = "x" * MIN_DESCRIPTION_CHARS
    table = TableSemantics.model_validate(
        {"description": at_bound, "columns": {"a": at_bound}}
    )
    assert table.description == at_bound
    assert table.columns["a"] == at_bound


def test_a_table_with_no_columns_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate({"description": "y" * 40, "columns": {}})


def test_a_time_column_naming_a_column_that_does_not_exist_is_refused():
    with pytest.raises(ValueError):
        TableSemantics.model_validate({
            "description": "y" * 40,
            "columns": {"observed_at": "z" * 40},
            "time_column": "recorded_at",
        })
