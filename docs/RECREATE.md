# Recreating this from an empty GCP project

The ordered path from nothing to a running, grounded agent estate. The order
matters more than it looks: several steps succeed while producing nothing if
their inputs are missing. The most dangerous is the property graph — created
over empty tables it **succeeds and returns zero rows**, so the failure
presents as working code.

Budget roughly half a day, most of it waiting on data loads and agent
registration.

## 0. Prerequisites

- A GCP project with billing enabled, and Owner (or equivalent) on it
- `gcloud` CLI, authenticated: `gcloud auth login && gcloud auth application-default login`
- The `bq` CLI on your PATH
- Python 3.11+, then `pip install -r requirements.txt`

## 1. Enable the APIs

Derived from the services this repository actually calls:

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com
```

## 2. Configure the environment

```bash
cp .env.example .env
```

Fill in every required value. Almost everywhere, the code **raises a named
error** rather than defaulting — a placeholder default surfaces much later as a
confusing BigQuery 404 in whichever query happens to run first, which is a far
worse afternoon than an error at startup.

### Set these before you deploy

| Variable | Required | What goes wrong if it is unset |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | yes | Most code raises at startup. **The agent catalogue does not** — see the warning below. |
| `GOOGLE_CLOUD_PROJECT_NUMBER` | yes | Registration fails; generated A2A card URLs are wrong. |
| `VERTEX_STAGING_BUCKET` | yes | Agent registration (step 7) fails. The bucket must already exist. |
| `VIDEO_BUCKET` | yes | The showcase app serves no recordings. |
| `MINING_DATASET` | no — `mining_data` | — |
| `MINING_LOCATION` | no — `US` | — |
| `MINING_REGION` | no — `us-central1` | — |
| `BQ_CONNECTION_ID` | no — `gemini-connection` | — |
| `ENGINE_SERVICE_ACCOUNT` | no — derived from the project | — |
| `BQ_BINARY` | no — resolved from `PATH` | Set it only if the `bq` CLI is not on your `PATH`. |

> **The one place a missing variable fails quietly.**
> `vendor/agent_registry/catalog_definitions.py` falls back to the visible
> placeholders `unset-project` and `unset-project-number` instead of raising,
> because it is also imported by tooling that inspects the catalogue offline
> and never reaches GCP. The trade-off is that an unset environment produces a
> catalogue that looks fine and is wrong.
>
> Catch it by eye: if a generated A2A card contains
> `sa-mining-agent-runner@unset-project.iam.gserviceaccount.com`, or a URL with
> `unset-project-number` in it, your environment is not set. Export the
> variables and regenerate.

Export them into the shell you run these commands from — a `.env` file on disk
is not read automatically by the scripts:

```bash
set -a && . ./.env && set +a
```

The deployed containers get these separately: `scripts/deploy.py` and
`scripts/deploy_apps.py` both pass `--set-env-vars=GOOGLE_CLOUD_PROJECT=…`
through to Cloud Run. Cloud Run, unlike App Engine, does not provide that
variable on its own, and the agent packages resolve it at **import** time — so
an agent container without it does not fail on a query, it fails to start.

Create the staging bucket referenced by `VERTEX_STAGING_BUCKET` before step 7;
Agent Engine does not create it for you:

```bash
gcloud storage buckets create gs://YOUR-STAGING-BUCKET --location=us-central1
```

## 3. Identity — three service accounts, not one per agent

```bash
# Dry run. Prints exactly the operations the live path would perform,
# and touches nothing. This is what the module does when run directly.
python -m infra.iam.service_accounts

