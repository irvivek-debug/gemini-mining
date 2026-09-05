"""Tests for run_diagnostic — the tool that executes a driver's fixed query.

`method_lookup` hands the agent its driver tree but withholds each driver's
SQL, on the reasoning that a model handed a query will paraphrase or mutate the
diagnostic.  `run_diagnostic` closes the loop: the agent names a driver, the
runtime resolves the SQL, runs it, and returns the result.  The diagnostic that
ships is the diagnostic that runs.

The guard travels with every result, because a result that arrives without its
guard invites an unguarded recommendation.  The SQL text and the file path do
not — returning them would undo the withholding that `method_lookup` enforces.
"""
import json
import shutil
from pathlib import Path

import pytest

from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.method.pack import load_pack
from mining_agents.tools import run_diagnostic as module
from mining_agents.tools.method_lookup import PACK_DIR, PACKS
from mining_agents.tools.run_diagnostic import _referenced_tables, make_run_diagnostic

#: What S07-SP3 — the one agent that holds this tool — declares. Written out
#: rather than read from the catalog so that a test which widened the agent's
#: access would have to say so here too.
S07_SP3_TABLES = [
    "mining_data.metallurgical_recovery",
    "mining_data.crusher_states",
]


def test_an_unknown_driver_id_fails_with_the_valid_ids_listed():
    # A model that guessed an id needs to see the real ones so it can self-
    # correct without calling method_lookup again.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    env = run("no_such_driver")
    assert env["success"] is False
    assert env["error"]["code"] == "NO_SUCH_DRIVER"
    # The message must name the real ids so the model can self-correct.
    for real_id in ("liberation", "feed_variability", "bypass"):
        assert real_id in env["error"]["message"], (
            f"real id {real_id!r} missing from error message: {env['error']['message']}"
        )


def test_a_not_instrumented_driver_succeeds_with_driver_status_and_question():
    # A driver with no diagnostic behind it is a SUCCESSFUL call: the tool did
    # what it was asked and truthfully reported that no query covers this
    # driver. It must NOT be a failure envelope — the workspace UI renders
    # every success:false identically as "that lookup failed", which is the
    # inverse of what the pack means (nothing failed) and gives an agent every
    # reason to drop the driver instead of reporting the gap. That defeats the
    # declared-not-dropped mechanism pinned in
    # tests/method/test_p6_pack.py::test_the_uninstrumented_drivers_are_declared_not_omitted.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    env = run("reagent_regime")
    assert env["success"] is True, env.get("error")
    assert env["error"] is None
    data = env["data"]
    # Shape matches the instrumented success path — driver, status, guard,
    # rows — so a caller can branch on `status` instead of on error presence.
    assert data["driver"] == "reagent_regime"
    assert data["status"] == "not_instrumented"
    assert data["rows"] == []
    assert data["question"]  # non-empty; proves the driver's context travels
    # The agent must be told this is a gap to report, not a call to drop.
    note = data["note"].lower()
    assert "not" in note and ("omit" in note or "drop" in note)
    assert "fail" not in note, (
        "the not_instrumented note must not describe this call as a failure"
    )


def test_a_genuine_error_still_fails_unknown_driver_persona_and_undeclared_table():
    # The fix above must not weaken any real error path. A wrong
    # implementation that made everything succeed — e.g. by returning `ok()`
    # unconditionally — would slip past every other test in this module if
    # they were not re-checked here in one place, pinned against `success`.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    unknown_driver = run("no_such_driver")
    assert unknown_driver["success"] is False
    assert unknown_driver["error"]["code"] == "NO_SUCH_DRIVER"

    unknown_persona = make_run_diagnostic("P4", S07_SP3_TABLES)("liberation")
    assert unknown_persona["success"] is False
    assert unknown_persona["error"]["code"] == "NO_METHOD_PACK"

    undeclared_table = make_run_diagnostic(
        "P6", ["mining_data.metallurgical_recovery"]
    )("liberation")
    assert undeclared_table["success"] is False
    assert undeclared_table["error"]["code"] == "UNDECLARED_TABLE"


def test_a_persona_with_no_pack_fails_with_no_method_pack():
    # A persona that has no pack must fail loudly.  An agent with no method
    # must stop and escalate, not return an improvised answer.
    env = make_run_diagnostic("P4", S07_SP3_TABLES)("liberation")
    assert env["success"] is False
    assert env["error"]["code"] == "NO_METHOD_PACK"


def test_no_envelope_carries_the_sql_text_or_a_sql_path():
    # Returning the SQL text would undo the withholding that method_lookup
    # enforces.  Assert against the full JSON dump so a field added anywhere
    # in the envelope is caught, not just in the obvious places. Covers a
    # genuine failure (no_such_driver) and the not_instrumented success path
    # (reagent_regime) — the latter never touches a .sql file, but the guard
    # is worth keeping now that it is a success envelope too.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    for driver_id in ("no_such_driver", "reagent_regime"):
        dumped = json.dumps(run(driver_id))
        assert ".sql" not in dumped, f"{driver_id!r}: a .sql path leaked: {dumped}"
        assert "WITH cs AS" not in dumped, f"{driver_id!r}: SQL text leaked: {dumped}"


