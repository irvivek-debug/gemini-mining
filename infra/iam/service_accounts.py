"""Three shared service accounts, one per least-privilege tier.

Every agent runs as one of exactly three accounts. This is a deliberate
departure from one-account-per-agent, ruled on 2026-08-12:

  1. Only 52 things actually deploy — 12 `Workflow` graphs and 40 `LlmAgent`s.
     A swarm's 4 sub-agents are nodes inside their coordinator's graph and
     share its process, so they can never hold a separate runtime identity.
     48 of the original 100 accounts could not have been attached to anything.
  2. This build is a functional showcase that is demonstrated repeatedly. The
     default quota is 100 service accounts per project; a 100-account build
     exhausts a fresh project on its first run and cannot be repeated.

WHAT THIS COSTS, accepted knowingly: an agent runs with its whole tier's
access rather than its own. There is no intra-tier isolation — a prompt
injection that reaches one agent's query tool reaches every table its tier
can read. Per-agent (or per-swarm) accounts are the documented hardening
path for a customer taking this to production.

WHAT THIS DISSOLVES: biometric table access can no longer be restricted by
IAM, because the agents that read biometric data and the agents that do not
now share an account. See `test_biometric_access_is_not_restricted_at_the_iam_layer`
— the control has to live in the application layer or it does not exist.

No service-account credential file is ever created, downloaded, or stored —
Workload Identity Federation supplies credentials at runtime. This file
contains no credential-management calls of any kind.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from typing import Literal

from mining_agents.catalog.definitions import AgentDef, ALL_AGENTS
from mining_agents.config import settings

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------
# `aiplatform.user` is what lets an agent call its own Gemini model: it is the
# only one of these roles carrying `aiplatform.endpoints.predict`, and ADK's
# containers run against the Vertex backend. It is therefore a baseline for all
# 100 agents, not a privilege tier.
#
# It was previously granted to coordinators alone, on the rationale that they
# needed it "for A2A invocation". Both halves were wrong. There is no A2A call
# to authorise — a swarm's specialists are nodes in the coordinator's own
# `Workflow` graph and share its process — and every agent, coordinator or not,
# needs the role to reach a model at all. A fork running `apply()` under the
# old table produced base and approver accounts that could not answer a single
# query; the live project only worked because the role had been granted by hand
# outside this module. D01 running as `mag-agent-base` is the proof: its only
# project-level roles are this one and jobUser, and jobUser carries no
# aiplatform permission.
MODEL_ROLE = "roles/aiplatform.user"
BASE_ROLES = ["roles/bigquery.dataViewer", "roles/bigquery.jobUser", MODEL_ROLE]
HITL_ROLE = "roles/bigquery.dataEditor"

# What `doc_search` needs beyond dataViewer. The tool runs VECTOR_SEARCH against
# a remote embedding model, and a remote model is reached through a BigQuery
# CONNECTION — a resource that lives outside the dataset and is not covered by
# its ACL. Without this the query is refused with `bigquery.connections.use`,
# 403, before it reads a row.
DOC_ROLE = "roles/bigquery.connectionUser"

# bigquery.* roles that BigQuery only accepts at project level. A dataset ACL
# accepts READER/WRITER/OWNER (and the IAM roles that map onto them); jobUser
# grants query execution against the project's billing and has no ACL form.
# connectionUser has no ACL form either — the connection is not in the dataset,
# so there is no ACL that could name it — and `_resource_kind` sends every
# unlisted `roles/bigquery.*` to the dataset, which is why it must be listed
# here rather than left to the default.
_PROJECT_LEVEL_BQ_ROLES = frozenset({"roles/bigquery.jobUser", DOC_ROLE})

Tier = Literal["base", "approver", "coordinator"]

# The three accounts. Ordered least- to most-privileged.
TIER_ACCOUNT_ID: dict[Tier, str] = {
    "base": "mag-agent-base",
    "approver": "mag-agent-approver",
    "coordinator": "mag-agent-coordinator",
}

# Roles held by each ACCOUNT — the union over every agent assigned to it.
#
# The coordinator account carries dataEditor because 9 of the 12 coordinators
# are HITL. S03, S06, and S12 are not, and therefore gain write access to
# agent_approvals that they do not need. That over-grant is the price of
# collapsing four distinct role combinations onto three accounts; it is
# pinned by test_the_coordinator_account_over_grants_dataeditor_to_three so
# it cannot become invisible.
#
# NOT THE WHOLE TABLE. `DOC_ROLE` is appended below, to whichever tiers actually
# run an agent holding `doc_search` — derived from the catalog rather than
# written in here, so the role follows the tool as later personas pick it up.
#
# Once MODEL_ROLE moved to the baseline (see above), `approver` and
# `coordinator` became identical grants, and for a while the third account was
# pure attribution: the identity Cloud Run logs, traces and BigQuery job history
# show, conferring no extra privilege. DOC_ROLE ends that — the coordinator
# account now holds one role the approver does not, because the only agents that
# search documents today run inside a coordinator's process. See
# `test_the_coordinator_account_holds_exactly_one_role_the_approver_does_not`.
TIER_ROLES: dict[Tier, list[str]] = {
    "base": [*BASE_ROLES],
    "approver": [*BASE_ROLES, HITL_ROLE],
    "coordinator": [*BASE_ROLES, HITL_ROLE],
}

# Resource-kind tag — derivable from the plan entry; never re-decided in apply().
ResourceKind = Literal["project", "dataset", "table"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def tier_of(agent: AgentDef) -> Tier:
    """Which of the three accounts this agent runs as.

    Coordinators are checked first so that a coordinator which is also HITL
    lands on the coordinator account. Since MODEL_ROLE moved to the baseline
    the two accounts carry the same grants, so this ordering no longer changes
    what the agent can do — it decides which identity the audit trail shows.
    """
    if agent.swarm_role == "coordinator":
        return "coordinator"
    if agent.hitl_required:
        return "approver"
    return "base"


def running_tier_of(agent: AgentDef) -> Tier:
    """Which account is authenticated when THIS agent's tools actually run.

    `tier_of` answers a question about the agent's own privilege class. This
    answers the operational one, and for a swarm's 4 sub-agents the two
    disagree: a specialist is a node in its coordinator's `Workflow` graph,
    inside the coordinator's process, holding no runtime identity of its own,
    so every query it issues is issued as the coordinator.

    Granting a tool's role by `tier_of` therefore grants it to an account that
    never runs the tool. That is precisely how `doc_search` shipped returning
    403: S07-SP3 is `tier_of` "base", but the VECTOR_SEARCH reaches BigQuery
    as mag-agent-coordinator, and it was the coordinator account that lacked
    the connection grant.

    Only the 52 entrypoints are ever deployed, and for all of them the two
    functions agree — which is why the distinction stayed invisible until a
    sub-agent needed a role its coordinator did not already hold.
    """
    if agent.swarm_role in ("specialist", "critic"):
        return "coordinator"
    return tier_of(agent)


def sa_id(agent: AgentDef) -> str:
    """The GCP service-account ID (≤30 chars) this agent runs as.

    Shared per tier — many agents return the same ID by design.
    """
    return TIER_ACCOUNT_ID[tier_of(agent)]


def sa_email(agent: AgentDef) -> str:
    """Full service-account email address for the given agent."""
    return f"{sa_id(agent)}@{settings().project_id}.iam.gserviceaccount.com"


def _grant_doc_role_to_the_tiers_that_search_documents() -> None:
    """Append DOC_ROLE to every tier that actually executes a `doc_search` holder.

    Derived from the catalog, not hand-listed, for the reason the rest of this
    module keeps re-learning: a hand-written role table records a fact about the
    catalog on the day it was written and cannot notice the catalog changing.
    P6 is the first persona whose pack uses `doc_search`; P1, P2, P3, P5 and P8
    follow, and the first of them on a tier this does not already cover would
    otherwise reproduce the same 403 — a failure the agent reports honestly and
    which therefore looks like a working agent giving a cautious answer.
    """
    for tier in sorted({
        running_tier_of(agent)
        for agent in ALL_AGENTS
        if "doc_search" in agent.tools
    }):
        if DOC_ROLE not in TIER_ROLES[tier]:
            TIER_ROLES[tier].append(DOC_ROLE)


_grant_doc_role_to_the_tiers_that_search_documents()


def tier_roles(agent: AgentDef) -> list[str]:
    """The IAM roles held by the account this agent runs as.

    These are the ACCOUNT's roles, not the agent's minimum requirement. A
    non-HITL coordinator returns dataEditor here because it shares an account
    with nine HITL coordinators — see the TIER_ROLES comment.
    """
    return list(TIER_ROLES[tier_of(agent)])


def _resource_kind(role: str) -> ResourceKind:
    """Derive the binding resource scope from the role.

    - dataEditor         → table-scoped (agent_approvals only; never project-level)
    - bigquery.jobUser   → project-level. jobUser authorises *running* a query and
                           is billed to the project; BigQuery rejects it as a
                           dataset ACL entry. It is the one bigquery.* role that
                           cannot be dataset-scoped.
    - other bigquery.*   → dataset-scoped (mining_data ACL)
    - aiplatform.*       → project-level
    """
    if role == HITL_ROLE:
        return "table"
    if role in _PROJECT_LEVEL_BQ_ROLES:
        return "project"
    if role.startswith("roles/bigquery."):
        return "dataset"
    return "project"


def plan() -> list[dict]:
    """Return the three-row create-and-bind plan. Pure data; touches nothing.

    Each entry:
      {
        "tier":       str,        # "base" | "approver" | "coordinator"
        "account_id": str,        # the ≤30-char GCP account ID
        "email":      str,        # full SA email
        "agents":     [str, ...], # every agent_id that runs as this account
        "bindings": [
          {
            "role":          str,   # e.g. "roles/bigquery.dataViewer"
            "resource":      str,   # project / dataset / table reference
            "resource_kind": str,   # "project" | "dataset" | "table"
          },
          ...
        ],
      }

    `agents` is carried so the plan stays auditable: a reader can see which of
    the 100 catalog agents each account speaks for without re-deriving it.

    resource_kind is stored in the plan so that apply() routes each binding to
    the correct GCP API without re-deciding scope inside apply().
    """
    s = settings()
    dataset_ref = f"{s.project_id}:{s.dataset}"
    table_ref = f"{s.project_id}.{s.dataset}.agent_approvals"

    members: dict[Tier, list[str]] = {tier: [] for tier in TIER_ACCOUNT_ID}
    for agent in ALL_AGENTS:
        members[tier_of(agent)].append(agent.agent_id)

    entries = []
    for tier, account_id in TIER_ACCOUNT_ID.items():
        bindings = []
        for role in TIER_ROLES[tier]:
            kind = _resource_kind(role)
            if kind == "table":
                resource = table_ref
            elif kind == "dataset":
                resource = dataset_ref
            else:
                resource = s.project_id
            bindings.append({
                "role": role,
                "resource": resource,
                "resource_kind": kind,
            })
        entries.append({
            "tier": tier,
            "account_id": account_id,
            "email": f"{account_id}@{s.project_id}.iam.gserviceaccount.com",
            "agents": members[tier],
            "bindings": bindings,
        })
    return entries


# ---------------------------------------------------------------------------
# apply() — implements all three binding kinds; dry_run=True by default.
# apply(dry_run=False) must never be called by tests, automation, or CI
# without explicit customer approval and a resolved quota.
# ---------------------------------------------------------------------------

def _fmt_create(entry: dict, project_id: str) -> list[str]:
    return [
        "gcloud", "iam", "service-accounts", "create",
        entry["account_id"],
        f"--project={project_id}",
        f"--display-name=Mining agents — {entry['tier']} tier "
        f"({len(entry['agents'])} agents)",
    ]


def _fmt_project_binding(email: str, role: str, project_id: str) -> list[str]:
    return [
        "gcloud", "projects", "add-iam-policy-binding", project_id,
        f"--member=serviceAccount:{email}",
        f"--role={role}",
    ]


def apply(dry_run: bool = True) -> None:
    """Create the three tier service accounts and bind their roles.

    dry_run=True (default): print exactly the operations the live path performs;
                            touch nothing.
    dry_run=False:          execute them. Do NOT call with dry_run=False until the
                            customer has given explicit approval.

    Both branches walk plan() and accumulate identically; only the final step
    differs. Dataset and table scopes have no single-command CLI form — they are
    read-modify-write cycles against an existing policy, so batching them once at
    the end is what the live path does and what the dry run reports. Printing an
    invented one-liner per binding would produce an audit that does not match
    execution.
    """
    s = settings()

    # dataset ACL and table IAM are read-modify-write: accumulate every addition,
    # then apply each policy once. Applying per-binding would re-read and
    # overwrite the policy on every pass and lose concurrent edits.
    dataset_additions: list[tuple[str, str]] = []   # (email, role)
    table_additions: dict[str, list[tuple[str, str]]] = {}  # table_ref -> [(email, role)]

    for entry in plan():
        create_cmd = _fmt_create(entry, s.project_id)
        if dry_run:
            # shlex.join, not " ".join: the display name contains spaces and
            # parentheses. A dry run exists to be pasted into a shell and
            # audited, so it has to survive being pasted into a shell.
            print(shlex.join(create_cmd))
        else:
            subprocess.run(create_cmd, check=False)  # already-exists is not an error

        for binding in entry["bindings"]:
            role = binding["role"]
            email = entry["email"]
            kind = binding["resource_kind"]

            if kind == "project":
                cmd = _fmt_project_binding(email, role, s.project_id)
                if dry_run:
                    print(shlex.join(cmd))
                else:
                    subprocess.run(cmd, check=True)

            elif kind == "dataset":
                dataset_additions.append((email, role))

            elif kind == "table":
                table_additions.setdefault(binding["resource"], []).append(
                    (email, role)
                )

    if dry_run:
        _print_dataset_acl_plan(s, dataset_additions)
        for tref, members in table_additions.items():
            _print_table_iam_plan(s, tref, members)
    else:
        _apply_dataset_acl(s, dataset_additions)
        for tref, members in table_additions.items():
            _apply_table_iam(s, tref, members)


def _print_dataset_acl_plan(s, additions: list[tuple[str, str]]) -> None:
    """Report the dataset ACL read-modify-write that _apply_dataset_acl performs."""
    dataset_ref = f"{s.project_id}:{s.dataset}"
    print()
    print(f"# dataset ACL patch on {dataset_ref} "
          f"({len(additions)} entries, applied as one read-modify-write):")
    print(f"{s.bq_binary} show --format=prettyjson {dataset_ref}")
    print("#   append to .access, then write the merged document back:")
    for email, role in additions:
        print(f"#     {{\"role\": \"{_bq_acl_role(role)}\", "
              f"\"userByEmail\": \"{email}\"}}")
    print("#   (bq will not read the document from a pipe — write it to a file)")
    print(f"{s.bq_binary} update --source=MERGED_ACL.json {dataset_ref}")


def _print_table_iam_plan(s, table_ref: str, members: list[tuple[str, str]]) -> None:
    """Report the table IAM read-modify-write that _apply_table_iam performs."""
    bq_table = table_ref.replace(".", ":", 1)
    print()
    print(f"# table IAM patch on {bq_table} "
          f"({len(members)} members, applied as one read-modify-write):")
    print(f"{s.bq_binary} get-iam-policy --format=prettyjson {bq_table}")
    print("#   append to .bindings, then write the merged policy back:")
    for email, role in members:
        print(f"#     {role} -> serviceAccount:{email}")
    print("#   (bq will not read the policy from a pipe — write it to a file)")
    print(f"{s.bq_binary} set-iam-policy {bq_table} MERGED_POLICY.json")


def _bq_write_json(doc: dict, argv_for) -> None:
    """Hand a JSON document to bq as a real file on disk.

    bq rejects `/dev/stdin` — it validates the argument with an is-a-regular-file
    check, and a pipe is not a regular file, so piping the document in fails with
    "Source path is not a file: /dev/stdin". The merged document therefore goes
    to a named temp file, which is removed whether or not bq succeeds.

    `argv_for` builds the command from the path because the two callers place it
    differently: `update` takes `--source=PATH`, `set-iam-policy` takes it
    positionally.
    """
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(doc, handle)
        subprocess.run(argv_for(path), check=True)
    finally:
        os.unlink(path)


def _apply_dataset_acl(s, additions: list[tuple[str, str]]) -> None:
    """Read the current dataset ACL, append new members, and write it back."""
    dataset_ref = f"{s.project_id}:{s.dataset}"
    result = subprocess.run(
        [s.bq_binary, "show", "--format=prettyjson", dataset_ref],
        capture_output=True, text=True, check=True,
    )
    meta = json.loads(result.stdout)
    acl = meta.get("access", [])

    existing = {
        (e.get("role", ""), e.get("userByEmail", ""))
        for e in acl
    }
    for email, role in additions:
        bq_role = _bq_acl_role(role)
        if (bq_role, email) not in existing:
            acl.append({"role": bq_role, "userByEmail": email})
            existing.add((bq_role, email))

    meta["access"] = acl

    _bq_write_json(
        meta,
        lambda path: [s.bq_binary, "update", f"--source={path}", dataset_ref],
    )


def _apply_table_iam(s, table_ref: str, members: list[tuple[str, str]]) -> None:
    """Read the table IAM policy, append members, and write it back."""
    # table_ref uses dot notation: project.dataset.table
    bq_table = table_ref.replace(".", ":", 1)  # project:dataset.table for bq CLI
    result = subprocess.run(
        [s.bq_binary, "get-iam-policy", "--format=prettyjson", bq_table],
        capture_output=True, text=True, check=True,
    )
    policy = json.loads(result.stdout)
    bindings = policy.setdefault("bindings", [])

    role_to_members: dict[str, set[str]] = {}
    for b in bindings:
        role_to_members[b["role"]] = set(b.get("members", []))

    for email, role in members:
        member_str = f"serviceAccount:{email}"
        role_to_members.setdefault(role, set()).add(member_str)

    policy["bindings"] = [
        {"role": role, "members": sorted(m)}
        for role, m in sorted(role_to_members.items())
    ]
    _bq_write_json(
        policy,
        lambda path: [s.bq_binary, "set-iam-policy", bq_table, path],
    )


_ACL_ROLE_BY_IAM_ROLE = {
    "roles/bigquery.dataViewer": "READER",
    "roles/bigquery.dataEditor": "WRITER",
    "roles/bigquery.dataOwner": "OWNER",
}


def _bq_acl_role(iam_role: str) -> str:
    """Convert an IAM role to its BigQuery dataset ACL role name.

    Raises on any role with no ACL form. Falling back to the IAM string would
    write an entry BigQuery rejects with a 400 — and the rejection would name
    the whole ACL, not the offending role.
    """
    try:
        return _ACL_ROLE_BY_IAM_ROLE[iam_role]
    except KeyError:
        raise ValueError(
            f"{iam_role!r} has no BigQuery dataset ACL equivalent; it must be "
            f"bound at project or table scope. Check _resource_kind()."
        ) from None


if __name__ == "__main__":
    apply(dry_run=True)
