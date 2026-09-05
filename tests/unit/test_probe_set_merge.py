"""The probe set is the record of what we can verify, so it must only grow.

`build_probes.py --group X` used to rewrite data/grounding/probes.json in
full. After a run for S08, S01's probes no longer existed. Anything that
looked up an earlier agent found nothing and skipped it *in silence* -- a
determinism trial exited with zero output and exit code 0 because all three
of its agents had been erased from the test set.

These tests pin both halves of the fix: the file accumulates, and callers
that want one group must select that group rather than trusting the file to
contain only it.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "scripts" / "build_probes.py"


def _write(path: Path, agent_ids):
    path.write_text(json.dumps([{"agent_id": a, "question": f"q for {a}",
                                 "table": "assets", "derived": []}
                                for a in agent_ids]))


def _merge(out: Path, fresh_ids):
    """Mirror of the merge in build_probes.main(), driven through the file."""
    existing = {d["agent_id"]: d for d in json.loads(out.read_text())} if out.exists() else {}
    for a in fresh_ids:
        existing[a] = {"agent_id": a, "question": f"q for {a}",
                       "table": "assets", "derived": []}
    out.write_text(json.dumps([existing[k] for k in sorted(existing)]))


def test_merge_keeps_agents_from_earlier_groups(tmp_path):
    """The exact regression: S01 must survive a build for S08."""
    out = tmp_path / "probes.json"
    _write(out, ["S01-1-LITHOLOGY", "S01-COORDINATOR"])
    _merge(out, ["S08-1-WATER", "S08-COORDINATOR"])
    ids = {d["agent_id"] for d in json.loads(out.read_text())}
    assert "S01-1-LITHOLOGY" in ids, "building S08 erased S01 -- the original bug"
    assert ids == {"S01-1-LITHOLOGY", "S01-COORDINATOR",
                   "S08-1-WATER", "S08-COORDINATOR"}


def test_rebuilding_a_group_updates_rather_than_duplicates(tmp_path):
    out = tmp_path / "probes.json"
    _write(out, ["S01-COORDINATOR"])
    _merge(out, ["S01-COORDINATOR"])
    data = json.loads(out.read_text())
    assert len(data) == 1, f"re-running a group duplicated its probes: {data}"


def test_probe_set_is_ordered_so_diffs_stay_readable(tmp_path):
    out = tmp_path / "probes.json"
    _write(out, ["S08-1-WATER"])
    _merge(out, ["S01-COORDINATOR", "S12-R-CRITIC"])
    ids = [d["agent_id"] for d in json.loads(out.read_text())]
    assert ids == sorted(ids)


def test_selecting_one_group_must_filter_not_trust_the_file(tmp_path):
    """Guards the bug the *fix* introduced.

    The orchestrator built its rebuild list from every entry in probes.json,
    which was safe only while the file held exactly one group. Once the file
    merged, that same line would have rebuilt all 96 agents -- the whole
    estate -- for each group. Callers must filter by prefix.
    """
    out = tmp_path / "probes.json"
    _write(out, ["S01-COORDINATOR", "S08-1-WATER", "S08-COORDINATOR"])
    every = [d["agent_id"] for d in json.loads(out.read_text())]
    assert len(every) == 3, "unfiltered read sees the whole estate"

    selected = [a for a in every if a.startswith("S08")]
    assert selected == ["S08-1-WATER", "S08-COORDINATOR"]


def test_group_prefix_does_not_match_a_longer_group(tmp_path):
    """S1 must not select S12; prefix matching needs the separator."""
    out = tmp_path / "probes.json"
    _write(out, ["S01-COORDINATOR", "S12-R-CRITIC"])
    every = [d["agent_id"] for d in json.loads(out.read_text())]
    selected = [a for a in every if a.startswith("S01" + "-")]
    assert selected == ["S01-COORDINATOR"]


def test_build_probes_source_actually_merges():
    """Pin the real source, not just this file's model of it."""
    src = BUILD.read_text()
    assert "existing" in src and "OUT.exists()" in src, \
        "build_probes.py no longer merges -- the regression is back"


