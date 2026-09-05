"""Project-wide constants and calibration data for the mining data generator.

Loads schemas.json and stats.json from data/profile/ rather than restating
their numbers as literals — hardcoded copies drift when the live tables are
updated and the profile is recaptured.
"""

import json
import os
from pathlib import Path

SEED = 20260810
# mining_agents/config.py reads the same variable, so one export points the
# generator and the agents at the same place. There is no default: a
# placeholder project would surface later as a confusing BigQuery 404 in
# whichever load happened to run first.
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
if not PROJECT_ID:
    raise RuntimeError(
        "GOOGLE_CLOUD_PROJECT is unset. Copy .env.example to .env and set it "
        "to your own GCP project ID (see docs/RECREATE.md)."
    )
DATASET = os.environ.get("MINING_DATASET", "mining_data")
BACKUP_SUFFIX = "_original_20260810"

# Tables that will be rewritten by tasks 2-11 and must be backed up first.
REWRITE_TABLES = [
    "telemetry_stream",
    "metallurgical_recovery",
    "crusher_states",
    "erp_work_orders",
    "maintenance_logs",
    "biometric_fatigue_logs",
    "fatigue_logs_node",
    "inventory_levels",
    "drill_assay_logs",
    "geological_block_models",
]

# --- Load calibration data from disk (never hardcode these numbers) ----------

_PROFILE_DIR = Path(__file__).parent.parent / "profile"


def _load_json(filename: str) -> dict:
    with open(_PROFILE_DIR / filename) as f:
        return json.load(f)


SCHEMAS: dict = _load_json("schemas.json")
STATS: dict = _load_json("stats.json")
