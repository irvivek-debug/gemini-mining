"""Idempotent backup of the ten tables that tasks 2–11 will rewrite.

Backup naming: <table>_original_20260810 in the same dataset.

Safety guarantee: if a backup already exists with a matching row count the
table is left untouched and the run is reported as SKIPPED.  This prevents a
second run after a bad load from overwriting the only good copy.
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from typing import Literal

from google.cloud import bigquery

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    BACKUP_SUFFIX,
    DATASET,
    PROJECT_ID,
    REWRITE_TABLES,
    SCHEMAS,
)

Status = Literal["CREATED", "SKIPPED", "ERROR"]


@dataclass
class BackupResult:
    table: str
    backup: str
    status: Status
    source_rows: int
    backup_rows: int
    message: str


def _row_count(client: bigquery.Client, table_ref: str) -> int:
    query = f"SELECT COUNT(*) AS n FROM `{table_ref}`"
    result = client.query(query).result()
    return next(result).n


def _table_exists(client: bigquery.Client, dataset: str, table: str) -> bool:
    try:
        client.get_table(f"{PROJECT_ID}.{dataset}.{table}")
        return True
    except Exception:
        return False


def backup_table(
    client: bigquery.Client,
    table_name: str,
    *,
    dataset: str = DATASET,
) -> BackupResult:
    """Back up a single table.  Returns a BackupResult describing the outcome."""
    backup_name = table_name + BACKUP_SUFFIX
    source_ref = f"{PROJECT_ID}.{dataset}.{table_name}"
    backup_ref = f"{PROJECT_ID}.{dataset}.{backup_name}"

    # Get source row count from the pre-captured schema profile so we don't
    # need an extra query just to learn the expected count.
    source_rows = SCHEMAS["schemas"][table_name]["num_rows"]

    if _table_exists(client, dataset, backup_name):
        backup_rows = _row_count(client, backup_ref)
        if backup_rows == source_rows:
            return BackupResult(
                table=table_name,
                backup=backup_name,
                status="SKIPPED",
                source_rows=source_rows,
                backup_rows=backup_rows,
                message=f"backup already exists with {backup_rows} rows — skipped",
            )
        # Counts mismatch — flag as error rather than silently overwriting.
        return BackupResult(
            table=table_name,
            backup=backup_name,
            status="ERROR",
            source_rows=source_rows,
            backup_rows=backup_rows,
            message=(
                f"backup exists but has {backup_rows} rows vs expected {source_rows} "
                f"— manual inspection required"
            ),
        )

    # Create the backup using a CTAS query (no DROP, no schema change).
    sql = f"CREATE TABLE `{backup_ref}` AS SELECT * FROM `{source_ref}`"
    client.query(sql).result()

    backup_rows = _row_count(client, backup_ref)
    if backup_rows != source_rows:
        return BackupResult(
            table=table_name,
            backup=backup_name,
            status="ERROR",
            source_rows=source_rows,
            backup_rows=backup_rows,
            message=(
                f"backup created but row count mismatch: "
                f"got {backup_rows}, expected {source_rows}"
            ),
        )

    return BackupResult(
        table=table_name,
        backup=backup_name,
        status="CREATED",
        source_rows=source_rows,
        backup_rows=backup_rows,
        message=f"created with {backup_rows} rows",
    )


def backup_all(
    client: bigquery.Client | None = None,
    *,
    dataset: str = DATASET,
) -> list[BackupResult]:
    """Back up all REWRITE_TABLES.  Prints a status line for each table."""
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)

    results: list[BackupResult] = []
    for table_name in REWRITE_TABLES:
        result = backup_table(client, table_name, dataset=dataset)
        tag = {"CREATED": "OK     ", "SKIPPED": "SKIPPED", "ERROR": "ERROR  "}[result.status]
        print(
            f"[{tag}] {result.table:<30} -> {result.backup}"
            f"  ({result.backup_rows} rows)  {result.message}"
        )
        results.append(result)

    errors = [r for r in results if r.status == "ERROR"]
    if errors:
        print(f"\n{len(errors)} error(s) — see above.", file=sys.stderr)
        sys.exit(1)

    print(
        f"\nDone. {sum(1 for r in results if r.status == 'CREATED')} created, "
        f"{sum(1 for r in results if r.status == 'SKIPPED')} skipped."
    )
    return results


if __name__ == "__main__":
    backup_all()
