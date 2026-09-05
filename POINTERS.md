# Where everything lives

This repository is the authoritative codebase. Some assets are deliberately
**not** in git because they are large and fully regenerable.

| Asset | Where it comes from |
|---|---|
| Agent walkthrough recordings | Regenerate with `scripts/uat_run.py` |
| BigQuery scenario recordings | Regenerate with `scripts/record_bq_scenarios.py` |
| Generated parquet datasets | Regenerate with `data/generator/run_all.py` |
| Document corpus for the vector index | See `docs/RECREATE.md` § raw vault |
| Agent estate (101 ADK agents) | Register with `scripts/register_agents.py` |

Videos are excluded on purpose: GitHub rejects the payload, and every capture
can be re-recorded from the harness. `.gitignore` records which paths are
derived and why.

## Evidence trail

The original build left its receipts in the repository:

- `data/uat/ledger*.jsonl` — per-agent run ledger
- `data/grounding/results.jsonl` — grounding verification results
- `reports/` — scorecards and review passes

These are historical records of a specific run. They are useful as a reference
for what "done" looked like; they are not assertions about your own deployment.

## Regenerating from zero

`docs/RECREATE.md` is the ordered path from an empty GCP project to a running
estate. Read it before running anything in `scripts/` — several steps depend on
earlier ones in ways that fail quietly if skipped (most notably, a property
graph created over empty tables succeeds and returns nothing).
