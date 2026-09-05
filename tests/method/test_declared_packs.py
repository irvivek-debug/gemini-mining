"""The three packs authored against agents whose data did not exist yet:
AGT-13 (warranty), AGT-14 (contract integrity), AGT-19 (strategic planning).

`contracts`, `contract_transactions`, `rebate_claims`, `invoices`,
`warranty_entitlements`, `warranty_claims`, `plan_versions`,
`plan_assumptions`, `plan_scenarios`, `capital_options` and
`contained_metal_price_deck` now exist, so ten of the sixteen drivers across
these three packs carry a fixed diagnostic and are `instrumented`. The
remaining six stay `not_instrumented` for a measured reason each, stated in
the pack's own module docstring — not_instrumented is still a full, honest
answer (see test_p6_pack.py, test_p3_pack.py), never a gap dropped from the
tree.

This file holds three kinds of test:
  - structural tests against every driver in all three packs, regardless of
    status: every SQL file that is named exists, every SQL file uses
    @parameters rather than literals, no guard carries a verdict word or
    describes a specific dataset, and status is one of the two the schema
    allows.
  - a single pinned map of every driver's status, so a driver silently
    flipped in either direction fails one assertion instead of drifting
    unnoticed through the rest of the suite.
  - `@pytest.mark.integration` tests against live BigQuery, one or more per
    instrumented driver, pinning the measured magnitude the way
    test_p6_pack.py pins `[23, 116, 28]` — a test that only checks the query
    runs is not a reproduction.
"""
import re
from pathlib import Path

import pytest

from mining_agents.method.pack import load_pack
from mining_agents.tools.bq_query import assert_no_interpolation, run_query

ROOT = Path(__file__).resolve().parents[2]

PACKS = {
    "agt13": ROOT / "method" / "agt13-warranty.yaml",
    "agt14": ROOT / "method" / "agt14-contract-integrity.yaml",
    "agt19": ROOT / "method" / "agt19-strategic-planning.yaml",
}

# The definitive status of every driver in all three packs. A driver flipped
# in either direction — instrumented without the data to back it, or left
# not_instrumented after its data arrived — fails this one map rather than
# drifting unnoticed through the rest of the file.
DRIVER_STATUS = {
    "agt13": {
        "entitlement_coverage": "instrumented",
        "expired_unclaimed": "instrumented",
        "own_cost_repairs": "instrumented",
        "evidence_completeness": "not_instrumented",
        "claim_cycle_time": "instrumented",
    },
    "agt14": {
        "price_variance": "instrumented",
        "contract_coverage": "instrumented",
        "bid_to_contract_terms": "not_instrumented",
        "rebate_entitlement": "instrumented",
        "duplicate_payment": "instrumented",
        "clause_attribution": "instrumented",
    },
    "agt19": {
        "assumption_staleness": "instrumented",
        "reversal_cost": "instrumented",
        "local_vs_group_divergence": "not_instrumented",
        "capital_option_dominance": "not_instrumented",
        "plan_output_completeness": "not_instrumented",
    },
}

# Tables the still-not_instrumented drivers' questions must name, so the
# question keeps doubling as the data-generator's spec for what remains
# missing. Drivers that flipped to instrumented dropped the "Requires X
# table" framing entirely (see test_p3_pack.py / test_p6_pack.py style), so
# they are deliberately absent from this map.
EXPECTED_TABLES_FOR_DECLARED = {
    "agt13": {"warranty_claims", "maintenance_logs"},
    "agt14": {"procurement_bids", "rfp_items"},
    "agt19": {
        "site_plans",
        "group_plan",
        "capital_options",
        "option_outcomes",
        "plan_versions",
        "plan_assumptions",
        "plan_scenarios",
        "plan_output_checklist",
    },
}

TABLE_TOKEN = re.compile(r"`([a-z][a-z0-9_]*)`")

