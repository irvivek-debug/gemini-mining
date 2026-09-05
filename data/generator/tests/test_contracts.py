"""Tests for data/generator/contracts.py (Task 2b — AGT-14 contract data).

Verifies the four tables' schemas, that every foreign key resolves (bid_id ->
procurement_bids, part_number -> inventory_levels/rfp_items, contract_id ->
contracts), and the design invariants the module docstring states: leakage and
coverage-gap counts are sane, rebate tiers are ordered, and invoice
duplication is present but a minority. The banded realism properties (leakage
fraction, coverage-gap fraction) are tested in ``test_realism.py`` R9/R10 —
this file is schema and provenance, not statistics.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import pytest
from google.cloud import bigquery

from config import PROJECT_ID, DATASET
import contracts as C


@pytest.fixture(scope="module")
def client():
    return bigquery.Client(project=PROJECT_ID)


@pytest.fixture(scope="module")
def built():
    contracts = C.build_contracts()
    transactions = C.build_contract_transactions(contracts)
    rebate_claims = C.build_rebate_claims(contracts, transactions)
    invoices = C.build_invoices(transactions)
    return {
        "contracts": contracts,
        "contract_transactions": transactions,
        "rebate_claims": rebate_claims,
        "invoices": invoices,
    }


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class TestSchema:
    def test_contracts_columns(self, built):
        assert list(built["contracts"].columns) == [
            "contract_id", "vendor_name", "part_number", "agreed_unit_price",
            "effective_from", "effective_to", "bid_id", "rebate_schedule",
        ]

    def test_contract_transactions_columns(self, built):
        assert list(built["contract_transactions"].columns) == [
            "transaction_id", "contract_id", "vendor_name", "part_number",
            "paid_unit_price", "transaction_date",
        ]

    def test_rebate_claims_columns(self, built):
        assert list(built["rebate_claims"].columns) == [
            "claim_id", "contract_id", "period", "amount_claimed", "amount_entitled",
        ]

    def test_invoices_columns(self, built):
        assert list(built["invoices"].columns) == [
            "invoice_id", "vendor_name", "invoice_number", "amount", "payment_date",
        ]

    def test_primary_keys_unique(self, built):
        assert built["contracts"].contract_id.is_unique
        assert built["contract_transactions"].transaction_id.is_unique
        assert built["rebate_claims"].claim_id.is_unique
        assert built["invoices"].invoice_id.is_unique

    def test_row_counts_nonzero_and_stable_across_two_builds(self):
        # Determinism: two independent builds from the same seed must agree
        # exactly, the same guarantee test_supply_chain.py pins elsewhere.
        c1 = C.build_contracts()
        c2 = C.build_contracts()
        pd.testing.assert_frame_equal(c1, c2)
        t1 = C.build_contract_transactions(c1)
        t2 = C.build_contract_transactions(c2)
        pd.testing.assert_frame_equal(t1, t2)


# ---------------------------------------------------------------------------
# Foreign keys — every one must actually resolve
# ---------------------------------------------------------------------------


class TestForeignKeys:
    def test_contracts_bid_id_resolves_to_accepted_procurement_bids(self, built, client):
        bid_ids = set(
            r.bid_id for r in client.query(
                f"SELECT bid_id FROM `{PROJECT_ID}.{DATASET}.procurement_bids` "
                "WHERE bid_status = 'ACCEPTED'"
            ).result()
        )
        missing = set(built["contracts"].bid_id) - bid_ids
        assert not missing, f"contract bid_id(s) not an ACCEPTED bid: {missing}"

    def test_contracts_part_number_resolves_to_inventory_levels(self, built, client):
        parts = set(
            r.part_number for r in client.query(
                f"SELECT part_number FROM `{PROJECT_ID}.{DATASET}.inventory_levels`"
            ).result()
        )
        missing = set(built["contracts"].part_number) - parts
        assert not missing, f"contract part_number(s) missing from inventory_levels: {missing}"

    def test_contracts_part_number_matches_rfp_items_scope(self, built, client):
        scoped = set(
            r.part_number for r in client.query(
                f"SELECT part_number FROM `{PROJECT_ID}.{DATASET}.rfp_items`"
            ).result()
        )
        assert set(built["contracts"].part_number) <= scoped, (
            "a contract exists for a part_number rfp_items never scoped"
        )

    def test_on_contract_transactions_resolve_to_a_real_contract(self, built):
        contracts = built["contracts"]
        tx = built["contract_transactions"]
        on = tx[tx.contract_id.notna()]
        missing = set(on.contract_id) - set(contracts.contract_id)
        assert not missing, f"contract_transactions.contract_id(s) dangling: {missing}"

    def test_off_contract_transactions_exist_and_are_null(self, built):
        tx = built["contract_transactions"]
        off = tx[tx.contract_id.isna()]
        assert len(off) > 0, "no off-contract (NULL contract_id) transactions generated"

    def test_rebate_claims_contract_id_resolves(self, built):
        contracts = built["contracts"]
        claims = built["rebate_claims"]
        assert len(claims) > 0, "no rebate claim rows generated"
        missing = set(claims.contract_id) - set(contracts.contract_id)
        assert not missing, f"rebate_claims.contract_id(s) dangling: {missing}"

    def test_invoices_vendor_name_matches_a_transaction_vendor(self, built):
        tx_vendors = set(built["contract_transactions"].vendor_name)
        inv_vendors = set(built["invoices"].vendor_name)
        assert inv_vendors <= tx_vendors


# ---------------------------------------------------------------------------
# Design invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_agreed_unit_price_is_a_discount_off_catalogue_list_price(self, built):
        inv = C.load_inventory().set_index("part_number").unit_price_usd
        for row in built["contracts"].itertuples():
            list_price = float(inv[row.part_number])
            assert 0.0 < row.agreed_unit_price < list_price, (
                f"{row.contract_id}: agreed {row.agreed_unit_price} is not a "
                f"discount off list {list_price}"
            )

    def test_rebate_schedule_is_valid_json_with_two_increasing_tiers(self, built):
        for row in built["contracts"].itertuples():
            tiers = json.loads(row.rebate_schedule)
            assert len(tiers) == 2
            assert tiers[0]["tier_threshold_usd"] < tiers[1]["tier_threshold_usd"]
            assert tiers[0]["tier_rate_pct"] < tiers[1]["tier_rate_pct"]

    def test_rebate_amount_claimed_never_exceeds_amount_entitled(self, built):
        claims = built["rebate_claims"]
        over = claims[claims.amount_claimed > claims.amount_entitled + 0.01]
        assert over.empty, f"rebate claim(s) exceed entitlement: {over.claim_id.tolist()}"

    def test_rebate_claims_are_a_genuine_mix_of_full_partial_and_abandoned(self, built):
        claims = built["rebate_claims"]
        full = (claims.amount_claimed >= claims.amount_entitled - 0.01).sum()
        zero = (claims.amount_claimed == 0.0).sum()
        assert full > 0, "no rebate period was ever fully claimed"
        assert zero > 0, "no rebate entitlement was ever abandoned"
        assert full < len(claims), "every rebate period was fully claimed — no leakage to find"

    def test_invoice_duplicates_exist_but_are_a_minority(self, built):
        invoices = built["invoices"]
        dup_groups = invoices.groupby(["vendor_name", "amount"]).size()
        duplicated_rows = int(dup_groups[dup_groups > 1].sum())
        assert duplicated_rows > 0, "no duplicate-looking invoices at all"
        assert duplicated_rows < len(invoices) * 0.5, (
            "more than half the invoices look duplicated — not a minority"
        )

    def test_exact_duplicate_invoices_match_on_every_named_column(self, built):
        invoices = built["invoices"]
        exact = invoices[
            invoices.duplicated(
                subset=["vendor_name", "invoice_number", "amount", "payment_date"],
                keep=False,
            )
        ]
        assert len(exact) > 0, "no exact (vendor/invoice_number/amount/date) duplicates"

    def test_all_dates_inside_the_operational_window_family(self, built):
        # Transactions/invoices must sit inside the same window erp_work_orders
        # and maintenance_logs use; contract effective ranges may extend
        # outside it (a contract predates and outlives the observed window).
        tx_dates = pd.to_datetime(built["contract_transactions"].transaction_date, utc=True)
        assert tx_dates.min() >= C.WINDOW_START
        assert tx_dates.max() <= C.WINDOW_END
