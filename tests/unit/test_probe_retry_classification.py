"""The retry-once block runs unattended, and only on the failure path.

Every live run so far has passed, so this branch has never executed. It is
tested here against the harness's own source text -- not a paraphrase --
so a drift in the script is a test failure rather than a silent no-op at
3am.

Why it exists: a single FAIL cannot distinguish a broken agent from a bad
minute. S01-1-LITHOLOGY stalled after 1 tool call in 67s, then passed the
identical probe minutes later with 7 calls in 24s. S08-R-CRITIC did the
same. Both were recorded as failures by a harness that never asked twice.
"""
import pathlib
import re

import pytest

HARNESS = pathlib.Path("/tmp/probe_group.py")
pytestmark = pytest.mark.skipif(not HARNESS.exists(), reason="harness not present")


def _retry_block() -> str:
    """The real retry code, lifted from the harness by its anchors."""
    src = HARNESS.read_text()
    start = src.index('    if not r.get("passed"):')
    end = src.index("    results.append(r)", start)
    import textwrap
    return textwrap.dedent(src[start:end])


def _run(first_passed: bool, second_passed: bool) -> dict:
    """Execute the harness's own retry block against stubbed attempts."""
    attempts = iter([
        {"passed": first_passed, "tool_calls": 1, "latency_s": 67.3,
         "checks": {"matches_live_source": first_passed}, "reply_chars": 0,
         "tool_errors": []},
        {"passed": second_passed, "tool_calls": 7, "latency_s": 24.4,
         "checks": {"matches_live_source": second_passed}, "reply_chars": 900,
         "tool_errors": []},
    ])
    env = {"r": next(attempts), "p": object(), "eng": {}, "H": {},
           "probe_once": lambda *a, **k: next(attempts),
           "time": type("T", (), {"sleep": staticmethod(lambda s: None)})}
    exec(compile(_retry_block(), "<retry>", "exec"), env)
    return env["r"]


def test_a_failure_that_passes_on_retry_is_marked_transient():
    r = _run(first_passed=False, second_passed=True)
    assert r["passed"] is True
    assert r["failure_kind"] == "transient"


def test_a_failure_that_fails_twice_is_marked_persistent():
    r = _run(first_passed=False, second_passed=False)
    assert r["passed"] is False
    assert r["failure_kind"] == "persistent"


def test_the_first_attempt_is_preserved_as_evidence():
    """Without this the transient signature -- 1 tool call, 67s -- is lost."""
    r = _run(first_passed=False, second_passed=True)
    assert r["first_attempt"]["tool_calls"] == 1
    assert r["first_attempt"]["latency_s"] == 67.3


def test_a_pass_is_never_retried():
    """The block must not fire on success; retrying 96 passes doubles the run."""
    block = _retry_block()
    assert 'if not r.get("passed")' in block


def test_harness_still_records_evidence_fields():
    src = HARNESS.read_text()
    for field in ("reply", "tool_names", "tool_errors", "question", "reply_chars"):
        assert f'"{field}"' in src, f"harness stopped recording {field}"


# --- evidence must survive a run that dies -----------------------------------

def test_results_are_flushed_per_agent_not_at_the_end():
    """The D group died on an expired credential and lost every result.

    Buffering to the end means a run that is killed, times out, or loses its
    credential discards work already paid for, and the report silently keeps
    describing a smaller estate.
    """
    src = pathlib.Path("scripts/probe_group.py").read_text()
    loop = src[src.index("for p in load_probes():"):]
    assert 'OUT.open("a")' in loop, "results no longer written inside the loop"
    assert "fh.flush()" in loop, "write is not flushed; a kill still loses it"
    assert "for r in results: fh.write" not in src, "end-of-run buffered write is back"


def test_the_write_happens_after_the_retry_decision():
    """Otherwise the record on disk is the unretried one, misclassifying it."""
    src = pathlib.Path("scripts/probe_group.py").read_text()
    retry = src.index('r2["failure_kind"]')
    write = src.index('OUT.open("a")')
    assert retry < write, "result is written before the retry has classified it"
