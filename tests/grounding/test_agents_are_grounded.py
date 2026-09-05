"""Every registered agent must prove it reads the warehouse, not its memory.

WHY THIS IS A TEST AND NOT A REPORT
The grounding probes were producing data/grounding/results.jsonl -- a log. Logs
do not fail, so an agent that silently stopped querying would show up as a line
nobody read. These are the same three gates as assertions, so "is the estate
healthy?" is one command.

Marked integration: they invoke live Agent Engines and query live BigQuery, and
each agent takes 25-45s. Run the whole estate with
    pytest -m integration tests/grounding -q
or one persona with
    pytest -m integration tests/grounding -q -k S01
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

RESULTS = ROOT / "data" / "grounding" / "results.jsonl"


def _latest_results() -> dict[str, dict]:
    """Newest recorded probe per agent.

    The file is append-only and agents are re-probed after each rebuild, so the
    last entry for an agent is the current truth. Deduping here rather than in
    the runner keeps the raw history intact.
    """
    if not RESULTS.exists():
        return {}
    out = {}
    for line in RESULTS.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["agent_id"]] = r
    return out


def _registered() -> set[str]:
    from register_agents import GE_AGENTS, paged  # noqa: PLC0415
    ident = re.compile(r"\(([A-Z0-9][A-Z0-9\-]*)\)\s*$")
    return {m.group(1) for a in paged(GE_AGENTS, "agents")
            if (m := ident.search(a.get("displayName", "")))}


@pytest.mark.integration
def test_every_probed_agent_matched_live_data():
    """Gate 1+2: the reported figure is the one in BigQuery right now."""
    results = _latest_results()
    if not results:
        pytest.skip("no probes recorded yet — run scripts/build_probes.py and probe")
    bad = {a: r for a, r in results.items() if not r["checks"]["matches_live_source"]}
    assert not bad, (
        f"{len(bad)} agents reported a figure that is not in the warehouse: "
        + ", ".join(f"{a} (truth {r['truth']}, said {r['matched_number']})"
                    for a, r in list(bad.items())[:6])
    )


@pytest.mark.integration
def test_every_probed_agent_cited_its_table():
    """Gate 3a: a number without a source is not evidence.

    Citation must be in identifier form. The bare word fails on purpose --
    "88 assets" would otherwise satisfy a check for the table `assets`.
    """
    results = _latest_results()
    if not results:
        pytest.skip("no probes recorded yet")
    bad = [a for a, r in results.items() if not r["checks"]["cites_its_source"]]
    assert not bad, f"{len(bad)} agents reported figures without naming a table: {bad[:8]}"


@pytest.mark.integration
def test_every_probed_agent_got_its_derived_maths_right():
    """Gate 3b: derived figures are recomputed from the truth row."""
    results = _latest_results()
    if not results:
        pytest.skip("no probes recorded yet")
    bad = [a for a, r in results.items() if not r["checks"]["derived_maths_correct"]]
    assert not bad, f"{len(bad)} agents got a derived figure wrong: {bad[:8]}"


@pytest.mark.integration
def test_agents_actually_called_a_tool():
    """A grounded answer without a tool call is a coincidence, not grounding.

    All 100 agents once answered fluently with no tools attached at all. Tool
    calls are the mechanical evidence that a query happened; the numbers alone
    could in principle be memorised from an earlier run.
    """
    results = _latest_results()
    if not results:
        pytest.skip("no probes recorded yet")
    bad = [a for a, r in results.items() if r.get("tool_calls", 0) == 0]
    assert not bad, f"{len(bad)} agents answered without calling any tool: {bad[:8]}"


@pytest.mark.integration
def test_every_registered_agent_has_been_probed():
    """Coverage. An unprobed agent is an unverified agent.

    This is expected to fail during the conversion, and that is the point: it
    names exactly which agents still have no grounding evidence.
    """
    results, registered = _latest_results(), _registered()
    if not results:
        pytest.skip("no probes recorded yet")
    missing = sorted(registered - set(results))
    assert not missing, (
        f"{len(missing)} of {len(registered)} registered agents have no grounding "
        f"probe on record: {missing[:10]}"
    )
