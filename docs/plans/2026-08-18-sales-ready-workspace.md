# Sales-ready workspace — implementation plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** turn a workspace that reads like internal documentation into one a
sales or consulting team puts in front of a mining client.

**User's brief, verbatim, seven items:** (1) a good framing page, built from CEO
slides 3, 4 and 6 plus published research on agentic AI impact in mining; (2) the
cockpit shows the metrics agents impact with broad percentage ranges; (3) each
agent shows its impact on metrics in percentages; (4) the UX is too verbose and
the sidecar chat is not visually distinct from the agent; (5) positive framing
throughout — "the agents that cannot act on their own conclusion" is too
tactical; (6) every line SMART and impactful, and far more visual, since the
app indexes on text; (7) create data for any gaps so the demo is complete —
consistent with existing data, need not be scientific.

## Global Constraints

- Python `python3`; pytest as `PYTHONPATH=. <python> -m pytest -q`.
- **JS tests need a quoted glob:** `node --test 'tests/js/*.test.js'`.
- `apps/shared/*.js` load as script tags into ONE global scope. A duplicate `var` is a SyntaxError that blanks the screen. Grep before declaring.
- Commodity-neutral: "contained metal", never a named metal — including in cited research (say "a concentrate producer", not the metal).
- **Every benchmark percentage is attributed to its source and labelled an industry range, never presented as measured on this site's data.** An unattributed number is the thing that kills a CFO conversation.
- Site-measured numbers stay distinguishable from benchmark ranges. A reader must always be able to tell which is which.
- No absolute currency figure invented for the client; the opex denominator stays `[CLIENT INPUT REQUIRED]`.
- Nothing references this repo's data generator, "synthetic data", or the demo dataset.
- **Positive framing means positive positioning of TRUE statements, never gloss.** "Cannot act on its own conclusion" -> "Advisory by default: every recommendation lands with a named human." Same fact, stated as the governance strength it is. Do not soften a limit into an untruth.
- **TESTS MUST BE ABLE TO FAIL.** No tautologies, no floors at or below the value they guard.

## The benchmark set (researched 2026-08-18, use these exact figures)

| Metric | Range | Source |
|---|---|---|
| Throughput | +2-5% | BCG, mature AI sites in mining & metals |
| Throughput | +4-8% | McKinsey, metals & mining |
| Margin | +2-4 pts | BCG |
| Mineral recovery | +1-3% | McKinsey |
| Unplanned downtime | -30-50% | McKinsey / Deloitte, predictive maintenance |
| Maintenance cost | -18-25% | McKinsey |
| Contract value recovered | +3-5% | industry contract-management research |
| Agentic AI value pool | $2.6-4.4tn globally | McKinsey |
| Firms getting no material value | 60% | BCG AI Radar 2026 |
| Firms at substantial value at scale | 5% | BCG AI Radar 2026 |

NOTE: S09's card already states the widely quoted "9.2% contract value leakage"
figure is a misattribution. Do not reintroduce it. The 3-5% RECOVERY figure is a
different and defensible claim; keep both consistent.

---

### Task A: The impact model in the catalog

**Files:** `mining_agents/catalog/definitions.py`, `tests/catalog/test_definitions.py`

- [ ] Add `MetricImpact` (metric, direction, low_pct, high_pct, source) and hang a list off `AgentCard`.
- [ ] Populate for all seven carded agents from the benchmark table. An agent with no defensible benchmark carries none — do not invent one.
- [ ] Validate: direction in {increase, decrease}; low <= high; source non-empty and naming a firm.
- [ ] Test the source is always present — an impact without attribution must raise. Enumerate; do not check "non-empty string".

### Task B: The framing page

**Files:** `apps/workspace/value.html`, `apps/workspace/value.js`, `tests/js/value.test.js`

- [ ] Band 1 — THE ARGUMENT, from CEO slide 3's five steps: economics inverted (margin 24%->10%, grades -40% since 1991); playbook exhausted; remaining cost is judgement not muscle; agents are the first technology reaching that layer; the window is short (58% of mining executives prioritising AI budget in 12 months).
- [ ] Band 2 — THE LEVERS, from CEO slide 6: a table of six traditional levers with residual headroom, ending on the digital/dashboards row and the line "The industry spent a decade building the nervous system and never installed the reflex." This is the hinge of the whole argument; give it the weight of a pull-quote.
- [ ] Band 3 — WHAT THE EVIDENCE SUPPORTS: the benchmark table as a visual, every figure attributed on the face of it.
- [ ] Band 4 — WHY MOST PROGRAMMES MISS IT: 60% no material value, 5% at scale, and what this build does differently (coverage declared, evidence classed, every number traceable). This turns the honesty machinery into the differentiator.
- [ ] Keep the opex denominator as `[CLIENT INPUT REQUIRED]`.
- [ ] **Visual, not prose.** Charts, bars, tables. Cut every sentence that a number could carry.

### Task C: Cockpit metric ranges

**Files:** `apps/workspace/index.html` / its module, tests.

- [ ] Show the metrics this build's agents impact, each with its benchmark range and source, and the site-measured position where one exists.
- [ ] The two kinds of number must be visually distinct and labelled.

### Task D: Agent cards — impact, and positive copy

**Files:** `apps/workspace/agent-card.js`, `scripts/build_app_data.py`, tests.

- [ ] Render each agent's metric impacts as ranges with attribution.
- [ ] Re-cut coverage positively: "4 diagnostics proven, 2 scoped" rather than "4 of 6 instrumented". The fact is unchanged.
- [ ] Re-cut authority positively: advisory by default, every recommendation to a named human.
- [ ] Keep the honest-limit field. It is the most credible thing on the card; make it read as rigour rather than apology.

### Task E: Visual system and the sidecar

**Files:** `apps/shared/shell.js`, CSS, `apps/workspace/chat.js`, tests.

- [ ] Give the sidecar chat a visually distinct treatment from agent output — different surface, border and label. Today they read as one thing, which is the single worst UX defect reported.
- [ ] Verbosity pass across every screen: cut explanatory prose that a label, number or chart can carry.
- [ ] Add visuals: coverage bars, range bars, metric sparklines where data exists.

### Task F: Data completion

**Files:** `data/generator/**`

- [ ] Fill gaps so no screen shows an empty state in the demo. Consistent with existing data; scientific realism is explicitly relaxed per the brief, but values must remain operationally plausible and dates must sit in the existing window.

### Task G: Deploy and verify

- [ ] Full suite, both languages.
- [ ] `scripts/deploy_apps.py::apply(dry_run=False, confirm="yes-deploy-for-real")`.
- [ ] Verify in a real browser against the deployed revision; record measured character counts and headings.
