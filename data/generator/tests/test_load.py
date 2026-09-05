"""Tests for data/generator/load.py and run_all.py (Task 8 — the loader).

Two halves.

Offline: the load order covers every rewritten table exactly once and is stable
across processes; `bq load` is invoked with an explicit schema and the profile's
partitioning/clustering flags; the rollback SQL truncates and re-inserts rather
than dropping; and nothing but a `*_staging_` table can be deleted.

Against BigQuery, describing the state after `run_all.py --apply`: every live
table holds exactly the rows of its parquet, its columns match its
`*_original_20260810` backup on (name, type, ordinal position, nullability),
its partitioning and clustering match the pre-rewrite profile, and every backup
is still intact so a rollback remains possible.  The tier classification in
load.py is re-derived from the deployed property graphs so it cannot drift.

These BigQuery tests are unconditional: after Task 8 the loaded state *is* the
expected state, so a rolled-back or half-loaded dataset should be a red suite,
not a silent skip.
"""

import json
import os
import subprocess
import sys

# abspath matters: config.py locates data/profile/ relative to its own __file__.
_GENERATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_GENERATOR_DIR, "..", ".."))
sys.path.insert(0, _GENERATOR_DIR)
sys.path.insert(0, _REPO_ROOT)

import pytest
from google.cloud import bigquery

import load
import run_all
from config import BACKUP_SUFFIX, DATASET, PROJECT_ID, REWRITE_TABLES, SCHEMAS


@pytest.fixture(scope="module")
def client():
    return bigquery.Client(project=PROJECT_ID)


@pytest.fixture(scope="module")
def live_row_counts(client):
    """One query for every table's row count, live and backup alike."""
    sql = f"SELECT table_id, row_count FROM `{PROJECT_ID}.{DATASET}.__TABLES__`"
    return {r.table_id: r.row_count for r in client.query(sql).result()}


@pytest.fixture(scope="module")
def all_columns(client):
    """{table_name: [(column, type, ordinal, is_nullable), ...]} in one query."""
    names = [t for t in load.LOAD_ORDER] + [
        load.backup_name(t) for t in load.LOAD_ORDER
    ]
    sql = f"""
        SELECT table_name, column_name, data_type, ordinal_position, is_nullable
        FROM `{PROJECT_ID}.{DATASET}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name IN UNNEST(@names)
        ORDER BY table_name, ordinal_position
    """
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("names", "STRING", names)
            ]
        ),
    )
    out: dict[str, list] = {}
    for r in job.result():
        out.setdefault(r.table_name, []).append(
            (r.column_name, r.data_type, r.ordinal_position, r.is_nullable)
        )
    return out


# ---------------------------------------------------------------------------
# The deliberate post-load deepening
# ---------------------------------------------------------------------------
# scripts/deepen_core_data.py runs after the load and intentionally changes one
# table in LOAD_ORDER. inventory_levels was thin enough that a spares or
# stockout agent asked to rank a portfolio could only ever name a handful of
# parts -- a floor on what the product can demonstrate rather than a fact about
# the mine. The script appends parts under a `SKU-EXT-` prefix, keeps the
# original rows verbatim, and rewrites the table with part_number first.
#
# That result is the intended live state, not drift: `spares_inventory` is a
# view over this table and `purchase_orders` is anchored to its part numbers,
# so downstream data was built on the deepened shape.
#
# These tests therefore assert the deepened contract explicitly -- the original
# rows still reconcile to the parquet and the backup, the extra rows are all
# identifiable as extensions, and the column set still matches the backup while
# the order matches what the deepening declares. Relaxing them to "whatever is
# live" would delete the guard that a rolled-back or half-loaded dataset is a
# red suite, which is the only reason this half of the file exists.
DEEPENED = "inventory_levels"
EXTENSION_PREFIX = "SKU-EXT-"
DEEPENED_COLUMN_ORDER = [
    "part_number",
    "part_description",
    "stock_level",
    "reorder_point_limit",
    "lead_time_days",
    "unit_price_usd",
]


@pytest.fixture(scope="module")
def deepened_split(client):
    """Original vs extension row counts in the one deepened table."""
    sql = f"""
        SELECT
          COUNTIF(NOT STARTS_WITH(part_number, @prefix)) AS original_rows,
          COUNTIF(STARTS_WITH(part_number, @prefix)) AS extension_rows
        FROM `{PROJECT_ID}.{DATASET}.{DEEPENED}`
    """
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("prefix", "STRING", EXTENSION_PREFIX)
            ]
        ),
    )
    row = list(job.result())[0]
    return {"original_rows": row.original_rows, "extension_rows": row.extension_rows}


