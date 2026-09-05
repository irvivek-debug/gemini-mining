"""The rebuild tool must not be blind to the defect it repairs.

`--all` selected rebuild targets with a liveness ping ("Reply with the
single word: ok"). A toolless agent answers that perfectly, so it was
logged "skipping — already answering" and never rebuilt. Run against the
18 toolless deep solvers, it would have skipped every one and reported
broken: 0.

`--check` had the same flaw and reported them "working".
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "rebuild_engines.py"
sys.path.insert(0, str(ROOT / "scripts"))


def _fn(name: str) -> ast.FunctionDef:
    tree = ast.parse(SRC.read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name}() is gone")


def _calls_in(node) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def test_target_selection_does_not_use_the_liveness_ping():
    """The regression: liveness cannot detect a toolless agent."""
    calls = _calls_in(_fn("main"))
    assert "invoke" not in calls, \
        "main() calls invoke() again — toolless agents will be skipped as healthy"
    assert "health" in calls


def test_health_checks_grounding():
    assert "verify" in _calls_in(_fn("health"))


def test_health_says_so_when_it_only_checked_liveness():
    """An unverifiable agent must not be silently counted as healthy."""
    src = ast.get_source_segment(SRC.read_text(), _fn("health"))
    assert "LIVENESS ONLY" in src
    assert "invoke(resource)" in src, "no fallback for agents without a probe"


def test_health_falls_back_only_when_no_probe_exists(monkeypatch):
    """Uses monkeypatch, not direct assignment: patching the shared module in
    place leaked the stub into other test files and failed an unrelated test."""
    import rebuild_engines as r
    import verify_grounded as vg

    def no_probe(aid):
        raise vg.NoProbe(aid)

    monkeypatch.setattr(vg, "probe_for", no_probe)
    monkeypatch.setattr(r, "invoke", lambda res, **kw: (True, "ok"))
    good, detail = r.health("AGENT-WITHOUT-PROBE", "projects/x/y/z")
    assert good is True
    assert "LIVENESS ONLY" in detail and "grounding unverified" in detail


def test_health_reports_an_ungrounded_agent_as_broken(monkeypatch):
    import rebuild_engines as r
    import verify_grounded as vg

    class P:
        agent_id = "D17"
        question = "q"

    monkeypatch.setattr(vg, "probe_for", lambda aid: P())
    monkeypatch.setattr(vg, "verify", lambda aid, res: (False, "NO TOOL CALLS"))
    good, detail = r.health("D17", "projects/x/y/z")
    assert good is False and "NO TOOL CALLS" in detail


def test_the_summary_does_not_claim_more_than_it_verified():
    src = SRC.read_text()
    assert "rebuilt and verified" not in src, \
        "'verified' overstates a liveness check; say what was actually proven"
    assert "rebuilt and grounded" in src
