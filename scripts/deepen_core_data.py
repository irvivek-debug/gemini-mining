"""Deepen the estate's thinnest tables to a size that supports analysis.

WHY THESE THREE
assets held 5 rows -- one crusher, one mill, one pump, one conveyor, one truck.
An asset-integrity or reliability agent asked to rank a maintenance portfolio
could only ever name five things, which is a floor on what the product can
demonstrate rather than a fact about the mine. inventory_levels and stockpiles
were thin for the same reason.

WHAT IS PRESERVED
The five original assets are kept verbatim, ids and all, because
telemetry_stream, crusher_states, maintenance_logs and lube_samples already key
to them -- replacing them would break every one of those joins. New assets
extend the register; they do not replace it.

New stockpiles stay anchored to the real locations named in haulage_routes and
carry grades drawn from the block model's own distribution, so a blending
figure computed from stockpiles still reconciles with geology.

Seeded, so a re-run reproduces the same estate.
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
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "generated"
SEED = 20260822


def bq(sql: str) -> list[dict]:
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
                        "--format=json", "--max_rows=5000", sql], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"query failed:\n{p.stderr.strip()}")
    return json.loads(p.stdout or "[]")


def load(name: str, rows: list[dict], schema: str) -> None:
    f = OUT / f"{name}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "load", "--replace",
                        "--source_format=NEWLINE_DELIMITED_JSON",
                        f"{DATASET}.{name}", str(f), schema], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"load {name} failed:\n{p.stderr.strip()}")
    print(f"  {name:<22} {len(rows):>4} rows")


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--load", action="store_true")
    args = ap.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    # Pinned by id, not "whatever is in the table now". Reading the live table
    # made this generator append to its own previous output: a second run took
    # assets from 88 to 171 and carried the first run's mistakes forward. The
    # seed set is the five assets the dataset shipped with, which every
    # telemetry, crusher_states, maintenance_logs and lube_samples row keys to.
    SEED_ASSETS = ("CRUSHER-03", "MILL-01", "PUMP-104A", "CONVEYOR-02", "TRUCK-08")
    existing = bq(f"SELECT * FROM `{PROJECT}.{DATASET}.assets` "
                  f"WHERE asset_id IN {SEED_ASSETS} ORDER BY asset_id")
    if len(existing) != len(SEED_ASSETS):
        raise SystemExit(f"expected the {len(SEED_ASSETS)} original assets, found "
                         f"{len(existing)} — refusing to rebuild the register from a "
                         f"partial seed")
    routes = bq(f"SELECT DISTINCT source_location, destination_location "
                f"FROM `{PROJECT}.{DATASET}.haulage_routes`")
    blocks = bq(f"SELECT copper_grade_pct_est FROM `{PROJECT}.{DATASET}.geological_block_models` "
                f"WHERE copper_grade_pct_est IS NOT NULL")
    # Same reasoning: only the parts the dataset shipped with, never the
    # extensions this script added on a previous run.
    inv = bq(f"SELECT * FROM `{PROJECT}.{DATASET}.inventory_levels` "
             f"WHERE NOT STARTS_WITH(part_number, 'SKU-EXT-') ORDER BY part_number")

    locs = sorted({r["source_location"] for r in routes} | {r["destination_location"] for r in routes})
    stock_locs = [l for l in locs if "Stockpile" in l] or ["Stockpile East"]
    grades = [float(b["copper_grade_pct_est"]) for b in blocks]
    mean_g = sum(grades) / len(grades)

    # ---- assets: keep all five originals, extend the register around them
    FLEET = [("HAUL_TRUCK", "CAT 797F Haul Truck", 22), ("EXCAVATOR", "Hitachi EX3600 Excavator", 4),
             ("DOZER", "CAT D11 Track Dozer", 6), ("DRILL_RIG", "Epiroc PV-351 Blasthole Drill", 5),
             ("GRADER", "CAT 24M Motor Grader", 3), ("WATER_CART", "CAT 777 Water Cart", 3)]
    PLANT = [("CRUSHER", "Metso MP1000 Cone Crusher", 3), ("GRINDING_MILL", "SAG/Ball Mill", 4),
             ("CONVEYOR", "Overland Conveyor", 8), ("PUMP", "Warman Slurry Pump", 9),
             ("FLOTATION_CELL", "Outotec TankCell e300", 6), ("THICKENER", "High-Rate Thickener", 3),
             ("SCREEN", "Vibrating Screen", 4), ("SUBSTATION", "11kV Substation", 3)]
    # The five originals define the real column semantics, and my first pass
    # got three of them wrong: criticality_rating carries CRITICAL/HIGH (not
    # A/B/C), current_state holds a JSON of LIVE SENSOR READINGS (not a status
    # word), and location_gis is WKT POINT(lon lat) (not a place name).
    # physics_parameters holds solver constants. Writing status strings into
    # current_state would have handed every asset agent two incompatible
    # vocabularies in one column.
    STATE_BY_TYPE = {
        "HAUL_TRUCK":     lambda r: {"speed_kmh": round(r.uniform(8, 46), 1),
                                     "payload_tons": round(r.uniform(140, 232), 1),
                                     "engine_temp_c": round(r.uniform(78, 104), 1)},
        "EXCAVATOR":      lambda r: {"bucket_passes_per_hour": round(r.uniform(28, 62), 1),
                                     "hydraulic_pressure_bar": round(r.uniform(240, 350), 1),
                                     "engine_temp_c": round(r.uniform(74, 99), 1)},
        "DOZER":          lambda r: {"blade_load_pct": round(r.uniform(45, 95), 1),
                                     "engine_temp_c": round(r.uniform(72, 98), 1)},
        "DRILL_RIG":      lambda r: {"penetration_rate_m_per_min": round(r.uniform(0.4, 1.9), 2),
                                     "rotary_torque_nm": round(r.uniform(2800, 6200), 1)},
        "GRADER":         lambda r: {"speed_kmh": round(r.uniform(6, 28), 1),
                                     "engine_temp_c": round(r.uniform(70, 95), 1)},
        "WATER_CART":     lambda r: {"tank_level_pct": round(r.uniform(5, 100), 1),
                                     "speed_kmh": round(r.uniform(8, 34), 1)},
        "CRUSHER":        lambda r: {"rotational_torque_nm": round(r.uniform(3200, 4600), 1),
                                     "feed_rate_tph": round(r.uniform(880, 1340), 1),
                                     "gap_size_setting_mm": round(r.uniform(110, 165), 1),
                                     "temperature_c": round(r.uniform(58, 92), 1)},
        "GRINDING_MILL":  lambda r: {"rotational_speed_rpm": round(r.uniform(11, 17), 1),
                                     "power_draw_mw": round(r.uniform(2.8, 5.4), 2),
                                     "temperature_c": round(r.uniform(70, 96), 1)},
        "CONVEYOR":       lambda r: {"speed_mps": round(r.uniform(2.8, 5.6), 2),
                                     "belt_tension_kn": round(r.uniform(18, 34), 1),
                                     "load_pct": round(r.uniform(42, 97), 1)},
        "PUMP":           lambda r: {"vibration_hz": round(r.uniform(6, 19), 1),
                                     "temperature_c": round(r.uniform(62, 94), 1),
                                     "rotational_speed_rpm": round(r.uniform(900, 1480), 1)},
        "FLOTATION_CELL": lambda r: {"air_flow_m3_per_min": round(r.uniform(4, 13), 2),
                                     "froth_depth_mm": round(r.uniform(60, 220), 1)},
        "THICKENER":      lambda r: {"underflow_density_pct": round(r.uniform(48, 68), 1),
                                     "rake_torque_pct": round(r.uniform(20, 78), 1)},
        "SCREEN":         lambda r: {"stroke_mm": round(r.uniform(6, 14), 1),
                                     "load_pct": round(r.uniform(40, 96), 1)},
        "SUBSTATION":     lambda r: {"load_mw": round(r.uniform(1.2, 9.4), 2),
                                     "temperature_c": round(r.uniform(28, 71), 1)},
    }
    assets = list(existing)
    have = {a["asset_id"] for a in assets}
    for group in (FLEET, PLANT):
        for atype, name, count in group:
            for i in range(1, count + 1):
                aid = f"{atype.split('_')[0][:8]}-{i:02d}"
                while aid in have:
                    i += 1
                    aid = f"{atype.split('_')[0][:8]}-{i:02d}"
                have.add(aid)
                state = STATE_BY_TYPE.get(atype, lambda r: {"load_pct": round(r.uniform(30, 95), 1)})(rng)
                assets.append({
                    "asset_id": aid, "asset_name": f"{name} {i:02d}", "asset_type": atype,
                    # Same vocabulary the originals use, extended downward.
                    "criticality_rating": rng.choices(
                        ["CRITICAL", "HIGH", "MEDIUM", "LOW"], [0.16, 0.30, 0.34, 0.20])[0],
                    "installation_date": (dt.date(2018, 1, 1) +
                                          dt.timedelta(days=rng.randrange(2800))).isoformat(),
                    # WKT POINT near the site's own coordinates, as the
                    # originals record it.
                    "location_gis": (f"POINT({116.8532 + rng.uniform(-0.06, 0.06):.4f} "
                                     f"{-23.1189 + rng.uniform(-0.05, 0.05):.4f})"),
                    "current_state": json.dumps(state),
                    "physics_parameters": json.dumps({
                        "alpha": round(rng.uniform(0.008, 0.05), 4),
                        "friction_mu": round(rng.uniform(0.009, 0.04), 4),
                        "cooling_k": round(rng.uniform(0.02, 0.09), 4)}),
                })

    # ---- inventory: extend with named consumables the register lacked
    KINDS = ["Bearing", "Seal Kit", "Hydraulic Hose", "Filter Element", "Liner Plate",
             "Coupling", "Gearbox Assembly", "Impeller", "Drive Belt", "Sensor Module",
             "Valve Actuator", "Wear Plate", "Screen Panel", "Pump Shaft", "Motor Winding"]
    FITS = sorted({a["asset_type"] for a in assets})
    inventory = list(inv)
    seen = {r["part_number"] for r in inventory}
    i = 0
    while len(inventory) < 140:
        i += 1
        pn = f"SKU-EXT-{i:04d}"
        if pn in seen:
            continue
        seen.add(pn)
        kind = rng.choice(KINDS); fits = rng.choice(FITS)
        lead = rng.choice([7, 14, 21, 28, 45, 60, 90])
        stock = rng.randrange(0, 260)
        inventory.append({
            "part_number": pn,
            "part_description": f"{kind} — {fits.replace('_',' ').title()}",
            "stock_level": stock,
            "reorder_point_limit": max(2, int(stock * rng.uniform(0.25, 1.4))),
            "lead_time_days": lead,
            "unit_price_usd": round(rng.uniform(28, 14200), 2)})

    # ---- stockpiles: more lifts per real location, graded from the block model
    stock = []
    n = 0
    for li, loc in enumerate(stock_locs, 1):
        for j in range(1, 31):
            n += 1
            stock.append({"stockpile_id": f"SP-{li:02d}-{j:02d}", "location": loc,
                          "as_at": (dt.date(2025, 9, 3) + dt.timedelta(days=rng.randrange(330))).isoformat(),
                          "material_class": rng.choices(
                              ["ROM Ore", "Low Grade", "Oxide", "Waste", "Blend Feed"],
                              [0.34, 0.24, 0.14, 0.16, 0.12])[0],
                          "tonnes": round(rng.uniform(3_000, 96_000), 1),
                          "contained_grade_pct": round(mean_g * rng.uniform(0.62, 1.42), 4),
                          "moisture_pct": round(rng.uniform(2.0, 9.6), 2),
                          "reclaim_rate_tph": round(rng.uniform(380, 1900), 1)})

    T = [("assets", assets,
          "asset_id:STRING,asset_name:STRING,asset_type:STRING,current_state:STRING,"
          "criticality_rating:STRING,installation_date:DATE,location_gis:STRING,physics_parameters:STRING"),
         ("inventory_levels", inventory,
          "part_number:STRING,part_description:STRING,stock_level:INT64,"
          "reorder_point_limit:INT64,lead_time_days:INT64,unit_price_usd:FLOAT64"),
         ("stockpiles", stock,
          "stockpile_id:STRING,location:STRING,as_at:DATE,material_class:STRING,tonnes:FLOAT64,"
          "contained_grade_pct:FLOAT64,moisture_pct:FLOAT64,reclaim_rate_tph:FLOAT64")]
    print(f"originals preserved: {len(existing)} assets, {len(inv)} parts\n")
    for name, rows, schema in T:
        if args.load:
            load(name, rows, schema)
        else:
            print(f"  {name:<22} {len(rows):>4} rows (dry run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
