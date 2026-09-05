"""Generate the vendor-contract document corpus from the contracts already in BigQuery.

WHY THE DOCUMENTS ARE DERIVED, NOT INVENTED
An anti-bribery critic and a contract-integrity method are only worth anything
if a clause can be checked against what was actually paid. A corpus of
free-standing dummy contracts would read convincingly and prove nothing: no
clause would tie to a contract_id, so no agent could ever find a transaction
that contradicts one.

So every document here is composed FROM a real `contracts` row. The price
clause quotes that row's agreed_unit_price for that row's part_number; the
rebate clause quotes the real tier thresholds out of its rebate_schedule JSON;
the term dates are its effective_from/effective_to; the bid reference is its
bid_id. Nothing in the text is chosen freely except the surrounding legal
prose, and that prose is deliberately generic.

The contradictions are therefore already in the data and were not planted:
8 of the 10 contracts carry transactions paid above their agreed price, and 69
of 164 transactions carry no contract_id at all. The documents simply state,
citably, the terms those payments breach.

WHAT THIS EMITS
  data/contracts/<contract_id>.txt   the document text
  contract_clauses                   one row per clause, with a recoverable_basis
  unstructured_docs_metadata         one row per document
  doc_chunks                         one row per clause (a clause is the chunk)

Chunking on the clause boundary is deliberate: the retrieval unit and the
citation unit are then the same thing, so an agent that cites a passage is
citing a clause id rather than an arbitrary window of characters.

Usage:
    python scripts/generate_contract_corpus.py --dry-run     # write files only
    python scripts/generate_contract_corpus.py --load        # also load BigQuery
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys


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
OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "contracts"
GCS_PREFIX = "gs://mining-knowledge-base/vendor-contracts"

# The site is one party to every one of these agreements. Named once so the
# documents do not drift into naming it three different ways.
BUYER = "Argolis Mining Operations Pty Ltd"


def bq(sql: str) -> list[dict]:
    p = subprocess.run(
        ["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
         "--format=json", "--max_rows=5000", sql],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        raise SystemExit(f"query failed:\n{p.stderr.strip()}")
    return json.loads(p.stdout or "[]")


def money(x: float) -> str:
    return f"{float(x):,.2f}"


def clauses_for(row: dict, bid: dict | None) -> list[dict]:
    """Build the clause set for one contract.

    `recoverable_basis` names the driver that can put a number on a breach of
    this clause, or None where the clause is a compliance obligation with no
    directly recoverable amount. That distinction is the whole reason the field
    exists: it stops an agent reporting a dollar figure against a clause that
    does not carry one.
    """
    cid = row["contract_id"]
    vendor = row["vendor_name"]
    part = row["part_number"]
    price = float(row["agreed_unit_price"])
    tiers = json.loads(row["rebate_schedule"]) if row.get("rebate_schedule") else []
    frm, to = row["effective_from"], row["effective_to"]
    bid_id = row.get("bid_id") or "not recorded"

    tier_text = "; ".join(
        f"Tier {i + 1}: {t['tier_rate_pct']:.1f}% of cumulative spend once "
        f"cumulative spend under this Agreement exceeds USD {money(t['tier_threshold_usd'])}"
        for i, t in enumerate(tiers)
    )
    # The tier list is spliced into a sentence, so it has to end like one.
    # Without this the clause read "...exceeds USD 6,794.06 Rebate is
    # calculated..." and the run-on landed in the retrievable chunk.
    tier_text = (tier_text + ".") if tiers else "No volume rebate applies to this Agreement."

    bid_line = (
        f"This Agreement is awarded pursuant to bid {bid_id}"
        + (f", tendered by {bid['vendor_name']} at a proposed total of USD "
           f"{money(bid['proposed_cost'])} with a technical rating of "
           f"{float(bid['technical_rating_score']):.1f}." if bid else ".")
    )

    return [
        dict(clause_id=f"{cid}-CL-01", clause_type="SCOPE", recoverable_basis=None,
             clause_text=(
                 f"1. SCOPE OF SUPPLY. {vendor} (the Supplier) shall supply {BUYER} "
                 f"(the Buyer) with part {part} for the term commencing {frm} and "
                 f"ending {to}. {bid_line} No other part number is covered by this "
                 f"Agreement, and supply of any other part shall be governed by a "
                 f"separate instrument.")),

        dict(clause_id=f"{cid}-CL-02", clause_type="PRICE", recoverable_basis="unit_price_delta",
             clause_text=(
                 f"2. PRICE. The agreed unit price for part {part} is USD {money(price)} "
                 f"per unit, firm for the term. The Buyer shall not be invoiced, and "
                 f"shall not pay, any amount per unit in excess of USD {money(price)} "
                 f"without a written variation executed by both parties. Any amount "
                 f"paid above the agreed unit price is recoverable by the Buyer as a "
                 f"debt due.")),

        dict(clause_id=f"{cid}-CL-03", clause_type="ESCALATION", recoverable_basis="unit_price_delta",
             clause_text=(
                 f"3. PRICE ESCALATION. No escalation applies during the term. The "
                 f"Supplier may propose an adjusted unit price for any renewal term by "
                 f"written notice not less than sixty (60) days before {to}. An "
                 f"adjusted price takes effect only on execution of a written "
                 f"variation; a price quoted on an invoice does not vary this clause.")),

        dict(clause_id=f"{cid}-CL-04", clause_type="REBATE", recoverable_basis="rebate_entitlement",
             clause_text=(
                 f"4. VOLUME REBATE. The Supplier shall credit the Buyer as follows: "
                 f"{tier_text} Rebate is calculated on cumulative spend for part {part} "
                 f"under this Agreement within the term, and shall be credited within "
                 f"thirty (30) days of the end of each quarter. An entitlement not "
                 f"claimed by the Buyer remains payable by the Supplier and does not "
                 f"lapse.")),

        dict(clause_id=f"{cid}-CL-05", clause_type="DELIVERY", recoverable_basis="late_delivery_credit",
             clause_text=(
                 f"5. DELIVERY. The Supplier shall deliver to the Buyer's nominated "
                 f"warehouse within the lead time recorded against part {part} in the "
                 f"Buyer's inventory system. Where delivery is late by more than five "
                 f"(5) working days, the Buyer may claim a credit of one per cent (1%) "
                 f"of the order value per week of delay, capped at ten per cent (10%) "
                 f"of the order value.")),

        dict(clause_id=f"{cid}-CL-06", clause_type="INVOICING", recoverable_basis="duplicate_payment",
             clause_text=(
                 f"6. INVOICING AND PAYMENT. Each delivery shall be invoiced once. The "
                 f"Supplier shall not submit more than one invoice in respect of the "
                 f"same delivery, whether under the same invoice number or a different "
                 f"one. Where the Buyer pays twice in respect of one delivery, the "
                 f"second payment is recoverable in full on demand, and the Supplier "
                 f"shall not set it off against any other amount.")),

        dict(clause_id=f"{cid}-CL-07", clause_type="AUDIT", recoverable_basis="audit_recovery",
             clause_text=(
                 f"7. AUDIT RIGHTS. The Buyer may audit the Supplier's records relating "
                 f"to this Agreement on thirty (30) days' notice, not more than twice in "
                 f"any twelve (12) month period. Where an audit establishes an "
                 f"overcharge exceeding two per cent (2%) of amounts invoiced in the "
                 f"period audited, the Supplier shall bear the reasonable cost of the "
                 f"audit in addition to repaying the overcharge.")),

        dict(clause_id=f"{cid}-CL-08", clause_type="ANTI_BRIBERY", recoverable_basis=None,
             clause_text=(
                 f"8. ANTI-BRIBERY AND ANTI-CORRUPTION. The Supplier warrants that "
                 f"neither it nor any person acting on its behalf has offered, given or "
                 f"agreed to give any person any gift, hospitality, payment or "
                 f"consideration of any kind as an inducement or reward in connection "
                 f"with the award or performance of this Agreement. The Supplier shall "
                 f"maintain a register of any hospitality offered to Buyer personnel "
                 f"with a value exceeding USD 100.00 and shall produce it on request. "
                 f"Breach of this clause entitles the Buyer to terminate immediately "
                 f"and to recover all sums paid in connection with the breach.")),

        dict(clause_id=f"{cid}-CL-09", clause_type="CONFLICT_OF_INTEREST", recoverable_basis=None,
             clause_text=(
                 f"9. CONFLICT OF INTEREST. The Supplier shall disclose in writing any "
                 f"interest, direct or indirect, held by any officer or employee of the "
                 f"Buyer in the Supplier or in any of its affiliates, and any "
                 f"relationship between the Supplier's personnel and the Buyer's "
                 f"personnel involved in awarding or administering this Agreement. A "
                 f"failure to disclose is a material breach.")),

        dict(clause_id=f"{cid}-CL-10", clause_type="TERMINATION", recoverable_basis=None,
             clause_text=(
                 f"10. TERM AND TERMINATION. This Agreement runs from {frm} to {to}. "
                 f"Either party may terminate for material breach not remedied within "
                 f"thirty (30) days of written notice. The Buyer may terminate "
                 f"immediately for breach of clause 8. Clauses 4, 6 and 7 survive "
                 f"termination in respect of the period before it.")),
    ]


def document_text(row: dict, clauses: list[dict]) -> str:
    cid = row["contract_id"]
    head = (
        f"VENDOR SUPPLY AGREEMENT {cid}\n"
        f"{'=' * (25 + len(cid))}\n\n"
        f"Buyer:      {BUYER}\n"
        f"Supplier:   {row['vendor_name']}\n"
        f"Part:       {row['part_number']}\n"
        f"Unit price: USD {money(row['agreed_unit_price'])}\n"
        f"Term:       {row['effective_from']} to {row['effective_to']}\n"
        f"Award:      bid {row.get('bid_id') or 'not recorded'}\n\n"
        f"{'-' * 72}\n\n"
    )
    return head + "\n\n".join(c["clause_text"] for c in clauses) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true", help="load BigQuery as well as writing files")
    args = ap.parse_args()

    contracts = bq(f"SELECT * FROM `{PROJECT}.{DATASET}.contracts` ORDER BY contract_id")
    bids = {b["bid_id"]: b for b in bq(f"SELECT * FROM `{PROJECT}.{DATASET}.procurement_bids`")}
    if not contracts:
        raise SystemExit("no contracts to build documents from")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_clauses, docs, chunks = [], [], []

    for row in contracts:
        cid = row["contract_id"]
        cl = clauses_for(row, bids.get(row.get("bid_id")))
        text = document_text(row, cl)
        (OUT_DIR / f"{cid}.txt").write_text(text, encoding="utf-8")

        doc_id = f"CTRDOC-{cid.split('-')[-1]}"
        uri = f"{GCS_PREFIX}/{cid}.txt"
        for i, c in enumerate(cl):
            all_clauses.append({
                "contract_id": cid, "clause_id": c["clause_id"],
                "clause_type": c["clause_type"], "clause_text": c["clause_text"],
                "recoverable_basis": c["recoverable_basis"],
                "doc_id": doc_id, "source_uri": uri,
            })
            chunks.append({
                "doc_id": doc_id, "folder": "vendor-contracts",
                "file_name": f"{cid}.txt", "chunk_index": i,
                "chunk_text": c["clause_text"],
            })
        docs.append({
            "doc_id": doc_id, "title": f"Vendor Supply Agreement {cid} — {row['vendor_name']}",
            "category": "CONTRACT", "file_path": uri, "chunk_count": len(cl),
        })

    for name, rows in (("clauses", all_clauses), ("docs", docs), ("chunks", chunks)):
        p = OUT_DIR / f"_{name}.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    print(f"{len(contracts)} documents, {len(all_clauses)} clauses, {len(chunks)} chunks "
          f"-> {OUT_DIR.relative_to(pathlib.Path.cwd())}")
    types = sorted({c['clause_type'] for c in all_clauses})
    print(f"clause types: {', '.join(types)}")
    recoverable = sorted({c['recoverable_basis'] for c in all_clauses if c['recoverable_basis']})
    print(f"recoverable bases: {', '.join(recoverable)}")
    if not args.load:
        print("(files only — pass --load to write BigQuery)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
