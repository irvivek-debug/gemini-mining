# Critical Review — Full Agent Recording Estate (100 agents, 2026-08-28)

Method: two evidence layers, no video content assumed.
**Mechanical layer** — ledger↔GCS reconciliation, response latencies, check
flags, video sizes, for all 100 agents. **Judged layer** — four independent
judges scored every agent's final UAT transcript (prompt, reply, follow-up)
on function / logic / grounding / business-voice, 1–10, strict rubric, with
arithmetic spot-checked. Scores are transcript quality; what the *video*
shows on top of that is covered under systemic findings.

## Estate scorecard

| Dimension | Mean | Median | Agents ≤5 |
|---|---|---|---|
| Function (does it do the job) | 7.6 | 8 | 15 |
| Logic (internally consistent) | 8.1 | 8 | 3 |
| Grounding (real data, not echo) | 8.1 | 8 | 3 |
| Business voice (persona fit) | 7.6 | 8 | 3 |
| **Overall** | **7.86** | | |

Distribution: 57 agents ≥8 (ship-grade), 27 at 7–8 (solid), 14 at 6–7
(mediocre), 2 below 6 (defective). By role: critics 8.42 > coordinators
8.35 > specialists 7.94 > domain agents 7.47 — the swarm-structured agents
consistently outperform the flat domain agents.

Coverage is flawless: 100/100 agents have GCS videos whose filenames match
their passing ledger rows; zero failed sub-checks; no missing or undersized
captures.

## The two defective recordings (fix before anyone sees them)

- **D13 (bucket-tooth detection, 5.2)** — declares "no missing tooth" as a
  safety assurance *after admitting no camera feed exists*, then contradicts
  itself in the follow-up. An ungrounded safety claim is the single worst
  thing a grounding-pitch demo can contain.
- **D36 (berth clearance, 5.8)** — claims a 5m clearance margin is "actively
  enforced" with no sensor evidence, having admitted LiDAR isn't logged.

Same failure shape: the agent invents an all-clear where the data is silent.
These two undermine the central sales claim ("agents that read data, not
hallucinate") and should be re-prompted and re-recorded first.

## Systemic findings (ranked by impact)

1. **Every one of the 100 videos contains the killed turn-2.** All final
   ledger rows are two-turn; the governance follow-up you cut ("what are you
   NOT permitted to do") is ~3,000 chars of answer and ~20% of each video's
   wait time. No current video reflects the single-turn format.

2. **~2 minutes of dead air per video.** Median first-response is 124s
   (p90 194s, max 260s); 24 agents exceed 4 minutes total session. The GE
   UI's latency is baked into every recording — a viewer watches a spinner
   for a third of the runtime. (The BQ v3 recordings don't have this problem;
   the Conversational Analytics UI answers in seconds.)

3. **The review scroll is unreadable (user-reported, root-caused).** Both
   recorders scrolled answers as a continuous crawl — `uat_run.py` at
   100px/650ms, `record_bq_scenarios.py`'s end pass at 110px/600ms — so the
   text never sits still and a human cannot read it; the BQ per-turn dwell
   additionally jumped to the *bottom* of each answer, so anything taller
   than one screen showed only its tail and the headline finding was never
   static on screen. Every existing video has this baked in. **Both
   recorders are now fixed** to page-stepping: show a full viewport, hold it
   static ~5–6s for reading, step one screen with a small overlap, repeat —
   dwell time scales with answer length. Any re-record scope inherits the
   fix; existing videos can only be cured by re-recording.

4. **A ~15-agent cluster where the prompt asks for data the estate doesn't
   hold.** Flags: hedging-refusal (8), no-final-answer (4), generic-no-data
   (4), no-computation (2). D11, D15, D18, D22, D25, D38, D39, S01-1, S02-1,
   S03-3, S06-1, S06-3, S07-1, S08-2, S09-1. The agents behave *honestly*
   (that's the grounding discipline working) but the videos end without a
   deliverable — a refusal is a poor sales artifact. This is a **PRD defect,
   not an agent defect**: those prompts need rewriting to be answerable, or
   the missing columns need adding to the estate.

5. **Four arithmetic/logic slips that survive on camera.** D34 (Arrhenius
   shelf-life table off ~1000×), D29 (suspected lb/kWh vs g/kWh unit error),
   S03-1-GEOMETRY (powder factor contradicts its own figures), and
   S03-COORDINATOR (Kuz-Ram result doesn't follow from stated inputs). A
   technical buyer who checks will find them.

6. **12 coordinator videos show no delegation.** Recorded before the swarms
   were wired; the coordinators answer solo. S01-COORDINATOR-V2 now proves
   real A2A consultation — once the S02–S12 batch lands, the coordinator
   set should be re-recorded showing `consult_*` calls, or the "swarm"
   story in those videos stays cosmetic.

7. **Rendering and polish defects**: raw LaTeX artifacts in S08 replies
   (same class as BQ-S1's), a triple-word glitch in S09-COORDINATOR,
   a "% Fe" column label in S12-R-CRITIC's copper estate, a transaction-count
   subtotal inconsistency in S10-1-CONTRACT, and a "claimed-actuation"
   overreach in S05-R-CRITIC ("ENFORCED — 0.00 tph" from an advisory agent).

8. **Bucket debris**: 8 agents carry stray failed-attempt videos in GCS
   (~504MB, incl. a 360MB stuck capture beside S07-1-REAGENT's normal take).
   The referenced videos are all correct; the strays should be deleted.

## What's genuinely excellent

S12 (rail/blend/berth/critic all ≥8.9 with to-the-cent laytime sums), S10
and S11 (procurement/inventory — verified Gamma fits, dollar totals exact),
S08-COORDINATOR and the critics as a class (S01-R-CRITIC's QA/QC audit and
S10-R-CRITIC's duplicate-invoice catch are the best grounding proof in the
estate), S02-2-SCHEDULE, S04-3-PAYLOAD. Refusal-to-fabricate on trap prompts
(S10-COORDINATOR's fake invoice, S11-COORDINATOR's uncataloged part,
S04-2-ROUTE's nonexistent ramp) is exactly the story the showcase sells.

## Remediation options

| Scope | Effort | What it buys |
|---|---|---|
| A. Fix the 2 defective + 4 arithmetic agents (re-prompt, re-record 6) | ~1 evening | Removes everything a hostile viewer can score a direct hit on |
| B. + rewrite the 15 data-gap prompts, re-record those | ~2 evenings | Every video ends with a deliverable |
| C. + re-record 12 coordinators post-v2 batch (delegation on film) | ~1 evening, gated on quota | The swarm story becomes real on camera |
| D. Full estate re-record (single-turn, dwell-hardened recorder, clean sidebar) | ~2–3 nights unattended | Kills turn-2 and dead-air everywhere; uniform v3 quality |

Recommendation: **A + C are mandatory** for credibility; B is high-value;
D is worth it only if the estate videos are a primary sales surface — the
per-agent pages could alternatively be re-pointed at trimmed/edited copies.

## Per-agent scores

See `/tmp/judge_merged.json` (full per-agent scores, flags, notes) —
persisted copy at `data/uat/estate_judgment_20260828.json`.