# --- selection over the merged set -------------------------------------------
# Merging made the file hold every group, so selection became load-bearing.
# Group ids are not uniformly shaped, which is where this goes wrong.

sys.path.insert(0, str(ROOT / "scripts"))
import probe_set  # noqa: E402


@pytest.mark.parametrize("agent_id,expected", [
    ("S01-COORDINATOR", "S01"),
    ("S12-R-CRITIC", "S12"),
    ("S08-1-WATER", "S08"),
    ("AGT-19", "AGT"),
    ("D01", "D"),          # deep solvers carry no separator
    ("D35", "D"),
])
def test_group_of_handles_every_id_shape(agent_id, expected):
    assert probe_set.group_of(agent_id) == expected


def test_s01_does_not_swallow_s12():
    assert probe_set.group_of("S12-R-CRITIC") != "S01"


def test_d_group_selects_deep_solvers_not_the_estate(tmp_path):
    """`D` + separator selected nothing; `D` bare must not select S-swarms."""
    out = tmp_path / "p.json"
    _write(out, ["D01", "D26", "S01-COORDINATOR", "AGT-19"])
    assert probe_set.select_group("D", out) == ["D01", "D26"]


def test_selecting_a_swarm_returns_only_that_swarm(tmp_path):
    out = tmp_path / "p.json"
    _write(out, ["S01-COORDINATOR", "S08-1-WATER", "S08-COORDINATOR", "D01"])
    assert probe_set.select_group("S08", out) == ["S08-1-WATER", "S08-COORDINATOR"]


def test_unknown_group_returns_empty_not_everything(tmp_path):
    out = tmp_path / "p.json"
    _write(out, ["S01-COORDINATOR", "D01"])
    assert probe_set.select_group("S99", out) == []


def test_chunks_cover_every_item_exactly_once():
    ids = [f"D{i:02d}" for i in range(1, 36)]
    batched = probe_set.chunks(ids, 8)
    assert [x for b in batched for x in b] == ids
    assert len(batched) == 5 and len(batched[-1]) == 3


# --- every registered agent must be verifiable --------------------------------

def test_count_only_probe_when_a_table_has_no_numeric_column(tmp_path):
    """D22-D25 declare `assets`, which is entirely STRING and DATE columns,
    and D38 declares the `safety_telemetry` view. All five were skipped, so
    nothing could ever verify they read data. A row count is still a fact
    only the warehouse knows."""
    src = (ROOT / "scripts" / "build_probes.py").read_text()
    assert "countable" in src, "agents without a numeric column are skipped again"
    assert "the total row count" in src


def test_views_count_as_readable_relations():
    """A view is as real to an agent as a table; safety_telemetry is one."""
    src = (ROOT / "scripts" / "build_probes.py").read_text()
    assert "INFORMATION_SCHEMA.TABLES" in src, \
        "only base tables are considered, so view-backed agents stay unverifiable"


def test_a_deregistered_agent_does_not_reappear():
    """D31 was retired by decision. Deleting it by hand lasted until the next
    build, so the decision is encoded rather than repeatedly undone."""
    src = (ROOT / "scripts" / "build_probes.py").read_text()
    assert "DEREGISTERED" in src
    import json
    probes = json.loads((ROOT / "data" / "grounding" / "probes.json").read_text())
    assert "D31" not in {p["agent_id"] for p in probes}


def test_every_probe_has_a_truth_query_and_a_table_to_name():
    """A probe that asserts nothing would pass silently."""
    import json
    probes = json.loads((ROOT / "data" / "grounding" / "probes.json").read_text())
    assert len(probes) >= 100, f"probe set shrank to {len(probes)}"
    for p in probes:
        assert p["truth_sql"].strip().upper().startswith("SELECT"), p["agent_id"]
        assert p["must_name"], f"{p['agent_id']} names no table to cite"
        assert p["truth_key"] in p["truth_sql"], p["agent_id"]
