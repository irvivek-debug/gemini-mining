"""BigQuery load and rollback for the ten regenerated tables.

Inputs are the parquet files the Task 2-7 generators wrote to
``data/generated/<table_name>.parquet``.  Nothing here regenerates data and
nothing here reads a live rewritten table: the generators calibrate against the
frozen ``*_original_20260810`` backups, and this module is what overwrites the
live copies, so a generator that read a live table would silently stop being
reproducible after the first apply.

Load order
----------
``LOAD_ORDER`` is dimensions, then facts, then edges.  The tiers are not a
judgement call; they are read off the deployed property-graph DDL
(``INFORMATION_SCHEMA.PROPERTY_GRAPHS``), and ``tests/test_load.py`` re-derives
them from BigQuery and fails if this file drifts:

* ``EDGE_TABLES``      - rewritten tables that some property graph declares in
  its ``EDGE TABLES`` clause: ``erp_work_orders`` (HAS_WORK_ORDER, Asset ->
  WorkOrder) and ``fatigue_logs_node`` (LOGGED_FOR, FatigueLog -> Operator).
* ``DIMENSION_TABLES`` - rewritten tables that appear only as ``NODE TABLES``
  and are pointed at by an edge: ``inventory_levels`` (SparePart, the
  destination of REPLACED_PART and BID_FOR).
* ``FACT_TABLES``      - everything else: standalone measurement tables that no
  graph references.

Within each tier the order is the ``config.REWRITE_TABLES`` order.  The list is
a literal Python list built by iterating that list; no set or dict iteration
order is involved, and no RNG is seeded here, so the order is byte-stable
across processes regardless of ``PYTHONHASHSEED``.

Schema, partitioning and clustering
-----------------------------------
Every load passes an explicit JSON schema (``bq load --schema``) taken from
``data/profile/schemas.json``, which was captured from the live tables before
any rewrite.  That pins column names, types, modes and *ordinal position*
independently of the parquet file's own field order.

Partitioning and clustering also come from the profile, not from the backups.
The Task-1 backups were made with ``CREATE TABLE ... AS SELECT *``, which copies
rows but drops the partition and cluster specs, so every ``*_original_20260810``
table is unpartitioned.  Comparing a loaded table's partitioning against its
backup would therefore "verify" the spec away.  Column-level comparison
(``INFORMATION_SCHEMA.COLUMNS``) is still done against the backup, since CTAS
does preserve columns.

Rollback
--------
``python data/generator/load.py --rollback`` restores every live table from its
``*_original_20260810`` backup.  The mechanism is ``TRUNCATE TABLE`` followed by
an explicit-column ``INSERT ... SELECT``: the live table object is never
dropped, so its partition spec, cluster spec and the property-graph bindings
that name it all survive.  ``run_all.py --dry-run`` executes this exact code
path against a throwaway staging table to prove it works.

No function in this module can touch a backup: :func:`drop_table` refuses any
name that does not end in ``STAGING_SUFFIX``, and the backups are only ever
read.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from google.cloud import bigquery

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (  # noqa: E402
    BACKUP_SUFFIX,
    DATASET,
    PROJECT_ID,
    REWRITE_TABLES,
    SCHEMAS,
)

#: Suffix for the throwaway tables `--dry-run` writes to.  Distinct from
#: BACKUP_SUFFIX so the two can never be confused by a prefix/suffix test.
STAGING_SUFFIX = "_staging_20260810"

GENERATED_DIR = Path(__file__).resolve().parent.parent / "generated"

# --- Load tiers (see module docstring; verified against the deployed graphs) --

EDGE_TABLES = [t for t in REWRITE_TABLES
               if t in ("erp_work_orders", "fatigue_logs_node")]
DIMENSION_TABLES = [t for t in REWRITE_TABLES if t in ("inventory_levels",)]
FACT_TABLES = [t for t in REWRITE_TABLES
               if t not in EDGE_TABLES and t not in DIMENSION_TABLES]

LOAD_ORDER: list[str] = DIMENSION_TABLES + FACT_TABLES + EDGE_TABLES


@dataclass
class TableCheck:
    """Outcome of loading and verifying one table."""

    table: str
    target: str
    rows_expected: int
    rows_loaded: int
    schema_ok: bool
    partitioning_ok: bool
    content_ok: bool
    message: str

    @property
    def ok(self) -> bool:
        return (
            self.rows_loaded == self.rows_expected
            and self.schema_ok
            and self.partitioning_ok
            and self.content_ok
        )


# ---------------------------------------------------------------------------
# Naming helpers
# ---------------------------------------------------------------------------


def parquet_path(table: str) -> Path:
    return GENERATED_DIR / f"{table}.parquet"


def backup_name(table: str) -> str:
    return table + BACKUP_SUFFIX


def staging_name(table: str) -> str:
    return table + STAGING_SUFFIX


def table_ref(name: str) -> str:
    """Fully-qualified `project.dataset.table` for SQL interpolation."""
    return f"{PROJECT_ID}.{DATASET}.{name}"


def bq_target(name: str) -> str:
    """`project:dataset.table` — the form the bq CLI wants."""
    return f"{PROJECT_ID}:{DATASET}.{name}"


# ---------------------------------------------------------------------------
# Profile lookups
# ---------------------------------------------------------------------------


def schema_fields(table: str) -> list[dict]:
    """Column list for `table` exactly as captured before any rewrite."""
    return SCHEMAS["schemas"][table]["columns"]


def column_names(table: str) -> list[str]:
    return [c["name"] for c in schema_fields(table)]


def partition_spec(table: str) -> tuple[str | None, str | None]:
    profile = SCHEMAS["schemas"][table]
    return profile["partitioning"], profile["partition_type"]


def clustering_spec(table: str) -> list[str] | None:
    return SCHEMAS["schemas"][table]["clustering"]


def write_schema_file(table: str, directory: Path) -> Path:
    """Write the profile schema as a bq-CLI JSON schema file."""
    path = directory / f"{table}.schema.json"
    path.write_text(json.dumps(schema_fields(table), indent=1))
    return path


# ---------------------------------------------------------------------------
# bq load
# ---------------------------------------------------------------------------


def _bq_binary() -> str:
    found = shutil.which("bq")
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / "bq"
    if fallback.exists():
        return str(fallback)
    raise RuntimeError("bq CLI not found on PATH or in ~/.local/bin")


def bq_load_command(table: str, target: str, schema_file: Path) -> list[str]:
    """Argv for `bq load`, with the profile's partitioning/clustering flags.

    Split out from :func:`load_table` so the flag construction can be unit
    tested without touching BigQuery.
    """
    argv = [
        _bq_binary(),
        "load",
        "--source_format=PARQUET",
        "--parquet_enable_list_inference=true",
        "--replace",
        f"--schema={schema_file}",
    ]
    field, ptype = partition_spec(table)
    if field is not None:
        argv.append(f"--time_partitioning_field={field}")
        argv.append(f"--time_partitioning_type={ptype}")
    clustering = clustering_spec(table)
    if clustering:
        argv.append("--clustering_fields=" + ",".join(clustering))
    argv.append(bq_target(target))
    argv.append(str(parquet_path(table)))
    return argv


def load_table(table: str, target: str, schema_dir: Path) -> None:
    """Load `data/generated/<table>.parquet` into `target`, replacing its rows.

    `--replace` is a WRITE_TRUNCATE load: it swaps the contents of an existing
    table rather than dropping it, so property-graph bindings survive.
    """
    schema_file = write_schema_file(table, schema_dir)
    argv = bq_load_command(table, target, schema_file)
    proc = subprocess.run(argv, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"bq load failed for {target} (exit {proc.returncode})\n"
            f"argv: {' '.join(argv)}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def parquet_row_count(table: str) -> int:
    import pyarrow.parquet as pq

    return pq.ParquetFile(parquet_path(table)).metadata.num_rows


def repeated_columns(table: str) -> list[str]:
    """Names of REPEATED (array) columns in the profile schema for `table`."""
    return [
        c["name"]
        for c in schema_fields(table)
        if c.get("mode") == "REPEATED"
    ]


def parquet_array_cardinality(table: str, column: str) -> int:
    """Total number of elements across all rows in a REPEATED parquet column."""
    import pyarrow.parquet as pq

    col = pq.read_table(parquet_path(table), columns=[column]).column(column)
    return sum(len(row.as_py()) for row in col)


def bq_array_cardinality(client: bigquery.Client, name: str, column: str) -> int:
    """Total number of elements across all rows of a REPEATED BigQuery column."""
    sql = f"SELECT SUM(ARRAY_LENGTH(`{column}`)) AS n FROM `{table_ref(name)}`"
    row = next(iter(client.query(sql).result()))
    return row.n or 0


def check_repeated_content(
    client: bigquery.Client, table: str, loaded: str
) -> tuple[bool, str]:
    """For every REPEATED column: assert total array cardinality matches the parquet.

    A table can load with perfect row count and schema while its arrays are
    silently empty (e.g. missing --parquet_enable_list_inference).  This check
    catches that class of bug by comparing element counts, not just row counts.
    Returns (ok, message).  If the table has no REPEATED columns, returns True.
    """
    cols = repeated_columns(table)
    if not cols:
        return True, "no REPEATED columns"
    problems = []
    details = []
    for col in cols:
        want = parquet_array_cardinality(table, col)
        got = bq_array_cardinality(client, loaded, col)
        details.append(f"{col}: bq={got} parquet={want}")
        if got != want:
            problems.append(
                f"{col} has {got} elements in BigQuery but {want} in parquet"
            )
    if problems:
        return False, "; ".join(problems)
    return True, "array cardinality ok (" + ", ".join(details) + ")"


def row_count(client: bigquery.Client, name: str) -> int:
    sql = f"SELECT COUNT(*) AS n FROM `{table_ref(name)}`"
    return next(iter(client.query(sql).result())).n


def information_schema_columns(
    client: bigquery.Client, name: str
) -> list[tuple[str, str, int, str]]:
    """(column_name, data_type, ordinal_position, is_nullable) for `name`.

    This is the tuple the brief calls "byte-identical schema".  It deliberately
    excludes `is_partitioning_column` and `clustering_ordinal_position`, which
    differ between a partitioned table and its CTAS backup by construction;
    those are checked separately in :func:`check_partitioning`.
    """
    sql = f"""
        SELECT column_name, data_type, ordinal_position, is_nullable
        FROM `{PROJECT_ID}.{DATASET}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = @table
        ORDER BY ordinal_position
    """
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("table", "STRING", name)
            ]
        ),
    )
    return [
        (r.column_name, r.data_type, r.ordinal_position, r.is_nullable)
        for r in job.result()
    ]


def check_schema_against_backup(
    client: bigquery.Client, table: str, loaded: str
) -> tuple[bool, str]:
    got = information_schema_columns(client, loaded)
    want = information_schema_columns(client, backup_name(table))
    if not want:
        return False, f"backup {backup_name(table)} has no columns — missing?"
    if got == want:
        return True, f"{len(got)} columns identical to {backup_name(table)}"
    return False, f"schema differs from backup:\n  got  {got}\n  want {want}"


def check_partitioning(
    client: bigquery.Client, table: str, loaded: str
) -> tuple[bool, str]:
    """Partitioning/clustering of `loaded` vs the pre-rewrite profile."""
    meta = client.get_table(table_ref(loaded))
    want_field, want_type = partition_spec(table)
    want_cluster = clustering_spec(table)

    got_field = meta.time_partitioning.field if meta.time_partitioning else None
    got_type = meta.time_partitioning.type_ if meta.time_partitioning else None
    got_cluster = list(meta.clustering_fields) if meta.clustering_fields else None

    problems = []
    if (got_field, got_type) != (want_field, want_type):
        problems.append(
            f"partitioning {got_field}/{got_type} != profile {want_field}/{want_type}"
        )
    if got_cluster != (list(want_cluster) if want_cluster else None):
        problems.append(f"clustering {got_cluster} != profile {want_cluster}")
    if problems:
        return False, "; ".join(problems)
    return True, f"partition={got_field}/{got_type} cluster={got_cluster}"


def content_digest(client: bigquery.Client, name: str) -> tuple[int, str]:
    """(row count, order-independent MD5 of the whole table).

    Used to prove a rollback reproduced its source exactly rather than merely
    landing on the right row count.
    """
    sql = f"""
        SELECT COUNT(*) AS n,
               TO_HEX(MD5(COALESCE(STRING_AGG(j, '\\n' ORDER BY j), ''))) AS h
        FROM (SELECT TO_JSON_STRING(t) AS j FROM `{table_ref(name)}` t)
    """
    row = next(iter(client.query(sql).result()))
    return row.n, row.h


def load_and_verify(
    client: bigquery.Client, table: str, target: str, schema_dir: Path
) -> TableCheck:
    expected = parquet_row_count(table)
    load_table(table, target, schema_dir)
    loaded = row_count(client, target)
    schema_ok, schema_msg = check_schema_against_backup(client, table, target)
    part_ok, part_msg = check_partitioning(client, table, target)
    content_ok, content_msg = check_repeated_content(client, table, target)
    return TableCheck(
        table=table,
        target=target,
        rows_expected=expected,
        rows_loaded=loaded,
        schema_ok=schema_ok,
        partitioning_ok=part_ok,
        content_ok=content_ok,
        message=f"{schema_msg}; {part_msg}; {content_msg}",
    )


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


def restore_sql(table: str, target: str) -> str:
    """Multi-statement script restoring `target` from `table`'s frozen backup.

    TRUNCATE + INSERT rather than CREATE OR REPLACE: the table object survives,
    so its partition spec, cluster spec and property-graph bindings do too.
    The column list is spelled out in profile order so the restore cannot
    silently reorder columns.
    """
    cols = ", ".join(f"`{c}`" for c in column_names(table))
    return (
        f"TRUNCATE TABLE `{table_ref(target)}`;\n"
        f"INSERT INTO `{table_ref(target)}` ({cols})\n"
        f"SELECT {cols} FROM `{table_ref(backup_name(table))}`;\n"
    )


def restore_table(client: bigquery.Client, table: str, target: str) -> None:
    client.query(restore_sql(table, target)).result()


def rollback_all(client: bigquery.Client | None = None) -> None:
    """Restore all ten live tables from their frozen backups."""
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)
    for table in LOAD_ORDER:
        restore_table(client, table, table)
        n, _ = content_digest(client, table)
        backup_n, _ = content_digest(client, backup_name(table))
        status = "OK   " if n == backup_n else "ERROR"
        print(f"[{status}] {table:<28} restored {n} rows from {backup_name(table)}")
        if n != backup_n:
            raise RuntimeError(
                f"{table}: restored {n} rows but backup has {backup_n}"
            )
    print(f"\nRolled back {len(LOAD_ORDER)} tables from {BACKUP_SUFFIX} backups.")


# ---------------------------------------------------------------------------
# Staging lifecycle
# ---------------------------------------------------------------------------


def drop_table(client: bigquery.Client, name: str) -> None:
    """Drop a staging table.

    Refuses anything that is not a staging table.  This is the only delete in
    the module, and it exists so that no code path — present or future — can
    remove a live table or the only copy of the pre-rewrite data.
    """
    if not name.endswith(STAGING_SUFFIX):
        raise ValueError(
            f"refusing to drop {name!r}: only *{STAGING_SUFFIX} tables may be "
            "dropped by this module"
        )
    client.delete_table(table_ref(name), not_found_ok=True)


def live_fingerprints(client: bigquery.Client) -> dict[str, tuple[int, int]]:
    """(num_rows, last-modified epoch ms) for the ten live tables and backups.

    Snapshotted either side of a dry run to prove it touched nothing live.
    """
    out: dict[str, tuple[int, int]] = {}
    for table in LOAD_ORDER:
        for name in (table, backup_name(table)):
            meta = client.get_table(table_ref(name))
            out[name] = (meta.num_rows, int(meta.modified.timestamp() * 1000))
    return out


# ---------------------------------------------------------------------------
# Dry run / apply
# ---------------------------------------------------------------------------


def _print_check(check: TableCheck) -> None:
    tag = "OK   " if check.ok else "ERROR"
    print(
        f"[{tag}] {check.table:<28} -> {check.target:<44} "
        f"{check.rows_loaded}/{check.rows_expected} rows  {check.message}"
    )


def _require_backups(client: bigquery.Client) -> None:
    """Refuse to apply unless every rollback source is present and populated."""
    for table in LOAD_ORDER:
        name = backup_name(table)
        expected = SCHEMAS["schemas"][table]["num_rows"]
        try:
            meta = client.get_table(table_ref(name))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"rollback source {name} is missing ({exc}); refusing to apply"
            ) from exc
        if meta.num_rows != expected:
            raise RuntimeError(
                f"rollback source {name} has {meta.num_rows} rows, profile says "
                f"{expected}; refusing to apply"
            )


def prove_rollback(client: bigquery.Client, table: str) -> None:
    """Run the real rollback against a staging table and check it end to end.

    The staging table already holds the *regenerated* rows, which differ from
    the backup.  Truncating it and running :func:`restore_table` must reproduce
    the backup byte for byte — checked by row count and by an order-independent
    content digest, so a no-op restore (0 rows) or a wrong-source restore both
    fail.
    """
    staging = staging_name(table)
    before_n, before_h = content_digest(client, staging)
    backup_n, backup_h = content_digest(client, backup_name(table))
    print(
        f"  staging {staging} holds {before_n} regenerated rows "
        f"(digest {before_h[:12]}…)"
    )
    print(
        f"  backup  {backup_name(table)} holds {backup_n} rows "
        f"(digest {backup_h[:12]}…)"
    )
    if before_h == backup_h:
        raise RuntimeError(
            f"rollback proof is vacuous: {staging} already equals its backup, "
            "so a no-op restore would pass"
        )

    client.query(f"TRUNCATE TABLE `{table_ref(staging)}`").result()
    emptied, _ = content_digest(client, staging)
    if emptied != 0:
        raise RuntimeError(f"could not empty {staging} before the rollback proof")

    restore_table(client, table, staging)

    after_n, after_h = content_digest(client, staging)
    if (after_n, after_h) != (backup_n, backup_h):
        raise RuntimeError(
            f"rollback did not reproduce the backup: {staging} is "
            f"{after_n} rows/{after_h}, backup is {backup_n} rows/{backup_h}"
        )
    print(
        f"  rollback restored {after_n} rows, digest {after_h[:12]}… "
        f"— matches {backup_name(table)}"
    )


def dry_run(client: bigquery.Client | None = None) -> list[TableCheck]:
    """Load every table into a `*_staging_` copy, verify, prove rollback, clean up.

    Never modifies, replaces or deletes a live table or a backup — asserted by
    fingerprinting both sets either side of the run.
    """
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)

    before = live_fingerprints(client)
    checks: list[TableCheck] = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            schema_dir = Path(tmp)
            for table in LOAD_ORDER:
                check = load_and_verify(
                    client, table, staging_name(table), schema_dir
                )
                _print_check(check)
                checks.append(check)

        failed = [c for c in checks if not c.ok]
        if failed:
            raise RuntimeError(
                f"{len(failed)} staging table(s) failed verification: "
                + ", ".join(c.table for c in failed)
            )

        print("\nProving rollback against a throwaway staging table:")
        prove_rollback(client, LOAD_ORDER[0])
    finally:
        for table in LOAD_ORDER:
            drop_table(client, staging_name(table))
        print(f"\nDropped {len(LOAD_ORDER)} staging tables.")

    after = live_fingerprints(client)
    if before != after:
        changed = sorted(k for k in before if before[k] != after[k])
        raise RuntimeError(
            f"dry run modified live or backup tables: {changed}"
        )
    print(
        f"Verified untouched: {len(after)} live and backup tables have identical "
        "row counts and last-modified times."
    )
    return checks


def apply(client: bigquery.Client | None = None) -> list[TableCheck]:
    """Load every table into its live target, then verify schema and partitioning."""
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)

    _require_backups(client)
    backups_before = {
        backup_name(t): content_digest(client, backup_name(t)) for t in LOAD_ORDER
    }

    checks: list[TableCheck] = []
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp)
        for table in LOAD_ORDER:
            check = load_and_verify(client, table, table, schema_dir)
            _print_check(check)
            checks.append(check)

    failed = [c for c in checks if not c.ok]
    if failed:
        raise RuntimeError(
            f"{len(failed)} table(s) failed verification: "
            + ", ".join(c.table for c in failed)
            + f"\nRoll back with: python {Path(__file__).name} --rollback"
        )

    backups_after = {
        backup_name(t): content_digest(client, backup_name(t)) for t in LOAD_ORDER
    }
    if backups_before != backups_after:
        raise RuntimeError("apply modified a frozen backup — this must never happen")
    print(f"\nBackups unchanged: {len(backups_after)} *{BACKUP_SUFFIX} tables intact.")
    return checks


# ---------------------------------------------------------------------------
# Task 2b — brand-new tables (contracts, warranty, capital/plan)
#
# These ten tables have no `*_original_20260810` backup because they never
# existed before Task 2b: there is nothing to roll back to except "the table
# is empty," which is not what REWRITE_TABLES / LOAD_ORDER / apply() /
# dry_run() mean by "rewrite." Rather than force them through that pipeline
# (which would need a fabricated zero-row backup and profiled partition specs
# that were never real), they get their own straight load using the exact
# same primitives (`write_schema_file`, `bq_load_command`, `load_table`) —
# "the existing loader," just without the backup/rollback contract that does
# not apply to a table with no prior state.
# ---------------------------------------------------------------------------

NEW_TABLES_2B: list[str] = [
    "contracts",
    "contract_transactions",
    "rebate_claims",
    "invoices",
    "warranty_entitlements",
    "warranty_claims",
    "plan_versions",
    "plan_assumptions",
    "plan_scenarios",
    "capital_options",
    # Added post-launch (Task 2b defect fix): the dense multi-year price curve
    # plan_assumptions.assumed_value samples from for the contained-metal
    # metric. See capital.py's module docstring — six quarterly points alone
    # cannot carry a measurable autocorrelation, so the deck ships as its own
    # table and R12 in tests/test_realism.py measures it directly.
    "contained_metal_price_deck",
]


def load_new_tables_2b(client: bigquery.Client | None = None) -> dict[str, int]:
    """Load every Task 2b table straight into its live name; return row counts."""
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)
    counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory() as tmp:
        schema_dir = Path(tmp)
        for table in NEW_TABLES_2B:
            load_table(table, table, schema_dir)
            counts[table] = row_count(client, table)
            expected = parquet_row_count(table)
            tag = "OK   " if counts[table] == expected else "ERROR"
            print(f"[{tag}] {table:<24} {counts[table]}/{expected} rows")
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Roll the ten regenerated tables back to their frozen backups."
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help=f"restore every live table from its *{BACKUP_SUFFIX} backup",
    )
    args = parser.parse_args(argv)
    if not args.rollback:
        parser.error("nothing to do; pass --rollback (loading is run_all.py's job)")
    rollback_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
