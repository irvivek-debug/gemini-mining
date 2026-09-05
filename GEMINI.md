# Working in this repository

Guidance for an AI coding agent (Antigravity / Gemini CLI) working on this
codebase. Part one is how to deploy it. Part two is the engineering patterns
the original build paid for; ignoring those reproduces bugs already fixed once.

---

# Part 1 — Deploying this repository

`docs/RECREATE.md` is the authoritative, ordered procedure. **Read it before
running anything.** This section is the operating contract around it.

## Before you run a single command

Ask the user for these and wait for real answers. Do not invent them, and do
not proceed with placeholders — the catalogue will silently generate
`...@unset-project.iam.gserviceaccount.com` if you do:

1. Their GCP **project ID** and **project number**
2. Whether billing is enabled on it
3. A **staging bucket** name, and a **video bucket** name
4. Explicit confirmation that they want to spend money (see the cost gate)

Write them into `.env` (copied from `.env.example`), then export them into your
shell — nothing loads that file automatically:

```bash
cp .env.example .env      # then fill it in
set -a && . ./.env && set +a
```

## The cost gate — STOP here

Three steps in `docs/RECREATE.md` create billable, hard-to-undo resources:

| Step | What it does | Why it needs a human |
|---|---|---|
| 5 `--apply` | **Overwrites ten live BigQuery tables** | Destroys existing data in that dataset |
| 7 register | Creates **101 Vertex AI Agent Engine instances** | Billable, and near the default quota of 100 |
| 8 deploy | Creates **52+ Cloud Run services** | Billable, and slow to unpick |

**Stop and get explicit confirmation before each of those three.** Present what
will be created, in which project, and wait. A dry run first is always correct:
step 5 has `--dry-run`, step 7 registers nothing without
`--confirm yes-register-for-real`, and `scripts/deploy.py` prints its argv
before executing.

Never run `scripts/deploy.py`'s printed domain-binding command yourself. It is
printed deliberately and left for a human.

## Order is not a suggestion

Several steps succeed while producing nothing when their inputs are missing.
The worst is the property graph: created over empty tables it **succeeds and
returns zero rows**, so a broken deployment looks like a working one. Load the
data (step 5) before creating the graph or registering agents.

## How to tell it actually worked

Do not report success because commands exited zero. Run step 9:

```bash
python scripts/verify_grounded.py
python scripts/grounding_test.py
pytest tests/
```

These prove a **read happened** — `meta.tables_read` in the tool envelope,
checked against the live source — rather than proving an agent replied. An
agent that answers fluently while querying nothing passes a liveness check and
fails this one. That distinction is the entire point of the project.

## Failure signatures worth recognising

| What you see | What it actually is |
|---|---|
| `RuntimeError: GOOGLE_CLOUD_PROJECT is unset` | `.env` not exported into this shell |
| `...@unset-project.iam.gserviceaccount.com` in output | Same, but the catalogue fell back quietly |
| Model 404, "not found or no access" | Regional endpoint. The tiered models are `global` only |
| A container that will not start | Missing `GOOGLE_CLOUD_PROJECT`; config resolves at import time |
| Graph query returns zero rows, no error | Data was never loaded |
| Agent answers confidently, cites nothing | Grounding is broken — this is the failure this repo exists to prevent |
| Registration fails near the 100th agent | `ReasoningEngineEntitiesPerProjectPerRegion` quota |

## Rules for you, the agent

- Do not hardcode a project ID, project number, service-account email, bucket,
  or endpoint anywhere — including tests, fixtures, and docstrings. Everything
  comes from the environment.
- Do not weaken a failing check to make a step pass.
- If a command fails, report the actual error. Do not summarise it as "some
  issues" and continue.
- Report denominators honestly: "97 of 100 agents registered" is information,
  "deployed successfully" is not.

---

# Part 2 — Engineering patterns

## The domain rule

Language is **commodity-neutral**: say "contained metal", not a named
commodity. Value is stated as a **range**, never a single point figure. This
is not stylistic — a point estimate on a synthetic dataset reads as a claim.

## Grounding: the failure that looks like success

An agent that answers fluently while querying nothing is the defining failure
here. Six layers must line up for an agent to really read data — model access,
tool registration, tool implementation, IAM on the runtime identity, the
declared-table list, and the dataset itself. When grounding breaks, the symptom
is almost never an error; it is a confident answer with no rows behind it.

Verify grounding by proving a **read happened** (`meta.tables_read` in the tool
envelope, checked against the live source), not by proving the agent replied.
Never assert against a pinned row count: a deliberately deepened table turns a
passing test into a lie.

## Silent-empty is the deadliest shape

Four separate incidents in this codebase shared one shape: a lookup failed and
the code carried on as if there were nothing to find — a swallowed import
returning `{}`, a 401 rendered as "0 agents", a JS error rendered as an empty
reply. **Any branch where "not found" and "nothing to do" are the same is where
the next one lives.** Raise; never return an empty default from an error path.

## Configuration

Every GCP value comes from the environment. A required value with no safe
default must raise a `RuntimeError` naming the variable and pointing at
`docs/RECREATE.md`. Do not reintroduce a hardcoded project ID, project number,
service-account email, bucket, or endpoint anywhere in the tree — including
tests, fixtures, and docstrings.

## Model IDs

Model IDs rot fast and are never hardcoded outside `references/model-policy.md`.
Refer to **tiers** (`reasoning`, `balanced`) everywhere else and resolve through
`model_for_tier()`. Both tiered models are published only on the `global`
endpoint; a regionally-scoped client returns 404 in a way that reads like a
missing grant rather than a location mismatch.

## Data and durability

- Accumulating datasets **merge, never replace**. A registry rewritten wholesale
  per group silently erased every other group's entries.
- Flush results **per item, not at the end**. A results file written only after
  a full run loses every record when the run dies mid-way, and the report then
  describes a smaller, cleaner world than the one that exists.
- Selection logic ("which agents belong to group X") lives in **one tested
  function**. Agent IDs are irregular (`S08-1-WATER` but also `D26`, no
  separator), so naive prefix matching either misses a class or lets `S01`
  swallow `S12`.

## Long-running jobs

A token fetched once at startup expires when the run outlives it, and the
failure lands on whichever items ran last — reading as *their* defect. Cache
credentials with a TTL well inside the token lifetime, and raise loudly on an
empty token rather than sending a bearer header with nothing in it.

## Property graphs

A property graph created over empty tables **succeeds** and returns zero rows
with no error, so the failure presents as working code. Load the data before
creating the graph.

## Tests

Test properties, not literals. Every gate must be mutation-checked: if breaking
the thing under test does not turn the test red, the test is decorative. Report
denominators honestly — "97 of 100" is information, "passing" is not.
