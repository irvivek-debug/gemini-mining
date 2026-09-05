"""The post-rebuild gate must reject what the old one accepted.

The old gate sent `Reply with the single word: ok` and passed anything that
answered. A toolless agent -- the exact defect being rebuilt away -- passes
that cleanly. These tests pin the cases that distinguish the two.

verdict() is pure, so the real scoring path is exercised with no network.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_grounded as vg  # noqa: E402


@pytest.fixture(autouse=True)
def _stub_scoring(monkeypatch):
    """Stand in for BigQuery: a reply containing 19959 is the grounded one."""
    class P:
        agent_id = "D17"
        question = "how many rows"
    monkeypatch.setattr(vg, "probe_for", lambda a: P())
    monkeypatch.setattr(vg, "evaluate", lambda p, reply: (
        {"passed": True, "matched_number": 19959.0, "truth": 19959.0,
         "checks": {"matches_live_source": True, "cites_its_source": True,
                    "derived_maths_correct": True}}
        if "19959" in reply else
        {"passed": False, "matched_number": None, "truth": 19959.0,
         "checks": {"matches_live_source": False, "cites_its_source": False,
                    "derived_maths_correct": True}}))


def test_a_toolless_agent_is_rejected():
    """The old liveness gate passed this. It is the whole point."""
    ok, detail = vg.verdict("D17", calls=[], reply="I cannot query the database directly.")
    assert ok is False
    assert "NO TOOL CALLS" in detail


def test_a_fluent_but_sourceless_answer_is_rejected():
    """Confident prose with no tool call is the failure mode that shipped."""
    ok, detail = vg.verdict("D17", calls=[],
                            reply="The plant telemetry table holds roughly 20,000 rows.")
    assert ok is False


def test_a_grounded_agent_is_accepted():
    ok, detail = vg.verdict("D17", calls=["list_table_ids", "execute_sql"],
                            reply="`mining_data.plant_telemetry` has 19959 rows.")
    assert ok is True
    assert "grounded" in detail and "2 tool calls" in detail


def test_tools_called_but_wrong_number_is_rejected():
    """Calling tools is not the same as answering from them."""
    ok, detail = vg.verdict("D17", calls=["execute_sql"],
                            reply="The table has about 42000 rows.")
    assert ok is False
    assert "ungrounded" in detail
    assert "live=19959.0" in detail


def test_tools_called_but_empty_reply_is_rejected():
    ok, detail = vg.verdict("D17", calls=["execute_sql"], reply="   ")
    assert ok is False
    assert "empty reply" in detail


def test_an_agent_with_no_probe_cannot_be_called_verified(monkeypatch):
    """Silence about an unverifiable agent is how gaps got recorded as passes."""
    def boom(a):
        raise vg.NoProbe(a)
    monkeypatch.setattr(vg, "probe_for", boom)
    ok, detail = vg.verify("UNKNOWN-AGENT", "projects/x/y/z")
    assert ok is False
    assert "no probe" in detail


def test_the_old_liveness_prompt_is_not_what_gets_sent():
    """Guards against the gate quietly reverting to a smoke test.

    Checks code, not prose -- the module docstring names the old prompt on
    purpose, to explain what this replaced.
    """
    import ast
    src = (ROOT / "scripts" / "verify_grounded.py").read_text()
    tree = ast.parse(src)
    literals = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    docstrings = {ast.get_docstring(n, clean=False) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
    code_literals = literals - docstrings
    assert not any("Reply with the single word" in s for s in code_literals), \
        "the liveness smoke test is back as the verification prompt"
    assert "p.question" in src, "verification must send the agent's real probe"
