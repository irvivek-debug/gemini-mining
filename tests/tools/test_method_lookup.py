"""Tests for method_lookup — the tool that hands an agent its driver tree.

The driver tree IS the method: it tells the agent which diagnostics exist, in
what order, and what guard conditions fence each recommendation. These tests
confirm that the contract between the tool and the agent is stable, and that
the tool fails loudly rather than silently when no pack is available.
"""
import json

import pytest

from mining_agents.tools.method_lookup import PACK_DIR, PACKS, make_method_lookup


def test_p6_returns_its_metric_and_every_driver():
    said = make_method_lookup("P6")()
    assert said["success"], said.get("error")
    data = said["data"]
    assert data["metric"] == "unit cost per tonne of contained metal"
    assert len(data["drivers"]) == 5


def test_uninstrumented_drivers_are_returned_not_filtered():
    # The agent must be able to say a driver was not instrumented. Filtering
    # them here would make that impossible and the answer would imply the
    # tree was fully explored.
    drivers = make_method_lookup("P6")()["data"]["drivers"]
    assert {d["status"] for d in drivers} == {"instrumented", "not_instrumented"}


def test_the_sql_is_not_exposed_to_the_model():
    # Handing the model raw SQL invites it to paraphrase or mutate the
    # diagnostic. The pack is fixed and auditable; the agent asks for a
    # result by driver id, and the runtime supplies the query.
    for driver in make_method_lookup("P6")()["data"]["drivers"]:
        assert "sql" not in driver, "exposing SQL invites the model to edit the method"


def test_a_persona_with_no_pack_fails_honestly():
    # A missing pack must surface as a known error code, not a crash. An agent
    # with no method has no business returning an answer; it should stop and
    # escalate.
    said = make_method_lookup("P4")()
    assert said["success"] is False
    assert said["error"]["code"] == "NO_METHOD_PACK"


def test_the_tool_reads_no_site_data():
    # method_lookup returns METHOD, not site data. tables_read must be empty so
    # the UX provenance panel does not show a fake table entry. rows_scanned
    # must be zero for the same reason.
    said = make_method_lookup("P6")()
    assert said["meta"]["tables_read"] == []
    assert said["meta"]["rows_scanned"] == 0


def test_each_driver_exposes_exactly_the_contracted_keys():
    # Deleting guard or doc_query from the projection leaves all other tests
    # passing while silently breaking the agent's method contract. guard is
    # what fences every recommendation; doc_query is what drives retrieval.
    # Pinning the exact key set means a dropped field is a test failure, not a
    # silent gap.
    expected_keys = {"id", "question", "status", "controllable", "guard", "doc_query"}
    for driver in make_method_lookup("P6")()["data"]["drivers"]:
        assert set(driver.keys()) == expected_keys, (
            f"driver {driver.get('id')!r} has unexpected keys: {set(driver.keys())}"
        )


def test_pack_root_is_returned():
    # root is the governing metric's root cause framing; the agent uses it to
    # orient the diagnostic. It was never asserted, so it could be silently
    # dropped from the projection.
    data = make_method_lookup("P6")()["data"]
    assert data["root"] == "contained metal lost to tailings"


def test_the_liberation_driver_carries_a_non_empty_guard():
    # guard is the constraint the agent must honour before recommending
    # anything. An empty guard is an unguarded recommendation waiting to happen.
    drivers = {d["id"]: d for d in make_method_lookup("P6")()["data"]["drivers"]}
    assert drivers["liberation"]["guard"], (
        "liberation driver has an empty guard; every recommendation it triggers "
        "must be fenced by the throughput-neutrality check"
    )


def test_a_malformed_pack_returns_a_fail_envelope_not_a_traceback(
    tmp_path, monkeypatch
):
    # yaml.YAMLError is not caught by the original (OSError, PackError) handler,
    # so a malformed YAML file propagates as a ParserError straight into the ADK
    # runtime. A tool that is the agent's entry point into its method must fail
    # as an envelope, never as a traceback.
    bad = tmp_path / "bad.yaml"
    bad.write_text(": bad: yaml: [\n")  # malformed YAML
    monkeypatch.setitem(PACKS, "P_BAD", "bad.yaml")
    monkeypatch.setattr("mining_agents.tools.method_lookup.PACK_DIR", tmp_path)
    env = make_method_lookup("P_BAD")()
    assert env["success"] is False
    assert env["error"]["code"] == "NO_METHOD_PACK"


def test_a_missing_pack_does_not_leak_an_absolute_filesystem_path(monkeypatch):
    # The one tool whose whole design withholds file paths from the model must
    # not put an absolute path in its own error message. The model would see
    # the host filesystem layout, which is ironic and unnecessary.
    monkeypatch.setitem(PACKS, "P_GONE", "nope.yaml")
    env = make_method_lookup("P_GONE")()
    assert env["success"] is False
    dumped = json.dumps(env)
    assert "/Users/" not in dumped, "absolute path leaked into failure envelope"
    assert "/home/" not in dumped, "absolute path leaked into failure envelope"
    # The bare filename should be in details so support can identify the pack.
    assert "nope.yaml" in dumped
