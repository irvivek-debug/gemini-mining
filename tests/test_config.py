import pytest
from mining_agents.config import (
    MODEL_LOCATION,
    llm_for_tier,
    model_for_tier,
    settings,
)


def test_settings_reads_the_project_id_from_the_environment(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project-123")
    s = settings()
    assert s.project_id == "test-project-123"
    assert s.dataset == "mining_data"
    assert s.location == "US"


def test_settings_raises_when_project_id_is_unset(monkeypatch):
    """A placeholder default would surface as a confusing BigQuery 404 later —
    settings() must fail loudly and immediately instead."""
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(RuntimeError):
        settings()


def test_model_for_tier_resolves_both_tiers():
    reasoning = model_for_tier("reasoning")
    balanced = model_for_tier("balanced")
    assert reasoning.startswith("gemini-"), f"reasoning tier returned unexpected model ID: {reasoning!r}"
    assert balanced.startswith("gemini-"), f"balanced tier returned unexpected model ID: {balanced!r}"
    assert reasoning != balanced


def test_both_configured_models_are_callable_in_this_project():
    """A withdrawn or misspelled model ID must fail here, not at deploy time.

    model-policy.md is edited by hand and nothing else validates it, so a typo
    would survive every other test in this suite and surface as a 404 on the
    first live agent run. One token per model keeps this cheap.

    The location comes from MODEL_LOCATION rather than a literal. This test
    once hardcoded "global" while the agents inherited their deployment region,
    so it passed against an endpoint no agent ever called and the models 404'd
    in production anyway. A test may not name the value it is validating.
    """
    import json
    import urllib.error
    import urllib.request

    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    project = settings().project_id
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }).encode()

    for tier in ("reasoning", "balanced"):
        model = model_for_tier(tier)
        host = (
            "aiplatform.googleapis.com"
            if MODEL_LOCATION == "global"
            else f"{MODEL_LOCATION}-aiplatform.googleapis.com"
        )
        url = (
            f"https://{host}/v1/projects/{project}"
            f"/locations/{MODEL_LOCATION}/publishers/google/models/{model}"
            ":generateContent"
        )
        request = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        })
        try:
            urllib.request.urlopen(request)
        except urllib.error.HTTPError as exc:
            raise AssertionError(
                f"tier {tier!r} names {model!r}, which this project cannot call "
                f"(HTTP {exc.code}). Fix references/model-policy.md."
            ) from exc


def test_no_floating_model_alias_is_configured():
    """A `-latest` alias changes underneath a demo and breaks reproducibility."""
    for tier in ("reasoning", "balanced"):
        assert not model_for_tier(tier).endswith("-latest"), tier


def test_the_llm_pins_the_location_instead_of_inheriting_the_deployment_region():
    """Agent Engine runs regionally, but these models are published only in
    `global`. An LLM that inherits the engine's region 404s on every call, and
    the error reads as a missing model rather than a wrong endpoint."""
    for tier in ("reasoning", "balanced"):
        llm = llm_for_tier(tier)
        assert llm.model == model_for_tier(tier), tier
        assert llm.client_kwargs["location"] == MODEL_LOCATION, tier
        assert llm.client_kwargs["vertexai"] is True, tier


def test_model_for_tier_rejects_pattern_c_tier():
    with pytest.raises(ValueError):
        model_for_tier("high-volume-subagent")


def test_no_raw_model_id_outside_model_policy():
    """The design forbids raw model IDs anywhere but references/model-policy.md.

    Scans all .py, .md, .json, .toml, .yaml, .yml files under the repo root,
    excluding .git/, agent-tool scratch directories, and any virtualenv.

    Guard: assert the scanned set is non-empty and plausibly large FIRST.
    A broken glob that matches nothing must not pass this test.
    """
    import pathlib, re
    root = pathlib.Path(__file__).resolve().parents[1]
    policy = root / "references" / "model-policy.md"
    pattern = re.compile(r"gemini-[0-9]")

    # Directories to skip entirely (relative to root).
    # docs/ is excluded because planning documents are expected to name model
    # IDs for discussion purposes (the same reason references/ is excluded).
    # Agent-tool scratch dirs are excluded: they hold working files, not source.
    # packages/ is gitignored build output: since the Cloud Run move each
    # deployable package carries its own copy of references/model-policy.md,
    # because Cloud Run has no --extra_packages and only the agent folder is
    # copied into the image. Scanning those copies would report one offender
    # per agent for a file that is legitimately exempt at its source. The rule
    # still bites where it matters — scripts/packages.py, which generates the
    # tree, remains in scope.
    # `vendor` holds verbatim copies of upstream artefacts (see
    # vendor/agent_registry/README.md). The model-ID rule governs what THIS
    # repo hard-codes; editing a vendored file to satisfy it would destroy the
    # verbatim property that makes the copy trustworthy in the first place.
    _SKIP_DIRS = {"venv", "env", "site-packages", "__pycache__",
                  "docs", "packages", "vendor"}

    def _should_skip(path: pathlib.Path) -> bool:
        for part in path.relative_to(root).parts[:-1]:
            # Any dot-directory is tooling state, not source: .git, .venv,
            # caches, and whatever editor or agent scratch dir happens to
            # exist in a given checkout.
            if part.startswith(".") or part in _SKIP_DIRS:
                return True
        return False

    extensions = {".py", ".md", ".json", ".toml", ".yaml", ".yml"}
    scanned = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in extensions:
            continue
        if _should_skip(path):
            continue
        scanned.append(path)

    # Population pin — a broken glob must not silently pass.
    assert len(scanned) > 50, (
        f"scan visited only {len(scanned)} files — expected >50; "
        "the glob may be broken or the repo has shrunk unexpectedly"
    )

    offenders = []
    for path in scanned:
        if path == policy:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            offenders.append(str(path.relative_to(root)))

    assert offenders == [], f"raw model IDs found outside model-policy.md: {offenders}"
