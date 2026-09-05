"""Task 9 — the realism gate (R1–R8) over the ten regenerated tables, live in BigQuery.

Eight tests, one per assertion in the Task 9 brief:

  R1  lag-1 autocorrelation in [0.75, 0.95] for every asset*metric
  R2  diurnal amplitude > 3% of mean for every continuous series
  R3  two-product mass balance holds to 0.01 pp on every metallurgy row
  R4  corr(repair_cost, actual_duration_hours) in [0.70, 0.90]
  R5  corr(sleep_deficit_hours, heart_rate_bpm) in [0.35, 0.55]
  R6  all four property graphs traverse and return > 0 rows
  R7  no NULLs in key columns; no negative stock, duration or cost
  R8  every summary statistic quoted in the PRD still holds

Every test runs against the *live* tables in `mining_data`.  Seven of the eight
also re-run the identical measurement against the frozen `_original_20260810`
backups and require it to FAIL there.  That is the point: an assertion that
cannot distinguish the regenerated data from the flat, uncorrelated data it
replaced is not a gate, it is decoration.  R6 cannot use the backups (the
property graphs are bound to the live tables by name), so it carries an explicit
negative control instead — a structurally identical traversal whose only
difference is a sentinel key that matches nothing, which must return exactly
zero rows.  Without that control, "the query returned rows" and "the query ran"
are indistinguishable, and a property graph over unmatched tables succeeds
silently with zero rows.

Nothing here writes.  The suite reads live tables and backups and asserts.

Task 2b adds six more, over the brand-new contract/warranty/plan tables that
have no `_original_20260810` backup to discriminate against (they never
existed before). Each instead carries its own mutation-tested negative
control: the generator constant that produces the property is forced to a
value that should break it, the same measurement is re-run, and the test
requires it to fall outside the band:

  R9   contract leakage is a minority of on-contract transactions, in
       [0.10, 0.32] — forcing LEAKAGE_PROB to 0.0 or 1.0 must fall outside it
  R10  contract coverage is incomplete, in [0.20, 0.60] of all transactions —
       forcing the gap sources (spot parts, renewal gap) to zero must not
  R11  warranty coverage produces a real cliff, not a coin flip — a >=0.85
       eligible-repair spread across assets, and a >=0.85 before/after
       differential at each cliff asset's own measured coverage-cutoff date —
       forcing every entitlement into the same coverage group collapses both
  R11b repairs inside warranty cover are a genuine minority of all shipped
       repairs, in [0.15, 0.35] — not the ~everything an over-broad coverage
       window produces and not zero; the same uniform-coverage mutation as
       R11 must push it out of band
  R12  the shipped `contained_metal_price_deck` table has lag-1
       autocorrelation in [0.55, 0.95] — a shuffle of the same shipped
       values, and phi=0 (independent draws), must both fall outside it
  R13  plan assumptions go stale at differing rates — max minus min
       supersede-count across the 6 plan versions is >= 4 of 7 metrics —
       forcing every metric's hazard to 0 collapses the spread to exactly 0
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# abspath matters: config.py locates data/profile/ relative to its own __file__,
# so an unnormalised ".." on sys.path would send it looking in tests/profile/.
_GENERATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _GENERATOR_DIR)

import numpy as np
import pandas as pd
import pytest
from google.cloud import bigquery

from config import BACKUP_SUFFIX, DATASET, PROJECT_ID

import capital as CAP
import contracts as CTR
import warranty as WTY

# --- Bands, verbatim from the Task 9 brief ----------------------------------

LAG1_BAND = (0.75, 0.95)
DIURNAL_MIN_FRACTION_OF_MEAN = 0.03
MASS_BALANCE_TOLERANCE_PP = 0.01
COST_DURATION_BAND = (0.70, 0.90)
FATIGUE_BAND = (0.35, 0.55)

LIVE = ""  # the empty table-name suffix: the live table

_PRD_PATH = Path(_GENERATOR_DIR).parent.parent / "docs" / "phase-1-prd.md"


def _t(table: str, suffix: str = LIVE) -> str:
    """Fully-qualified, back-quoted table reference."""
    return f"`{PROJECT_ID}.{DATASET}.{table}{suffix}`"


@pytest.fixture(scope="module")
def client():
    return bigquery.Client(project=PROJECT_ID)


def _frame(client, sql: str, **params) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(k, "STRING", v) for k, v in params.items()
        ]
    )
    return client.query(sql, job_config=job_config).to_dataframe()


# ===========================================================================
# R1 / R2 — telemetry series shape
# ===========================================================================


@pytest.fixture(scope="module")
def telemetry(client):
    """{suffix: DataFrame} for the live telemetry table and its frozen backup."""
    out = {}
    for suffix in (LIVE, BACKUP_SUFFIX):
        out[suffix] = _frame(
            client,
            f"""
            SELECT asset_id, metric_name, timestamp, metric_value
            FROM {_t('telemetry_stream', suffix)}
            ORDER BY asset_id, metric_name, timestamp
            """,
        )
    return out


def _series(df: pd.DataFrame):
    """Yield ((asset_id, metric_name), time-ordered values) for every series."""
    for key, group in df.groupby(["asset_id", "metric_name"], sort=True):
        yield key, group


def _lag1(values: np.ndarray) -> float:
    return float(np.corrcoef(values[:-1], values[1:])[0, 1])


def _measure_lag1(df: pd.DataFrame) -> dict:
    return {
        key: _lag1(group["metric_value"].to_numpy(dtype=float))
        for key, group in _series(df)
    }


def _measure_diurnal(df: pd.DataFrame) -> dict:
    """{series: (amplitude, 3%-of-mean threshold)} using hour-of-day means.

    Amplitude is max(hourly mean) - min(hourly mean), the same estimator
    test_telemetry.py uses, so R2 and the per-table test cannot disagree.
    """
    hours = pd.to_datetime(df["timestamp"], utc=True).dt.hour
    df = df.assign(hour=hours)
    out = {}
    for key, group in _series(df):
        hourly = group.groupby("hour")["metric_value"].mean()
        amplitude = float(hourly.max() - hourly.min())
        threshold = DIURNAL_MIN_FRACTION_OF_MEAN * abs(
            float(group["metric_value"].mean())
        )
        out[key] = (amplitude, threshold)
    return out


def test_r1_lag1_autocorrelation_in_band(telemetry):
    """R1: every telemetry asset*metric series has lag-1 autocorrelation in [0.75, 0.95].

    Scope note: "asset*metric" is the (asset_id, metric_name) key of
    telemetry_stream, the only table keyed that way.  crusher_states and
    metallurgical_recovery are daily aggregates -- crusher_states is literally
    the daily mean of the 2-hourly telemetry -- and daily means of an AR(1)
    process do not carry the parent process's lag-1 coefficient.  Their measured
    values are recorded in the Task 9 report; they are not, and cannot be, held
    to this band.
    """
    low, high = LAG1_BAND
    live = _measure_lag1(telemetry[LIVE])
    assert live, "telemetry_stream returned no series — the fixture is broken"

    out_of_band = {k: v for k, v in live.items() if not low <= v <= high}
    assert not out_of_band, (
        "lag-1 autocorrelation outside "
        f"[{low}, {high}]: "
        + "; ".join(f"{a}/{m}={v:.4f}" for (a, m), v in sorted(out_of_band.items()))
    )

    # Discrimination: the same measurement on the pre-regeneration backup must
    # fail for every series it contains.  If this ever passes, R1 is inert.
    old = _measure_lag1(telemetry[BACKUP_SUFFIX])
    assert old, "backup telemetry returned no series"
    still_in_band = {k: v for k, v in old.items() if low <= v <= high}
    assert not still_in_band, (
        "R1 does not discriminate: pre-regeneration series inside the band: "
        + "; ".join(f"{a}/{m}={v:.4f}" for (a, m), v in sorted(still_in_band.items()))
    )


def test_r2_diurnal_amplitude_exceeds_three_percent(telemetry):
    """R2: every continuous series shows a hour-of-day swing > 3% of its mean."""
    live = _measure_diurnal(telemetry[LIVE])
    assert live, "telemetry_stream returned no series — the fixture is broken"

    flat = {k: v for k, v in live.items() if v[0] <= v[1]}
    assert not flat, (
        "diurnal amplitude <= 3% of mean: "
        + "; ".join(
            f"{a}/{m} amp={amp:.4f} threshold={thr:.4f}"
            for (a, m), (amp, thr) in sorted(flat.items())
        )
    )

    # Discrimination: the backup must fail this as a set.  Four of its five
    # series are flat; PUMP-104A/vibration_hz passes on the backup too, because
    # the pre-existing degradation ramp already moved that one series.
    old = _measure_diurnal(telemetry[BACKUP_SUFFIX])
    old_flat = {k: v for k, v in old.items() if v[0] <= v[1]}
    assert old_flat, (
        "R2 does not discriminate: every pre-regeneration series already "
        "cleared the 3% threshold"
    )


# ===========================================================================
# R3 — two-product mass balance
# ===========================================================================


def _mass_balance_deviation(client, suffix: str) -> pd.Series:
    """|stored recovery - recovery recomputed from the grades|, in pp, per row.

    R = 100*c*(f - t) / (f*(c - t)) with c = concentrate, f = feed, t = tailings.
    """
    df = _frame(
        client,
        f"""
        SELECT timestamp, concentrator_id, feed_grade_pct,
               concentrate_grade_pct, tailings_grade_pct, recovery_rate_pct
        FROM {_t('metallurgical_recovery', suffix)}
        """,
    )
    assert not df.empty, f"metallurgical_recovery{suffix} is empty"
    f = df["feed_grade_pct"]
    c = df["concentrate_grade_pct"]
    t = df["tailings_grade_pct"]
    recomputed = 100.0 * c * (f - t) / (f * (c - t))
    return (recomputed - df["recovery_rate_pct"]).abs()


def test_r3_two_product_mass_balance(client):
    """R3: recovery is reproducible from the three grade columns to 0.01 pp."""
    live = _mass_balance_deviation(client, LIVE)
    worst = float(live.max())
    breaches = int((live > MASS_BALANCE_TOLERANCE_PP).sum())
    assert breaches == 0, (
        f"{breaches} of {len(live)} metallurgy rows break the two-product mass "
        f"balance by more than {MASS_BALANCE_TOLERANCE_PP} pp "
        f"(worst {worst:.6f} pp)"
    )

    old = _mass_balance_deviation(client, BACKUP_SUFFIX)
    assert int((old > MASS_BALANCE_TOLERANCE_PP).sum()) > 0, (
        "R3 does not discriminate: the pre-regeneration metallurgy rows already "
        f"satisfy mass balance (worst {float(old.max()):.6f} pp)"
    )


# ===========================================================================
# R4 — repair cost vs repair duration
# ===========================================================================


def _cost_duration_corr(client, suffix: str) -> tuple[float, int]:
    df = _frame(
        client,
        f"""
        SELECT w.repair_cost, m.actual_duration_hours
        FROM {_t('erp_work_orders', suffix)} w
        JOIN {_t('maintenance_logs', suffix)} m USING (work_order_id)
        """,
    )
    assert not df.empty, f"the work-order/log join is empty for suffix {suffix!r}"
    return (
        float(df["repair_cost"].corr(df["actual_duration_hours"])),
        len(df),
    )


def test_r4_repair_cost_tracks_duration(client):
    """R4: corr(repair_cost, actual_duration_hours) in [0.70, 0.90]."""
    low, high = COST_DURATION_BAND
    corr, n = _cost_duration_corr(client, LIVE)
    assert low <= corr <= high, (
        f"corr(repair_cost, actual_duration_hours) = {corr:.4f} over {n} joined "
        f"rows, outside [{low}, {high}]"
    )

    old_corr, old_n = _cost_duration_corr(client, BACKUP_SUFFIX)
    assert not low <= old_corr <= high, (
        f"R4 does not discriminate: the pre-regeneration join already gives "
        f"{old_corr:.4f} over {old_n} rows"
    )


# ===========================================================================
# R5 — sleep deficit vs heart rate
# ===========================================================================

FATIGUE_TABLES = ("biometric_fatigue_logs", "fatigue_logs_node")


def _fatigue_corr(client, table: str, suffix: str) -> tuple[float, int]:
    df = _frame(
        client,
        f"""
        SELECT sleep_deficit_hours, heart_rate_bpm
        FROM {_t(table, suffix)}
        """,
    )
    assert not df.empty, f"{table}{suffix} is empty"
    return (
        float(
            df["sleep_deficit_hours"].corr(df["heart_rate_bpm"].astype(float))
        ),
        len(df),
    )


def test_r5_sleep_deficit_drives_heart_rate(client):
    """R5: corr(sleep_deficit_hours, heart_rate_bpm) in [0.35, 0.55].

    Checked on both fatigue tables: fatigue_logs_node is the graph-facing copy
    of biometric_fatigue_logs, and a correlation present in one but not the
    other would mean the two have diverged.
    """
    low, high = FATIGUE_BAND
    failures = []
    for table in FATIGUE_TABLES:
        corr, n = _fatigue_corr(client, table, LIVE)
        if not low <= corr <= high:
            failures.append(f"{table}: {corr:.4f} over {n} rows")
    assert not failures, (
        f"corr(sleep_deficit_hours, heart_rate_bpm) outside [{low}, {high}] — "
        + "; ".join(failures)
    )

    still_in_band = []
    for table in FATIGUE_TABLES:
        corr, _ = _fatigue_corr(client, table, BACKUP_SUFFIX)
        if low <= corr <= high:
            still_in_band.append(f"{table}: {corr:.4f}")
    assert not still_in_band, (
        "R5 does not discriminate: pre-regeneration tables already in band — "
        + "; ".join(still_in_band)
    )


# ===========================================================================
# R6 — the four property graphs
# ===========================================================================


@dataclass(frozen=True)
class GraphProbe:
    graph: str
    sql: str
    #: parameter set that must match real data
    positive: dict
    #: identical shape, sentinel key — must match nothing
    negative: dict


# Edge labels and directions below are taken from the deployed graphs
# (INFORMATION_SCHEMA.PROPERTY_GRAPHS) and from working code
# (supply_chain._S08_SQL) — NOT from docs/phase-3-design.md section 3.2, whose
# traversals name the edge *tables* where a label is required and do not run.
GRAPH_PROBES = (
    GraphProbe(
        graph="MiningAssetGraph",
        sql=f"""
        SELECT * FROM GRAPH_TABLE(
          {DATASET}.MiningAssetGraph
          MATCH (origin:assets WHERE origin.asset_id = @asset_id)
                -[:DEPENDS_ON]->{{1,3}} (impacted:assets)
          COLUMNS (origin.asset_id AS fail_origin,
                   impacted.asset_id AS impacted_asset,
                   impacted.criticality_rating AS impacted_criticality)
        )
        """,
        positive={"asset_id": "CONVEYOR-02"},
        negative={"asset_id": "ASSET-THAT-DOES-NOT-EXIST"},
    ),
    GraphProbe(
        graph="MiningOntologyGraph",
        sql=f"""
        SELECT * FROM GRAPH_TABLE(
          {DATASET}.MiningOntologyGraph
          MATCH (s:ontology_concepts WHERE s.concept_name = @concept)
                -[r:RELATED_TO]-> (o:ontology_concepts)
          COLUMNS (s.concept_name AS subject, r.predicate AS predicate,
                   o.concept_name AS object)
        )
        """,
        positive={"concept": "CONVEYOR-02"},
        negative={"concept": "CONCEPT-THAT-DOES-NOT-EXIST"},
    ),
    GraphProbe(
        graph="MiningOperationsSafetyGraph",
        sql=f"""
        SELECT * FROM GRAPH_TABLE(
          {DATASET}.MiningOperationsSafetyGraph
          MATCH (f:FatigueLog) -[:LOGGED_FOR]->
                (o:Operator WHERE o.operator_id = @operator_id)
                -[:OPERATES]-> (v:Vehicle) -[:INVOLVED_IN]-> (i:Incident)
          COLUMNS (f.log_id AS log_id, o.operator_id AS operator_id,
                   v.vehicle_id AS vehicle_id, i.incident_id AS incident_id,
                   i.severity_level AS severity_level)
        )
        """,
        positive={"operator_id": "OP-103"},
        negative={"operator_id": "OP-THAT-DOES-NOT-EXIST"},
    ),
    GraphProbe(
        graph="MiningSupplyChainGraph",
        sql=f"""
        SELECT * FROM GRAPH_TABLE(
          {DATASET}.MiningSupplyChainGraph
          MATCH (p:SparePart) <-[:REPLACED_PART]- (w:WorkOrder)
                <-[:HAS_WORK_ORDER]- (a:Asset WHERE a.asset_id = @asset_id)
          COLUMNS (p.part_number AS part_number, w.work_order_id AS work_order_id,
                   w.priority AS priority, a.asset_id AS asset_id)
        )
        """,
        positive={"asset_id": "PUMP-104A"},
        negative={"asset_id": "ASSET-THAT-DOES-NOT-EXIST"},
    ),
)


def test_r6_all_four_property_graphs_traverse(client):
    """R6: each of the four graphs returns > 0 rows, and its negative control 0.

    This is the guard against the named trap.  A GRAPH_TABLE query over empty or
    unmatched tables returns zero rows without erroring, so a test that only
    asserts the query ran passes over broken data.  Asserting > 0 catches that;
    the paired negative control proves the > 0 assertion is not vacuous, because
    the same query shape with a sentinel key does return zero.
    """
    assert len(GRAPH_PROBES) == 4, "R6 must cover all four deployed graphs"
    deployed = {
        row.property_graph_name
        for row in client.query(
            "SELECT property_graph_name FROM "
            f"`{PROJECT_ID}.{DATASET}.INFORMATION_SCHEMA.PROPERTY_GRAPHS`"
        ).result()
    }
    covered = {probe.graph for probe in GRAPH_PROBES}
    assert covered == deployed, (
        f"R6 covers {sorted(covered)} but the dataset deploys {sorted(deployed)}"
    )

    empty, leaky = [], []
    for probe in GRAPH_PROBES:
        rows = len(_frame(client, probe.sql, **probe.positive))
        if rows == 0:
            empty.append(f"{probe.graph} ({probe.positive})")
        control = len(_frame(client, probe.sql, **probe.negative))
        if control != 0:
            leaky.append(f"{probe.graph} returned {control} rows for a sentinel key")

    assert not empty, "property graph traversal returned zero rows: " + "; ".join(empty)
    assert not leaky, (
        "R6's negative control is broken — the row-count assertion cannot "
        "distinguish a real match from no match: " + "; ".join(leaky)
    )


# ===========================================================================
# R7 — key columns and sign constraints
# ===========================================================================

#: (name, SQL returning a single INT64 violation count). {s} is the table
#: suffix: empty for live, BACKUP_SUFFIX for the frozen copy.  Every rewritten
#: table appears at least once.
_R7_CHECKS = (
    # --- NULLs in key columns -------------------------------------------------
    ("telemetry_stream key NULLs",
     "SELECT COUNTIF(asset_id IS NULL OR metric_name IS NULL "
     "OR timestamp IS NULL OR metric_value IS NULL) FROM {telemetry_stream}"),
    ("metallurgical_recovery key NULLs",
     "SELECT COUNTIF(concentrator_id IS NULL OR timestamp IS NULL "
     "OR feed_grade_pct IS NULL OR concentrate_grade_pct IS NULL "
     "OR tailings_grade_pct IS NULL OR recovery_rate_pct IS NULL) "
     "FROM {metallurgical_recovery}"),
    ("crusher_states key NULLs",
     "SELECT COUNTIF(asset_id IS NULL OR timestamp IS NULL "
     "OR feed_rate_tph IS NULL OR gap_size_setting_mm IS NULL "
     "OR rotational_torque_nm IS NULL) FROM {crusher_states}"),
    ("erp_work_orders key NULLs",
     "SELECT COUNTIF(work_order_id IS NULL OR asset_id IS NULL "
     "OR status IS NULL OR priority IS NULL OR repair_cost IS NULL) "
     "FROM {erp_work_orders}"),
    ("maintenance_logs key NULLs",
     "SELECT COUNTIF(log_entry_id IS NULL OR work_order_id IS NULL "
     "OR asset_id IS NULL OR actual_duration_hours IS NULL) "
     "FROM {maintenance_logs}"),
    ("biometric_fatigue_logs key NULLs",
     "SELECT COUNTIF(operator_id IS NULL OR timestamp IS NULL "
     "OR heart_rate_bpm IS NULL OR sleep_deficit_hours IS NULL "
     "OR microsleep_events_detected IS NULL) FROM {biometric_fatigue_logs}"),
    ("fatigue_logs_node key NULLs",
     "SELECT COUNTIF(log_id IS NULL OR operator_id IS NULL OR timestamp IS NULL "
     "OR heart_rate_bpm IS NULL OR sleep_deficit_hours IS NULL) "
     "FROM {fatigue_logs_node}"),
    ("inventory_levels key NULLs",
     "SELECT COUNTIF(part_number IS NULL OR stock_level IS NULL "
     "OR reorder_point_limit IS NULL OR unit_price_usd IS NULL "
     "OR lead_time_days IS NULL) FROM {inventory_levels}"),
    ("drill_assay_logs key NULLs",
     "SELECT COUNTIF(drill_hole_id IS NULL OR geology_code IS NULL "
     "OR depth_start_meters IS NULL OR depth_end_meters IS NULL "
     "OR copper_grade_pct IS NULL OR gold_grade_gpt IS NULL) "
     "FROM {drill_assay_logs}"),
    ("geological_block_models key NULLs",
     "SELECT COUNTIF(block_id IS NULL OR lithology_type IS NULL "
     "OR centroid_x IS NULL OR centroid_y IS NULL OR centroid_z IS NULL "
     "OR copper_grade_pct_est IS NULL OR gold_grade_gpt_est IS NULL "
     "OR specific_gravity IS NULL) FROM {geological_block_models}"),
    # --- duplicate keys -------------------------------------------------------
    ("inventory_levels duplicate part_number",
     "SELECT COUNT(*) - COUNT(DISTINCT part_number) FROM {inventory_levels}"),
    ("erp_work_orders duplicate work_order_id",
     "SELECT COUNT(*) - COUNT(DISTINCT work_order_id) FROM {erp_work_orders}"),
    ("fatigue_logs_node duplicate log_id",
     "SELECT COUNT(*) - COUNT(DISTINCT log_id) FROM {fatigue_logs_node}"),
    # --- negative stock, duration, cost --------------------------------------
    ("negative stock", "SELECT COUNTIF(stock_level < 0) FROM {inventory_levels}"),
    ("negative reorder point",
     "SELECT COUNTIF(reorder_point_limit < 0) FROM {inventory_levels}"),
    ("negative lead time",
     "SELECT COUNTIF(lead_time_days < 0) FROM {inventory_levels}"),
    ("negative unit price",
     "SELECT COUNTIF(unit_price_usd < 0) FROM {inventory_levels}"),
    ("negative duration",
     "SELECT COUNTIF(actual_duration_hours < 0) FROM {maintenance_logs}"),
    ("negative repair cost",
     "SELECT COUNTIF(repair_cost < 0) FROM {erp_work_orders}"),
    # --- other sign / range constraints on the regenerated columns ------------
    ("negative grades (metallurgy)",
     "SELECT COUNTIF(feed_grade_pct < 0 OR concentrate_grade_pct < 0 "
     "OR tailings_grade_pct < 0 OR recovery_rate_pct < 0) "
     "FROM {metallurgical_recovery}"),
    ("negative crusher readings",
     "SELECT COUNTIF(feed_rate_tph < 0 OR rotational_torque_nm < 0 "
     "OR gap_size_setting_mm < 0) FROM {crusher_states}"),
    ("negative fatigue readings",
     "SELECT COUNTIF(sleep_deficit_hours < 0 OR heart_rate_bpm < 0 "
     "OR microsleep_events_detected < 0) FROM {biometric_fatigue_logs}"),
    ("negative assay grades / inverted intervals",
     "SELECT COUNTIF(copper_grade_pct < 0 OR gold_grade_gpt < 0 "
     "OR depth_start_meters < 0 OR depth_end_meters <= depth_start_meters) "
     "FROM {drill_assay_logs}"),
    ("non-positive specific gravity / negative block grades",
     "SELECT COUNTIF(specific_gravity <= 0 OR copper_grade_pct_est < 0 "
     "OR gold_grade_gpt_est < 0) FROM {geological_block_models}"),
    # --- key columns that must resolve ---------------------------------------
    # A key column holding a value that resolves to nothing is as broken as a
    # NULL, and unlike the NULL checks these DO discriminate: the frozen
    # inventory_levels is missing two SKUs that maintenance_logs references.
    ("parts_replaced SKU missing from inventory_levels",
     "SELECT COUNT(*) FROM (SELECT DISTINCT sku FROM {maintenance_logs}, "
     "UNNEST(parts_replaced) AS sku WHERE sku NOT IN "
     "(SELECT part_number FROM {inventory_levels}))"),
    ("work_order_parts_edge SKU missing from inventory_levels",
     "SELECT COUNT(*) FROM (SELECT DISTINCT part_number FROM "
     f"{_t('work_order_parts_edge')} WHERE part_number NOT IN "
     "(SELECT part_number FROM {inventory_levels}))"),
    ("maintenance_logs work_order_id missing from erp_work_orders",
     "SELECT COUNTIF(work_order_id NOT IN "
     "(SELECT work_order_id FROM {erp_work_orders})) FROM {maintenance_logs}"),
    ("erp_work_orders asset_id missing from assets",
     "SELECT COUNTIF(asset_id NOT IN "
     f"(SELECT asset_id FROM {_t('assets')})) FROM {{erp_work_orders}}"),
    ("fatigue_logs_node operator_id missing from operators_node",
     "SELECT COUNTIF(operator_id NOT IN "
     f"(SELECT operator_id FROM {_t('operators_node')})) FROM {{fatigue_logs_node}}"),
    ("drill_assay_logs drill_hole_id missing from drill_holes",
     "SELECT COUNTIF(drill_hole_id NOT IN "
     f"(SELECT drill_hole_id FROM {_t('drill_holes')})) FROM {{drill_assay_logs}}"),
)

_R7_TABLES = (
    "telemetry_stream", "metallurgical_recovery", "crusher_states",
    "erp_work_orders", "maintenance_logs", "biometric_fatigue_logs",
    "fatigue_logs_node", "inventory_levels", "drill_assay_logs",
    "geological_block_models",
)


def _r7_violations(client, suffix: str) -> dict:
    """{check name: violation count} — all checks in a single query."""
    refs = {table: _t(table, suffix) for table in _R7_TABLES}
    selects = [
        f"SELECT {i} AS idx, ({sql.format(**refs)}) AS violations"
        for i, (_, sql) in enumerate(_R7_CHECKS)
    ]
    rows = client.query("\nUNION ALL\n".join(selects)).result()
    counts = {row.idx: row.violations for row in rows}
    return {name: counts[i] for i, (name, _) in enumerate(_R7_CHECKS)}


def test_r7_key_columns_and_sign_constraints(client):
    """R7: no NULL or dangling key columns; no negative stock, duration or cost."""
    live = _r7_violations(client, LIVE)
    assert len(live) == len(_R7_CHECKS)
    breaches = {k: v for k, v in live.items() if v != 0}
    assert not breaches, "integrity violations in the live tables: " + "; ".join(
        f"{k}={v}" for k, v in sorted(breaches.items())
    )

    # Discrimination: the NULL and sign checks pass on the backup too (the
    # original data was flat, not malformed) — they are regression guards.  The
    # resolve-to-a-real-row checks are what bite: the frozen inventory_levels is
    # missing SKUs that maintenance_logs and work_order_parts_edge reference.
    old = _r7_violations(client, BACKUP_SUFFIX)
    assert any(v != 0 for v in old.values()), (
        "R7 does not discriminate: the pre-regeneration tables pass every check"
    )


# ===========================================================================
# R8 — the summary statistics quoted in the PRD
# ===========================================================================


@dataclass(frozen=True)
class PrdClaim:
    """A number quoted in docs/phase-1-prd.md, and the query that re-derives it.

    ``pattern`` is matched against the PRD text; its capture groups are the
    claimed values.  ``sql`` returns one row whose columns, in order, are the
    measured values.  ``tolerances`` gives the allowed absolute error per group,
    sized to the precision the PRD quotes (0 for a count).

    The expected values are read out of the document rather than restated here,
    so this check fails both when the data drifts from the PRD and when the PRD
    drifts from the data.  Restating them would only test the test.
    """

    label: str
    pattern: str
    sql: str
    tolerances: tuple
    #: True if the query reads at least one rewritten table, i.e. the claim can
    #: be re-evaluated against the frozen backups.
    backed_up: bool = True


PRD_CLAIMS = (
    PrdClaim(
        "§1 work orders at CRITICAL priority",
        r"Work orders at CRITICAL priority \|\s*\*\*([\d,]+) of ([\d,]+)\*\*",
        "SELECT COUNTIF(priority = 'CRITICAL') AS a, COUNT(*) AS b "
        "FROM {erp_work_orders}",
        (0, 0),
    ),
    PrdClaim(
        "§1 cancelled work orders and their booked cost",
        r"Work orders CANCELLED[^|]*\|\s*\*\*([\d,]+) of ([\d,]+)\*\*, "
        r"\$([\d,.]+)k booked repair cost",
        "SELECT COUNTIF(status = 'CANCELLED') AS a, COUNT(*) AS b, "
        "SUM(IF(status = 'CANCELLED', repair_cost, 0)) / 1000 AS c "
        "FROM {erp_work_orders}",
        (0, 0, 0.5),
    ),
    PrdClaim(
        "§1 spare parts below reorder point and mean lead time",
        r"Spare parts below reorder point \|\s*\*\*([\d,]+) of ([\d,]+)\*\*, "
        r"against ([\d.]+)-day mean lead time",
        "SELECT COUNTIF(stock_level < reorder_point_limit) AS a, COUNT(*) AS b, "
        "AVG(lead_time_days) AS c FROM {inventory_levels}",
        (0, 0, 0.05),
    ),
    PrdClaim(
        "§1 concentrator recovery spread",
        r"Concentrator recovery spread \|\s*\*\*([\d.]+)%\s*[–—-]\s*([\d.]+)%\*\* "
        r"\(mean ([\d.]+)%\)",
        "SELECT MIN(recovery_rate_pct) AS a, MAX(recovery_rate_pct) AS b, "
        "AVG(recovery_rate_pct) AS c FROM {metallurgical_recovery}",
        (0.05, 0.05, 0.05),
    ),
    PrdClaim(
        "§1 safety incidents on record",
        r"Safety incidents on record \|\s*\*\*([\d,]+)\*\*",
        f"SELECT COUNT(*) AS a FROM {_t('safety_incidents')}",
        (0,),
        backed_up=False,
    ),
    PrdClaim(
        "§1 fatigue readings and operator population",
        r"\*\*([\d,]+)\*\* across ([\d,]+) operators",
        "SELECT COUNT(*) AS a, COUNT(DISTINCT operator_id) AS b "
        "FROM {biometric_fatigue_logs}",
        (0, 0),
    ),
    PrdClaim(
        "§2 procurement bids awaiting evaluation",
        r"([\d,]+) bids to evaluate",
        f"SELECT COUNT(*) AS a FROM {_t('procurement_bids')}",
        (0,),
        backed_up=False,
    ),
    PrdClaim(
        "§2 assay intervals vs modelled blocks",
        r"([\d,]+) assay intervals vs ([\d,]+) modelled blocks",
        "SELECT (SELECT COUNT(*) FROM {drill_assay_logs}) AS a, "
        "(SELECT COUNT(*) FROM {geological_block_models}) AS b",
        (0, 0),
    ),
    PrdClaim(
        "§4 recovery-rate variance baseline",
        r"([\d.]+) pt spread \(([\d.]+)\s*[–—-]\s*([\d.]+)\)",
        "SELECT MAX(recovery_rate_pct) - MIN(recovery_rate_pct) AS a, "
        "MIN(recovery_rate_pct) AS b, MAX(recovery_rate_pct) AS c "
        "FROM {metallurgical_recovery}",
        (0.05, 0.05, 0.05),
    ),
    PrdClaim(
        "§4 parts below reorder point baseline",
        r"Parts below reorder point \|\s*([\d,]+) of ([\d,]+) \(([\d.]+)%\)",
        "SELECT COUNTIF(stock_level < reorder_point_limit) AS a, COUNT(*) AS b, "
        "100 * COUNTIF(stock_level < reorder_point_limit) / COUNT(*) AS c "
        "FROM {inventory_levels}",
        (0, 0, 0.05),
    ),
    PrdClaim(
        "§4 CRITICAL work orders open",
        r"([\d,]+) OPEN of ([\d,]+) CRITICAL",
        "SELECT COUNTIF(priority = 'CRITICAL' AND status = 'OPEN') AS a, "
        "COUNTIF(priority = 'CRITICAL') AS b FROM {erp_work_orders}",
        (0, 0),
    ),
    PrdClaim(
        "§5.2 D08 cancelled work orders",
        r"([\d,]+) CANCELLED `erp_work_orders`",
        "SELECT COUNTIF(status = 'CANCELLED') AS a FROM {erp_work_orders}",
        (0,),
    ),
    PrdClaim(
        "§5.2 D31 below-ROP parts",
        r"([\d,]+) below-ROP parts",
        "SELECT COUNTIF(stock_level < reorder_point_limit) AS a "
        "FROM {inventory_levels}",
        (0,),
    ),
    PrdClaim(
        "§5.3 operations-safety graph edge count",
        r"richest graph \(([\d,]+) edges\)",
        "SELECT (SELECT COUNT(*) FROM {fatigue_logs_node}) + "
        f"(SELECT COUNT(*) FROM {_t('operator_vehicle_assignments')}) + "
        f"(SELECT COUNT(*) FROM {_t('incident_involvements')}) AS a",
        (0,),
    ),
)

#: The §7 assumption names the assets telemetry covers.  It is prose, not a
#: number, but it is a summary statistic about the data and the 100-agent build
#: reads it to decide which assets D01-D04 and S01 can be grounded on.
#: Groups: (cadence, window start, window end).  The asset names are pulled out
#: of the whole matched span, so the sentence can be reworded without breaking
#: the check as long as it still names the assets before the window.
_TELEMETRY_COVERAGE_PATTERN = (
    r"ASSUMPTION\*\*: Telemetry cover[^(]*"
    r"\(([\w-]+), (\d{4}-\d{2}-\d{2}) → (\d{4}-\d{2}-\d{2})\)"
)

#: Accepted spellings of a sampling cadence, keyed by the median gap in minutes.
_CADENCE_ALIASES = {
    60: {"hourly"},
    120: {"two-hourly", "2-hourly", "bi-hourly"},
    1440: {"daily"},
}


@pytest.fixture(scope="module")
def prd_text() -> str:
    assert _PRD_PATH.exists(), f"PRD not found at {_PRD_PATH}"
    return _PRD_PATH.read_text(encoding="utf-8")


def _num(text: str) -> float:
    return float(text.replace(",", ""))


_CLAIM_VALUE_ALIASES = ("a", "b", "c")


def _evaluate_claims(client, prd_text: str, suffix: str) -> list:
    """Return a list of human-readable mismatch strings for the given suffix.

    Every claim's query is padded to a fixed (idx, v0, v1, v2) shape and issued
    as one UNION ALL, so R8 costs one BigQuery round trip per suffix rather than
    one per claim.
    """
    refs = {table: _t(table, suffix) for table in _R7_TABLES}
    claims = [
        claim for claim in PRD_CLAIMS if suffix == LIVE or claim.backed_up
    ]
    width = len(_CLAIM_VALUE_ALIASES)
    selects = []
    for i, claim in enumerate(claims):
        n = len(claim.tolerances)
        assert 1 <= n <= width, f"R8 claim {claim.label!r} has {n} values"
        projected = [
            f"CAST({_CLAIM_VALUE_ALIASES[j]} AS FLOAT64) AS v{j}" for j in range(n)
        ] + [f"CAST(NULL AS FLOAT64) AS v{j}" for j in range(n, width)]
        selects.append(
            f"SELECT {i} AS idx, {', '.join(projected)} "
            f"FROM ({claim.sql.format(**refs)})"
        )
    measured = {
        row.idx: [row[f"v{j}"] for j in range(width)]
        for row in client.query("\nUNION ALL\n".join(selects)).result()
    }

    mismatches = []
    for i, claim in enumerate(claims):
        match = re.search(claim.pattern, prd_text)
        assert match, (
            f"R8 cannot find the PRD claim {claim.label!r} — the document was "
            f"reworded without updating this test (pattern: {claim.pattern})"
        )
        claimed = [_num(g) for g in match.groups()]
        assert len(claimed) == len(claim.tolerances), (
            f"R8 claim {claim.label!r} is malformed: the PRD pattern captured "
            f"{len(claimed)} values but {len(claim.tolerances)} tolerances are "
            "declared"
        )
        for j, (c, tol) in enumerate(zip(claimed, claim.tolerances)):
            m = measured[i][j]
            if abs(c - float(m)) > tol:
                mismatches.append(
                    f"{claim.label} [{j}]: PRD says {c:g}, data says {float(m):g} "
                    f"(tolerance {tol:g})"
                )
    return mismatches


def test_r8_prd_summary_statistics_still_hold(client, prd_text):
    """R8: every summary statistic quoted in the PRD is re-derivable from the data.

    Deliberately *not* a blanket comparison against data/profile/stats.json:
    crusher_states.feed_rate_tph and rotational_torque_nm are now the CRUSHER-03
    daily means derived from telemetry_stream (1153.23 / 66.16), not draws from
    the profile (1119.95 / 103.32).  That is a hard cross-table constraint and a
    correctness feature; a profile-wide check would report it as a defect.
    """
    mismatches = _evaluate_claims(client, prd_text, LIVE)

    # Telemetry coverage, quoted as prose in the §7 assumption.
    match = re.search(_TELEMETRY_COVERAGE_PATTERN, prd_text)
    assert match, "R8 cannot find the §7 telemetry-coverage assumption in the PRD"
    claimed_assets = set(re.findall(r"`([A-Z]+[A-Z0-9]*-[A-Z0-9]+)`", match.group(0)))
    assert claimed_assets, (
        "the §7 telemetry assumption names no assets — R8's coverage check "
        "would be vacuous"
    )
    telemetry_ref = _t("telemetry_stream")
    row = list(
        client.query(
            "SELECT STRING_AGG(DISTINCT asset_id, ',' ORDER BY asset_id) AS ids, "
            "FORMAT_DATE('%Y-%m-%d', MIN(DATE(timestamp))) AS lo, "
            "FORMAT_DATE('%Y-%m-%d', MAX(DATE(timestamp))) AS hi, "
            "(SELECT APPROX_QUANTILES(gap, 2)[OFFSET(1)] FROM ("
            "  SELECT TIMESTAMP_DIFF(timestamp, LAG(timestamp) OVER ("
            "    PARTITION BY asset_id, metric_name ORDER BY timestamp"
            f"  ), MINUTE) AS gap FROM {telemetry_ref}"
            ") WHERE gap IS NOT NULL) AS median_gap_minutes "
            f"FROM {telemetry_ref}"
        ).result()
    )[0]
    measured_assets = set(row.ids.split(","))
    if claimed_assets != measured_assets:
        mismatches.append(
            f"§7 telemetry coverage: PRD says {sorted(claimed_assets)}, "
            f"data holds {sorted(measured_assets)}"
        )
    if (match.group(2), match.group(3)) != (row.lo, row.hi):
        mismatches.append(
            f"§7 telemetry window: PRD says {match.group(2)} → {match.group(3)}, "
            f"data spans {row.lo} → {row.hi}"
        )
    accepted = _CADENCE_ALIASES.get(row.median_gap_minutes, set())
    if match.group(1) not in accepted:
        mismatches.append(
            f"§7 telemetry cadence: PRD says {match.group(1)!r}, median sample "
            f"gap is {row.median_gap_minutes} minutes (accepted: "
            f"{sorted(accepted) or 'no standard name'})"
        )

    assert not mismatches, (
        "the PRD quotes summary statistics the live data no longer supports — "
        "correct the figure or correct the data:\n  " + "\n  ".join(mismatches)
    )

    # Discrimination: re-derive the same claims from the frozen backups.  The
    # PRD describes the regenerated data, so several must now disagree.
    old = _evaluate_claims(client, prd_text, BACKUP_SUFFIX)
    assert old, (
        "R8 does not discriminate: every PRD figure is equally true of the "
        "pre-regeneration tables"
    )


# ===========================================================================
# R9 — contract leakage is a minority of on-contract transactions
# ===========================================================================

LEAKAGE_BAND = (0.10, 0.32)


def _leak_rate(leakage_prob: float | None = None) -> tuple[float, int]:
    """(fraction of on-contract transactions paid above agreed price, n)."""
    contracts = CTR.build_contracts()
    if leakage_prob is None:
        tx = CTR.build_contract_transactions(contracts)
    else:
        original = CTR.LEAKAGE_PROB
        CTR.LEAKAGE_PROB = leakage_prob
        try:
            tx = CTR.build_contract_transactions(contracts)
        finally:
            CTR.LEAKAGE_PROB = original
    on = tx.dropna(subset=["contract_id"]).copy()
    assert not on.empty, "no on-contract transactions generated"
    agreed = contracts.set_index("contract_id").agreed_unit_price
    on["agreed"] = on.contract_id.map(agreed)
    return float((on.paid_unit_price > on.agreed).mean()), len(on)


def test_r9_contract_leakage_is_a_minority_not_all_and_not_none():
    """R9: leakage rate over on-contract transactions sits in [0.10, 0.32].

    An agent that reports 100% of transactions leaking has found a generator
    artefact, not a finding — and 0% would mean the whole driver is inert.
    Both extremes are checked as explicit mutations below, not asserted by
    argument: forcing every transaction to leak, and forcing none to, must
    each independently fall outside the band this test polices.
    """
    low, high = LEAKAGE_BAND
    rate, n = _leak_rate()
    assert low <= rate <= high, (
        f"leakage rate {rate:.4f} over {n} on-contract transactions outside "
        f"[{low}, {high}]"
    )

    zero_rate, _ = _leak_rate(leakage_prob=0.0)
    assert not (low <= zero_rate <= high), (
        f"R9 does not discriminate: forcing LEAKAGE_PROB=0.0 still gives a "
        f"rate ({zero_rate:.4f}) inside the band"
    )
    all_rate, _ = _leak_rate(leakage_prob=1.0)
    assert not (low <= all_rate <= high), (
        f"R9 does not discriminate: forcing LEAKAGE_PROB=1.0 still gives a "
        f"rate ({all_rate:.4f}) inside the band"
    )


# ===========================================================================
# R10 — contract coverage is incomplete
# ===========================================================================

COVERAGE_GAP_BAND = (0.20, 0.60)


def _coverage_gap(n_spot_parts: int | None = None,
                   renewal_gap_days: int | None = None) -> tuple[float, int]:
    """(fraction of ALL contract_transactions with contract_id NULL, n)."""
    orig_spot, orig_gap = CTR.N_SPOT_PARTS, CTR.RENEWAL_GAP_DAYS
    if n_spot_parts is not None:
        CTR.N_SPOT_PARTS = n_spot_parts
    if renewal_gap_days is not None:
        CTR.RENEWAL_GAP_DAYS = renewal_gap_days
    try:
        contracts = CTR.build_contracts()
        tx = CTR.build_contract_transactions(contracts)
    finally:
        CTR.N_SPOT_PARTS, CTR.RENEWAL_GAP_DAYS = orig_spot, orig_gap
    return float(tx.contract_id.isna().mean()), len(tx)


def test_r10_contract_coverage_is_incomplete():
    """R10: the fraction of transactions with no live contract is in [0.20, 0.60].

    Two independent sources feed this gap (uncontracted spot parts, and the
    renewal gap between a lapsing contract and its replacement) — see
    contracts.py's module docstring. Removing both must collapse the gap
    below the band.
    """
    low, high = COVERAGE_GAP_BAND
    gap, n = _coverage_gap()
    assert low <= gap <= high, (
        f"contract coverage gap {gap:.4f} over {n} transactions outside "
        f"[{low}, {high}]"
    )

    collapsed, _ = _coverage_gap(n_spot_parts=0, renewal_gap_days=0)
    assert not (low <= collapsed <= high), (
        f"R10 does not discriminate: removing both gap sources still gives a "
        f"gap ({collapsed:.4f}) inside the band"
    )


# ===========================================================================
# R11 — warranty expiry produces a real cliff, not a uniform distribution
# ===========================================================================

ELIGIBILITY_SPREAD_MIN = 0.85
CLIFF_DIFFERENTIAL_MIN = 0.85
CLIFF_ASSETS = ("CRUSHER-03", "MILL-01", "PUMP-104A")


def _eligibility(plan=None):
    repairs = WTY.load_completed_repairs()
    cliff_dates = WTY.cliff_cutoff_date_by_asset(repairs)
    entitlements = WTY.build_entitlements(cliff_dates, plan=plan or WTY.ENTITLEMENT_PLAN)
    repairs = repairs.assign(
        eligible=[
            WTY._active_entitlement(entitlements, r.asset_id, r.created_at) is not None
            for r in repairs.itertuples()
        ]
    )
    return repairs, entitlements, cliff_dates


def test_r11_warranty_expiry_produces_a_real_cliff():
    """R11: coverage eligibility swings sharply, both across assets and across
    a single cliff asset's own expiry date — never a smooth, coin-flip spread.
    """
    repairs, entitlements, cliff_dates = _eligibility()
    by_asset = repairs.groupby("asset_id").eligible.mean()
    spread = float(by_asset.max() - by_asset.min())
    assert spread >= ELIGIBILITY_SPREAD_MIN, (
        f"eligible-repair fraction spread across assets is only {spread:.4f} "
        f"(< {ELIGIBILITY_SPREAD_MIN}): {by_asset.to_dict()}"
    )

    weak = []
    for asset in CLIFF_ASSETS:
        cutoff = cliff_dates[asset]
        sub = repairs[repairs.asset_id == asset]
        before = sub[sub.created_at <= cutoff]
        after = sub[sub.created_at > cutoff]
        assert len(before) > 0 and len(after) > 0, (
            f"{asset}: cliff cutoff does not split its repairs into both sides"
        )
        differential = float(before.eligible.mean() - after.eligible.mean())
        if differential < CLIFF_DIFFERENTIAL_MIN:
            weak.append(f"{asset}: {differential:.4f}")
    assert not weak, (
        f"before/after eligibility differential below {CLIFF_DIFFERENTIAL_MIN} "
        "for: " + "; ".join(weak)
    )

    # Discrimination: collapse every entitlement into the same ("full")
    # coverage group and confirm the asset-spread assertion above now fails.
    uniform_plan = [dict(spec, group="full") for spec in WTY.ENTITLEMENT_PLAN]
    repairs2, _, _ = _eligibility(plan=uniform_plan)
    spread2 = float(
        repairs2.groupby("asset_id").eligible.mean().max()
        - repairs2.groupby("asset_id").eligible.mean().min()
    )
    assert spread2 < ELIGIBILITY_SPREAD_MIN, (
        f"R11 does not discriminate: a uniform coverage plan still gives a "
        f"spread of {spread2:.4f} across assets"
    )


# ===========================================================================
# R11b — repairs inside warranty cover are a genuine minority, not ~everything
# ===========================================================================

#: A producing mine's fleet is mostly past its OEM warranty window at any
#: given moment: heavy mining equipment typically carries 12-24 months of
#: manufacturer cover from commissioning, so a mixed-age fleet has a minority
#: of assets -- and their repairs -- inside any live coverage window, not the
#: near-total coverage a too-broad synthetic window produces. Not zero either:
#: an own-cost-repair finding needs a real, non-trivial population of covered
#: repairs to draw from.
COVERAGE_MINORITY_BAND = (0.15, 0.35)


def _shipped_coverage_fraction(client) -> tuple[float, int]:
    """(fraction of distinct completed repairs matched by >=1 live
    `warranty_entitlements` row, total distinct repairs) -- measured directly
    against the tables that actually shipped to BigQuery, joined and DE-
    DUPLICATED on work_order_id so a repair matched by both of an asset's two
    entitlements is counted once, not twice.
    """
    df = _frame(
        client,
        f"""
        SELECT
          COUNT(DISTINCT wo.work_order_id) AS total,
          COUNT(DISTINCT IF(we.entitlement_id IS NOT NULL, wo.work_order_id, NULL))
            AS inside
        FROM {_t('erp_work_orders')} wo
        JOIN {_t('maintenance_logs')} ml USING (work_order_id)
        LEFT JOIN {_t('warranty_entitlements')} we
          ON we.asset_id = wo.asset_id
         AND DATE(wo.created_at) BETWEEN we.coverage_start AND we.coverage_end
        """,
    )
    row = df.iloc[0]
    total = int(row.total)
    assert total > 0, "the shipped work-order/maintenance-log join is empty"
    return float(row.inside) / total, total


def test_r11b_repairs_inside_cover_are_a_genuine_minority(client):
    """R11b: the fraction of shipped repairs an active warranty entitlement
    actually covers is a minority, in [0.15, 0.35] -- not the ~everything a
    coverage window spanning the whole work-order window would produce (a
    naive analyst join measured 150 of 152 "inside cover" against an earlier
    version of this data, before the coverage windows were narrowed to
    straddle the work-order window instead of enclosing it), and not zero,
    which would make AGT-13's own-cost-repair finding trivial by
    construction.

    Measured against the live `warranty_entitlements` / `erp_work_orders` /
    `maintenance_logs` tables in BigQuery -- the tables that actually ship --
    not an in-memory recomputation.
    """
    low, high = COVERAGE_MINORITY_BAND
    fraction, n = _shipped_coverage_fraction(client)
    assert low <= fraction <= high, (
        f"fraction of shipped repairs inside warranty cover = {fraction:.4f} "
        f"over {n} distinct repairs, outside [{low}, {high}]"
    )

    # Discrimination: the same "collapse every entitlement into 'full'"
    # mutation R11 uses -- every repair becomes eligible, which must land
    # far outside a minority band.
    uniform_plan = [dict(spec, group="full") for spec in WTY.ENTITLEMENT_PLAN]
    repairs2, _, _ = _eligibility(plan=uniform_plan)
    collapsed = float(repairs2.eligible.mean())
    assert not (low <= collapsed <= high), (
        f"R11b does not discriminate: a uniform 'full' coverage plan still "
        f"gives a fraction ({collapsed:.4f}) inside the minority band"
    )


# ===========================================================================
# R12 — the contained-metal reference price is a persistent series, not noise
# ===========================================================================

LAG1_PRICE_BAND = (0.55, 0.95)


def _shipped_price_deck_lag1(client) -> tuple[float, int]:
    """Lag-1 autocorrelation of `contained_metal_price_deck`, measured
    directly against the table live in BigQuery -- not
    `capital.build_price_deck()` called in-memory, and specifically not the
    old `plan_assumptions.assumed_value` column, whose 6 quarterly points per
    metric give only 5 lag-1 pairs: not a measurable autocorrelation at all.
    An earlier version of this test measured an in-memory series that was
    never shipped as its own table; the actual `plan_assumptions` table's
    lag-1 correlation on its sparse quarterly points was ~0.07 -- the
    contained-metal price deck below is what makes this property real.
    """
    df = _frame(
        client,
        f"""
        SELECT contained_metal_price_usd_per_tonne
        FROM {_t('contained_metal_price_deck')}
        ORDER BY price_date
        """,
    )
    series = df.contained_metal_price_usd_per_tonne.to_numpy(dtype=float)
    assert len(series) >= 50, (
        f"contained_metal_price_deck has only {len(series)} rows — too few "
        "for a meaningful lag-1 measurement"
    )
    return float(np.corrcoef(series[:-1], series[1:])[0, 1]), len(series)


def _generator_price_deck_lag1(phi: float | None = None) -> float:
    """Same measurement, recomputed in-memory from the generator function —
    used only for the mutation-testing discrimination checks below, which
    perturb a generator constant rather than reload BigQuery.
    """
    if phi is None:
        series = CAP.build_price_deck().contained_metal_price_usd_per_tonne.to_numpy()
    else:
        original = CAP.PRICE_DECK_OU_PHI
        CAP.PRICE_DECK_OU_PHI = phi
        try:
            series = CAP.build_price_deck().contained_metal_price_usd_per_tonne.to_numpy()
        finally:
            CAP.PRICE_DECK_OU_PHI = original
    return float(np.corrcoef(series[:-1], series[1:])[0, 1])


def test_r12_contained_metal_price_autocorrelation_in_band(client):
    """R12: lag-1 autocorrelation of the shipped `contained_metal_price_deck`
    table is in [0.55, 0.95] — a plausible mean-reverting random walk, not
    white noise. Never tied to a named metal anywhere in this measurement.
    """
    low, high = LAG1_PRICE_BAND
    live, n = _shipped_price_deck_lag1(client)
    assert low <= live <= high, (
        f"contained-metal price deck lag-1 autocorrelation {live:.4f} over "
        f"{n} rows, outside [{low}, {high}]"
    )

    # Discrimination 1: an i.i.d. shuffle of the exact same shipped values.
    df = _frame(
        client,
        f"SELECT contained_metal_price_usd_per_tonne "
        f"FROM {_t('contained_metal_price_deck')} ORDER BY price_date",
    )
    series = df.contained_metal_price_usd_per_tonne.to_numpy(dtype=float)
    shuffled = series.copy()
    np.random.default_rng(0).shuffle(shuffled)
    shuffled_lag1 = float(np.corrcoef(shuffled[:-1], shuffled[1:])[0, 1])
    assert not (low <= shuffled_lag1 <= high), (
        f"R12 does not discriminate: a shuffled version of the same shipped "
        f"values still autocorrelates at {shuffled_lag1:.4f}"
    )

    # Discrimination 2: phi=0 means independent draws, not a random walk.
    independent = _generator_price_deck_lag1(phi=0.0)
    assert not (low <= independent <= high), (
        f"R12 does not discriminate: PRICE_DECK_OU_PHI=0.0 still "
        f"autocorrelates at {independent:.4f}"
    )


# ===========================================================================
# R13 — plan assumptions go stale at differing rates
# ===========================================================================

STALENESS_SPREAD_MIN = 4  # of 6 plan versions
STALENESS_SPREAD_METRIC_COUNT = len(CAP.ASSUMPTION_METRICS)


def _supersede_counts(hazard_override: float | None = None) -> pd.Series:
    plan_versions = CAP.build_plan_versions()
    if hazard_override is None:
        pa = CAP.build_plan_assumptions(plan_versions)
    else:
        original = CAP.ASSUMPTION_METRICS
        CAP.ASSUMPTION_METRICS = {
            name: (spec[0], spec[1], spec[2], spec[3], hazard_override, spec[5], spec[6])
            for name, spec in original.items()
        }
        try:
            pa = CAP.build_plan_assumptions(plan_versions)
        finally:
            CAP.ASSUMPTION_METRICS = original
    return pa.groupby("metric_name").apply(lambda g: int(g.superseded_date.notna().sum()))


def test_r13_assumption_staleness_differs_by_metric():
    """R13: how often an assumption goes stale before the next scheduled
    review differs sharply by metric — a volatile one (contained-metal price)
    supersedes almost every cycle, a stable one (discount rate) almost never.
    """
    counts = _supersede_counts()
    assert len(counts) == STALENESS_SPREAD_METRIC_COUNT
    spread = int(counts.max() - counts.min())
    assert spread >= STALENESS_SPREAD_MIN, (
        f"supersede-count spread across metrics is only {spread} "
        f"(< {STALENESS_SPREAD_MIN}): {counts.to_dict()}"
    )

    # Discrimination: force every metric's hazard to 0 — a deterministic
    # collapse to zero supersessions everywhere, spread == 0.
    collapsed = _supersede_counts(hazard_override=0.0)
    collapsed_spread = int(collapsed.max() - collapsed.min())
    assert collapsed_spread < STALENESS_SPREAD_MIN, (
        f"R13 does not discriminate: a zero hazard for every metric still "
        f"gives a spread of {collapsed_spread}"
    )