VERDICT_WORDS = ("too few", "too many", "unevidenced", "no signal", "insufficient")

# Table lists for the integration tests below, mirroring test_p3_pack.py's
# BOTH / INCIDENT_TABLES / FATIGUE_TABLES constants.
AGT13_ENTITLEMENT_TABLES = [
    "mining_data.maintenance_logs",
    "mining_data.erp_work_orders",
    "mining_data.warranty_entitlements",
    "mining_data.warranty_claims",
]
AGT13_CLAIM_CYCLE_TABLES = [
    "mining_data.warranty_claims",
    "mining_data.erp_work_orders",
    "mining_data.warranty_entitlements",
]
AGT14_CONTRACT_TXN_TABLES = ["mining_data.contract_transactions", "mining_data.contracts"]
AGT14_REBATE_TABLES = ["mining_data.rebate_claims", "mining_data.contracts"]
AGT14_INVOICE_TABLES = ["mining_data.invoices"]
AGT19_ASSUMPTION_TABLES = [
    "mining_data.plan_assumptions",
    "mining_data.plan_versions",
    "mining_data.contained_metal_price_deck",
]
AGT19_SCENARIO_TABLES = ["mining_data.plan_scenarios", "mining_data.plan_versions"]


def _driver(pack_name, driver_id):
    pack = load_pack(PACKS[pack_name])
    return next(d for d in pack.drivers if d.id == driver_id)


# --------------------------------------------------------------------------
# Structural tests — no BigQuery required.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", PACKS)
def test_the_pack_loads_with_at_least_four_drivers(name):
    pack = load_pack(PACKS[name])
    assert len(pack.drivers) >= 4, (
        f"{name}: only {len(pack.drivers)} drivers; an empty or near-empty "
        "pack must not pass"
    )
    ids = [d.id for d in pack.drivers]
    assert len(set(ids)) == len(ids), f"{name}: duplicate driver ids {ids}"


@pytest.mark.parametrize("name", PACKS)
def test_every_driver_status_matches_the_pinned_map(name):
    pack = load_pack(PACKS[name])
    statuses = {d.id: d.status for d in pack.drivers}
    assert statuses == DRIVER_STATUS[name], (
        f"{name}: loaded statuses {statuses} do not match the pinned map "
        f"{DRIVER_STATUS[name]} — a driver's instrumentation state changed "
        "without this test being updated to match"
    )


@pytest.mark.parametrize("name", PACKS)
def test_every_named_sql_file_exists(name):
    for driver in load_pack(PACKS[name]).drivers:
        if driver.sql:
            assert (ROOT / "method" / driver.sql).is_file(), driver.sql


@pytest.mark.parametrize("name", PACKS)
def test_every_diagnostic_uses_parameters_not_literals(name):
    for driver in load_pack(PACKS[name]).drivers:
        if driver.sql:
            assert_no_interpolation((ROOT / "method" / driver.sql).read_text())


@pytest.mark.parametrize("name", PACKS)
def test_not_instrumented_drivers_carry_no_sql_or_compare(name):
    # load_pack already refuses sql/compare on a not_instrumented driver at
    # load time; this is a second, independent check directly on the parsed
    # Driver objects, restricted to the drivers this file expects to still be
    # declared.
    pack = load_pack(PACKS[name])
    for driver in pack.drivers:
        if driver.status != "not_instrumented":
            continue
        assert driver.sql is None, f"{name}/{driver.id}: carries sql {driver.sql!r}"
        assert driver.compare is None, (
            f"{name}/{driver.id}: carries compare {driver.compare!r}"
        )


@pytest.mark.parametrize("name", PACKS)
def test_instrumented_drivers_carry_sql_and_a_guard(name):
    pack = load_pack(PACKS[name])
    for driver in pack.drivers:
        if driver.status != "instrumented":
            continue
        assert driver.sql, f"{name}/{driver.id}: instrumented but carries no sql"
        assert driver.guard, f"{name}/{driver.id}: instrumented but carries no guard"


