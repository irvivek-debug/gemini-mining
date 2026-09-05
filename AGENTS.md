# Agent rules for this repository

**Read [`GEMINI.md`](GEMINI.md) first — it is the full contract.** This file
exists because some agent runtimes load `AGENTS.md` and not `GEMINI.md`; the
essentials are repeated here so neither path leaves you uninformed.

To deploy this repository, follow [`docs/RECREATE.md`](docs/RECREATE.md) in
order, under the operating rules in `GEMINI.md`.

## The five things that matter most

1. **Nothing is hardcoded.** Every GCP value — project ID, project number,
   service accounts, buckets, endpoints — comes from the environment. Copy
   `.env.example` to `.env`, fill it in, and export it with
   `set -a && . ./.env && set +a`. No dotenv library loads it for you.

2. **Stop before spending money.** Three steps create billable, hard-to-undo
   resources: overwriting ten live BigQuery tables (step 5 `--apply`),
   registering 101 Vertex AI Agent Engine instances (step 7), and deploying
   52+ Cloud Run services (step 8). Get explicit human confirmation before
   each. Dry-run first — every one of them supports it.

3. **Order is load-bearing.** Steps succeed while producing nothing if their
   inputs are missing. A property graph built over empty tables *succeeds* and
   returns zero rows, so a broken deployment looks like a working one.

4. **Exit code zero is not success.** Verify with
   `python scripts/verify_grounded.py` and `pytest tests/`. These prove a read
   actually happened, not merely that an agent replied. An agent that answers
   fluently while querying nothing is the failure this codebase exists to
   prevent.

5. **Report honestly.** Give real numbers and real errors. "97 of 100
   registered" is information; "deployed successfully" is not. Never weaken a
   failing check to make a step pass.

## If you see this, stop and fix it

- `RuntimeError: GOOGLE_CLOUD_PROJECT is unset` — `.env` was not exported.
- `...@unset-project.iam.gserviceaccount.com` anywhere in output — same cause,
  but the agent catalogue fell back to a placeholder quietly instead of raising.