@pytest.fixture(scope="module")
def graph_tables(client):
    """(node table ids, edge table ids) across every property graph in the dataset."""
    sql = (
        "SELECT property_graph_metadata_json AS meta "
        f"FROM `{PROJECT_ID}.{DATASET}.INFORMATION_SCHEMA.PROPERTY_GRAPHS`"
    )
    nodes, edges = set(), set()
    rows = list(client.query(sql).result())
    assert rows, "no property graphs found — fixture is broken, not the code"
    for row in rows:
        # The column is a JSON type, so the client may hand back a dict already.
        meta = row.meta if isinstance(row.meta, dict) else json.loads(row.meta)
        for entry in meta.get("nodeTables", []):
            nodes.add(entry["dataSourceTable"]["tableId"])
        for entry in meta.get("edgeTables", []):
            edges.add(entry["dataSourceTable"]["tableId"])
    return nodes, edges


# ---------------------------------------------------------------------------
# Load order
# ---------------------------------------------------------------------------


class TestLoadOrder:
    def test_covers_every_rewritten_table_exactly_once(self):
        assert sorted(load.LOAD_ORDER) == sorted(REWRITE_TABLES)
        assert len(load.LOAD_ORDER) == len(set(load.LOAD_ORDER))

    def test_tiers_are_disjoint_and_exhaustive(self):
        tiers = load.DIMENSION_TABLES + load.FACT_TABLES + load.EDGE_TABLES
        assert tiers == load.LOAD_ORDER
        assert len(set(tiers)) == len(tiers)

    def test_dimensions_then_facts_then_edges(self):
        index = {t: i for i, t in enumerate(load.LOAD_ORDER)}
        assert load.DIMENSION_TABLES and load.FACT_TABLES and load.EDGE_TABLES
        assert max(index[t] for t in load.DIMENSION_TABLES) < min(
            index[t] for t in load.FACT_TABLES
        )
        assert max(index[t] for t in load.FACT_TABLES) < min(
            index[t] for t in load.EDGE_TABLES
        )

    def test_order_is_a_list_not_a_set(self):
        # A set would make the load order vary with insertion/hash behaviour.
        assert isinstance(load.LOAD_ORDER, list)

    def test_stable_across_hash_seeds(self, tmp_path):
        """The Task-2 determinism bug came from PYTHONHASHSEED-salted hash()."""
        code = (
            f"import sys; sys.path.insert(0, {_GENERATOR_DIR!r});"
            "import json, load;"
            "print(json.dumps([load.LOAD_ORDER, load.DIMENSION_TABLES,"
            " load.FACT_TABLES, load.EDGE_TABLES]))"
        )

        def run(seed):
            env = dict(os.environ, PYTHONHASHSEED=str(seed))
            proc = subprocess.run(
                [sys.executable, "-c", code],
                env=env, check=True, capture_output=True, text=True, cwd=_REPO_ROOT,
            )
            return proc.stdout.strip()

        assert run(1) == run(424242)


class TestTiersMatchTheDeployedGraphs:
    """The tiering in load.py is read off the property-graph DDL, so re-derive it."""

    def test_edge_tier_is_exactly_the_graph_edge_tables(self, graph_tables):
        _, edges = graph_tables
        assert sorted(load.EDGE_TABLES) == sorted(
            t for t in REWRITE_TABLES if t in edges
        )

    def test_dimension_tier_is_node_only_tables(self, graph_tables):
        nodes, edges = graph_tables
        expected = [t for t in REWRITE_TABLES if t in nodes and t not in edges]
        assert sorted(load.DIMENSION_TABLES) == sorted(expected)

    def test_fact_tier_is_in_no_graph(self, graph_tables):
        nodes, edges = graph_tables
        for table in load.FACT_TABLES:
            assert table not in nodes and table not in edges, table


# ---------------------------------------------------------------------------
# bq load invocation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def commands(tmp_path_factory):
    """The argv load.py would run for each table, plus the schema file it wrote."""
    directory = tmp_path_factory.mktemp("schemas")
    out = {}
    for table in load.LOAD_ORDER:
        schema_file = load.write_schema_file(table, directory)
        out[table] = (
            load.bq_load_command(table, load.staging_name(table), schema_file),
            schema_file,
        )
    return out


