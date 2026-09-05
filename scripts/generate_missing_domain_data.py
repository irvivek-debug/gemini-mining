"""Generate the declared tables that have no equivalent anywhere in mining_data.

WHY THESE ARE GENERATED AND THE OTHERS ARE VIEWS
Of the 26 tables the agent catalogue declares but does not have, 14 turned out
to be real data under a different name and became views (see
infra/ddl/declared_table_views.sql). The 12 built here have no source at all:
nothing in the dataset carries a blast design, a piezometer reading, a rail
consist, a vessel laycan or a reagent line.

EVERY ROW IS ANCHORED TO SOMETHING THAT ALREADY EXISTS
This is the difference between generated data and invented data. Blast designs
key to real block_ids from geological_block_models. Piezometers and geotech
sensors key to the real Tailings Gate and Pit Floor Bench locations named in
haulage_routes. Water balance reconciles against real metallurgical_recovery
timestamps. Rail loads out of the real stockpiles it feeds, and vessels load
from the rail that arrives. Lube samples key to real asset_ids and real
work_order_ids from maintenance_logs.

So a join across these tables resolves, and a total computed one way agrees
with the same total computed another. Free-standing random rows would satisfy
"the table exists" and fail the first question anyone asks of them.

Seeded, so a re-run reproduces the same estate rather than silently moving
every number under the tests that pin them.
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
START = dt.date(2025, 9, 3)
END = dt.date(2026, 8, 1)


def bq(sql: str) -> list[dict]:
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
                        "--format=json", "--max_rows=5000", sql],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"query failed:\n{p.stderr.strip()}")
    return json.loads(p.stdout or "[]")


def load(name: str, rows: list[dict], schema: str) -> None:
    f = OUT / f"{name}.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    spec = schema
    if ":REPEATED" in schema:
        # bq's inline schema has no syntax for a repeated field, so one is
        # written out as a JSON schema file instead.
        js = []
        for col in schema.split(","):
            bits = col.split(":")
            e = {"name": bits[0], "type": {"FLOAT64": "FLOAT", "INT64": "INTEGER"}
                 .get(bits[1], bits[1])}
            if len(bits) > 2:
                e["mode"] = bits[2]
            js.append(e)
        sf = OUT / f"_{name}.schema.json"
        sf.write_text(json.dumps(js, indent=1))
        spec = str(sf)
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "load", "--replace",
                        "--source_format=NEWLINE_DELIMITED_JSON",
                        f"{DATASET}.{name}", str(f), spec],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"load {name} failed:\n{p.stderr.strip()}")
    print(f"  {name:<26} {len(rows):>5} rows")


def d(rng, a=START, b=END):
    return a + dt.timedelta(days=rng.randrange((b - a).days))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    blocks = bq(f"SELECT block_id, centroid_x, centroid_y, centroid_z, lithology_type, "
                f"copper_grade_pct_est, gold_grade_gpt_est, specific_gravity "
                f"FROM `{PROJECT}.{DATASET}.geological_block_models` ORDER BY block_id")
    routes = bq(f"SELECT route_id, source_location, destination_location, distance_meters "
                f"FROM `{PROJECT}.{DATASET}.haulage_routes` ORDER BY route_id")
    assets = bq(f"SELECT asset_id, asset_type, asset_name FROM `{PROJECT}.{DATASET}.assets`")
    recov = bq(f"SELECT timestamp, concentrator_id, feed_grade_pct, recovery_rate_pct "
               f"FROM `{PROJECT}.{DATASET}.metallurgical_recovery` ORDER BY timestamp")
    wos = bq(f"SELECT work_order_id, asset_id FROM `{PROJECT}.{DATASET}.maintenance_logs` "
             f"WHERE asset_id IS NOT NULL")
    parts = bq(f"SELECT part_number FROM `{PROJECT}.{DATASET}.inventory_levels` ORDER BY part_number")

    locations = sorted({r["source_location"] for r in routes} |
                       {r["destination_location"] for r in routes})
    benches = [l for l in locations if "Bench" in l]
    stock_locs = [l for l in locations if "Stockpile" in l]
    tsf_locs = [l for l in locations if "Tailings" in l]
    print(f"anchors: {len(blocks)} blocks, {len(routes)} routes, {len(assets)} assets, "
          f"{len(benches)} benches, {len(stock_locs)} stockpiles, {len(tsf_locs)} TSF gates")

    # -- blast_designs: one design per sampled ore block, powder factor scaled
    #    to that block's own specific gravity so the two tables agree.
    blast = []
    for i, b in enumerate(rng.sample(blocks, min(180, len(blocks))), 1):
        sg = float(b["specific_gravity"] or 2.7)
        burden = round(rng.uniform(4.0, 7.5), 2)
        blast.append({
            "blast_id": f"BL-{i:05d}", "block_id": b["block_id"],
            "design_date": d(rng).isoformat(),
            "bench_location": rng.choice(benches) if benches else "Pit Floor Bench 4",
            "burden_m": burden, "spacing_m": round(burden * rng.uniform(1.1, 1.35), 2),
            "hole_diameter_mm": rng.choice([115, 127, 152, 165]),
            "hole_depth_m": round(rng.uniform(8.0, 16.0), 1),
            "powder_factor_kg_per_m3": round(sg * rng.uniform(0.24, 0.36), 3),
            "explosive_type": rng.choice(["ANFO", "Emulsion", "Heavy ANFO 70:30"]),
            "designed_by": rng.choice(["D. Miller", "E. Ramos", "T. Al-Mansoor"]),
            "approved": rng.random() > 0.15,
        })
    # -- survey_scans: as-built voids against the same blocks that were blasted
    survey = [{
        "scan_id": f"SCAN-{i:05d}", "block_id": b["block_id"],
        "scan_date": d(rng).isoformat(),
        "scanner_type": rng.choice(["LiDAR", "Photogrammetry", "Drone LiDAR"]),
        "point_count": rng.randrange(180_000, 2_400_000),
        "designed_volume_m3": round(v := rng.uniform(1800, 14500), 1),
        "measured_volume_m3": round(v * rng.uniform(0.94, 1.07), 1),
        "centroid_x": b["centroid_x"], "centroid_y": b["centroid_y"], "centroid_z": b["centroid_z"],
    } for i, b in enumerate(rng.sample(blocks, min(120, len(blocks))), 1)]

    # -- geotech_sensors / tsf_piezometers: real bench and TSF locations
    geo = []
    for i in range(1, 241):
        loc = rng.choice(benches or locations)
        geo.append({"reading_id": f"GT-{i:05d}",
                    "sensor_id": f"GEO-{rng.randrange(1,13):02d}",
                    "bench_location": loc, "timestamp": (
                        dt.datetime.combine(d(rng), dt.time(rng.randrange(24), rng.randrange(60)))
                        .isoformat() + "Z"),
                    "displacement_mm": round(rng.gauss(2.1, 1.4), 3),
                    "pore_pressure_kpa": round(rng.uniform(35, 190), 1),
                    "slope_angle_deg": round(rng.uniform(38, 55), 1),
                    "alarm_state": rng.choices(["NORMAL", "WATCH", "ALERT"], [0.86, 0.11, 0.03])[0]})
    piez = []
    for i in range(1, 201):
        piez.append({"reading_id": f"PZ-{i:05d}",
                     "piezometer_id": f"TSF-PZ-{rng.randrange(1,9):02d}",
                     "tsf_location": rng.choice(tsf_locs or ["Tailings Gate 1"]),
                     "timestamp": (dt.datetime.combine(d(rng), dt.time(rng.randrange(24)))
                                   .isoformat() + "Z"),
                     "pore_pressure_kpa": round(rng.uniform(60, 240), 1),
                     "phreatic_surface_m": round(rng.uniform(2.5, 11.0), 2),
                     "factor_of_safety": round(rng.gauss(1.62, 0.14), 3),
                     "beach_width_m": round(rng.uniform(45, 120), 1)})

    # -- water_balance_logs: one row per real recovery timestamp, so plant water
    #    and plant metallurgy share a clock and can be reconciled.
    water = []
    for i, r in enumerate(recov, 1):
        inflow = rng.uniform(820, 1350)
        evap, seep = inflow * rng.uniform(0.04, 0.09), inflow * rng.uniform(0.02, 0.05)
        water.append({"log_id": f"WB-{i:05d}", "timestamp": r["timestamp"],
                      "concentrator_id": r["concentrator_id"],
                      "inflow_m3": round(inflow, 1), "evaporation_m3": round(evap, 1),
                      "seepage_m3": round(seep, 1),
                      "process_return_m3": round(inflow * rng.uniform(0.55, 0.72), 1),
                      "net_storage_change_m3": round(inflow - evap - seep, 1)})

    # -- stockpiles: the real stockpile locations, graded from the block model
    grades = [float(b["copper_grade_pct_est"] or 0) for b in blocks if b["copper_grade_pct_est"]]
    mean_grade = sum(grades) / max(len(grades), 1)
    stock = []
    for i, loc in enumerate(stock_locs or ["Stockpile East"], 1):
        for j in range(4):
            stock.append({"stockpile_id": f"SP-{i:02d}-{j+1}", "location": loc,
                          "as_at": d(rng).isoformat(),
                          "material_class": rng.choice(["ROM Ore", "Low Grade", "Oxide", "Waste"]),
                          "tonnes": round(rng.uniform(4_000, 92_000), 1),
                          "contained_grade_pct": round(mean_grade * rng.uniform(0.7, 1.35), 4),
                          "moisture_pct": round(rng.uniform(2.1, 9.4), 2),
                          "reclaim_rate_tph": round(rng.uniform(400, 1800), 1)})

    # -- rail_schedules loads OUT of those stockpiles; port_vessels loads the rail.
    rail = []
    for i in range(1, 121):
        sp = rng.choice(stock)
        dep = d(rng)
        rail.append({"consist_id": f"RK-{i:05d}", "origin_stockpile_id": sp["stockpile_id"],
                     "origin_location": sp["location"], "destination_port": "Port Terminal 1",
                     "departure_date": dep.isoformat(),
                     "arrival_date": (dep + dt.timedelta(days=rng.choice([1, 1, 2]))).isoformat(),
                     "wagons": rng.choice([96, 120, 160, 240]),
                     "payload_tonnes": round(rng.uniform(9_000, 26_000), 1),
                     "cycle_time_hours": round(rng.uniform(18, 46), 1),
                     "delayed": rng.random() < 0.22})
    vessels = []
    for i in range(1, 41):
        loaded = rng.sample(rail, rng.randint(2, 5))
        arrive = max(dt.date.fromisoformat(r["arrival_date"]) for r in loaded)
        laycan = arrive + dt.timedelta(days=rng.choice([0, 1, 2, 3]))
        depart = laycan + dt.timedelta(days=rng.choice([1, 2, 2, 3, 5]))
        vessels.append({"vessel_id": f"VSL-{i:04d}",
                        "vessel_name": f"MV {rng.choice(['Pacific','Southern','Iron','Cape','Austral'])} "
                                       f"{rng.choice(['Trader','Voyager','Pioneer','Spirit'])}",
                        "berth": rng.choice(["Berth 1", "Berth 2"]),
                        "laycan_start": laycan.isoformat(),
                        "arrival_date": arrive.isoformat(),
                        "departure_date": depart.isoformat(),
                        "consist_ids": [r["consist_id"] for r in loaded],
                        "loaded_tonnes": round(sum(r["payload_tonnes"] for r in loaded), 1),
                        "moisture_pct": round(rng.uniform(6.2, 9.8), 2),
                        "tml_pct": 10.0,
                        "demurrage_days": max(0, (depart - laycan).days - 2)})

    # -- tenement_leases: the licence footprint over the real block-model extent
    xs = [float(b["centroid_x"]) for b in blocks]; ys = [float(b["centroid_y"]) for b in blocks]
    ten = [{"tenement_id": f"ML-{7400+i}", "holder": "Argolis Mining Operations Pty Ltd",
            "status": rng.choice(["GRANTED", "GRANTED", "GRANTED", "RENEWAL PENDING"]),
            "grant_date": (START - dt.timedelta(days=rng.randrange(900, 3600))).isoformat(),
            "expiry_date": (END + dt.timedelta(days=rng.randrange(400, 4000))).isoformat(),
            "area_hectares": round(rng.uniform(420, 3100), 1),
            "min_x": round(min(xs), 1), "max_x": round(max(xs), 1),
            "min_y": round(min(ys), 1), "max_y": round(max(ys), 1),
            "annual_rent_usd": round(rng.uniform(18_000, 140_000), 2)} for i in range(1, 7)]

    # -- consumables the spares catalogue does not carry
    reagent = [{"part_number": f"RGT-{i:04d}",
                "part_description": n, "stock_level": rng.randrange(20, 900),
                "reorder_point_limit": rng.randrange(15, 260),
                "lead_time_days": rng.choice([7, 14, 21, 30, 45]),
                "unit_price_usd": round(rng.uniform(3.2, 78.0), 2),
                "reagent_class": c}
               for i, (n, c) in enumerate([
                   ("Potassium Amyl Xanthate (PAX) 25kg", "Collector"),
                   ("Sodium Isobutyl Xanthate (SIBX) 25kg", "Collector"),
                   ("Sodium Ethyl Xanthate (SEX) 25kg", "Collector"),
                   ("MIBC Frother 200L", "Frother"),
                   ("Polypropylene Glycol Frother 200L", "Frother"),
                   ("Anionic Flocculant 25kg", "Flocculant"),
                   ("Hydrated Lime 1t bulk bag", "pH Modifier"),
                   ("Copper Sulphate Activator 25kg", "Activator"),
                   ("Sodium Cyanide Briquettes 50kg", "Depressant"),
                   ("Sulphuric Acid 98% 1000L IBC", "pH Modifier")], 1)]
    explosive = [{"part_number": f"EXP-{i:04d}", "part_description": n,
                  "stock_level": rng.randrange(40, 2400),
                  "reorder_point_limit": rng.randrange(30, 700),
                  "lead_time_days": rng.choice([10, 21, 35]),
                  "unit_price_usd": round(rng.uniform(1.8, 240.0), 2),
                  "un_class": c, "magazine": rng.choice(["MAG-01", "MAG-02"])}
                 for i, (n, c) in enumerate([
                     ("ANFO Prill 1t bulk bag", "1.5D"),
                     ("Heavy ANFO 70:30 Emulsion 1t", "1.5D"),
                     ("Packaged Emulsion 32mm x 400mm", "1.1D"),
                     ("Electronic Detonator 15m", "1.1B"),
                     ("Non-Electric Shock Tube 4.8m", "1.4B"),
                     ("Cast Booster 400g", "1.1D"),
                     ("Detonating Cord 10g/m", "1.1D")], 1)]

    # -- lube_samples key to real assets and real work orders
    lube = []
    for i in range(1, 221):
        w = rng.choice(wos) if wos else {"work_order_id": None, "asset_id": assets[0]["asset_id"]}
        lube.append({"sample_id": f"OIL-{i:05d}", "asset_id": w["asset_id"],
                     "work_order_id": w["work_order_id"],
                     "sampled_at": (dt.datetime.combine(d(rng), dt.time(rng.randrange(24)))
                                    .isoformat() + "Z"),
                     "lubricant_grade": rng.choice(["ISO VG 220", "ISO VG 320", "SAE 15W-40"]),
                     "iron_ppm": round(rng.gauss(28, 16), 1),
                     "copper_ppm": round(rng.gauss(9, 6), 1),
                     "silicon_ppm": round(rng.gauss(14, 9), 1),
                     "water_pct": round(abs(rng.gauss(0.06, 0.05)), 3),
                     "viscosity_cst_40c": round(rng.gauss(220, 22), 1),
                     "iso_4406_code": f"{rng.randrange(15,23)}/{rng.randrange(13,21)}/{rng.randrange(10,18)}",
                     "verdict": rng.choices(["NORMAL", "MONITOR", "ACTION"], [0.72, 0.22, 0.06])[0]})

    TABLES = [
      ("blast_designs", blast, "blast_id:STRING,block_id:STRING,design_date:DATE,bench_location:STRING,burden_m:FLOAT64,spacing_m:FLOAT64,hole_diameter_mm:INT64,hole_depth_m:FLOAT64,powder_factor_kg_per_m3:FLOAT64,explosive_type:STRING,designed_by:STRING,approved:BOOL"),
      ("survey_scans", survey, "scan_id:STRING,block_id:STRING,scan_date:DATE,scanner_type:STRING,point_count:INT64,designed_volume_m3:FLOAT64,measured_volume_m3:FLOAT64,centroid_x:FLOAT64,centroid_y:FLOAT64,centroid_z:FLOAT64"),
      ("geotech_sensors", geo, "reading_id:STRING,sensor_id:STRING,bench_location:STRING,timestamp:TIMESTAMP,displacement_mm:FLOAT64,pore_pressure_kpa:FLOAT64,slope_angle_deg:FLOAT64,alarm_state:STRING"),
      ("tsf_piezometers", piez, "reading_id:STRING,piezometer_id:STRING,tsf_location:STRING,timestamp:TIMESTAMP,pore_pressure_kpa:FLOAT64,phreatic_surface_m:FLOAT64,factor_of_safety:FLOAT64,beach_width_m:FLOAT64"),
      ("water_balance_logs", water, "log_id:STRING,timestamp:TIMESTAMP,concentrator_id:STRING,inflow_m3:FLOAT64,evaporation_m3:FLOAT64,seepage_m3:FLOAT64,process_return_m3:FLOAT64,net_storage_change_m3:FLOAT64"),
      ("stockpiles", stock, "stockpile_id:STRING,location:STRING,as_at:DATE,material_class:STRING,tonnes:FLOAT64,contained_grade_pct:FLOAT64,moisture_pct:FLOAT64,reclaim_rate_tph:FLOAT64"),
      ("rail_schedules", rail, "consist_id:STRING,origin_stockpile_id:STRING,origin_location:STRING,destination_port:STRING,departure_date:DATE,arrival_date:DATE,wagons:INT64,payload_tonnes:FLOAT64,cycle_time_hours:FLOAT64,delayed:BOOL"),
      ("port_vessels", vessels, "vessel_id:STRING,vessel_name:STRING,berth:STRING,laycan_start:DATE,arrival_date:DATE,departure_date:DATE,consist_ids:STRING:REPEATED,loaded_tonnes:FLOAT64,moisture_pct:FLOAT64,tml_pct:FLOAT64,demurrage_days:INT64"),
      ("tenement_leases", ten, "tenement_id:STRING,holder:STRING,status:STRING,grant_date:DATE,expiry_date:DATE,area_hectares:FLOAT64,min_x:FLOAT64,max_x:FLOAT64,min_y:FLOAT64,max_y:FLOAT64,annual_rent_usd:FLOAT64"),
      ("reagent_inventory", reagent, "part_number:STRING,part_description:STRING,stock_level:INT64,reorder_point_limit:INT64,lead_time_days:INT64,unit_price_usd:FLOAT64,reagent_class:STRING"),
      ("explosives_inventory", explosive, "part_number:STRING,part_description:STRING,stock_level:INT64,reorder_point_limit:INT64,lead_time_days:INT64,unit_price_usd:FLOAT64,un_class:STRING,magazine:STRING"),
      ("lube_samples", lube, "sample_id:STRING,asset_id:STRING,work_order_id:STRING,sampled_at:TIMESTAMP,lubricant_grade:STRING,iron_ppm:FLOAT64,copper_ppm:FLOAT64,silicon_ppm:FLOAT64,water_pct:FLOAT64,viscosity_cst_40c:FLOAT64,iso_4406_code:STRING,verdict:STRING"),
    ]
    print()
    for name, rows, schema in TABLES:
        if args.load:
            load(name, rows, schema)
        else:
            (OUT / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            print(f"  {name:<26} {len(rows):>5} rows (file only)")
    if not args.load:
        print("\n(pass --load to write BigQuery)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
