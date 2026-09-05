# Gemini Mining

A reference implementation of a grounded, multi-agent system for mining and
upstream/downstream petroleum operations, built on the Google Agent Development
Kit (ADK), Vertex AI Agent Engine, Gemini, and BigQuery.

Every agent in this repository answers from data it actually queries. That is
the point of the project: an agent that sounds right while reading nothing is
the failure mode this codebase is organised to prevent.

## What this is

| | |
|---|---|
| Agent estate | 101 agents, registry schema v2.0.0 |
| Framework | Google ADK, deployed to Vertex AI Agent Engine |
| Models | Gemini, resolved by tier — see `references/model-policy.md` |
| Grounding | BigQuery, with declared-table enforcement per agent |
| Identity | 3 service accounts, one per capability tier |
| Tests | 60 test modules |

The synthetic dataset, the agent catalogue, the persona method packs, the
deployment scripts, and the showcase front-ends are all here. Nothing is
stubbed: `scripts/` builds the data, registers the agents, and records the
evidence.

## Repository layout

| Path | What lives there |
|---|---|
| `mining_agents/` | Agent package: config, registry, tool envelope, run log |
| `mining_agents/tools/` | BigQuery query, BQML predict, ontology and method lookup, approval |
| `mining_agents/safety/` | Output filtering and untrusted-content handling |
| `data/generator/` | Ten synthetic-data generators (geology, haulage, fatigue, metallurgy, supply chain, …) |
| `infra/ddl/` | BigQuery table and view definitions |
| `infra/iam/` | Service-account definitions with plan/apply |
| `method/` | Persona method packs (YAML) — the reasoning each persona applies |
| `vendor/agent_registry/` | Agent catalogue and manifest |
| `scripts/` | Data build, agent registration, deployment, grounding verification, recording |
| `apps/frontend/` | Showcase UI |
| `apps/workspace/` | Persona workspace server |
| `docs/specs/`, `docs/plans/` | Design specs and implementation plans |
| `tests/` | Unit, integration, integrity, and showcase tests |

## Running it in your own project

This repository contains **no project-specific identifiers**. Every GCP value
is read from the environment, and the code raises a named error rather than
falling back to a placeholder — a silent default surfaces later as a confusing
BigQuery 404 in whichever query happens to run first.

Start here: **[docs/RECREATE.md](docs/RECREATE.md)** walks the full path from an
empty GCP project to a registered agent estate, in order.

```bash
cp .env.example .env                 # fill in your project values
set -a && . ./.env && set +a         # nothing loads .env automatically
```

You need a GCP project with billing, `gcloud` and `bq` authenticated, and
Python 3.11+. Budget about half a day, most of it waiting on data loads and
agent registration.

### Deploying with an AI agent CLI

This repository is set up to be deployed by an agent (Antigravity `agy`, Gemini
CLI, or similar). Point it at the repository root and ask it to follow
`docs/RECREATE.md`:

```bash
agy -i "Read GEMINI.md, then deploy this repository by following docs/RECREATE.md in order. Ask me for the project values first, and stop for my confirmation before any billable step."
```

Use `-i` (interactive), not `-p`. `-p` runs a single prompt non-interactively
and prints the answer, so the agent could neither ask you for the project
values nor stop at the confirmation gates.

The rules the agent operates under live in **[GEMINI.md](GEMINI.md)** (and
[AGENTS.md](AGENTS.md), for runtimes that read that name instead). Both are
loaded automatically as directory rules. They tell the agent what to collect
from you up front, where to stop for confirmation, and — importantly — how to
tell a working deployment from one that merely ran without errors.

**Three steps cost real money and are slow to undo**: overwriting ten live
BigQuery tables, registering 101 Vertex AI Agent Engine instances, and
deploying 52+ Cloud Run services. Each supports a dry run, and the agent is
instructed to stop and ask before each one. Read what it proposes before you
approve it.

## Design principles

These are load-bearing, and the code is written to enforce them:

- **Grounding is verified, not assumed.** `scripts/verify_grounded.py` proves an
  agent read data, rather than proving it responded.
- **A lookup that fails must raise.** "Not found" and "nothing to do" are never
  the same branch; an empty default is how a broken pipeline reports success.
- **Agents read only their declared tables.** Enforced by dry run before
  execution, not by convention.
- **Value is stated as a range, and commodity-neutral.** The domain language is
  "contained metal", not a specific commodity, and estimates are ranges rather
  than false-precision point figures.

## Status

This is a reference and showcase implementation, not a production system. The
data is synthetic. See `docs/RECREATE.md` for what it takes to stand up, and
`reports/` for the evidence trail from the original build.

## License

No license is granted yet — see the repository owner before reuse.