class TestBqLoadCommand:
    def test_uses_bq_load_with_explicit_schema_and_replace(self, commands):
        for table, (argv, schema_file) in commands.items():
            assert argv[1] == "load", table
            assert "--source_format=PARQUET" in argv, table
            assert "--replace" in argv, table
            assert f"--schema={schema_file}" in argv, table
            assert str(load.parquet_path(table)) == argv[-1], table

    def test_partitioning_flags_match_the_profile(self, commands):
        for table, (argv, _) in commands.items():
            field, ptype = load.partition_spec(table)
            flags = [a for a in argv if a.startswith("--time_partitioning")]
            if field is None:
                assert flags == [], f"{table} is unpartitioned but got {flags}"
            else:
                assert f"--time_partitioning_field={field}" in argv, table
                assert f"--time_partitioning_type={ptype}" in argv, table

    def test_clustering_flags_match_the_profile(self, commands):
        for table, (argv, _) in commands.items():
            clustering = load.clustering_spec(table)
            flags = [a for a in argv if a.startswith("--clustering_fields")]
            if not clustering:
                assert flags == [], f"{table} is unclustered but got {flags}"
            else:
                assert flags == ["--clustering_fields=" + ",".join(clustering)], table

    def test_at_least_one_table_exercises_each_branch(self, commands):
        """Guards the two tests above against passing vacuously."""
        partitioned = [t for t in load.LOAD_ORDER if load.partition_spec(t)[0]]
        clustered = [t for t in load.LOAD_ORDER if load.clustering_spec(t)]
        assert partitioned and len(partitioned) < len(load.LOAD_ORDER)
        assert clustered and len(clustered) < len(load.LOAD_ORDER)

    def test_schema_file_is_the_pre_rewrite_profile(self, commands):
        for table, (_, schema_file) in commands.items():
            written = json.loads(schema_file.read_text())
            assert written == SCHEMAS["schemas"][table]["columns"], table

    def test_repeated_field_keeps_its_mode(self, commands):
        """maintenance_logs.parts_replaced is an ARRAY; an inline schema loses that."""
        _, schema_file = commands["maintenance_logs"]
        written = {c["name"]: c["mode"] for c in json.loads(schema_file.read_text())}
        assert written["parts_replaced"] == "REPEATED"

    def test_parquet_enable_list_inference_flag_present(self, commands):
        """Without this flag a 3-level parquet LIST does not map to REPEATED."""
        for table, (argv, _) in commands.items():
            assert "--parquet_enable_list_inference=true" in argv, (
                f"{table}: missing --parquet_enable_list_inference=true in {argv}"
            )


# ---------------------------------------------------------------------------
# Content-fidelity check for REPEATED columns
# ---------------------------------------------------------------------------


class TestCheckRepeatedContent:
    """The content-fidelity check must catch silently-empty arrays.

    Both directions are tested: the check passes when cardinalities match and
    fails (is not vacuous) when they do not.  A check that cannot fail is worse
    than none — that is what cost a day on this bug.
    """

    def test_passes_when_cardinalities_match(self):
        """Stub a BQ client that returns the same count as the parquet file."""
        want = load.parquet_array_cardinality("maintenance_logs", "parts_replaced")
        assert want > 0, "parquet must have actual values for this test to mean anything"

        class FakeClient:
            def query(self, sql):
                class FakeResult:
                    def result(self):
                        class FakeRow:
                            n = want
                        return iter([FakeRow()])
                return FakeResult()

        ok, msg = load.check_repeated_content(FakeClient(), "maintenance_logs", "maintenance_logs")
        assert ok, f"expected ok=True but got: {msg}"
        assert "bq=" in msg  # message includes the counts

    def test_fails_when_bq_arrays_are_empty(self):
        """Simulates the pre-fix state: parquet has 186 values, BQ has 0."""
        want = load.parquet_array_cardinality("maintenance_logs", "parts_replaced")
        assert want > 0

        class FakeClientEmpty:
            def query(self, sql):
                class FakeResult:
                    def result(self):
                        class FakeRow:
                            n = 0
                        return iter([FakeRow()])
                return FakeResult()

        ok, msg = load.check_repeated_content(FakeClientEmpty(), "maintenance_logs", "maintenance_logs")
        assert not ok, "check must fail when BigQuery arrays are empty"
        assert "parts_replaced" in msg

    def test_no_repeated_columns_returns_true(self):
        """Tables without REPEATED columns should pass unconditionally."""
        # telemetry_stream has no REPEATED columns
        assert load.repeated_columns("telemetry_stream") == []
        ok, msg = load.check_repeated_content(None, "telemetry_stream", "telemetry_stream")
        assert ok
        assert "no REPEATED" in msg

    def test_parquet_cardinality_matches_known_value(self):
        """Regression anchor: maintenance_logs has 186 parts_replaced values."""
        total = load.parquet_array_cardinality("maintenance_logs", "parts_replaced")
        assert total == 186, (
            f"Expected 186 parts_replaced values in parquet, got {total}. "
            "If the generator was re-run this anchor needs updating."
        )


