"""Deploy the two applications as one Cloud Run service, and give it an identity.

WHAT THIS DEPLOYS, AND WHY IT IS A SERVER AT ALL
------------------------------------------------
Application 1 (the case) is static and would be happy on a bucket. Application 2
is not, for one reason: `scripts/deploy.py` creates all 52 agent services with
`--no-allow-unauthenticated`, so calling one requires a Google-signed OIDC token
scoped to that service's URL, and no browser page can mint one. Something with a
service account has to sit in between. That something is
`apps/workspace/server.py`, and this module puts it on Cloud Run.

Running there is also what makes the proxy work at all. `fetch_id_token` reads
the metadata server, which exists on Cloud Run and does not exist on a laptop —
which is why the workspace screens read NOT CONNECTED in local development no
matter how recently you ran `gcloud auth application-default login`. A user
credential cannot mint an OIDC token for a Cloud Run audience. Only an attached
service account can.

WHY A FOURTH SERVICE ACCOUNT
-----------------------------
`infra/iam/service_accounts.py` provisions three accounts, one per privilege
tier, and every one of the 52 agents runs as one of them. The workspace is not
an agent. It reads no BigQuery table and calls no model; it needs to list Cloud
Run services and invoke them, which is a disjoint set of permissions from all
three tiers. Reusing a tier account would hand the public-facing web tier the
mining dataset, which is the one thing the tiering exists to prevent.

WHY run.invoker IS BOUND PER SERVICE AND NOT AT THE PROJECT
-----------------------------------------------------------
The project holds 166 Cloud Run services; 52 of them belong to this build and
114 are unrelated work sharing the sandbox. A project-level `roles/run.invoker`
grant is one command instead of 52, and it would let this service call every one
of those 114. The 52 bindings below cost a slower first run and nothing after
that, since re-binding an existing member is a no-op.
"""
from __future__ import annotations

import subprocess
import sys
import time

from mining_agents.config import settings
from mining_agents.registry import registrations
from scripts.deploy import REGION, service_name

# The workspace runs in the agents' region, and this is not cosmetic:
# `server.py` lists services under a single location and treats anything not
# returned as undeployed. A workspace in a different region would report all 52
# agents missing while every one of them was running.
SERVICE = "mag-workspace"

WORKSPACE_ACCOUNT_ID = "mag-workspace"

# Lets `/api/runtime` call services.list. Read-only: it confers no ability to
# deploy, delete, or change a service, so the worst a compromised web tier can
# do with it is learn the names of services it can already see in a URL.
VIEWER_ROLE = "roles/run.viewer"

# What actually admits the proxy to an agent endpoint.
INVOKER_ROLE = "roles/run.invoker"

# Same guard as scripts/deploy.py, and for the same reason: a boolean is too
# easy to reach by accident, and this accident builds a container and creates a
# public URL that costs money.
CONFIRM_PHRASE = "yes-deploy-for-real"


def workspace_service_account() -> str:
    """The identity the deployed workspace runs as."""
    return f"{WORKSPACE_ACCOUNT_ID}@{settings().project_id}.iam.gserviceaccount.com"


def agent_services() -> list[str]:
    """The 52 Cloud Run service names the proxy must be allowed to invoke.

    Derived through `service_name` from the same registry that
    `scripts/deploy.py` deployed, rather than from a list kept here or from a
    `gcloud run services list` glob. A hand-kept list drifts; a glob would pick
    up any service that happened to match the prefix, including one left behind
    by an abandoned experiment.
    """
    return sorted(service_name(e["agent_id"]) for e in registrations())


def iam_commands() -> list[list[str]]:
    """Every argv needed to create the account and grant it its two powers.

    Ordered create-then-bind. `create` answers an error if the account already
    exists, which the apply path treats as success — this module is meant to be
    re-runnable, and an existing account is the expected state on every run
    after the first.
    """
    project = settings().project_id
    email = workspace_service_account()
    member = f"serviceAccount:{email}"

    commands: list[list[str]] = [
        [
            "gcloud", "iam", "service-accounts", "create", WORKSPACE_ACCOUNT_ID,
            f"--project={project}",
            "--display-name=Mining agents — workspace web tier",
            "--description=Serves both applications and forwards prompts to the "
            "52 agent entrypoints. Holds no BigQuery access by design.",
        ],
        [
            "gcloud", "projects", "add-iam-policy-binding", project,
            f"--member={member}",
            f"--role={VIEWER_ROLE}",
            # Without this, gcloud prints the entire project IAM policy on every
            # one of the calls below. On a project with 166 services that is
            # thousands of lines of output hiding the one line that matters.
            "--condition=None",
        ],
    ]

    commands.extend(
        [
            "gcloud", "run", "services", "add-iam-policy-binding", svc,
            f"--project={project}",
            f"--region={REGION}",
            f"--member={member}",
            f"--role={INVOKER_ROLE}",
        ]
        for svc in agent_services()
    )
    return commands