@pytest.mark.parametrize("name", PACKS)
def test_no_guard_holds_a_verdict_word(name):
    """A guard is the method's caveat, true before any row is read."""
    pack = load_pack(PACKS[name])
    for driver in pack.drivers:
        said = (driver.guard or "").lower()
        for verdict in VERDICT_WORDS:
            assert verdict not in said, (
                f"{name}/{driver.id}: guard says {verdict!r}, which decides "
                "a diagnostic's result before it runs"
            )


@pytest.mark.parametrize("name", PACKS)
def test_no_guard_describes_the_data(name):
    """'in this dataset' is the marker of a guard describing data, not a
    measurement. See test_p3_pack.py::test_no_guard_describes_the_data for
    the full rationale; this pins the same rule on the three packs here.
    """
    pack = load_pack(PACKS[name])
    for driver in pack.drivers:
        said = (driver.guard or "").lower()
        assert "in this dataset" not in said, (
            f"{name}/{driver.id}: guard contains 'in this dataset', which "
            "describes the data rather than the measurement"
        )


@pytest.mark.parametrize("name", PACKS)
def test_every_not_instrumented_question_names_its_missing_tables(name):
    """Each still-not_instrumented driver's question doubles as the
    generator's spec for what remains missing. A question with no table
    named in it is a wish, not a spec.
    """
    pack = load_pack(PACKS[name])
    seen_tables = set()
    for driver in pack.drivers:
        if driver.status != "not_instrumented":
            continue
        tables = set(TABLE_TOKEN.findall(driver.question))
        assert tables, (
            f"{name}/{driver.id}: question names no table (no `backtick`-quoted "
            f"identifier found): {driver.question!r}"
        )
        seen_tables |= tables
    missing = EXPECTED_TABLES_FOR_DECLARED[name] - seen_tables
    assert not missing, f"{name}: expected tables never named: {missing}"


def test_agt19_states_the_permanent_l1_ceiling():
    """PRD §8.1: AGT-19 is the one agent whose authority can never be
    promoted. The Pack schema has no authority field, so this is stated in
    the file's own prose; the test reads the raw text because load_pack()
    strips comments along with everything else YAML doesn't parse into the
    schema.
    """
    text = PACKS["agt19"].read_text().lower()
    assert "permanently l1" in text or "permanent l1" in text, (
        "agt19-strategic-planning.yaml never states the permanent L1 ceiling"
    )
    assert "no promotion path" in text, (
        "agt19-strategic-planning.yaml never states that AGT-19 has no "
        "promotion path"
    )


@pytest.mark.parametrize("name", PACKS)
def test_no_pack_names_a_metal_or_a_dollar_amount(name):
    """Commodity-neutral and money-as-ranges are constraints inherited from
    the design doc. A named metal or a bare currency figure would break a
    fork that mines something else, or assert a precision this build cannot
    back.
    """
    text = PACKS[name].read_text().lower()
    for metal in ("copper", "gold", "iron ore", "nickel", "zinc", "lithium"):
        assert metal not in text, f"{name}: names a specific commodity {metal!r}"
    assert "$" not in text, f"{name}: contains a currency symbol"


@pytest.mark.parametrize("name", PACKS)
def test_no_pack_references_the_data_generator(name):
    """A customer forks this repo and inherits every word in it. A pack that
    told the reader 'this is synthetic/demo data' would be lying to every
    fork that has replaced that data with its own.
    """
    text = PACKS[name].read_text().lower()
    for phrase in ("synthetic data", "data generator", "demo dataset", "demo data"):
        assert phrase not in text, f"{name}: references {phrase!r}"


