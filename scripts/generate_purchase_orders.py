"""Generate `purchase_orders` from parts and vendors that already exist.

WHY THIS TABLE IS GENERATED AND THE OTHER TWO ARE VIEWS
`vendor_contracts` and `spares_inventory` are views because `contracts` and
`inventory_levels` already hold what the S10 and S11 agents need under a
different name. `purchase_orders` has no equivalent anywhere in the dataset,
so it is the one table here that is genuinely new.

It is still not invented from nothing. Every row draws its part from
`inventory_levels` (and inherits that part's lead_time_days and
unit_price_usd), its vendor from `contracts`, and its contract_id from a
contract that actually covers that part — so a lead-time query, a price query
and a coverage query all reconcile against the tables they join to.

Delivery performance is the signal S11-2-LEADTIME exists to read, so it is
deliberately spread: most orders land inside the quoted lead time, a minority
run late, and a few are still open. The spread is produced by a seeded
generator, so re-running this reproduces the same table rather than quietly
changing every figure under the tests that pin them.

Usage:
    python scripts/generate_purchase_orders.py            # write JSONL only
    python scripts/generate_purchase_orders.py --load     # also load BigQuery
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import random
import subprocess


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
DATASET = os.environ.get("MINING_DATASET", "mining_data")
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "contracts" / "_purchase_orders.jsonl"

# Fixed so the table is reproducible. Changing it changes every row.
SEED = 20260821
# The window the rest of the dataset sits in.
WINDOW_START = dt.date(2025, 9, 3)
WINDOW_END = dt.date(2026, 8, 1)
# Orders are weighted by whether the part is under contract, and that is a
# fact about procurement rather than a convenience here: a high-volume
# consumable gets a supply agreement precisely because it is ordered
# constantly, while a one-off spare is bought ad hoc. Weighting them equally
# produced 307 uncovered orders against 8 covered ones, which is not a coverage
# gap — it is 102 parts that were never going to have a contract in a dataset
# that only contracts three SKUs.
#
# Expanding `contracts` instead was the other option and was rejected:
# tests/method/test_declared_packs.py pins no_contract == 69, valid_window ==
# 95 and a 42.1% coverage gap against the live table. Those numbers are a
# measured finding the contract-integrity driver exists to surface, and adding
# rows would silently invalidate them.
ORDERS_CONTRACTED_PART = 26
ORDERS_UNCONTRACTED_PART = 1


def bq(sql: str) -> list[dict]:
    p = subprocess.run(
        ["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
         "--format=json", "--max_rows=5000", sql],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"query failed:\n{p.stderr.strip()}")
    return json.loads(p.stdout or "[]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    args = ap.parse_args()

    parts = bq(f"SELECT part_number, part_description, lead_time_days, unit_price_usd "
               f"FROM `{PROJECT}.{DATASET}.inventory_levels` ORDER BY part_number")
    contracts = bq(f"SELECT contract_id, vendor_name, part_number, agreed_unit_price, "
                   f"effective_from, effective_to FROM `{PROJECT}.{DATASET}.contracts`")
    if not parts:
        raise SystemExit("inventory_levels is empty — nothing to order")

    by_part: dict[str, list[dict]] = {}
    for c in contracts:
        by_part.setdefault(c["part_number"], []).append(c)
    vendors = sorted({c["vendor_name"] for c in contracts})

    rng = random.Random(SEED)
    span = (WINDOW_END - WINDOW_START).days
    rows, n = [], 0

    for part in parts:
        pn = part["part_number"]
        lead = int(part["lead_time_days"])
        base_price = float(part["unit_price_usd"])
        covering = by_part.get(pn, [])
        n_orders = ORDERS_CONTRACTED_PART if covering else ORDERS_UNCONTRACTED_PART

        for _ in range(n_orders):
            n += 1
            ordered = WINDOW_START + dt.timedelta(days=rng.randrange(span))
            promised = ordered + dt.timedelta(days=lead)

            # A contract covers the order only when one exists for the part AND
            # the order falls inside its term. Orders outside every term are
            # left uncovered on purpose: that is the coverage gap the contract
            # -integrity method is meant to surface, not an oversight here.
            match = next(
                (c for c in covering
                 if dt.date.fromisoformat(c["effective_from"]) <= ordered
                 <= dt.date.fromisoformat(c["effective_to"])),
                None,
            )
            vendor = match["vendor_name"] if match else rng.choice(vendors)
            unit_price = float(match["agreed_unit_price"]) if match else round(base_price * rng.uniform(0.97, 1.09), 2)

            roll = rng.random()
            if roll < 0.12:
                received = None                                    # still open
                slip = None
            elif roll < 0.34:
                slip = rng.randint(3, 21)                           # late
                received = promised + dt.timedelta(days=slip)
            else:
                slip = -rng.randint(0, 4)                           # on time or early
                received = promised + dt.timedelta(days=slip)

            qty = rng.choice([2, 4, 5, 8, 10, 12, 20])
            rows.append({
                "po_id": f"PO-{n:05d}",
                "part_number": pn,
                "part_description": part["part_description"],
                "vendor_name": vendor,
                "contract_id": match["contract_id"] if match else None,
                "order_date": ordered.isoformat(),
                "promised_date": promised.isoformat(),
                "received_date": received.isoformat() if received else None,
                "quoted_lead_time_days": lead,
                "actual_lead_time_days": (received - ordered).days if received else None,
                "qty_ordered": qty,
                "unit_price_usd": unit_price,
                "line_value_usd": round(qty * unit_price, 2),
            })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    late = sum(1 for r in rows if r["actual_lead_time_days"] is not None
               and r["actual_lead_time_days"] > r["quoted_lead_time_days"])
    open_ = sum(1 for r in rows if r["received_date"] is None)
    covered = sum(1 for r in rows if r["contract_id"])
    print(f"{len(rows)} purchase orders -> {OUT.name}")
    print(f"  contract-covered: {covered}   uncovered: {len(rows) - covered}")
    print(f"  received late: {late}   still open: {open_}")

    if args.load:
        schema = ("po_id:STRING,part_number:STRING,part_description:STRING,vendor_name:STRING,"
                  "contract_id:STRING,order_date:DATE,promised_date:DATE,received_date:DATE,"
                  "quoted_lead_time_days:INT64,actual_lead_time_days:INT64,qty_ordered:INT64,"
                  "unit_price_usd:FLOAT64,line_value_usd:FLOAT64")
        p = subprocess.run(
            ["bq", f"--project_id={PROJECT}", "load", "--replace",
             "--source_format=NEWLINE_DELIMITED_JSON",
             f"{DATASET}.purchase_orders", str(OUT), schema],
            capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit(f"load failed:\n{p.stderr.strip()}")
        print("  loaded into BigQuery")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
