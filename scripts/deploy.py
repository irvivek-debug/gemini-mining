"""Deploy the 52 entrypoints to Cloud Run and attach their runtime identity.

Ruling 1: the ADK 2.6.3 deploy verb takes an agent DIRECTORY, not an agent id:
  python -m google.adk.cli deploy cloud_run \\
    --project=<PROJECT> --region=<REGION> --service_name=<NAME> <AGENT_DIRECTORY>

Ruling 3: DOMAIN_BINDING_COMMAND is NEVER executed by this module. It is
printed with a warning and the caller is required to run it manually if approved.

WHY CLOUD RUN AND NOT AGENT ENGINE — ruled 2026-08-12
------------------------------------------------------
Agent Engine bills memory continuously whether or not anyone calls the agent.
Measured via Cloud Monitoring on this project: `reasoning_engine/cpu/
allocation_time` scales to zero, but `reasoning_engine/memory/allocation_time`
holds a flat 14,400 GiB-seconds per hour — exactly 4 GiB — across six-hour
windows with zero requests. At the catalogued rate of $0.009/GiB-hour that is
$26.28 per agent per month, idle, forever; $1,366/month for all 52. ADK exposes
no memory or CPU knob for the `agent_engine` verb, so the 4 GiB is not
negotiable.

Cloud Run scales to zero: idle cost is $0, and a 30-second query on 1 vCPU /
2 GiB costs about $0.0009. The standing cost becomes the container images in
Artifact Registry, roughly $6/month for 52.

Two things got simpler in the move, both of which had been real defects:

  * Identity is attached AT DEPLOY, via `--service-account`. The Agent Engine
    path had no such flag and needed a follow-up PATCH, which left a window
    where the agent ran as the shared Vertex service agent — holding none of
    the per-tier limits the access model is built on.
  * Instances are keyed by a real NAME. The Agent Engine path had to key on
    displayName, the only field this repo controlled, so renaming a deployed
    agent silently created a second billing instance. `gcloud run deploy
    <service>` is create-or-update on the name, so re-running is idempotent by
    construction and no read-back of live state is needed.

The dry run prints the exact argv the real run executes, because both come from
`deploy_command`. A dry run that renders a command by hand is worse than no dry
run at all: it reads as evidence while being free to drift from what actually
happens. This module had that defect once already.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from mining_agents.config import settings
from mining_agents.registry import registrations
from scripts.packages import write_packages

# The directory `deploy_command` points the ADK verb at. It is gitignored
# scratch that `write_packages` regenerates, which is exactly why a real deploy
# must rewrite it first — see `deploy`.
PACKAGES_DIR = Path("packages")

# Cloud Run has its own regions; `settings().location` is the BigQuery dataset
# location ("US") and is not one of them.
REGION = "us-central1"

# Cloud Run service names are RFC1035: lowercase alphanumerics and hyphens,
# starting with a letter, 63 characters max. Agent ids ("D01", "S07") are
# uppercase, so they cannot be used raw. The prefix keeps the 52 agents
# identifiable among the unrelated services already in this project.
SERVICE_PREFIX = "mag-"

# WHAT THIS COSTS YOU AND WHY IT IS NOT A DATABASE.
#
# ADK defaults `session_service_uri` to 'memory://' (cli_deploy.py:710). With
# scale-to-zero that means conversation history is lost whenever the container
# spins down — which, on an idle demo project, is minutes after each session.
#
# That is acceptable for a showcase, where each demo is one short conversation,
# and it is the only option here that adds no recurring cost. It is NOT
# acceptable for a fork running real traffic, so the value is a named constant
# rather than an omitted flag: the alternatives are one line each.
#
#   "agentengine://<engine_id>"  one shared Agent Engine, ~$26/month TOTAL for
#                                all 52 — not per agent
#   "postgresql://..."           any SQLAlchemy URL; Cloud SQL smallest ~$9/mo
#
# `deploy` prints a warning on every real run while this is in-memory, so the
# choice cannot be inherited silently by someone who forked the repo.
SESSION_SERVICE_URI = "memory://"

# Passing dry_run=False is not enough to deploy; the caller must also pass this
# phrase. A boolean is too easy to reach by accident, and the accident is
# expensive: a unit test that asserted `deploy(dry_run=False)` raised — written
# when it did — kept calling it after the implementation landed, and spent
# twenty-six minutes creating eight billable instances before anyone noticed.
# Nothing about the call site looked dangerous.
CONFIRM_PHRASE = "yes-deploy-for-real"

# ---------------------------------------------------------------------------
# The single copy of this command lives in docs/phase-3-design.md §5.5.
# This module NEVER executes it — see Ruling 3.
#
# The role is `roles/run.invoker`, not `roles/aiplatform.user`: on Cloud Run
# that is the permission that admits a caller to an agent endpoint. Granting
# aiplatform.user here would give the domain Vertex access while leaving every
# agent unreachable — wrong in both directions at once.
# ---------------------------------------------------------------------------
DOMAIN_BINDING_COMMAND = (
    "gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \\\n"
    '  --member="domain:${GOOGLE_DOMAIN}" \\\n'
    '  --role="roles/run.invoker"'
)


def print_domain_binding_warning() -> None:
    """Print the resolved domain-binding command and an explicit warning.

    Ruling 3: this function exists to make the command auditable. It is
    NEVER called from a code path that executes it.
    """
    s = settings()
    resolved = DOMAIN_BINDING_COMMAND.replace(
        "${GOOGLE_CLOUD_PROJECT}", s.project_id
    )
    print("=" * 72)
    print("DOMAIN-WIDE IAM BINDING — REQUIRES EXPLICIT HUMAN APPROVAL")
    print(resolved)
    print()
    print("This grants access to EVERY user in the domain in one action.")
    print("Acceptable only because this is an Argolis sandbox.")
    print("DO NOT copy this binding into a production project.")
    print("This script will NOT run it. Run it yourself if you approve.")
    print("=" * 72)


def service_name(agent_id: str) -> str:
    """The Cloud Run service name for an agent id.

    This is the deployment's identity: `gcloud run deploy` creates the service
    when the name is new and updates it in place when it is not, so this
    function is the whole of the no-duplicate-instances guarantee. It is
    derived from the agent id — which the catalog treats as immutable — rather
    than from the display name, which is prose and gets edited.
    """
    return f"{SERVICE_PREFIX}{agent_id.lower()}"


def deploy_command(agent_id: str, service_account: str) -> list[str]:
    """The argv that deploys one entrypoint.

    Everything after the bare `--` is forwarded verbatim to `gcloud run
    deploy`; everything before it is consumed by ADK. That separator is ADK's
    documented interface for gcloud passthrough, and it is the only way to
    reach `--service-account`, which ADK itself does not expose.
    """
    s = settings()
    return [
        # The interpreter running this script, not whatever `python` resolves
        # to on PATH — the ADK CLI and its deps live in this one.
        sys.executable,
        "-m",
        "google.adk.cli",
        "deploy",
        "cloud_run",
        f"--project={s.project_id}",
        f"--region={REGION}",
        f"--service_name={service_name(agent_id)}",
        # Names the module ADK imports from the staged directory, and so also
        # the app name a caller addresses. Without it ADK uses the temp
        # folder's basename, which is a timestamp.
        f"--app_name={agent_id}",
        f"--session_service_uri={SESSION_SERVICE_URI}",
        # Without this, ADK stages into a timestamped folder under its working
        # directory, which is `packages/` — the tree this repo regenerates and
        # scans. An interrupted deploy then leaves a half-copy of the repo
        # sitting inside it, which the model-policy scan reads as a stray
        # model id.
        f"--temp_folder={tempfile.gettempdir()}/adk-stage-{agent_id}",
        f"./{PACKAGES_DIR}/{agent_id}",
        "--",
        # The runtime identity. Set here, at create time, so there is no window
        # in which the agent runs as the project's default compute account —
        # which is Editor on this project and would make the tiering
        # decorative.
        f"--service-account={service_account}",
        # The container must carry its own project. Cloud Run does not set
        # GOOGLE_CLOUD_PROJECT for you, and mining_agents.config resolves it at
        # IMPORT time (graph_traverse builds its SQL at module level), so an
        # unset variable is not a late query error -- the container fails to
        # start. deploy_apps.py sets the same variable for the same reason.
        f"--set-env-vars=GOOGLE_CLOUD_PROJECT={s.project_id}",
        # Private by default. A public agent endpoint on a project holding
        # biometric tables is not a risk worth taking for demo convenience;
        # callers authenticate with an identity token.
        "--no-allow-unauthenticated",
        # Cloud Run's default request timeout is 300s. A Pattern A swarm does
        # not fit inside it: S07 on the governing P6 question was measured at
        # 293.99s and cut off mid-loop, after the critic had reported and while
        # the coordinator was still verifying. An earlier run of the same
        # question took 209s, so the margin was 90 seconds, and a critic that
        # checked its specialists more carefully spent it.
        #
        # What makes this worth a comment rather than a number: Cloud Run
        # closes the connection cleanly at the limit. There is no error, no
        # 504 on the stream, nothing in the events to distinguish "the platform
        # stopped it" from "the agent chose to stop". The page can only say the
        # agent finished without writing an answer, which is true and useless.
        # A deploy-time ceiling is the only place this can be fixed honestly.
        #
        # 3600s is the maximum Cloud Run allows for an HTTP/1 request. It is a
        # ceiling, not a budget — nothing here should take an hour — but an
        # unreached ceiling costs nothing and a breached one costs the answer.
        "--timeout=3600",
    ]


def deploy(
    dry_run: bool = True,
    only: tuple[str, ...] | None = None,
    confirm: str = "",
) -> None:
    """Deploy the externally-callable agents under their tier identities.

    dry_run=True (default) prints the argv and the full registration payload
    per agent and touches no cloud state. dry_run=False runs each deploy — but
    only when *confirm* is CONFIRM_PHRASE, so that reaching this by accident
    takes two deliberate arguments rather than one flipped boolean.

    *only* restricts the run to the given agent ids, which is what makes a
    representative-subset demo possible without editing the catalog.

    Ruling 3: DOMAIN_BINDING_COMMAND is printed and never executed.
    """
    if not dry_run and confirm != CONFIRM_PHRASE:
        raise PermissionError(
            "deploy(dry_run=False) builds containers and creates public-facing "
            f"Cloud Run services. Pass confirm={CONFIRM_PHRASE!r} to proceed. "
            "If you are reading this from a test, the test should be calling "
            "dry_run=True."
        )

    entries = list(registrations())
    if only:
        wanted = set(only)
        unknown = wanted - {e["agent_id"] for e in entries}
        if unknown:
            raise KeyError(f"not externally-callable entrypoints: {sorted(unknown)}")
        entries = [e for e in entries if e["agent_id"] in wanted]

    if not dry_run:
        # `packages/` is gitignored scratch, and this used to ship whatever was
        # already sitting in it. A live verification found S07 serving from a
        # container built four days before the code it was meant to be running:
        # the deploy read a stale package, the build succeeded, the service came
        # up healthy, and the agent quietly behaved like its previous self. A
        # deploy is now self-contained — regenerate, then ship — so the snapshot
        # cannot be older than the source it claims to be. A dry run does not
        # do this: it reports, and touching the working tree is a side effect
        # the name disclaims.
        written = write_packages(PACKAGES_DIR)
        print(f"# regenerated {len(written)} packages under {PACKAGES_DIR}/")

    if not dry_run and SESSION_SERVICE_URI == "memory://":
        print(
            "WARNING: sessions are in-memory. Cloud Run scales to zero, so "
            "conversation history is discarded when a container spins down. "
            "Fine for a demo; set SESSION_SERVICE_URI before running real "
            "traffic."
        )

    for entry in entries:
        agent_id = entry["agent_id"]
        service_account = entry["service_account"]
        argv = deploy_command(agent_id, service_account)

        print(f"# --- {agent_id} ---")
        print(" \\\n  ".join(argv))
        print(f"# Runtime service account: {service_account}")

        if dry_run:
            # Print the full payload — no truncation — so an auditor can read
            # caller_allowlist and guardrails (Ruling 6).
            print("Registration payload:")
            print(json.dumps(entry, indent=2))
            print()
            continue

        subprocess.run(argv, check=True)
        print(
            f"# deployed {agent_id} as {service_name(agent_id)}, "
            f"running as {service_account}"
        )
        print()

    if dry_run:
        print_domain_binding_warning()


if __name__ == "__main__":
    deploy(dry_run=True)