# ---------------------------------------------------------------------------
# Rollback SQL and delete safety
# ---------------------------------------------------------------------------


class TestRollbackSql:
    def test_reads_the_frozen_backup(self):
        for table in load.LOAD_ORDER:
            sql = load.restore_sql(table, table)
            assert f"{table}{BACKUP_SUFFIX}`" in sql, table

    def test_truncates_and_inserts_rather_than_dropping(self):
        for table in load.LOAD_ORDER:
            sql = load.restore_sql(table, table).upper()
            assert "TRUNCATE TABLE" in sql, table
            assert "INSERT INTO" in sql, table
            # Dropping would take the partition spec and the property-graph
            # bindings with it.
            assert "DROP " not in sql, table
            assert "CREATE OR REPLACE" not in sql, table

    def test_columns_are_listed_in_profile_order(self):
        for table in load.LOAD_ORDER:
            sql = load.restore_sql(table, table)
            positions = [sql.index(f"`{c}`") for c in load.column_names(table)]
            assert positions == sorted(positions), table

    def test_never_writes_to_a_backup(self):
        for table in load.LOAD_ORDER:
            sql = load.restore_sql(table, table)
            head = sql.split("SELECT")[0]
            assert BACKUP_SUFFIX not in head, table


class TestDeleteSafety:
    def test_staging_suffix_is_distinct_from_the_backup_suffix(self):
        assert load.STAGING_SUFFIX != BACKUP_SUFFIX
        assert not load.STAGING_SUFFIX.endswith(BACKUP_SUFFIX)
        assert not BACKUP_SUFFIX.endswith(load.STAGING_SUFFIX)

    @pytest.mark.parametrize(
        "name",
        [
            "inventory_levels",
            "inventory_levels" + BACKUP_SUFFIX,
            "telemetry_stream" + BACKUP_SUFFIX,
            "assets",
        ],
    )
    def test_drop_table_refuses_anything_but_staging(self, name):
        class Exploding:
            def delete_table(self, *a, **k):
                raise AssertionError(f"drop_table reached BigQuery for {name}")

        with pytest.raises(ValueError, match="refusing to drop"):
            load.drop_table(Exploding(), name)

    def test_drop_table_accepts_a_staging_name(self):
        seen = []

        class Recording:
            def delete_table(self, ref, not_found_ok=False):
                seen.append(ref)

        load.drop_table(Recording(), load.staging_name("inventory_levels"))
        assert seen == [load.table_ref(load.staging_name("inventory_levels"))]


# ---------------------------------------------------------------------------
# run_all wiring
# ---------------------------------------------------------------------------


#: The Task 2b tables (contracts.py/warranty.py/capital.py) are registered
#: in run_all.GENERATORS so a full `regenerate()` produces their parquet too,
#: but they are deliberately NOT in REWRITE_TABLES: that list drives the
#: backup/rollback contract in load.py, and these tables have no
#: `_original_20260810` backup because they never existed before Task 2b —
#: there is nothing to roll back to. See data/generator/contracts.py's module
#: docstring and load.py's `load_new_tables_2b`. `contained_metal_price_deck`
#: was added after the fact (a realism-defect fix, not part of the original
#: ten) but follows the exact same no-backup pattern.
TASK_2B_TABLES = frozenset(
    {
        "contracts", "contract_transactions", "rebate_claims", "invoices",
        "warranty_entitlements", "warranty_claims",
        "plan_versions", "plan_assumptions", "plan_scenarios", "capital_options",
        "contained_metal_price_deck",
    }
)


class TestRunAll:
    def test_generators_produce_the_rewritten_tables_plus_task_2b(self):
        """generated_tables() is REWRITE_TABLES plus the Task 2b tables above,
        with no overlap and no duplicate — not a bare superset check, which
        would pass even if a REWRITE_TABLES entry silently went missing.
        """
        produced = run_all.generated_tables()
        assert len(produced) == len(set(produced)), "a table is generated twice"
        assert set(produced) == set(REWRITE_TABLES) | TASK_2B_TABLES
        assert not (TASK_2B_TABLES & set(REWRITE_TABLES)), (
            "a Task 2b table leaked into REWRITE_TABLES — it would then be "
            "dragged into load.py's backup/rollback contract, which has "
            "nothing to back it up against"
        )

    def test_every_entry_point_exists_and_needs_no_arguments(self):
        """The generators are not uniform: maintenance's log builder takes no seed."""
        import importlib
        import inspect

        for module_name, entry_point, _ in run_all.GENERATORS:
            module = importlib.import_module(module_name)
            fn = getattr(module, entry_point, None)
            assert callable(fn), f"{module_name}.{entry_point} is not callable"
            required = [
                p
                for p in inspect.signature(fn).parameters.values()
                if p.default is inspect.Parameter.empty
                and p.kind
                in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
            ]
            assert not required, f"{module_name}.{entry_point} requires {required}"

    def test_generator_order_puts_producers_before_consumers(self):
        """metallurgy reads telemetry's parquet; supply_chain reads maintenance's."""
        order = [name for name, _, _ in run_all.GENERATORS]
        assert order.index("telemetry") < order.index("metallurgy")
        assert order.index("telemetry") < order.index("supply_chain")
        assert order.index("maintenance") < order.index("supply_chain")

    def test_a_mode_flag_is_required(self):
        with pytest.raises(SystemExit):
            run_all.main([])


