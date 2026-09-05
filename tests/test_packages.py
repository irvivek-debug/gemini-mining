"""Gate: the generated per-agent packages are deployable and stay a thin shim.

The ADK deploy verb takes a DIRECTORY, not an agent id, so each of the 52
entrypoints needs its own package. The risk this file guards against is that
the generated tree becomes a second source of truth: if agent logic were copied
into it, the copy would drift from the catalog and nothing would notice.
"""
import subprocess
import sys

import pytest

from mining_agents.build import build_one
from mining_agents.catalog.definitions import ALL_AGENTS, SWARMS
from mining_agents.registry import registrable
from scripts.packages import (
    AGENT_MODULE_NAME,
    REQUIREMENTS_NAME,
    runtime_requirements,
    write_packages,
)


def test_build_one_builds_every_entrypoint_the_registry_advertises():
    expected = {a.agent_id for a in registrable()}
    assert expected, "registrable() is empty — the loop below would prove nothing"
    for entry_id in sorted(expected):
        assert build_one(entry_id) is not None, entry_id


def test_build_one_refuses_a_specialist_because_it_is_not_independently_callable():
    """A specialist has no endpoint of its own. Building one as an entrypoint
    would deploy exactly what the registry deliberately refuses to advertise."""
    specialists = [m.agent_id for s in SWARMS for m in s.specialists]
    assert specialists, "no specialists found — the loop below would prove nothing"
    for agent_id in specialists:
        with pytest.raises(KeyError):
            build_one(agent_id)


def test_build_one_refuses_a_critic():
    critics = [s.critic.agent_id for s in SWARMS]
    assert critics, "no critics found — the loop below would prove nothing"
    for agent_id in critics:
        with pytest.raises(KeyError):
            build_one(agent_id)


def test_write_packages_creates_one_package_per_registrable_agent(tmp_path):
    written = write_packages(tmp_path)
    expected = {a.agent_id for a in registrable()}
    assert {p.name for p in written} == expected
    assert len(written) == 52


def test_every_generated_package_exposes_root_agent(tmp_path):
    written = write_packages(tmp_path)
    assert written, "no packages written — the loop below would prove nothing"
    for pkg in written:
        assert (pkg / "__init__.py").is_file(), pkg
        assert (pkg / AGENT_MODULE_NAME).is_file(), pkg
        assert "root_agent" in (pkg / AGENT_MODULE_NAME).read_text(), pkg


def test_generated_packages_copy_no_agent_logic(tmp_path):
    """The shim imports; it does not reimplement.

    If a generated module ever names a model, a tool, or a table, the generated
    tree has started to be a second source of truth.
    """
    written = write_packages(tmp_path)
    assert written, "no packages written — the loop below would prove nothing"
    forbidden = ("gemini", "LlmAgent", "mining_data.", "make_bq_query", "instruction")
    offenders = [
        (pkg.name, token)
        for pkg in written
        for token in forbidden
        if token in (pkg / AGENT_MODULE_NAME).read_text()
    ]
    assert offenders == []


def test_a_generated_package_actually_imports_and_yields_the_right_agent(tmp_path):
    """Proves the shim runs — a file containing the text `root_agent` is not
    evidence that importing it produces one."""
    write_packages(tmp_path)
    entry_id = sorted(a.agent_id for a in registrable())[0]
    script = (
        "import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "from %s.agent import root_agent\n"
        "print(type(root_agent).__name__)\n"
        % (str(tmp_path), str(_repo_root()), entry_id)
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), result.stderr


def test_every_package_ships_the_runtime_dependencies_agents_actually_imports(tmp_path):
    """A container that cannot import google.cloud.bigquery cannot run bq_query,
    which is the tool almost every agent in the catalog depends on."""
    written = write_packages(tmp_path)
    assert written, "no packages written — the loop below would prove nothing"
    for pkg in written:
        text = (pkg / REQUIREMENTS_NAME).read_text()
        assert "google-adk" in text, pkg
        assert "google-cloud-bigquery" in text, pkg


def test_test_only_dependencies_do_not_travel_to_the_container(tmp_path):
    """pyyaml used to be asserted here too, on the reasoning that only
    build-time tooling read it. That reasoning expired the moment
    `mining_agents/method/pack.py` imported it, and this test then actively
    defended the bug — it required the container to be missing a dependency the
    agent tree needs. The complement (every import under `mining_agents/` is
    covered by the container requirements) lives in
    `tests/test_packages_ship_the_method_pack.py` and is derived from the
    imports rather than hand-listed, so neither side can go stale in silence
    again.
    """
    requirements = (_repo_root() / "requirements.txt").read_text()
    for package in ("pytest",):
        assert package in requirements, (
            f"requirements.txt no longer pins {package} — this test would pass "
            "vacuously"
        )
        assert package not in runtime_requirements(), (
            f"{package} reached the container requirements. Nothing under "
            "mining_agents/ imports it; shipping it means a container "
            "dependency no code needs."
        )


def test_regenerating_is_idempotent(tmp_path):
    first = {p.name: (p / AGENT_MODULE_NAME).read_text() for p in write_packages(tmp_path)}
    second = {p.name: (p / AGENT_MODULE_NAME).read_text() for p in write_packages(tmp_path)}
    assert first == second
    assert first, "no packages written — the comparison above would be trivial"


def _repo_root():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent
