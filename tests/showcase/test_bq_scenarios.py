"""Feasibility gates for the BigQuery Data Agent showcase scenarios.

Each scenario in reports/bq_data_agent_showcase_prd.md is only demoable if
the data actually supports it: the tables are populated, the join paths
yield rows, and the insight-bearing signal exists. A prompt over data that
cannot answer it produces a fluent nothing — the worst possible demo.

No hardcoded expectations: every assertion is a property computed live
(a gap exists, outliers exist, the chain is non-empty), never a memorised
number that goes stale when the data deepens.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from build_probes import bq, PROJECT  # noqa: E402

pytestmark = pytest.mark.integration
DS = f"`{PROJECT}.mining_data`"


def q(sql: str):
    rows = bq(sql)
    assert rows is not None, "query returned None — transport failure, not empty data"
    return rows


# --- S1 grade reconciliation --------------------------------------------------

def test_s1_estimate_and_actual_share_a_join_key():
    rows = q(f"""
      SELECT b.lithology_type,
             AVG(b.copper_grade_pct_est) AS est,
             AVG(a.copper_grade_pct)     AS act,
             COUNT(DISTINCT b.block_id)  AS blocks
      FROM {DS}.geological_block_models b
      JOIN {DS}.drill_assay_logs a ON a.geology_code = b.lithology_type
      GROUP BY 1""")
    assert rows, "lithology_type never matches geology_code — S1's premise is dead"
    assert sum(int(r["blocks"]) for r in rows) > 100, "join covers too few blocks to matter"


def test_s1_a_reconciliation_gap_actually_exists():
    rows = q(f"""
      SELECT b.lithology_type,
             ABS(AVG(b.copper_grade_pct_est) - AVG(a.copper_grade_pct)) AS gap
      FROM {DS}.geological_block_models b
      JOIN {DS}.drill_assay_logs a ON a.geology_code = b.lithology_type
      GROUP BY 1 ORDER BY gap DESC""")
    top = float(rows[0]["gap"])
    assert top > 0.01, f"largest est-vs-actual gap is {top:.4f}pp — no story to tell"


# --- S2 anomaly hunt ----------------------------------------------------------

def test_s2_outliers_exist_to_be_found():
    rows = q(f"""
      WITH stats AS (
        SELECT metric_name, AVG(metric_value) mu, STDDEV(metric_value) sd
        FROM {DS}.telemetry_stream GROUP BY 1)
      SELECT t.metric_name, COUNT(*) AS n_outliers
      FROM {DS}.telemetry_stream t JOIN stats s USING (metric_name)
      WHERE s.sd > 0 AND ABS(t.metric_value - s.mu) > 3 * s.sd
      GROUP BY 1""")
    assert rows, "zero readings beyond 3 sigma — the anomaly hunt finds nothing"
    assert sum(int(r["n_outliers"]) for r in rows) >= 10, "too few outliers for a visible cluster"


def test_s2_an_asset_concentrates_anomalies():
    """The demo pivots on 'which asset produces the most' — needs a leader."""
    rows = q(f"""
      WITH stats AS (
        SELECT metric_name, AVG(metric_value) mu, STDDEV(metric_value) sd
        FROM {DS}.telemetry_stream GROUP BY 1)
      SELECT t.asset_id, COUNT(*) n
      FROM {DS}.telemetry_stream t JOIN stats s USING (metric_name)
      WHERE s.sd > 0 AND ABS(t.metric_value - s.mu) > 3 * s.sd
      GROUP BY 1 ORDER BY n DESC LIMIT 2""")
    assert rows and int(rows[0]["n"]) >= 3, "no asset owns a cluster of anomalies"


# --- S3 parts-to-failure graph ------------------------------------------------

def test_s3_the_two_hop_chain_is_non_empty():
    rows = q(f"""
      SELECT w.asset_id,
             COUNT(DISTINCT s.part_number) AS at_risk_parts,
             SUM(w.repair_cost)            AS hist_cost
      FROM {DS}.spares_inventory s
      JOIN {DS}.work_order_parts_edge e ON e.part_number = s.part_number
      JOIN {DS}.erp_work_orders w       ON w.work_order_id = e.work_order_id
      WHERE s.at_or_below_reorder
      GROUP BY 1""")
    assert rows, "no asset is reachable from an at-risk part — S3 has no graph to walk"
    assert any(float(r["hist_cost"] or 0) > 0 for r in rows), \
        "chain exists but carries zero repair cost — ranking has nothing to rank"


def test_s3_lead_times_differentiate_the_ranking():
    rows = q(f"""
      SELECT COUNT(DISTINCT lead_time_days) AS distinct_lead_times
      FROM {DS}.spares_inventory WHERE at_or_below_reorder""")
    assert int(rows[0]["distinct_lead_times"]) >= 2, \
        "all at-risk parts share one lead time — prompt 4's ranking logic degenerates"


# --- S4 pit-to-port cascade ---------------------------------------------------

def test_s4_the_four_hop_chain_reaches_a_vessel():
    rows = q(f"""
      SELECT sp.stockpile_id, r.consist_id, v.vessel_name, v.demurrage_days
      FROM {DS}.stockpiles sp
      JOIN {DS}.rail_schedules r ON r.origin_stockpile_id = sp.stockpile_id
      JOIN {DS}.port_vessels v   ON r.consist_id IN UNNEST(v.consist_ids)""")
    assert rows, "stockpile->rail->vessel chain is empty — the cascade cannot be traced"


def test_s4_demurrage_signal_exists():
    rows = q(f"""
      SELECT COUNT(*) AS n FROM {DS}.port_vessels WHERE demurrage_days > 0""")
    assert int(rows[0]["n"]) > 0, "no vessel ever incurred demurrage — no money at the end"


def test_s4_stockpiles_can_express_runout():
    rows = q(f"""
      SELECT COUNT(*) AS n FROM {DS}.stockpiles
      WHERE reclaim_rate_tph > 0 AND tonnes > 0""")
    assert int(rows[0]["n"]) >= 3, "too few stockpiles with reclaim rates — runout maths degenerates"


def test_s4_crusher_baseline_is_computable():
    rows = q(f"""
      SELECT AVG(feed_rate_tph) AS avg_feed FROM {DS}.crusher_states
      WHERE feed_rate_tph > 0""")
    assert rows and float(rows[0]["avg_feed"] or 0) > 0, "no crusher feed baseline for the outage maths"
