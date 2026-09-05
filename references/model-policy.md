# Model Policy

This is the **only** file in the repository permitted to contain a raw model ID.
All agent code refers to tiers. `mining_agents.config.model_for_tier()` parses the table below.

| Tier | Model ID | Used by |
|---|---|---|
| `reasoning` | `gemini-3.1-pro-preview` | 12 swarm coordinators, 12 swarm critics |
| `balanced` | `gemini-3.6-flash` | 36 swarm specialists, 40 Pattern B deep agents |

There is no `high-volume-subagent` tier. No Pattern C agent is in scope for this build.

To change a model, edit this table only. No code change is required.

## Why these two, on 2026-08-11

Chosen by calling `:generateContent` against this project directly rather than
from memory of model names. Confirmed callable here:

`gemini-3.6-flash` · `gemini-3.5-flash` · `gemini-3.1-pro-preview` ·
`gemini-3-flash-preview` · `gemini-flash-latest` · `gemini-2.5-pro` ·
`gemini-2.5-flash` · `gemini-2.5-flash-lite`

Returning 404 in every region tried, so not options: `gemini-3.1-pro` (the
preview suffix is required), `gemini-3.6-flash-preview` (3.6 Flash is GA, so
there is no preview alias), `gemini-3-pro-preview`, `gemini-3-pro`,
`gemini-2.0-flash`, `gemini-pro-latest`.

`gemini-3.6-flash` is the newest Flash and is **GA**, which is what 76 of the
100 agents run on. `gemini-3.1-pro-preview` is the newest Pro reachable from
this project and is **preview** — no GA deprecation guarantee, which matters
for a reference accelerator a customer forks. It carries only the 24 reasoning
agents. Falling back to `gemini-2.5-pro` is a one-line edit to the table above
and needs no code change.

Do not use `gemini-flash-latest` or any other floating alias: a model that
changes underneath a demo makes a failed run impossible to reproduce.

`tests/test_config.py` calls both configured IDs against the live endpoint, so
a model that is renamed or withdrawn fails the suite rather than the deploy.
