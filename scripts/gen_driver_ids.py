"""Generate tests/fixtures/driver-ids.json from method/*.yaml.

Run this whenever a pack is added or a driver id changes; the JSON fixture
feeds tests/js/plain.test.js and must not drift from what ships.

Run: python -m scripts.gen_driver_ids
"""
from __future__ import annotations

import json
import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
METHOD_DIR = REPO / "method"
OUT = REPO / "tests" / "fixtures" / "driver-ids.json"


def main() -> None:
    ids: list[str] = []
    for pack_file in sorted(METHOD_DIR.glob("*.yaml")):
        data = yaml.safe_load(pack_file.read_text()) or {}
        for driver in data.get("drivers", []):
            ids.append(driver["id"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ids, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} ({len(ids)} driver ids)")


if __name__ == "__main__":
    main()