# ---------------------------------------------------------------------------
# The loaded state in BigQuery
# ---------------------------------------------------------------------------


class TestLoadedState:
    def test_live_row_counts_match_the_parquet_files(
        self, live_row_counts, deepened_split
    ):
        for table in load.LOAD_ORDER:
            expected = load.parquet_row_count(table)
            if table != DEEPENED:
                assert live_row_counts[table] == expected, table
                continue
            # The deepening is additive: the rows the parquet loaded must still
            # all be there, and everything beyond them must be an extension.
            assert deepened_split["original_rows"] == expected, (
                f"{table}: {deepened_split['original_rows']} non-extension rows "
                f"live, parquet holds {expected} -- the load itself has drifted, "
                "which the deepening does not explain"
            )
            assert deepened_split["extension_rows"] > 0, (
                f"{table}: no {EXTENSION_PREFIX} rows -- the deepening is "
                "missing, so agents see the thin catalogue again"
            )
            assert live_row_counts[table] == expected + deepened_split["extension_rows"], (
                f"{table}: {live_row_counts[table]} rows live, expected "
                f"{expected} original + {deepened_split['extension_rows']} extension"
            )

    def test_live_tables_are_not_empty(self, live_row_counts):
        # A graph query over an empty table succeeds and returns zero rows, so
        # emptiness has to be caught here rather than downstream.
        for table in load.LOAD_ORDER:
            assert live_row_counts[table] > 0, table

    def test_columns_identical_to_the_frozen_backup(self, all_columns):
        for table in load.LOAD_ORDER:
            backup = load.backup_name(table)
            assert all_columns[backup], f"{backup} missing"
            if table != DEEPENED:
                assert all_columns[table] == all_columns[backup], table
                continue
            # The deepening reordered this table's columns but changed nothing
            # else, so compare on everything except ordinal position. A dropped,
            # added, retyped or newly-required column still fails here.
            def shape(cols):
                return sorted((c, t, n) for c, t, _, n in cols)

            assert shape(all_columns[table]) == shape(all_columns[backup]), (
                f"{table}: column set/types/nullability differ from {backup}; "
                "the deepening only reorders, so this is real schema drift"
            )

    def test_columns_also_match_the_pre_rewrite_profile(self, all_columns):
        for table in load.LOAD_ORDER:
            got = [c for c, _, _, _ in all_columns[table]]
            if table != DEEPENED:
                assert got == load.column_names(table), table
                continue
            assert sorted(got) == sorted(load.column_names(table)), (
                f"{table}: column names differ from the pre-rewrite profile"
            )
            # Order is pinned to what the deepening declares, so a future
            # rewrite that silently reshuffles `SELECT *` still fails.
            assert got == DEEPENED_COLUMN_ORDER, (
                f"{table}: live column order {got} is neither the profile's nor "
                "the order scripts/deepen_core_data.py declares"
            )

    def test_partitioning_and_clustering_preserved(self, client):
        for table in load.LOAD_ORDER:
            ok, message = load.check_partitioning(client, table, table)
            assert ok, f"{table}: {message}"

    def test_backups_still_intact(self, live_row_counts):
        """Rollback must remain possible after the apply."""
        for table in load.LOAD_ORDER:
            backup = load.backup_name(table)
            assert live_row_counts.get(backup) == SCHEMAS["schemas"][table]["num_rows"]

    def test_inventory_levels_gained_the_two_missing_skus(self, deepened_split):
        """The one table whose row count deliberately differs from its backup.

        Measured against the original rows, not the live total: the later
        deepening adds `SKU-EXT-` parts on top, and folding those into this
        count would hide the two SKUs this test exists to prove arrived.
        """
        assert (
            deepened_split["original_rows"]
            == SCHEMAS["schemas"][DEEPENED]["num_rows"] + 2
        )