# Apply, once you have read the plan above and agree with it.
python -c "from infra.iam.service_accounts import apply; apply(dry_run=False)"
```

Identity is per **capability tier**, not per agent. A hundred service accounts
would exhaust the project quota and buy nothing, because the meaningful
boundary is which data a tier may read.

Note the consequence, honestly: agents that share a tier share an IAM identity,
so IAM alone cannot separate them. The per-agent boundary is the declared-table
list enforced by dry run (step 5), plus the output filter in
`mining_agents/safety/`. If you are adapting this for production with genuinely
sensitive columns, add per-tier datasets or column-level access policies rather
than relying on those two layers.

## 4. BigQuery schema

```bash
bq --location=US mk --dataset "${GOOGLE_CLOUD_PROJECT}:mining_data"
python -m infra.apply_ddl
```

Run every command from the repository root — the modules import each other by
package path (`infra.*`, `mining_agents.*`), so `python infra/apply_ddl.py`
fails on the import while `python -m infra.apply_ddl` resolves.

`apply_ddl.py` is idempotent and verifies the objects exist afterwards rather
than trusting the DDL to have worked.

## 5. Generate and load the data

```bash
python data/generator/run_all.py --dry-run   # regenerates, loads nothing
python data/generator/run_all.py --apply     # overwrites the ten live tables
```

Ten generators run in dependency order (geology feeds haulage, and so on).
Generation takes about 30 seconds; the loads dominate.

**Do not skip ahead to the graph or the agents before this completes.** Empty
tables do not fail loudly anywhere downstream.

## 6. Embeddings and the document corpus

The vector index needs a document corpus in GCS plus a BigQuery remote
connection.

```bash
bq mk --connection --location=US --connection_type=CLOUD_RESOURCE gemini-connection
```

Grant the connection's service agent `roles/aiplatform.user` — `bq show
--connection` prints the identity to grant. Then:

```bash
python scripts/generate_contract_corpus.py   # synthesises the source documents
python scripts/build_doc_chunks.py
python scripts/build_doc_embeddings.py
```

If you are supplying your own corpus instead of the synthetic one, upload it to
the raw-vault bucket first; `build_doc_chunks.py` reads from there.

## 7. Register the agent estate

```bash
python scripts/register_agents.py --list     # what is and is not registered
python scripts/register_agents.py --confirm yes-register-for-real
```

Without `--confirm`, the script registers nothing. Use `--agents` with a
comma-separated list of agent ids to register a subset.

Two things that will otherwise cost you an afternoon:

- **Region.** The tiered models are published only on the `global` endpoint. A
  regionally-scoped client returns 404 in language that reads like a missing
  grant rather than a location mismatch. Model calls go to `global`; the session
  store stays regional because it lives under the (regional) engine resource.
- **Quota.** `ReasoningEngineEntitiesPerProjectPerRegion` defaults near 100 and
  this estate registers 101. Request an increase before you start, or register
  a subset.

## 8. Deploy the applications

```bash
python scripts/deploy_apps.py     # showcase + workspace as one Cloud Run service
python scripts/deploy.py          # the agent entrypoints
```

`deploy.py` prints — and deliberately does not run — any domain-binding
command. Run it yourself if you approve of it.

## 9. Verify grounding

This is the step that distinguishes a working estate from a convincing one.

```bash
python scripts/verify_grounded.py
python scripts/grounding_test.py
```

These prove a **read happened** (`meta.tables_read` in the tool envelope,
checked against the live source) rather than proving the agent replied. An
agent that answers fluently while querying nothing passes a liveness check and
fails this one. That is the entire point.

Run the test suite too:

```bash
pytest tests/
```

## 10. Optional — recordings and the showcase build

```bash
python scripts/uat_run.py                # per-agent walkthrough captures
python scripts/record_bq_scenarios.py    # BigQuery scenario captures
python scripts/build_shareable_html.py   # self-contained showcase page
```

## 11. Optional — sharing it outside your organisation

Cloud Run's built-in IAP uses a Google-managed OAuth client that **only admits
users inside the project's own organisation**. No IAM binding overrides this;
external users are refused before authorization is evaluated, behind a
misleading "You don't have access" page.

External access therefore requires the **load-balancer flavour of IAP**, which
accepts a custom OAuth client:

1. Create an external HTTPS load balancer with a serverless NEG pointing at the
   Cloud Run service.
2. Create a Web-application OAuth client. Its authorized redirect URI must be
   exactly `https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect`
   — without it, sign-in fails with "Access blocked: this app's request is
   invalid".
3. Enable IAP on the **backend service**, passing that client's ID and secret.
4. Only then set the Cloud Run service to `--no-iap` with ingress
   `internal-and-cloud-load-balancing`. In this order the application is never
   exposed unauthenticated. IAP takes a minute or two to begin intercepting —
   confirm you get a 302 to `accounts.google.com` before sharing the URL.
5. Grant viewers `roles/iap.httpsResourceAccessor` on the backend service.

Two sharp edges worth knowing in advance: a consent screen left in **Testing**
admits only individually listed test users (groups are not honoured, and
consents lapse after about a week), and `gcloud` sets `portName` from
`--protocol` in a way that makes `add-backend` reject serverless NEGs — create
the backend service with the default protocol.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `RuntimeError: GOOGLE_CLOUD_PROJECT is unset` | `.env` not created or not exported |
| Agent answers confidently, cites nothing | Grounding broken — run step 9, check the runtime identity's BigQuery roles |
| Model 404 "not found or no access" | Regional endpoint; tiered models are `global` only |
| Property graph returns zero rows, no error | Created before step 5 loaded the data |
| Agent registration fails near the 100th | `ReasoningEngineEntitiesPerProjectPerRegion` quota |
| `execute_sql` returns 403 | Runtime service account lacks a BigQuery role |
