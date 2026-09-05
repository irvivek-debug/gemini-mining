# Working in this repository

Guidance for an AI coding agent (Gemini CLI, Antigravity) working on this
codebase. These are the patterns the original build paid for; ignoring them
reproduces bugs that have already been fixed once.

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