@pytest.mark.integration
def test_the_success_envelope_carries_results_without_the_query_behind_them():
    # The failure paths above never touch the SQL file, so on their own they
    # would still pass if the success path returned the whole query. This is
    # the path that actually reads the file, so it is the one where a leak is
    # possible — and the one an agent sees on every real call.
    env = make_run_diagnostic("P6", S07_SP3_TABLES)("liberation")
    assert env["success"] is True, env.get("error")
    dumped = json.dumps(env)
    assert "WITH cs AS" not in dumped, f"SQL text leaked into the result: {dumped}"
    assert "sql/p6" not in dumped, f"the SQL file path leaked: {dumped}"
    # meta.tables_read legitimately names the tables, so a bare table name is
    # not evidence of a leak. A bound parameter marker is: it appears in
    # liberation.sql and has no reason to appear in a result. (NTILE was the
    # obvious second sentinel but lives only in feed_variability.sql, so
    # asserting it here would have passed no matter what leaked.)
    assert "@tight_max" not in dumped, f"a query parameter leaked: {dumped}"


@pytest.mark.integration
def test_liberation_returns_three_bands_and_a_non_empty_guard():
    # The magnitudes are pinned to match test_the_liberation_diagnostic_
    # reproduces_the_design_finding in tests/method/test_p6_pack.py.
    # Two tests pinning the same data cannot silently drift apart.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    env = run("liberation")
    assert env["success"] is True, env.get("error")
    data = env["data"]
    assert data["driver"] == "liberation"
    assert data["guard"]  # non-empty; the constraint the agent must honour
    rows = data["rows"]
    bands = {r["band"]: r for r in rows}
    assert set(bands) == {"tight", "mid", "wide"}
    assert [bands[b]["days"] for b in ("tight", "mid", "wide")] == [23, 116, 28]


@pytest.mark.integration
def test_liberation_meta_names_both_source_tables():
    # The provenance panel must show the real sources.  Deriving the declared
    # list from the SQL text via the _TABLE_REF regex is what makes this true:
    # if the regex under-extracts, the dry run refuses the query loudly.
    run = make_run_diagnostic("P6", S07_SP3_TABLES)
    env = run("liberation")
    assert env["success"] is True, env.get("error")
    tables = env["meta"]["tables_read"]
    assert "mining_data.crusher_states" in tables
    assert "mining_data.metallurgical_recovery" in tables


def test_a_missing_sql_file_is_a_structured_failure_not_a_traceback(tmp_path,
                                                                    monkeypatch):
    """The YAML can ship without the SQL, and has nearly done so twice.

    `method/` was once absent from SHARED_TREES, and a packaging ignore pattern
    could drop `*.sql` while leaving the pack in place — which is what
    test_run_diagnostic_finds_its_sql_from_inside_a_generated_package exists
    for. In that layout every driver resolves, and the file read then raises
    FileNotFoundError straight into the ADK runtime, bypassing every structured
    error path the agent knows how to read. A traceback is not an answer the
    agent can report, so the reader is told nothing at all.
    """
    shutil.copy(PACK_DIR / PACKS["P6"], tmp_path / PACKS["P6"])
    # The pack travels; sql/ does not. Exactly the shape of the two near misses.
    assert not (tmp_path / "sql").exists()
    monkeypatch.setattr(module, "PACK_DIR", Path(tmp_path))

    env = make_run_diagnostic("P6", S07_SP3_TABLES)("liberation")
    assert env["success"] is False
    assert env["error"]["code"] == "QUERY_FAILED"
    # Support has to be able to tell a missing file from a BigQuery refusal,
    # and the reason is the only place that distinction survives.
    assert env["error"]["details"]["reason"] == "FileNotFoundError"
    # The withholding still holds on this path: no path, no SQL.
    assert ".sql" not in json.dumps(env)


def test_a_driver_reaching_beyond_the_agents_declared_tables_is_refused():
    """The agent's own grant is the constraint, not the diagnostic's own SQL.

    `tables` is extracted from the very SQL that is then checked against it, so
    handing that list to run_query makes the declared-table check
    self-satisfying on this path. Nothing today reaches past S07-SP3's grant —
    but a fork that adds a diagnostic over biometric_fatigue_logs would get the
    rows AND skip the BIOMETRIC instruction gating, because that gating keys on
    source_tables. Silently.
    """
    run = make_run_diagnostic("P6", ["mining_data.metallurgical_recovery"])
    env = run("liberation")
    assert env["success"] is False, "a diagnostic reached past the agent's grant"
    assert env["error"]["code"] == "UNDECLARED_TABLE"
    assert env["error"]["details"]["undeclared"] == ["mining_data.crusher_states"]


def test_every_shipped_diagnostic_fits_the_agent_that_holds_it():
    """The other half of the check above: nothing shipped is refused today.

    A diagnostic that does not fit its agent is a finding for the pack author,
    never a reason to widen source_tables — widening would hand the agent every
    other query in the catalogue's reach as well.
    """
    holders = [a for a in ALL_AGENTS if "run_diagnostic" in a.tools]
    assert holders, "no agent holds run_diagnostic — this test would prove nothing"
    for agent in holders:
        pack = load_pack(PACK_DIR / PACKS[agent.persona])
        declared = set(agent.source_tables)
        for driver in pack.drivers:
            if not driver.sql:
                continue
            reads = set(_referenced_tables((PACK_DIR / driver.sql).read_text()))
            assert reads <= declared, (
                f"{agent.agent_id}: the {driver.id!r} diagnostic reads "
                f"{sorted(reads - declared)}, which the agent does not declare. "
                "Fix the pack or move the driver; do not widen the agent."
            )