# --------------------------------------------------------------------------
# Integration tests — live BigQuery, one block per instrumented driver.
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_entitlement_coverage_returns_work_order_grain_not_the_inflated_join():
    """The trap this driver exists to catch.

    Ten warranty_entitlements rows span five assets, two component-level
    entitlements per asset, and both of an asset's rows usually share the
    same coverage window. Joining a repair to warranty_entitlements on
    asset_id alone therefore matches both of an asset's entitlements, so a
    naive join returns one row per (repair, matching entitlement) pair
    rather than one row per repair. This test reproduces that naive count
    directly — independently of the shipped SQL — and asserts the shipped
    diagnostic returns the smaller, work-order-grain count instead.
    """
    driver = _driver("agt13", "entitlement_coverage")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT13_ENTITLEMENT_TABLES,
    )
    # The shipped diagnostic: one row per work order.
    work_order_ids = [r["work_order_id"] for r in rows]
    assert len(work_order_ids) == len(set(work_order_ids)), (
        "entitlement_coverage returned duplicate work_order_id rows; the "
        "diagnostic must aggregate to work-order grain"
    )
    assert len(rows) == 38, f"expected 38 distinct covered work orders, got {len(rows)}"

    # The naive join this driver exists to avoid: asset_id alone, no
    # aggregation. Built here rather than shipped, precisely so the shipped
    # SQL cannot regress toward it unnoticed.
    naive_sql = """
    SELECT m.work_order_id, w.entitlement_id
    FROM `mining_data.maintenance_logs` m
    JOIN `mining_data.erp_work_orders` wo ON wo.work_order_id = m.work_order_id
    JOIN `mining_data.warranty_entitlements` w
      ON m.asset_id = w.asset_id
     AND DATE(wo.created_at) BETWEEN w.coverage_start AND w.coverage_end
    """
    naive_rows, _ = run_query(naive_sql, {}, AGT13_ENTITLEMENT_TABLES)
    assert len(naive_rows) == 76, (
        f"expected the naive asset-only join to return 76 rows, got "
        f"{len(naive_rows)}; if this number changed, the trap this driver "
        "guards against may no longer be reproducible against live data"
    )
    assert len(rows) != len(naive_rows), (
        "the shipped diagnostic returned the same row count as the naive "
        "asset-only join; it is no longer aggregating to work-order grain"
    )

    # Every returned row must show the multiplicity the guard warns about —
    # not just that the count worked out to 38 by coincidence.
    assert {r["matching_entitlement_count"] for r in rows} == {2}, (
        "expected every covered work order to match exactly 2 component "
        "entitlements on its asset"
    )

    unclaimed = [r for r in rows if not r["has_claim"]]
    assert len(unclaimed) == 26, f"expected 26 unclaimed work orders, got {len(unclaimed)}"
    assert len(rows) - len(unclaimed) == 12, (
        f"expected 12 claimed work orders, got {len(rows) - len(unclaimed)}"
    )
    assert round(sum(r["repair_cost_usd"] for r in rows), 2) == 233360.0
    assert round(sum(r["repair_cost_usd"] for r in unclaimed), 2) == 152055.0


@pytest.mark.integration
def test_expired_unclaimed_reproduces_the_closed_window_split():
    driver = _driver("agt13", "expired_unclaimed")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT13_ENTITLEMENT_TABLES,
    )
    assert len(rows) == 14, f"expected 14 repairs in an already-closed window, got {len(rows)}"
    unclaimed = [r for r in rows if not r["has_claim"]]
    assert len(unclaimed) == 10, f"expected 10 unclaimed among them, got {len(unclaimed)}"
    assert round(sum(r["repair_cost_usd"] for r in unclaimed), 2) == 44380.0


@pytest.mark.integration
def test_own_cost_repairs_reproduces_the_open_window_split():
    driver = _driver("agt13", "own_cost_repairs")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT13_ENTITLEMENT_TABLES,
    )
    assert len(rows) == 16, f"expected 16 unclaimed repairs in a still-open window, got {len(rows)}"
    assert round(sum(r["repair_cost_usd"] for r in rows), 2) == 107675.0
    # own_cost_repairs.sql filters to NOT has_claim, so no returned row's
    # entitlement window may already be closed — a floor of 26 total
    # unclaimed (own_cost + expired_unclaimed) is the split this pair of
    # drivers partitions.
    assert len(rows) + 10 == 26, "own_cost_repairs and expired_unclaimed must partition the 26 unclaimed repairs"


