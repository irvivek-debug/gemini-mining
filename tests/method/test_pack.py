"""The pack is the part of the method that must be complete and inspectable."""
from pathlib import Path

import pytest

from mining_agents.method.pack import PackError, load_pack

FIXTURES = Path(__file__).parent / "fixtures"


def test_a_valid_pack_loads_its_drivers():
    pack = load_pack(FIXTURES / "valid.yaml")
    assert pack.metric == "unit cost per tonne of contained metal"
    assert [d.id for d in pack.drivers] == ["liberation", "reagent_regime"]
    assert pack.drivers[0].controllable is True
    assert pack.drivers[0].params == {"tight_max": 117, "wide_min": 123}


def test_an_outcome_decile_comparison_is_refused():
    # Comparing to the best decile of an outcome banks noise as achievable;
    # regression to the mean guarantees the prize is overstated.
    with pytest.raises(PackError, match="setting_band"):
        load_pack(FIXTURES / "outcome-decile.yaml")


def test_a_driver_without_a_status_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    controllable: false\n"
    )
    with pytest.raises(PackError, match="status"):
        load_pack(bad)


def test_an_unknown_status_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: probably\n    controllable: false\n"
    )
    with pytest.raises(PackError, match="probably"):
        load_pack(bad)


def test_a_status_that_states_a_verdict_is_refused(tmp_path):
    """`unevidenced` was a status, and it was a conclusion written in advance.

    A driver carrying both `sql` and a verdict has decided what its own query
    will show. On a fork whose data has plenty of bypass events, the pack would
    still have said "unevidenced" — which is the precomputed-report failure the
    whole redesign exists to replace. Status now says only whether a diagnostic
    exists; evidenced or not is a conclusion drawn at runtime from the rows.
    """
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: unevidenced\n    controllable: false\n"
    )
    with pytest.raises(PackError, match="unevidenced"):
        load_pack(bad)


def test_an_instrumented_driver_must_carry_a_diagnostic(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: instrumented\n    controllable: true\n    compare: setting_band\n"
    )
    with pytest.raises(PackError, match="sql"):
        load_pack(bad)


def test_a_not_instrumented_driver_may_not_carry_a_diagnostic(tmp_path):
    """The converse, which nothing checked while status carried a verdict.

    run_diagnostic decides DRIVER_NOT_INSTRUMENTED on the presence of `sql`,
    while method_lookup reports the `status` field — so a driver that declares
    one and carries the other tells the agent two different things about the
    same driver, and the agent reports whichever it read last.
    """
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: not_instrumented\n    controllable: true\n"
        "    sql: sql/p6/liberation.sql\n"
    )
    with pytest.raises(PackError, match="not_instrumented"):
        load_pack(bad)


def test_a_pack_with_no_drivers_is_refused(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("metric: m\nroot: r\ndrivers: []\n")
    with pytest.raises(PackError, match="driver"):
        load_pack(bad)


def test_a_comparison_on_a_driver_with_no_diagnostic_is_refused(tmp_path):
    # A comparison the pack cannot compute is a claim it cannot honour. Left
    # to load, it tells a pack author a comparison is happening when nothing
    # computes one.
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "metric: m\nroot: r\ndrivers:\n  - id: d\n    question: q\n"
        "    status: not_instrumented\n    controllable: false\n"
        "    compare: setting_band\n"
    )
    with pytest.raises(PackError, match="only an instrumented driver compares"):
        load_pack(bad)


def test_a_malformed_pack_is_refused_rather_than_crashing(tmp_path):
    """Every rejection is a PackError, not a traceback.

    This module exists to be a gate, so it has to fail the way a gate fails.
    An AttributeError raised from inside a comprehension tells a pack author
    nothing about which line of YAML is wrong. Each case below reached a bare
    TypeError or AttributeError before this test existed.
    """
    cases = {
        "drivers is a scalar": "metric: m\nroot: r\ndrivers: not_a_list\n",
        "a driver is a scalar": "metric: m\nroot: r\ndrivers:\n  - just_a_string\n",
        "the pack is a bare list": "- metric: m\n",
    }
    for name, text in cases.items():
        bad = tmp_path / f"{name.replace(' ', '_')}.yaml"
        bad.write_text(text)
        with pytest.raises(PackError):
            load_pack(bad)
