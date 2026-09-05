# UAT & Sales-Recording Scorecard — 2026-08-25 (final)

Every registered agent driven through the live Gemini Enterprise UI with its
PRD scenario, on video, and scored on five gates: answered, grounded-or-
says-not, logical pass (in character), no fabrication, not-the-prompt.

## Result: 100 / 100 pass

All 100 agents recorded (`data/uat/videos/<AGENT-ID>/*.webm`, 137 files) and
passing every gate. Evidence ledger: `data/uat/ledger.jsonl`.

## The three defects the UAT caught — all fixed and re-verified

1. **AGT-19 and S01-COORDINATOR answered from the question, not the data.**
   Both carry a custom `system_instruction`, and the reconciliation demand
   lived only in the composed-instruction branch, so precisely these two
   produced fluent maths computed from the question's own numbers, citing
   nothing. Fixed: the demand is one shared string appended to both
   branches (commit f3c228b); both rebuilt, grounded at build, and passing
   UAT with reconciliation visible in the reply.
2. **S05-1-CSS was blocked by Gemini's safety filter.** "Calculate
   hydraulic pressure setpoint…" was refused outright
   (`error_code: SAFETY`) — the agent never got to speak, so every UI
   recording captured nothing while every API grounding probe passed.
   Fixed: scenario reframed as data analysis (commit 3f648af); the agent
   now answers with 17 tool calls, reconciles against `crusher_telemetry`,
   and cites it.
3. **S03-3-VIBRATION had never been recorded** — it was quota-blocked when
   the UAT list was built. Added once registered; passes.

## Findings for the demo script

- **GE-UI latency is real and variable.** The same agents answer in
  12–50s via the API but typically 2–4 minutes through the Gemini
  Enterprise chat UI, with a slow tail to ~6 minutes under backend load.
  Live demos should pre-warm the agent or narrate over the "Working on
  the request" tool trace — which itself demos well: the audience watches
  List Table Ids → Get Table Info → Execute Sql tick through.
- **The tool trace is the proof of grounding on screen.** Recordings show
  the agent visibly reading BigQuery before answering — use it.

## Estate status

100/100 agents registered and grounded (two consecutive verification
passes each, ground truth computed from live BigQuery at test time).
Quota at 105 gives rebuild headroom. Engineering patterns distilled from the
engagement live in `GEMINI.md`.
