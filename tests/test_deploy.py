"""Gate: what the deploy sends is what the agents actually need at runtime.

The expensive failure this file guards against is a deploy that succeeds, a
container that builds, and an agent that then dies on its first query because a
file it reads at runtime never travelled. That round trip costs a full container
build to discover and the error surfaces nowhere near its cause. It has happened
once: `references/` was omitted and every agent crashed on `model-policy.md`.

Cloud Run makes that failure mode sharper, not milder. The `cloud_run` verb has
no `--extra_packages` — it copies the agent directory and nothing else — so the
question "did everything travel?" is now answered entirely by what
`scripts.packages` writes. `test_a_generated_package_imports_with_only_the_agents_root_on_sys_path`
is the test that actually answers it, by reproducing the container's import
environment rather than asserting about paths.
"""
import json
import pathlib
import subprocess
import sys
import textwrap

import pytest

from mining_agents.config import model_for_tier, settings
from mining_agents.registry import registrations
from scripts.deploy import (
    CONFIRM_PHRASE,
    REGION,
    SERVICE_PREFIX,
    SESSION_SERVICE_URI,
    deploy,
    deploy_command,
    service_name,
)
from scripts.packages import SHARED_TREES, write_packages

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def generated_packages(tmp_path_factory) -> pathlib.Path:
    """The real generated tree, written once and shared by the tests below."""
    root = tmp_path_factory.mktemp("packages")
    written = write_packages(root)
    assert written, "no packages generated — every test below would prove nothing"
    return root


def _display_name(agent_id: str) -> str:
    return next(e["display_name"] for e in registrations() if e["agent_id"] == agent_id)


def _service_account(agent_id: str) -> str:
    return next(
        e["service_account"] for e in registrations() if e["agent_id"] == agent_id
    )


# ---------------------------------------------------------------------------
# What travels to the container
# ---------------------------------------------------------------------------

def test_every_shared_tree_exists_in_the_repo():
    for tree in SHARED_TREES:
        assert (_REPO_ROOT / tree).is_dir(), (
            f"{tree} is declared in SHARED_TREES but is absent from the repo"
        )


def test_the_model_policy_file_travels_into_every_generated_package(
    generated_packages,
):
    """model_for_tier() opens this file every time an agent is built, so a
    container without it cannot construct a single agent.

    Checked by locating the file relative to each package rather than by
    trusting that `references` appears in SHARED_TREES: the constant naming the
    directory and the file actually landing in the right place are two
    different claims, and only the second one keeps the container alive.
    """
    policy = settings().model_policy_path.resolve()
    assert policy.is_file(), f"{policy} does not exist — this test proves nothing"
    relative = policy.relative_to(_REPO_ROOT)

    packages = sorted(p for p in generated_packages.iterdir() if p.is_dir())
    assert packages, "no packages on disk — the loop below would prove nothing"
    for package in packages:
        assert (package / relative).is_file(), (
            f"{relative} is read at runtime but did not travel into {package.name}"
        )


def test_the_shared_package_travels_into_every_generated_package(generated_packages):
    """Without this the shim's `from mining_agents.build import build_one`
    cannot resolve and no agent module imports at all."""
    packages = sorted(p for p in generated_packages.iterdir() if p.is_dir())
    assert packages, "no packages on disk — the loop below would prove nothing"
    for package in packages:
        assert (package / "mining_agents" / "build.py").is_file(), package.name


def test_no_build_artefacts_travel(generated_packages):
    """A .pyc compiled against this Mac's interpreter is not valid in the
    container's python:3.11-slim, and a stale one shadows the source it was
    built from."""
    strays = [
        str(p.relative_to(generated_packages))
        for p in generated_packages.rglob("*")
        if p.name == "__pycache__" or p.suffix == ".pyc"
    ]
    assert strays == []


