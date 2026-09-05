"""Task 2b — contract data for AGT-14 Procurement & Contract Integrity.

`method/agt14-contract-integrity.yaml` is the specification this module
implements: every driver's `question` names a table and the columns a
diagnostic needs, and this module builds exactly that data, joined correctly
to the tables that already exist (`procurement_bids`, `rfp_items`,
`inventory_levels`). Nothing here flips a driver's `status` — that is a later
task's job (Task 2c). This module only makes the data exist so that job is
possible.

Four tables, in dependency order:

    contracts             -- terms: who, what, at what price, for how long
    contract_transactions  -- purchases settled against those terms (or not)
    rebate_claims          -- volume-break entitlements, claimed or abandoned
    invoices                -- payment records, a minority accidentally duplicated

Provenance
----------
`rfp_items` has only 3 rows, covering 2 of the ~30 `rfp_id` values that
appear in `procurement_bids` (RFP-2026-10: SKU-BEARING-PUMP-G1,
SKU-BELT-SPLICE-G2; RFP-2026-11: SKU-LUBE-HEAVY-T2). A contract can only be
grounded in a bid whose *scope* is known, so contracts are built only from the
ACCEPTED bids against those two RFPs — 6 bids, 3 parts, 10 contract rows (two
vendor/part pairs each won two sequential bids, modelled as a renewal: the
earlier contract's `effective_to` precedes the later one's `effective_from`,
which is itself a source of the contract-coverage gap for transactions dated
in between). Every other `rfp_id` in `procurement_bids` has no known scope and
is not a source of contract data — inventing a part number for it would not be
data, it would be narration.

`agreed_unit_price` is anchored to `inventory_levels.unit_price_usd` (the
catalogue list price for that `part_number`) discounted by a per-contract
negotiated rate, not derived from `procurement_bids.proposed_cost` — that
figure is a lump-sum bid amount for an unstated quantity across a multi-item
RFP and cannot be divided into a unit price without inventing the split.

Neither `procurement_bids` nor `rfp_items` nor `inventory_levels` is in
`REWRITE_TABLES`, so all three are read live, matching the precedent in
`supply_chain.py` for tables Task 1 never backed up.

Realism, by design (measured and banded in `tests/test_realism.py` R9/R10)
------------------------------------------------------------------------
* **Leakage is a minority.** A transaction settled against a live contract is
  flagged a `LEAKAGE_PROB` Bernoulli draw; only a leaking transaction can pay
  above `agreed_unit_price` (by 5-28%), and every non-leaking transaction is
  drawn at or below it (93-100%). The fraction actually paid above contract is
  therefore controlled directly by `LEAKAGE_PROB`, not left to chance
  symmetry in a noise term — the target band is stated and tested, not
  discovered after the fact.
* **Coverage is incomplete on purpose.** Two sources of NULL `contract_id`:
  (1) a deliberate multi-week gap between a lapsing contract and its renewal
  for the two renewed vendor/part pairs, and (2) an entirely uncontracted
  population of spot purchases against catalogue parts that were never put
  out to tender at all. Both are real gaps a transaction can fall into, not a
  single dial.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np
import pandas as pd
from google.cloud import bigquery

from common import rng_for
from config import PROJECT_ID, DATASET, SEED

# --------------------------------------------------------------------------
# Window — must match the operational window every other table already uses
# (erp_work_orders / maintenance_logs span 2026-01-01 .. 2026-06-17).
# --------------------------------------------------------------------------

WINDOW_START = pd.Timestamp("2026-01-01", tz="UTC")
WINDOW_END = pd.Timestamp("2026-06-17", tz="UTC")

_GENERATED_DIR = os.path.join(os.path.dirname(__file__), "..", "generated")

# --------------------------------------------------------------------------
# Design parameters (not calibration — no prior data exists for these tables)
# --------------------------------------------------------------------------

#: Probability a transaction settled against a live contract pays above the
#: agreed price. This directly controls the measured leakage fraction that
#: R9 bands at [0.15, 0.35] — see the module docstring.
LEAKAGE_PROB = 0.22
LEAK_MULTIPLIER_RANGE = (1.05, 1.28)
COMPLIANT_MULTIPLIER_RANGE = (0.93, 1.00)

#: Off-contract spot purchases: parts with no RFP/contract at all, priced
#: near catalogue list (no negotiated discount, occasional spot premium).
SPOT_MULTIPLIER_RANGE = (0.98, 1.16)
N_SPOT_PARTS = 6
SPOT_TX_INTERVAL_DAYS = 16

CONTRACT_TX_INTERVAL_DAYS = 12

#: Renewal gap for the two vendor/part pairs whose winning vendor accepted
#: two sequential bids on the same RFP (see module docstring).
RENEWAL_GAP_DAYS = 14

#: Rebate tier basis is cumulative *spend* per contract per quarter (each
#: transaction's paid_unit_price stands for one settled lot — the pack names
#: no quantity column, so spend is the only volume proxy contract_transactions
#: actually carries).
REBATE_TIER1_RATE_PCT = 2.0
REBATE_TIER2_RATE_PCT = 4.5
REBATE_TIER2_MULTIPLIER = 2.2  # tier-2 threshold = tier-1 threshold * this

#: Fraction of eligible rebate periods where the site actually files a claim
#: for the full entitlement, rather than abandoning it (or filing partially).
REBATE_FULL_CLAIM_PROB = 0.30

#: Invoice duplication — a minority double-keyed (exact) or resubmitted
#: (fuzzy: same vendor/amount, different invoice_number, date drifted).
EXACT_DUPLICATE_RATE = 0.05
FUZZY_DUPLICATE_RATE = 0.02

# --------------------------------------------------------------------------
# Sources (all live — none of these three tables is in REWRITE_TABLES)
# --------------------------------------------------------------------------


def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _table(name: str) -> str:
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


def load_rfp_items() -> pd.DataFrame:
    return _client().query(
        f"SELECT rfp_id, part_number FROM {_table('rfp_items')} ORDER BY rfp_id, part_number"
    ).to_dataframe()


def load_accepted_bids() -> pd.DataFrame:
    """ACCEPTED bids against the RFPs `rfp_items` actually names a scope for."""
    rfp_ids = tuple(sorted(load_rfp_items().rfp_id.unique()))
    config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("rfp_ids", "STRING", rfp_ids)]
    )
    return _client().query(
        f"""
        SELECT bid_id, rfp_id, vendor_name, proposed_cost, technical_rating_score
        FROM {_table('procurement_bids')}
        WHERE bid_status = 'ACCEPTED' AND rfp_id IN UNNEST(@rfp_ids)
        ORDER BY rfp_id, vendor_name, bid_id
        """,
        job_config=config,
    ).to_dataframe()


def load_inventory() -> pd.DataFrame:
    return _client().query(
        f"SELECT part_number, unit_price_usd FROM {_table('inventory_levels')} "
        "ORDER BY part_number"
    ).to_dataframe()


# --------------------------------------------------------------------------
# contracts
# --------------------------------------------------------------------------


def build_contracts() -> pd.DataFrame:
    """One row per (bid, rfp_item part_number), 10 rows on the current data.

    Vendor/part pairs that won two ACCEPTED bids on the same RFP are treated
    as a renewal: the earlier bid governs an earlier term, the later bid a
    later one, with `RENEWAL_GAP_DAYS` of daylight between them so some
    transactions dated inside the gap resolve to no live contract at all.
    """
    items = load_rfp_items()
    bids = load_accepted_bids()
    prices = load_inventory().set_index("part_number").unit_price_usd

    rows = []
    for (rfp_id, vendor_name), group in bids.groupby(["rfp_id", "vendor_name"], sort=True):
        group = group.sort_values("bid_id").reset_index(drop=True)
        parts = items.loc[items.rfp_id == rfp_id, "part_number"].tolist()
        n_bids = len(group)
        for part_number in parts:
            list_price = float(prices[part_number])
            for i, bid in enumerate(group.itertuples()):
                rng = rng_for(SEED, "contract", bid.bid_id, part_number)
                discount = rng.uniform(0.05, 0.18)
                agreed_unit_price = round(list_price * (1.0 - discount), 2)

                if n_bids == 1:
                    eff_from = WINDOW_START - pd.Timedelta(days=120)
                    eff_to = WINDOW_END + pd.Timedelta(days=270)
                elif i == 0:
                    eff_from = WINDOW_START - pd.Timedelta(days=120)
                    # Renewal midpoint, staggered by lineage so not every
                    # vendor's contract lapses on the same calendar day.
                    midpoint = WINDOW_START + pd.Timedelta(
                        days=45 + int(rng.integers(0, 30))
                    )
                    eff_to = midpoint
                else:
                    eff_from = midpoint + pd.Timedelta(days=RENEWAL_GAP_DAYS)
                    eff_to = WINDOW_END + pd.Timedelta(days=270)

                tier1 = round(rng.uniform(2000.0, 6000.0), 2)
                rebate_schedule = json.dumps(
                    [
                        {
                            "tier_threshold_usd": tier1,
                            "tier_rate_pct": REBATE_TIER1_RATE_PCT,
                        },
                        {
                            "tier_threshold_usd": round(
                                tier1 * REBATE_TIER2_MULTIPLIER, 2
                            ),
                            "tier_rate_pct": REBATE_TIER2_RATE_PCT,
                        },
                    ]
                )

                rows.append(
                    {
                        "contract_id": f"CTR-{len(rows) + 1:04d}",
                        "vendor_name": vendor_name,
                        "part_number": part_number,
                        "agreed_unit_price": agreed_unit_price,
                        "effective_from": eff_from.date(),
                        "effective_to": eff_to.date(),
                        "bid_id": bid.bid_id,
                        "rebate_schedule": rebate_schedule,
                    }
                )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# contract_transactions
# --------------------------------------------------------------------------


def _governing_contract(contracts: pd.DataFrame, vendor_name: str, part_number: str,
                          tx_date: pd.Timestamp) -> Optional[str]:
    match = contracts[
        (contracts.vendor_name == vendor_name)
        & (contracts.part_number == part_number)
        & (pd.to_datetime(contracts.effective_from, utc=True) <= tx_date)
        & (pd.to_datetime(contracts.effective_to, utc=True) >= tx_date)
    ]
    if match.empty:
        return None
    return str(match.iloc[0].contract_id)


def _spot_parts(contracts: pd.DataFrame, inventory: pd.DataFrame) -> list[str]:
    contracted = set(contracts.part_number)
    candidates = sorted(set(inventory.part_number) - contracted)
    rng = rng_for(SEED, "spot-parts")
    idx = rng.choice(len(candidates), size=N_SPOT_PARTS, replace=False)
    return sorted(candidates[i] for i in idx)


def build_contract_transactions(contracts: pd.DataFrame) -> pd.DataFrame:
    inventory = load_inventory().set_index("part_number").unit_price_usd
    rows = []

    # On-contract-vendor-part transactions: one per lineage (vendor, part),
    # regardless of which specific contract row currently governs, so a
    # transaction dated inside a renewal gap correctly resolves to None.
    lineages = contracts[["vendor_name", "part_number"]].drop_duplicates()
    for lineage in lineages.itertuples():
        dates = pd.date_range(
            WINDOW_START, WINDOW_END, freq=f"{CONTRACT_TX_INTERVAL_DAYS}D", tz="UTC"
        )
        for tx_date in dates:
            contract_id = _governing_contract(
                contracts, lineage.vendor_name, lineage.part_number, tx_date
            )
            rng = rng_for(
                SEED, "tx", lineage.vendor_name, lineage.part_number, str(tx_date)
            )
            if contract_id is not None:
                agreed = float(
                    contracts.loc[contracts.contract_id == contract_id, "agreed_unit_price"].iloc[0]
                )
                is_leak = rng.random() < LEAKAGE_PROB
                if is_leak:
                    mult = rng.uniform(*LEAK_MULTIPLIER_RANGE)
                else:
                    mult = rng.uniform(*COMPLIANT_MULTIPLIER_RANGE)
                paid = round(agreed * mult, 2)
            else:
                # Renewal-gap transaction: still priced off the list price,
                # since no agreed rate governs it.
                paid = round(float(inventory[lineage.part_number]) * rng.uniform(*SPOT_MULTIPLIER_RANGE), 2)

            rows.append(
                {
                    "transaction_id": f"TXN-{len(rows) + 1:05d}",
                    "contract_id": contract_id,
                    "vendor_name": lineage.vendor_name,
                    "part_number": lineage.part_number,
                    "paid_unit_price": paid,
                    "transaction_date": tx_date.date(),
                }
            )

    # Off-contract spot purchases: parts with no RFP/contract lineage at all.
    spot_parts = _spot_parts(contracts, load_inventory())
    vendor_pool = sorted(contracts.vendor_name.unique())
    for part_number in spot_parts:
        list_price = float(inventory[part_number])
        dates = pd.date_range(
            WINDOW_START, WINDOW_END, freq=f"{SPOT_TX_INTERVAL_DAYS}D", tz="UTC"
        )
        for tx_date in dates:
            rng = rng_for(SEED, "spot-tx", part_number, str(tx_date))
            vendor_name = vendor_pool[int(rng.integers(0, len(vendor_pool)))]
            paid = round(list_price * rng.uniform(*SPOT_MULTIPLIER_RANGE), 2)
            rows.append(
                {
                    "transaction_id": f"TXN-{len(rows) + 1:05d}",
                    "contract_id": None,
                    "vendor_name": vendor_name,
                    "part_number": part_number,
                    "paid_unit_price": paid,
                    "transaction_date": tx_date.date(),
                }
            )

    return pd.DataFrame(rows).sort_values("transaction_id").reset_index(drop=True)


# --------------------------------------------------------------------------
# rebate_claims
# --------------------------------------------------------------------------


def _quarter_periods() -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    return [
        ("2026-Q1", pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-03-31", tz="UTC")),
        ("2026-Q2", pd.Timestamp("2026-04-01", tz="UTC"), pd.Timestamp("2026-06-17", tz="UTC")),
    ]


def build_rebate_claims(contracts: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    tx = transactions.dropna(subset=["contract_id"]).copy()
    tx["transaction_date"] = pd.to_datetime(tx.transaction_date, utc=True)

    rows = []
    for contract in contracts.itertuples():
        schedule = json.loads(contract.rebate_schedule)
        for period_label, start, end in _quarter_periods():
            period_tx = tx[
                (tx.contract_id == contract.contract_id)
                & (tx.transaction_date >= start)
                & (tx.transaction_date <= end)
            ]
            if period_tx.empty:
                continue
            spend = float(period_tx.paid_unit_price.sum())
            tiers_hit = [t for t in schedule if spend >= t["tier_threshold_usd"]]
            if not tiers_hit:
                continue
            best = max(tiers_hit, key=lambda t: t["tier_rate_pct"])
            amount_entitled = round(spend * best["tier_rate_pct"] / 100.0, 2)

            rng = rng_for(SEED, "rebate", contract.contract_id, period_label)
            if rng.random() < REBATE_FULL_CLAIM_PROB:
                amount_claimed = amount_entitled
            elif rng.random() < 0.5:
                amount_claimed = round(amount_entitled * rng.uniform(0.1, 0.6), 2)
            else:
                amount_claimed = 0.0

            rows.append(
                {
                    "claim_id": f"REB-{len(rows) + 1:04d}",
                    "contract_id": contract.contract_id,
                    "period": period_label,
                    "amount_claimed": amount_claimed,
                    "amount_entitled": amount_entitled,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# invoices
# --------------------------------------------------------------------------

_VENDOR_CODES = {
    "Apex Spares Ltd": "APX",
    "Atlas Mining Depot": "ATL",
    "Direct-Line Warehouse": "DLW",
    "Global Equip Corp": "GEC",
    "SiloParts Mining Supplies": "SPM",
}


def build_invoices(transactions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, txn in enumerate(transactions.itertuples()):
        rng = rng_for(SEED, "invoice", txn.transaction_id)
        qty = int(rng.integers(1, 41))
        amount = round(txn.paid_unit_price * qty, 2)
        tx_date = pd.Timestamp(txn.transaction_date, tz="UTC")
        payment_date = tx_date + pd.Timedelta(days=int(rng.integers(3, 22)))
        code = _VENDOR_CODES.get(txn.vendor_name, "VEN")
        invoice_number = f"{code}-{tx_date.strftime('%Y%m%d')}-{i % 1000:03d}"
        rows.append(
            {
                "invoice_id": f"INV-{len(rows) + 1:05d}",
                "vendor_name": txn.vendor_name,
                "invoice_number": invoice_number,
                "amount": amount,
                "payment_date": payment_date.date(),
            }
        )

    base = pd.DataFrame(rows)

    # Exact duplicates: a minority double-keyed under a new invoice_id.
    dup_rng = rng_for(SEED, "invoice-dup-exact")
    n_exact = max(1, int(round(len(base) * EXACT_DUPLICATE_RATE)))
    exact_idx = dup_rng.choice(len(base), size=n_exact, replace=False)
    exact_dupes = base.iloc[exact_idx].copy()
    exact_dupes["invoice_id"] = [
        f"INV-{len(base) + i + 1:05d}" for i in range(len(exact_dupes))
    ]

    # Fuzzy duplicates: same vendor/amount, resubmitted under a new invoice
    # number a few days later — the case a fuzzy matcher, not an exact-match
    # query, is needed to catch.
    fuzzy_rng = rng_for(SEED, "invoice-dup-fuzzy")
    n_fuzzy = max(1, int(round(len(base) * FUZZY_DUPLICATE_RATE)))
    remaining = np.setdiff1d(np.arange(len(base)), exact_idx)
    fuzzy_idx = fuzzy_rng.choice(remaining, size=min(n_fuzzy, len(remaining)), replace=False)
    fuzzy_dupes = base.iloc[fuzzy_idx].copy()
    fuzzy_dupes["invoice_id"] = [
        f"INV-{len(base) + len(exact_dupes) + i + 1:05d}" for i in range(len(fuzzy_dupes))
    ]
    fuzzy_dupes["invoice_number"] = fuzzy_dupes["invoice_number"] + "R"
    fuzzy_dupes["payment_date"] = fuzzy_dupes.apply(
        lambda r: (
            pd.Timestamp(r.payment_date, tz="UTC")
            + pd.Timedelta(days=int(fuzzy_rng.integers(1, 5)))
        ).date(),
        axis=1,
    )

    out = pd.concat([base, exact_dupes, fuzzy_dupes], ignore_index=True)
    return out[["invoice_id", "vendor_name", "invoice_number", "amount", "payment_date"]]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def write_parquet() -> dict[str, pd.DataFrame]:
    os.makedirs(_GENERATED_DIR, exist_ok=True)
    contracts = build_contracts()
    transactions = build_contract_transactions(contracts)
    rebate_claims = build_rebate_claims(contracts, transactions)
    invoices = build_invoices(transactions)

    tables = {
        "contracts": contracts,
        "contract_transactions": transactions,
        "rebate_claims": rebate_claims,
        "invoices": invoices,
    }
    for name, df in tables.items():
        df.to_parquet(os.path.join(_GENERATED_DIR, f"{name}.parquet"), index=False)
    return tables


if __name__ == "__main__":  # pragma: no cover
    tables = write_parquet()
    for name, df in tables.items():
        print(f"{name}: {len(df)} rows")
    tx = tables["contract_transactions"]
    on_contract = tx[tx.contract_id.notna()]
    leak_rate = float((on_contract.paid_unit_price >
                        on_contract.contract_id.map(
                            tables["contracts"].set_index("contract_id").agreed_unit_price
                        )).mean())
    coverage_gap = float(tx.contract_id.isna().mean())
    print(f"leakage rate (on-contract) = {leak_rate:.4f}")
    print(f"coverage gap (all transactions) = {coverage_gap:.4f}")
