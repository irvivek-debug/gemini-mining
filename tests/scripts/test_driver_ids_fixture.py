"""Drift guard: tests/fixtures/driver-ids.json must exactly match method/*.yaml.

The fixture is consumed by tests/js/plain.test.js to verify every driver id has
a reader-facing phrase. If a driver is added or removed from a pack and the
fixture is not regenerated, the JS test iterates a stale list — passing while a
new driver id reaches the activity log unformatted.

This test fails on any such drift. When it fails, re-run:

    python -m scripts.gen_driver_ids

to bring the fixture back into sync.
"""
import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
METHOD_DIR = ROOT / "method"
FIXTURE = ROOT / "tests" / "fixtures" / "driver-ids.json"


def _ids_from_packs() -> list[str]:
    """Read driver ids from method/*.yaml in sorted-filename order."""
    ids: list[str] = []
    for pack_file in sorted(METHOD_DIR.glob("*.yaml")):
        data = yaml.safe_load(pack_file.read_text()) or {}
        for driver in data.get("drivers", []):
            ids.append(driver["id"])
    return ids


def test_fixture_matches_packs() -> None:
    """The committed fixture must equal what the packs declare right now.

    Fails on any mismatch and names the ids that differ so the reader knows
    exactly what to fix before re-running gen_driver_ids.
    """
    from_packs = _ids_from_packs()
    from_fixture = json.loads(FIXTURE.read_text())

    pack_set = set(from_packs)
    fixture_set = set(from_fixture)

    only_in_packs = sorted(pack_set - fixture_set)
    only_in_fixture = sorted(fixture_set - pack_set)

    # Order matters too: the JS test iterates in fixture order, so an order
    # change is a change worth knowing about even when the id sets are equal.
    order_mismatch = (from_packs != from_fixture) and not (only_in_packs or only_in_fixture)

    messages: list[str] = []
    if only_in_packs:
        messages.append(
            f"ids in packs but missing from the fixture (not yet generated): "
            f"{only_in_packs}"
        )
    if only_in_fixture:
        messages.append(
            f"ids in the fixture but gone from the packs (stale fixture entry): "
            f"{only_in_fixture}"
        )
    if order_mismatch:
        messages.append(
            f"id order differs — fixture: {from_fixture}, packs: {from_packs}"
        )

    assert not messages, (
        "tests/fixtures/driver-ids.json has drifted from method/*.yaml.\n"
        + "\n".join(f"  - {m}" for m in messages)
        + "\nRe-run:  python -m scripts.gen_driver_ids"
    )
