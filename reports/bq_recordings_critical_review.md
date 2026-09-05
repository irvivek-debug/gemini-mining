# Critical Review — BQ Data Agent Scenario Recordings (v3, 2026-08-27)

Judge: evidence-bound review of the four gated recordings. Every claim below
comes from the transcripts, the per-turn screenshots, `turns.json`, or SQL
ground truth. No video content is described that was not verified in a
screenshot or transcript.

Dimensions (each /10):
- **Coverage** — does the scenario exercise the capability it was designed to sell, end to end
- **Grounding** — are the numbers real (verified against SQL ground truth), assumptions disclosed
- **Logic** — does the prompt arc build from context to a business decision without internal contradiction
- **UX** — what a viewer actually sees: pacing, rendering, clutter, readability
- **Sales** — business language, ranges not point prices where we control it, a closer worth quoting

| Scenario | Coverage | Grounding | Logic | UX | Sales | Overall |
|---|---|---|---|---|---|---|
| S1 grade reconciliation | 9 | 9 | 9 | 6 | 7 | **8.0** |
| S2 anomaly hunt | 9 | 10 | 10 | 7.5 | 9 | **9.1** |
| S3 parts-failure graph | 10 | 10 | 9 | 7.5 | 9 | **9.1** |
| S4 pit-to-port cascade | 9 | 9 | 7.5 | 7.5 | 9 | **8.4** |
| **Set average** | | | | | | **8.7** |

## What is genuinely strong

- **Every number checked out.** S1: BASALT 1.192% vs 1.087% = 0.105pp. S2: 37
  vibration anomalies, 17.11 Hz peak vs 5.60 Hz baseline. S3: CRUSHER-03
  $277,245 exposure, PUMP-104A $272,925, TRUCK-08 $232,985. S4: SP-02-11 5.3h
  first run-out, SP-02-01 6.2h on the rail-feeding chain. All match SQL.
- **The closers exist and land.** The two lost closers from v2 (S3 expedite,
  S4 brief) are on film with substantive answers. S2's shift-handover memo is
  the best single artifact in the set: thermal drift + 37 vibration anomalies
  correlated into a "developing fault, not bad sensor" argument with a named
  action. Screenshot-verified fully in frame after the dwell.
- **Assumptions are disclosed, and money is quoted in ranges.** S4's demurrage
  turn states "$20,000 to $35,000 USD per vessel-day" as an explicit assumption
  and gives exposure as $260k–$455k. S3 quotes repair costs as ranges in prose
  while the table carries exact figures. This is the house style.
- **The send/dwell hardening worked.** All 21 prompts verified on-page; no
  turn advanced while visibly busy except the one case below.

## Defects, ranked by impact

1. **Sidebar clutter in every frame (all four videos).** The conversation
   rail shows ~19 stale test conversations, including five literal
   "What questions can I ask?" entries and one prompt about operator sleep
   deficits — data that does not exist in this estate. To a buyer it reads as
   test debris and invites the question "why is your demo environment messy?"
   *Fix: delete old conversations (or collapse the rail via its chevron)
   before recording. Cheapest, highest-visual-impact fix on this list.*

2. **S1 turn 4 renders raw LaTeX.** The money-shot calculation shows as
   `$$\text{Planned Copper Metal} = …$$` markup — gibberish on screen at the
   exact moment the scenario proves its value. *Fix: append "show the
   arithmetic in plain numbers, no formula notation" to that prompt and
   re-record S1.*

3. **S1 turn 1 dwelled on a spinner.** The screenshot shows "Analyzing ." —
   the busy-detector regex covers "Analyzing context" but not bare
   "Analyzing", so the first dwell showed a working state (the answer appears
   moments later in the continuous video, but the intended hold-on-answer is
   lost for that turn). Only S1-T1 is affected; S2/S3/S4 turn-1 screenshots
   all show rendered answers. *Fix: add bare `Analyzing` to BUSY_JS.*

4. **S4's narrative anchor wobbles.** Turn 3 crowns SP-02-11 (5.3h) as
   first-out; turn 4 traces SP-02-01 (6.2h) as the chain feeding rail; the
   closer's bottleneck is "Stockpile North (SP-02-11 and SP-02-22)". Each
   claim is individually correct, but the star of the story changes twice. A
   sharp viewer will ask "so which stockpile is the problem?" *Fix: tighten
   turn 4's prompt to "for the stockpile that runs out first…" — or brief the
   presenter that buffer-risk and chain-exposure are two different lenses.*

5. **Long tables show ~2 rows in frame.** S2's 12-metric table and S3's
   ranking table render collapsed with an expander chevron the recorder never
   clicks; the dwell holds on a mostly-hidden table. *Fix: click the table
   expander before dwelling, or accept — the charts carry the visual load.*

6. **S1 turn 4's tonnage rests on an assumed block size.** The agent assumed
   100m×100m×25m blocks from centroid spacing (disclosed on screen), and
   135.7M tonnes / +141,767 t Cu follow from it. A mining audience may
   challenge the block size. *Fix: add block dimensions to the data catalog so
   the figure becomes data-driven, or arm the presenter with the caveat.*

7. **Commodity-neutrality is impossible inside the agent's own answers.**
   The dataset is copper/gold, and the agent names them with point values.
   Our controlled surfaces (prompts, companion doc, insight cards) stay
   neutral-with-ranges; the raw agent output cannot. Known and accepted —
   noted so nobody scores it as a regression later.

## Recommended remediation order

1. Clean the conversation rail, fix the busy regex (one line), amend the S1
   turn-4 prompt → **re-record S1 only** (~20 min). Fixes defects 1–3 for the
   weakest video; lifts S1 UX from 6 to ~8.5 and the set average to ~9.
2. Optionally tighten S4 turn-4 prompt and re-record S4 (~25 min) for defect 4.
3. S2 and S3 ship as-is.
