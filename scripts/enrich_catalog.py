"""Populate the data catalog for the BQ Data Agent showcase tables.

The Conversational Analytics engine retrieves table and column descriptions
through BigQuery's metadata layer (Dataplex Universal Catalog). Before this
script, 0 of 10 showcase tables had a description and 11 of 581 columns did:
the agent was working from column names alone. Descriptions written here are
business language — the mining jargon a presenter will actually use (CSS,
TML, laycan, demurrage) — so natural-language prompts land without naming
columns.

Idempotent: re-running overwrites the same descriptions.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_probes import PROJECT, bq
import subprocess


def ddl(sql: str) -> None:
    """DDL returns no rows; bq() insists on parsing JSON rows and dies on the
    success message. Run DDL raw and fail loudly on a non-zero exit."""
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query",
                        "--nouse_legacy_sql", sql], capture_output=True, text=True)
    if p.returncode != 0:
        import time
        time.sleep(5)          # transient DDL failures happen; one retry
        p = subprocess.run(["bq", f"--project_id={PROJECT}", "query",
                            "--nouse_legacy_sql", sql], capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit("DDL failed: " + (p.stderr.strip() or p.stdout.strip())[:400]
                             + "\n" + sql[:150])

DATASET = os.environ.get("MINING_DATASET", "mining_data")
DS = f"`{PROJECT}.{DATASET}`"

TABLES: dict[str, tuple[str, dict[str, str]]] = {
  "geological_block_models": (
    "Resource block model: one row per mining block with estimated (kriged) grades. "
    "The plan's view of the ore body — compare against drill_assay_logs actuals.",
    {"block_id": "Unique block identifier in the resource model",
     "copper_grade_pct_est": "Estimated (kriged) copper head grade, percent — the plan's grade",
     "gold_grade_gpt_est": "Estimated gold grade, grams per tonne",
     "lithology_type": "Modelled rock type (lithology) — joins to drill_assay_logs.geology_code",
     "specific_gravity": "Rock density used for tonnage conversion"}),
  "drill_assay_logs": (
    "Assay results from drill core: the laboratory-measured actual grades. "
    "Ground truth against the block model's estimates.",
    {"drill_hole_id": "Drill hole the sample came from",
     "copper_grade_pct": "Assayed (actual) copper grade, percent",
     "gold_grade_gpt": "Assayed gold grade, grams per tonne",
     "geology_code": "Logged rock type — joins to geological_block_models.lithology_type",
     "depth_start_meters": "Sample interval start depth", "depth_end_meters": "Sample interval end depth"}),
  "telemetry_stream": (
    "Plant sensor telemetry: every reading from fixed-plant instrumentation "
    "(vibration, belt tension, speed). The site's largest table.",
    {"metric_name": "Sensor metric, e.g. vibration_hz, belt_tension_kn, speed_kmh",
     "metric_value": "Reading value in the metric's native unit",
     "asset_id": "Plant asset that produced the reading", "timestamp": "Reading time (UTC)"}),
  "spares_inventory": (
    "Spare parts stockroom: current stock levels vs reorder points and supplier lead times. "
    "A part at_or_below_reorder is a stock-out risk.",
    {"part_number": "Spare part SKU", "stock_level": "Units on hand now",
     "reorder_point_limit": "Reorder point: at or below this level, replenishment is due",
     "lead_time_days": "Supplier lead time in days",
     "at_or_below_reorder": "TRUE when the part is at stock-out risk (stock at or below reorder point)",
     "unit_price_usd": "Unit price, USD", "stock_value_usd": "Value of stock on hand, USD"}),
  "work_order_parts_edge": (
    "Graph edge table linking maintenance work orders to the parts they consumed. "
    "Walk parts -> work orders -> assets to find which machine a stock-out stops.",
    {"work_order_id": "Work order that consumed the part (joins erp_work_orders)",
     "part_number": "Part consumed (joins spares_inventory)"}),
  "erp_work_orders": (
    "Maintenance work orders from the ERP: what was repaired on which asset and at what cost.",
    {"work_order_id": "Work order identifier", "asset_id": "Asset repaired",
     "repair_cost": "Total repair cost, USD", "priority": "Work order priority",
     "status": "Work order status", "description": "Work description"}),
  "crusher_states": (
    "Primary crusher operating states: feed rate, closed-side setting (CSS), torque, bypass. "
    "One row per state reading.",
    {"feed_rate_tph": "Crusher feed rate, tonnes per hour",
     "gap_size_setting_mm": "Closed-side setting (CSS) in millimetres — the crusher's discharge gap",
     "rotational_torque_nm": "Drive torque, newton-metres",
     "bypass_valve_open": "TRUE when the bypass is open (crusher not crushing)",
     "asset_id": "Crusher asset id", "timestamp": "Reading time (UTC)"}),
  "stockpiles": (
    "Ore stockpiles between plant and rail: tonnes on hand, contained grade, and reclaim rate. "
    "tonnes / reclaim_rate_tph = hours of buffer before run-out.",
    {"stockpile_id": "Stockpile identifier (joins rail_schedules.origin_stockpile_id)",
     "tonnes": "Tonnes currently on the pile", "contained_grade_pct": "Contained metal grade, percent",
     "reclaim_rate_tph": "Reclaim (draw-down) rate, tonnes per hour",
     "moisture_pct": "Moisture content, percent", "material_class": "Material classification"}),
  "rail_schedules": (
    "Heavy-haul rail consists from stockpile to port: origin, payload, cycle time, delays.",
    {"consist_id": "Train consist identifier (appears in port_vessels.consist_ids)",
     "origin_stockpile_id": "Stockpile the consist loads from",
     "payload_tonnes": "Payload, tonnes", "cycle_time_hours": "Round-trip cycle time, hours",
     "delayed": "TRUE if the consist ran late", "destination_port": "Destination port"}),
  "port_vessels": (
    "Vessels at the port: laycan, loading, moisture vs TML, and demurrage days incurred. "
    "consist_ids lists the rail consists that fed each vessel.",
    {"vessel_name": "Vessel name", "laycan_start": "Laycan window start (agreed loading window)",
     "loaded_tonnes": "Tonnes loaded", "demurrage_days": "Demurrage days incurred (paid delay beyond laytime)",
     "moisture_pct": "Cargo moisture, percent",
     "tml_pct": "Transportable Moisture Limit (TML) — IMSBC safety ceiling for moisture",
     "consist_ids": "Rail consists that delivered this vessel's cargo"}),
}


VIEWS = {"spares_inventory"}   # ALTER TABLE fails on a view ("DONE" yet rc!=0),
                               # and view columns cannot take DDL descriptions.


def main() -> int:
    for table, (tdesc, cols) in TABLES.items():
        kind = "VIEW" if table in VIEWS else "TABLE"
        ddl(f"ALTER {kind} {DS}.{table} SET OPTIONS (description = '''{tdesc}''')")
        described = 0
        if table not in VIEWS:
            for col, cdesc in cols.items():
                ddl(f"ALTER TABLE {DS}.{table} ALTER COLUMN {col} "
                    f"SET OPTIONS (description = '''{cdesc}''')")
            described = len(cols)
        print(f"  {table}: {kind.lower()} + {described} columns described", flush=True)

    # verify: the catalog must actually carry what we wrote
    r = bq(f"SELECT COUNTIF(option_name='description') n "
           f"FROM {DS}.INFORMATION_SCHEMA.TABLE_OPTIONS")
    c = bq(f"SELECT COUNTIF(description IS NOT NULL AND description != '') n "
           f"FROM {DS}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS")
    print(f"  VERIFIED: {r[0]['n']}/10 tables described, {c[0]['n']} columns described")
    assert int(r[0]["n"]) == 10, "table descriptions did not land"
    assert int(c[0]["n"]) >= 50, "column descriptions did not land"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
