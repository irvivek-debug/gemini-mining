"""Every agent must be told where its data lives.

No agent instruction named the BigQuery project, so each query began by
guessing: passing the dataset `mining_data` as a project id (400, invalid
project), calling search_catalog without its mandatory project_id, trying a
project named `test` (refused -- the toolset is locked to one project). All
95 agents did this on every run. Most recovered after burning three or four
tool calls; S11-2-LEADTIME exhausted its budget and returned nothing.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "vendor" / "agent_registry"))

import catalog_definitions as C  # noqa: E402
import register_agents as R  # noqa: E402


def build(agent) -> str:
    """The instruction as register_agents composes it, without touching cloud."""
    tables = ", ".join(agent.source_tables) or "your declared sources"
    data_access = (
        f"Your data lives in BigQuery project `{R.PROJECT}`, dataset "
        f"`{R.DATASET}`. Fully qualified, a table is "
        f"`{R.PROJECT}.{R.DATASET}.<table>`.\n"
        f"`{R.DATASET}` is the dataset, never the project. Tools that require a "
        f"project_id take `{R.PROJECT}`. Do not guess a project name and do not "
        f"omit project_id -- both fail, and the retries cost you the answer.\n"
    )
    return data_access + (agent.system_instruction or f"You are {agent.name}.")


@pytest.mark.parametrize("agent", C.CATALOG, ids=lambda a: a.agent_id)
def test_every_agent_is_told_its_project(agent):
    assert R.PROJECT in build(agent)


@pytest.mark.parametrize("agent", C.CATALOG, ids=lambda a: a.agent_id)
def test_every_agent_is_told_its_dataset(agent):
    assert R.DATASET in build(agent)


def test_agents_with_their_own_instruction_still_get_it():
    """The `or` branch skipped the composed text entirely, so the two agents
    carrying a custom system_instruction would have kept guessing."""
    custom = [a for a in C.CATALOG if (a.system_instruction or "").strip()]
    assert custom, "fixture assumption broken: no agent carries a custom instruction"
    for a in custom:
        built = build(a)
        assert R.PROJECT in built
        assert a.system_instruction[:40] in built, "custom instruction was dropped"


def test_the_instruction_distinguishes_dataset_from_project():
    """The actual failure was using the dataset name as a project id."""
    built = build(C.CATALOG[0])
    assert "never the project" in built


def test_source_is_wired_not_just_this_test_file():
    """Guards the real composition path, not this file's copy of it."""
    src = (ROOT / "scripts" / "register_agents.py").read_text()
    assert "data_access" in src
    assert src.count("data_access +") >= 2, \
        "preamble is no longer prepended to both branches"


# --- the reconciliation demand must reach every agent -------------------------
# It lived only in the composed branch. The two agents carrying a custom
# system_instruction (AGT-19, S01-COORDINATOR) never received it, and they
# were exactly the two UAT content failures: fluent answers computed from the
# question's own numbers, citing nothing.

def _built(agent) -> str:
    """The instruction exactly as register_agents composes it."""
    import re
    src = (ROOT / "scripts" / "register_agents.py").read_text()
    # execute the real assembly block against this agent, not a paraphrase
    ns = {"agent": agent, "PROJECT": R.PROJECT, "DATASET": R.DATASET}
    block = src[src.index("    tables = "):src.index("    app = AdkApp")]
    import textwrap
    exec(textwrap.dedent(block), ns)
    return ns["instruction"]


@pytest.mark.parametrize("agent",
    [a for a in C.CATALOG if (a.system_instruction or "").strip()],
    ids=lambda a: a.agent_id)
def test_custom_instruction_agents_get_the_reconciliation_demand(agent):
    built = _built(agent)
    assert "reconcile each one against" in built
    assert "Never present a figure computed only from numbers in the question" in built
    assert agent.system_instruction[:40] in built, "custom instruction was dropped"


def test_composed_agents_still_get_the_reconciliation_demand():
    agent = next(a for a in C.CATALOG if not (a.system_instruction or "").strip())
    built = _built(agent)
    assert "reconcile each one against" in built
    assert "Your governing method is" in built


def test_the_demand_is_one_string_not_two_copies():
    """Duplicated prose drifts; the demand must exist once and be shared."""
    src = (ROOT / "scripts" / "register_agents.py").read_text()
    assert src.count("reconcile each one against") == 1
    assert src.count("grounding_demand") >= 3  # defined once, used in both branches
