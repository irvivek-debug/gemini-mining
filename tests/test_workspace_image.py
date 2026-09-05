"""Gate: the workspace container's dependency list stays honest.

`apps/workspace/requirements.txt` is deliberately not the repository's. The
root list installs google-adk and google-cloud-aiplatform because that is what
an AGENT needs; this container runs no agent, and installing them here would
add roughly a gigabyte to the image for code paths the process never reaches.

That claim is only safe while it stays true. `server.py` imports
`mining_agents.registry` and `scripts.deploy` — modules shared with code that
does build agents — so a single module-level `from google.adk...` added
anywhere in that graph would silently reintroduce the dependency, and the
symptom would be a container that fails to start long after the commit that
caused it. This file catches it at test time instead.
"""
import json
import pathlib
import subprocess
import sys
import textwrap

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_REQUIREMENTS = _REPO_ROOT / "apps" / "workspace" / "requirements.txt"

# The two heavyweight trees the container exists to avoid. Blocking the parent
# path is enough: every submodule import passes through it.
_FORBIDDEN = ("google.adk", "google.cloud.aiplatform")


def test_the_workspace_image_needs_no_agent_sdk():
    """Importing the server must not reach for the ADK or the Vertex SDK.

    Runs in a subprocess with a meta_path finder that refuses the two trees,
    because under pytest they are installed and would satisfy the import
    quietly. The finder is installed before the import, so the failure is an
    ImportError naming the offending module rather than a silent pass.
    """
    script = textwrap.dedent(f"""
        import importlib.abc, json, sys

        FORBIDDEN = {_FORBIDDEN!r}

        class Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                for banned in FORBIDDEN:
                    if fullname == banned or fullname.startswith(banned + "."):
                        raise ImportError(
                            "apps.workspace.server reached for " + fullname
                        )
                return None

        sys.meta_path.insert(0, Blocker())
        sys.path.insert(0, {str(_REPO_ROOT)!r})

        import apps.workspace.server as server

        print(json.dumps({{"entrypoints": len(server._entrypoints())}}))
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        env={"PATH": "/usr/bin:/bin", "HOME": "/tmp",
             # Config, not a dependency: the deployed container carries this (see deploy_apps.py --set-env-vars).
             "GOOGLE_CLOUD_PROJECT": "test-project"},
    )
    assert result.returncode == 0, (
        f"the workspace container's dependency list is no longer "
        f"sufficient:\n{result.stderr}"
    )
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["entrypoints"] == 52, report


def test_the_requirements_list_pins_the_transport_that_fails_at_call_time():
    """`requests` must stay in the list, and not by accident.

    `google.auth.transport.requests` is an OPTIONAL extra of google-auth: it
    raises ImportError when the transport is CONSTRUCTED, not when the server
    is imported. The first deployed revision therefore came up healthy, served
    every page, and answered /api/runtime with a 500. No import check can catch
    that, so the pin is asserted here directly.
    """
    pinned = {
        line.split(">=")[0].split("[")[0].strip()
        for line in _REQUIREMENTS.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert "requests" in pinned, (
        "google.auth.transport.requests needs this and fails at call time, "
        "not at import time — removing it breaks /api/runtime in production "
        "while every other route keeps working."
    )