def test_a_shared_tree_cannot_collide_with_an_agent_id_or_the_staging_root(
    generated_packages,
):
    """Two directories are on sys.path in the container: the agents root
    (/app/agents) and this package's own directory. A shared tree named after
    an agent id — or named `agents` — is therefore importable from two places
    at once, and which one wins depends on insertion order."""
    entrypoints = {e["agent_id"] for e in registrations()}
    assert entrypoints, "no entrypoints — the assertions below would prove nothing"
    for tree in SHARED_TREES:
        assert tree != "agents", "collides with the ADK staging root"
        assert tree not in entrypoints, f"{tree} collides with an agent id"


def test_model_policy_resolves_every_tier_the_catalog_uses():
    """A tier absent from model-policy.md raises at build time, which in a
    container means the same opaque runtime failure as a missing file."""
    from mining_agents.catalog.definitions import ALL_AGENTS

    tiers = {a.model_tier for a in ALL_AGENTS}
    assert tiers, "no tiers found — the loop below would prove nothing"
    for tier in sorted(tiers):
        assert model_for_tier(tier)


def test_a_generated_package_imports_with_only_the_agents_root_on_sys_path(
    generated_packages,
):
    """The container's import environment, reproduced exactly.

    ADK's loader puts ONLY the agents root on sys.path — never the individual
    agent directory — so `import mining_agents` resolves solely because the
    generated `__init__.py` bootstraps its own directory onto the path. This
    runs in a subprocess with a cleared PYTHONPATH so the checkout cannot
    silently satisfy the import the way it does under pytest, and asserts on
    the resolved module file so that satisfying it from the checkout would
    fail rather than pass quietly.
    """
    agent_id = sorted(p.name for p in generated_packages.iterdir() if p.is_dir())[0]
    script = textwrap.dedent(f"""
        import importlib, json, sys
        sys.path.insert(0, {str(generated_packages)!r})
        module = importlib.import_module("{agent_id}.agent")
        import mining_agents.config as config
        print(json.dumps({{
            "agent_name": module.root_agent.name,
            "config_file": config.__file__,
            "policy": str(config.settings().model_policy_path),
            "policy_exists": config.settings().model_policy_path.is_file(),
        }}))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        # Run from the filesystem root and with no PYTHONPATH, so nothing but
        # the agents root can satisfy the import.
        cwd="/",
        env={"PATH": "/usr/bin:/bin", "HOME": "/tmp",
             # Config, not a dependency: the deployed container carries this (see deploy.py --set-env-vars).
             "GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    assert result.returncode == 0, (
        f"the container's import model does not work:\n{result.stderr}"
    )
    report = json.loads(result.stdout.strip().splitlines()[-1])

    assert report["agent_name"] == agent_id.lower()
    assert report["policy_exists"], report["policy"]
    # The imports must have resolved from inside the package, not the checkout.
    package = generated_packages / agent_id
    for key in ("config_file", "policy"):
        assert report[key].startswith(str(package)), (
            f"{key} resolved to {report[key]}, outside {package} — the test "
            f"passed using the checkout, which does not exist in the container"
        )


# ---------------------------------------------------------------------------
# The deploy command
# ---------------------------------------------------------------------------

def test_deploy_command_targets_a_cloud_run_region_not_the_bq_location():
    """`settings().location` is 'US', a BigQuery location. Passing it as
    --region deploys nowhere."""
    assert REGION != settings().location
    assert f"--region={REGION}" in deploy_command("D01", _service_account("D01"))


def test_deploy_command_points_at_the_generated_package_directory():
    """The ADK verb takes a directory, not an agent id (Ruling 1). It is the
    last ADK-side token, immediately before the gcloud separator."""
    argv = deploy_command("D01", _service_account("D01"))
    assert argv[argv.index("--") - 1] == "./packages/D01"


def test_deploy_command_does_not_pass_extra_packages():
    """`cloud_run` has no such flag — it hardcodes an empty extra-packages
    block into the Dockerfile — so passing one fails the deploy outright.
    Everything the container needs travels inside the package instead."""
    assert not any(
        a.startswith("--extra_packages") for a in deploy_command("D01", "sa@x.com")
    )


def test_deploy_command_sets_the_runtime_identity_on_the_gcloud_side():
    """ADK exposes no service-account flag of its own, so this has to reach
    gcloud through the `--` separator. Before the separator it would be parsed
    by ADK, which does not know the option, and the deploy would fail."""
    argv = deploy_command("D01", _service_account("D01"))
    flag = f"--service-account={_service_account('D01')}"
    assert flag in argv
    assert argv.index(flag) > argv.index("--"), (
        "the service account was passed to ADK rather than to gcloud"
    )


def test_deploy_command_sets_the_identity_for_the_agent_it_names():
    """One wrong pairing here gives an agent another tier's privileges, which
    no later test would notice: the deploy succeeds and the agent runs."""
    entries = registrations()
    assert entries, "no registrations — the loop below would prove nothing"
    for entry in entries:
        argv = deploy_command(entry["agent_id"], entry["service_account"])
        assert f"--service-account={entry['service_account']}" in argv
        assert f"--service_name={service_name(entry['agent_id'])}" in argv


def test_deploy_command_keeps_the_endpoint_private():
    """A public agent endpoint on a project holding biometric tables is not a
    risk worth taking for demo convenience."""
    assert "--no-allow-unauthenticated" in deploy_command("D01", "sa@x.com")


def test_deploy_command_allows_a_swarm_longer_than_the_cloud_run_default():
    """Cloud Run's default request timeout is 300s, and a Pattern A swarm
    exceeds it.

    Measured on S07 against the governing P6 question: the whole graph — three
    specialists in parallel, the join, the critic, then the coordinator — ran
    293.99s and was cut off by the platform mid-loop, after the critic had
    reported and while the coordinator was still verifying. No answer was ever
    written. An earlier run of the same question finished in 209s, which is why
    this stayed invisible: the margin was 90 seconds and a stricter critic
    consumed it.

    The failure mode is the worst kind. Cloud Run closes the connection
    cleanly, so the stream ends with `proxy-done` and no error; the page's only
    honest reading is "The agent finished without writing an answer." Nothing
    anywhere says the platform stopped it.

    3600s is the maximum Cloud Run allows for an HTTP/1 request. It is a
    ceiling, not a target — a run that needs an hour has a different problem —
    but there is no cost to a ceiling that is never reached, and every cost to
    one that is.
    """
    argv = deploy_command("D01", "sa@x.com")
    assert "--timeout=3600" in argv
    assert argv.index("--timeout=3600") > argv.index("--"), (
        "the timeout was passed to ADK rather than to gcloud"
    )


def test_deploy_command_states_the_session_backend_explicitly():
    """ADK defaults this to 'memory://' silently. Passing it makes the choice
    visible in the dry run, which is where anyone forking this will read it."""
    argv = deploy_command("D01", "sa@x.com")
    assert f"--session_service_uri={SESSION_SERVICE_URI}" in argv


def test_deploy_command_names_the_app_after_the_agent_not_the_temp_folder():
    """Without --app_name ADK uses the staging folder's basename, which is a
    timestamp — so the address a caller uses would change on every deploy."""
    assert "--app_name=D01" in deploy_command("D01", "sa@x.com")


# ---------------------------------------------------------------------------
# Service naming — the whole no-duplicate-instances guarantee
# ---------------------------------------------------------------------------

def test_service_names_are_valid_rfc1035_and_unique():
    """`gcloud run deploy` is create-or-update on this name, so a collision
    between two agents would have one silently overwrite the other, and an
    invalid name fails only after the container has been built."""
    import re

    entries = registrations()
    assert entries, "no registrations — the assertions below would prove nothing"
    names = [service_name(e["agent_id"]) for e in entries]
    assert len(set(names)) == len(names), "two agents share one service name"
    for name in names:
        assert re.fullmatch(r"[a-z]([-a-z0-9]*[a-z0-9])?", name), name
        assert len(name) <= 63, name


def test_service_name_derives_from_the_immutable_agent_id_not_the_display_name():
    """Display names are prose and get edited; agent ids do not. Keying the
    deployment on prose is what made the Agent Engine path create a second
    billing instance whenever someone reworded a name."""
    agent_id = "D01"
    assert service_name(agent_id) == f"{SERVICE_PREFIX}{agent_id.lower()}"
    assert _display_name(agent_id).lower() not in service_name(agent_id)


# ---------------------------------------------------------------------------
# The dry run
# ---------------------------------------------------------------------------

def test_deploy_refuses_an_id_that_is_not_an_entrypoint():
    """`only` is a filter, not an escape hatch: a typo must fail loudly rather
    than silently deploying nothing."""
    with pytest.raises(KeyError):
        deploy(dry_run=True, only=("S01", "not-an-agent"))


def test_a_real_deploy_needs_the_confirm_phrase_not_just_the_flag():
    with pytest.raises(PermissionError):
        deploy(dry_run=False, only=("D01",))


def test_dry_run_prints_the_argv_the_real_run_would_execute(capsys):
    """The two must come from one function. A dry run that renders the command
    separately reads as evidence while being free to drift from what happens."""
    deploy(dry_run=True, only=("D01",))
    printed = capsys.readouterr().out
    for token in deploy_command("D01", _service_account("D01")):
        assert token in printed, token


def test_dry_run_names_a_service_account_for_every_agent(capsys):
    entries = list(registrations())
    assert entries, "no registrations — the assertions below would prove nothing"
    deploy(dry_run=True)
    printed = capsys.readouterr().out
    for entry in entries:
        assert entry["service_account"] in printed, entry["agent_id"]


def test_dry_run_never_executes_the_domain_binding(capsys):
    """Ruling 3. The command is printed for audit and run by a human or not
    at all."""
    deploy(dry_run=True, only=("D01",))
    printed = capsys.readouterr().out
    assert "add-iam-policy-binding" in printed
    assert "roles/run.invoker" in printed, (
        "aiplatform.user does not admit a caller to a Cloud Run endpoint"
    )
    assert "will NOT run it" in printed


# ---------------------------------------------------------------------------
# The snapshot the real run ships
# ---------------------------------------------------------------------------

def test_a_real_deploy_regenerates_the_packages_before_it_ships_them(monkeypatch):
    """`packages/` is gitignored scratch, and `deploy()` used to ship whatever
    happened to be sitting in it.

    This is not a hypothetical. A live verification found S07 answering from a
    container built four days before the code it was supposed to be running:
    the deploy read a stale `packages/S07`, the container built cleanly, the
    service came up healthy, and the agent quietly behaved like the old one.
    Nothing failed, which is what made it expensive.

    A deploy must therefore be self-contained — regenerate, then ship — so the
    snapshot cannot be older than the source it claims to be.
    """
    calls: list[str] = []
    monkeypatch.setattr(
        "scripts.deploy.write_packages",
        lambda root: calls.append(str(root)) or [],
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: None)

    deploy(dry_run=False, only=("D01",), confirm=CONFIRM_PHRASE)

    assert calls, (
        "the real deploy shipped ./packages without regenerating it, so what "
        "reaches the container is whatever was last written there"
    )
    assert calls[0].endswith("packages"), calls


def test_a_dry_run_regenerates_nothing(monkeypatch):
    """A dry run reports; it does not touch the working tree. If it rewrote
    `packages/` it would be a side effect the name explicitly disclaims."""
    calls: list[str] = []
    monkeypatch.setattr(
        "scripts.deploy.write_packages",
        lambda root: calls.append(str(root)) or [],
    )
    deploy(dry_run=True, only=("D01",))
    assert calls == []