@pytest.mark.integration
def test_claim_cycle_time_reproduces_the_filing_gap_and_the_over_100_cases():
    """Some claims are filed after their own entitlement window has closed —
    pct_window_consumed_at_filing exceeds 100 for four of the twelve claims.
    A query that clamped or dropped these would understate exactly the
    finding this driver is for.
    """
    driver = _driver("agt13", "claim_cycle_time")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT13_CLAIM_CYCLE_TABLES,
    )
    assert len(rows) == 12, f"expected 12 filed claims, got {len(rows)}"
    over_100 = [r for r in rows if r["pct_window_consumed_at_filing"] > 100]
    assert len(over_100) == 4, (
        f"expected 4 claims filed after their own coverage_end, got {len(over_100)}"
    )
    mean_days = sum(r["days_repair_to_filing"] for r in rows) / len(rows)
    assert round(mean_days, 2) == 17.75, mean_days
    assert max(r["pct_window_consumed_at_filing"] for r in rows) == 103.6
    assert min(r["pct_window_consumed_at_filing"] for r in rows) == 60.1


@pytest.mark.integration
def test_price_variance_reproduces_the_measured_leakage():
    driver = _driver("agt14", "price_variance")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT14_CONTRACT_TXN_TABLES,
    )
    assert len(rows) == 10, f"expected 10 contracts with at least one transaction, got {len(rows)}"
    total_txn = sum(r["transaction_count"] for r in rows)
    total_above = sum(r["above_agreed_count"] for r in rows)
    assert total_txn == 95, f"expected 95 contract-linked transactions, got {total_txn}"
    assert total_above == 19, f"expected 19 transactions paid above the agreed price, got {total_above}"
    # 20.0% is the measured leakage rate this driver exists to surface.
    assert round(total_above / total_txn * 100, 1) == 20.0
    assert round(sum(r["leakage_usd"] for r in rows), 2) == 2979.93


@pytest.mark.integration
def test_contract_coverage_reproduces_the_null_contract_rate():
    driver = _driver("agt14", "contract_coverage")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT14_CONTRACT_TXN_TABLES,
    )
    by_state = {r["coverage_state"]: r["transaction_count"] for r in rows}
    assert by_state.get("no_contract") == 69, by_state
    assert by_state.get("valid_window") == 95, by_state
    assert "unknown_contract" not in by_state and "outside_window" not in by_state, (
        "no transaction in this build cites a dangling or out-of-window "
        f"contract_id; unexpected buckets present: {by_state}"
    )
    total = sum(by_state.values())
    assert total == 164, f"expected 164 total transactions, got {total}"
    # 42.1% is the measured coverage gap this driver exists to surface.
    assert round(by_state["no_contract"] / total * 100, 1) == 42.1


@pytest.mark.integration
def test_rebate_entitlement_reproduces_the_unclaimed_gap():
    driver = _driver("agt14", "rebate_entitlement")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT14_REBATE_TABLES,
    )
    assert len(rows) == 6, f"expected 6 filed rebate claims, got {len(rows)}"
    total_gap = round(sum(r["unclaimed_rebate_usd"] for r in rows), 2)
    assert total_gap == 1086.84, total_gap
    fully_unclaimed = [r for r in rows if r["amount_claimed"] == 0.0]
    assert len(fully_unclaimed) == 2, (
        f"expected 2 claims with zero amount_claimed, got {len(fully_unclaimed)}"
    )