def deploy_command(allow_unauthenticated: bool) -> list[str]:
    """The argv that builds and deploys the workspace.

    Both the dry run and the live run render the command from here, so a dry
    run cannot describe something other than what executes.
    """
    project = settings().project_id
    return [
        "gcloud", "run", "deploy", SERVICE,
        # Cloud Build reads the root Dockerfile. The build context is the whole
        # repository minus .gcloudignore, because the image copies
        # mining_agents/ and infra/ alongside apps/.
        "--source=.",
        f"--project={project}",
        f"--region={REGION}",
        f"--service-account={workspace_service_account()}",
        # The static tree is a few megabytes and the proxy holds one async
        # client; the default 512Mi is ample and the smallest step down from
        # what the agents take.
        "--cpu=1",
        "--memory=512Mi",
        # A ceiling, not a target. Cloud Run still scales to zero between
        # demos; this only bounds what a burst of traffic can spend.
        "--max-instances=3",
        # An agent may think for minutes and /api/invoke awaits it. The default
        # 300s would cut a long answer off mid-stream and report it as a proxy
        # failure, which reads as the agent being broken.
        "--timeout=600",
        f"--set-env-vars=GOOGLE_CLOUD_PROJECT={project}",
        "--allow-unauthenticated" if allow_unauthenticated else "--no-allow-unauthenticated",
    ]


def apply(
    dry_run: bool = True,
    allow_unauthenticated: bool = False,
    confirm: str = "",
) -> None:
    """Create the account, bind its roles, and deploy the workspace.

    dry_run=True (default) prints every command and touches nothing.

    allow_unauthenticated=True publishes the service to the open internet. Read
    the warning it prints before passing it: the agents behind this proxy were
    deliberately deployed private, and a public proxy holding run.invoker on all
    52 is a door into every one of them.
    """
    if not dry_run and confirm != CONFIRM_PHRASE:
        raise PermissionError(
            "apply(dry_run=False) creates a service account, grants it 53 IAM "
            "bindings, and builds a container. Pass "
            f"confirm={CONFIRM_PHRASE!r} to proceed."
        )

    if allow_unauthenticated:
        _print_public_access_warning()

    for argv in iam_commands():
        print(" \\\n  ".join(argv))
        if not dry_run:
            _run_tolerating_propagation(argv)
        print()

    argv = deploy_command(allow_unauthenticated)
    print(" \\\n  ".join(argv))
    if dry_run:
        print("\n# dry run — nothing above was executed")
        return
    subprocess.run(argv, check=True)


def _run_tolerating_propagation(argv: list[str], attempts: int = 4) -> None:
    """Run one gcloud command, retrying while IAM catches up with itself.

    Two failures are expected here and neither is fatal:

      * `create` on an account that already exists. This module is re-runnable
        and an existing account is the normal state on every run after the
        first.
      * `does not exist` on the project-level binding, moments after the create
        that made it. The account is created against the IAM API and the
        binding is applied against the Resource Manager API, and the second
        does not always see the first straight away. This is not hypothetical:
        it happened on the first real run of this module, while the 52
        service-level bindings issued immediately afterwards all succeeded.

    So the retry is narrow. Anything that fails `attempts` times in a row is
    reported and the run continues, because the deploy that follows fails
    loudly and legibly if the identity is genuinely not usable — which is a
    better error than one raised here about a policy write.
    """
    for attempt in range(attempts):
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.returncode == 0:
            return
        stderr = result.stderr.strip()
        if "already exists" in stderr:
            print("# already exists — nothing to do")
            return
        if "does not exist" in stderr and attempt < attempts - 1:
            # Backs off 2s, 4s, 6s. Observed propagation was under a second;
            # the ceiling is generous because the alternative is a broken
            # deploy that takes minutes to fail.
            time.sleep(2 * (attempt + 1))
            continue
        print(f"# FAILED: {stderr.splitlines()[-1] if stderr else result.returncode}")
        return


def _print_public_access_warning() -> None:
    """State plainly what --allow-unauthenticated does to the agents behind it."""
    print("=" * 72)
    print("PUBLIC SERVICE — READ THIS")
    print()
    print("The 52 agents are deployed --no-allow-unauthenticated. This service")
    print("is about to be deployed public, holding run.invoker on all 52. Anyone")
    print("who finds the URL can POST /api/invoke/<agent_id> and reach an agent,")
    print("which spends Gemini tokens and queries the mining dataset under the")
    print("agent's tier account.")
    print()
    print("Acceptable only because this is an Argolis sandbox holding synthetic")
    print("data. Do not carry this flag into a project with real production or")
    print("customer data.")
    print("=" * 72)
    print()


if __name__ == "__main__":
    apply(dry_run=True, allow_unauthenticated="--public" in sys.argv)