@pytest.mark.integration
def test_duplicate_payment_reproduces_the_exact_and_fuzzy_pairs():
    driver = _driver("agt14", "duplicate_payment")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT14_INVOICE_TABLES,
    )
    by_type = {r["match_type"]: r for r in rows}
    assert set(by_type) == {"exact_duplicate", "fuzzy_duplicate"}, set(by_type)
    assert by_type["exact_duplicate"]["pair_count"] == 8, by_type["exact_duplicate"]
    assert by_type["fuzzy_duplicate"]["pair_count"] == 2, by_type["fuzzy_duplicate"]
    assert round(by_type["exact_duplicate"]["amount_at_risk_usd"], 2) == 344111.24
    assert round(by_type["fuzzy_duplicate"]["amount_at_risk_usd"], 2) == 148890.5


@pytest.mark.integration
def test_assumption_staleness_reproduces_the_price_deck_evidence():
    """0.6712 lag-1 autocorrelation over 60 monthly pairs, and an
    8,297.5–9,750.1 observed range — pinned here rather than re-derived.
    """
    driver = _driver("agt19", "assumption_staleness")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT19_ASSUMPTION_TABLES,
    )
    assert len(rows) == 7, f"expected 7 metric_name rows, got {len(rows)}"
    by_metric = {r["metric_name"]: r for r in rows}
    price = by_metric["contained_metal_price_usd_per_tonne"]
    assert price["superseded_count"] == 6, price
    assert price["price_lag1_autocorr"] == 0.6712, price
    assert price["price_lag1_pairs"] == 60, price
    assert price["price_min_usd_per_tonne"] == 8297.5, price
    assert price["price_max_usd_per_tonne"] == 9750.1, price
    assert price["mean_days_stale_before_review"] == 71.3, price
    assert price["min_days_stale_before_review"] == 65, price
    assert price["max_days_stale_before_review"] == 77, price
    # Every other metric_name carries no independent series: its price
    # columns must be NULL, not zero and not the price metric's own value.
    for name, row in by_metric.items():
        if name == "contained_metal_price_usd_per_tonne":
            continue
        assert row["price_lag1_autocorr"] is None, (
            f"{name}: price_lag1_autocorr should be NULL for a metric with "
            "no independently observed series"
        )
    # discount_rate_pct never carries a superseded_date across all six plan
    # versions in this build — a genuinely stable assumption, not a query
    # defect, and its staleness columns must reflect that with NULL rather
    # than zero.
    discount = by_metric["discount_rate_pct"]
    assert discount["superseded_count"] == 0, discount
    assert discount["mean_days_stale_before_review"] is None, discount


@pytest.mark.integration
def test_reversal_cost_reproduces_the_per_plan_version_split():
    driver = _driver("agt19", "reversal_cost")
    rows, _ = run_query(
        (ROOT / "method" / driver.sql).read_text(), driver.params,
        AGT19_SCENARIO_TABLES,
    )
    assert len(rows) == 6, f"expected 6 plan versions, got {len(rows)}"
    total_scenarios = sum(r["scenario_count"] for r in rows)
    assert total_scenarios == 12, (
        f"expected all 12 plan_scenarios rows accounted for, got {total_scenarios}"
    )
    by_version = {r["plan_version_id"]: r for r in rows}
    assert by_version["PV-2025-Q1"]["min_reversal_cost_usd"] == 22068966.97
    assert by_version["PV-2025-Q1"]["max_reversal_cost_usd"] == 36436372.02
    assert by_version["PV-2026-Q1"]["min_reversal_cost_usd"] == 9132397.47
    assert by_version["PV-2026-Q1"]["max_reversal_cost_usd"] == 9917163.3
    # Every version's max must exceed its own min — a query that collapsed
    # the upside/downside pair to one value would pass a mere presence check
    # but would defeat the purpose of reporting a range at all.
    for version_id, row in by_version.items():
        assert row["max_reversal_cost_usd"] > row["min_reversal_cost_usd"], version_id
