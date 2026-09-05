# Mining Agent Estate — Sales & Presales Enablement Brief

> **Purpose.** Everything a seller or presales engineer needs to position, demo,
> and defend this asset. Structured for direct import into a presentation
> generator: each `##` is a section, each `###` a slide, and every slide carries
> a **Speaker note** with the words to say and the objection to expect.
>
> **Provenance rule.** Every number below was measured against the live dataset
> or the deployed estate on 2026-08-29. Nothing is illustrative. Where a figure
> is an order-of-magnitude framing rather than a measurement, it is labelled
> *class*. Where a claim needs an external citation we do not yet hold, it is
> marked **[CITATION NEEDED]** — do not present those as sourced.

---

## 1. The Executive Frame

### 1.1 The one-sentence positioning

A mining operation's value leaks across six domains at once, and no single role
can see across them. This estate puts **100 grounded agents** on the operation's
own data so that a predicted mill failure and an out-of-stock bearing are
recognised as *the same event* — not discovered six weeks apart.

**Speaker note.** Open here, not with the architecture. The buyer is a GM or a
COO. The line that lands is the last one: *the same event, six weeks apart.*
Pause after it. Do not say "AI" in the first minute.

### 1.2 The problem, in the operation's own numbers

Measured from the live dataset — not assumed, not modelled:

| Signal | Measured | Source table |
|---|---|---|
| Work orders at CRITICAL priority | **101 of 500** | `erp_work_orders` |
| Work orders CANCELLED (deferred, will resurface) | **104 of 500**, $617k booked repair cost | `erp_work_orders` |
| Spare parts below reorder point | **28 of 140**, against 21.6-day mean lead time | `inventory_levels` |
| Concentrator recovery spread | **88.2% – 95.2%** (mean 92.2%) | `metallurgical_recovery` |
| Safety incidents on record | **60**, including fatality-class events | `safety_incidents` |
| Fatigue readings unreviewed | **3,340** across 20 operators | `biometric_fatigue_logs` |

**Speaker note.** The power is that each row is owned by a *different person*,
sits in a *different table*, and is worked in a *different tool*. That is the
pitch. If the buyer starts debating whether 101 is a lot, you have lost the
thread — steer back to the disconnection, not the magnitude.

### 1.3 Why this is a board-level problem, not an IT one

The cost is not any single number. It is that the six numbers never meet. Every
one of them is a *known* signal already sitting in a table someone owns. The
failure is organisational latency, and that is what an agent estate compresses.

**[CITATION NEEDED]** — if you want the McKinsey/BCG framing on integrated
operations value capture, source and verify the specific figure before quoting
it. Do not present an unsourced industry percentage.

**Speaker note.** Expect: *"we already have dashboards."* Answer: dashboards
report state to the person who already owns that state. None of them crosses
an ownership boundary. That is exactly the gap here.

---

## 2. What Was Actually Built

### 2.1 The estate at a glance

| Dimension | Verified count |
|---|---|
| Agents deployed and grounded | **100 / 100** |
| Coordinated swarms | **12** (S01–S12) |
| Distinct personas served | **8** (P1–P8) |
| Value branches covered | **9** |
| Distinct data tables grounded | **25** |
| Dataset scale | **97 tables, 63,683 rows** |
| Agents requiring human-in-the-loop | **14** (86 advisory-only) |
| Recorded walkthroughs | **100** |
| Automated tests, green | **1,404** unit + functional gate |

**Speaker note.** "100 agents" is the headline, but **100/100 grounded** is the
credible part — every agent resolves to a real table and column. Say that
number, because most competitive demos cannot.

### 2.2 Coverage by persona

| Persona | Role | Agents |
|---|---|---|
| P3 | Mine Safety & Health Manager | 21 |
| P4 | Supply Chain / Procurement Manager | 18 |
| P1 | Reliability Engineer | 16 |
| P6 | Metallurgist / Concentrator Superintendent | 11 |
| P7 | Mine Ops / Dispatch Supervisor | 10 |
| P5 | Resource Geologist | 10 |
| P2 | Maintenance Planner | 9 |
| P8 | Shift Superintendent (escalation target for P1–P7) | 5 |

### 2.3 Coverage by value branch

| Branch | Agents | Branch | Agents |
|---|---|---|---|
| Safety | 21 | Maintenance execution | 9 |
| Asset reliability | 16 | Procurement | 8 |
| Processing | 11 | Site-wide | 5 |
| Mine operations | 10 | Geology | 10 |
| Supply chain | 10 | | |

**Speaker note.** Use this slide to answer *"is this MECE or did you just build
what was easy?"* The distribution follows the pain, not the data availability —
safety leads because fatigue and incident signals arrive faster than humans
triage them.

---

## 3. Proof It Is Real — The Grounding Story

### 3.1 What "grounded" means here

Every agent reads the operation's live tables at question time. Business
constants live in the **data**, never in the prompt. We verified this
mechanically: all 100 agent instructions were built and scanned for embedded
baseline figures — **zero** contained one.

**Speaker note.** This is the strongest technical differentiator and it is
demonstrable in seconds. When the data changed underneath the estate (a table
deliberately grew from 105 to 140 rows), **no agent needed rebuilding** — 19
agents read that table and all 19 reported the new number correctly, unchanged.

### 3.2 Every answer is cited

Each agent operates under a citation mandate:

> *"Every factual claim you make must cite the table it came from. An uncited
> number is a defect."*

Tool results carry `meta.tables_read`; the agent must quote those names. Agents
are also instructed that a failed call carries **no** data — they must say so
rather than fill the gap.

**Speaker note.** Demo this live if challenged on hallucination. Ask an agent
something the data cannot answer. It declines and says why. That moment sells
better than any successful answer.

### 3.3 The document keeps itself honest

The PRD's business baselines are re-derived from BigQuery by an automated test.
If the data drifts from the document — or the document from the data — the test
fails. The numbers on slide 1.2 cannot silently rot.

**Speaker note.** Presales gold. Most competitors' claim decks are static
assertions. Ours is enforced by CI.

---

## 4. The Four Flagship Demonstrations

Each was recorded live against BigQuery. Findings below are the agents' actual
outputs, not scripted.

### 4.1 "Where the block model lies" — reconciliation

- **Impact class:** $5–15M/yr
- **Finding:** BASALT is misestimated by **0.105 percentage points** across
  **182 blocks** — estimated 1.087%, assayed 1.192%.
- **Why it lands:** the resource model is the foundation of every downstream
  plan. A systematic grade bias compounds into every schedule built on it.

### 4.2 "The anomaly nobody was reading" — anomaly detection

- **Impact class:** $2–10M/yr
- **Finding:** **37 readings** on `vibration_hz` sit beyond three standard
  deviations — clustered, and nobody was reading them.
- **Why it lands:** the data was already being collected. The failure was
  attention, not instrumentation.

### 4.3 "Which stock-out stops which machine" — graph traversal

- **Impact class:** $2–8M/yr
- **Finding:** CRUSHER-03 depends on **5 parts** at stock-out risk, with
  **$277,245** of repair history flowing through them.
- **Why it lands:** this is the cross-boundary question no dashboard answers —
  it traverses from a part number to a machine to a cost history.

### 4.4 "Crusher to vessel in one question" — cross-domain cascade

- **Impact class:** $5–20M/event
- **Finding:** Stockpile SP-02-01 holds **6.2 hours** of reclaim buffer and
  feeds **9 vessels** — a six-hour crusher outage reaches the port.
- **Why it lands:** the strongest close. One question spans pit, plant,
  stockpile, rail, and port.

**Speaker note.** Lead with 4.4 for executives and 4.1 for technical audiences.
Impact figures are deliberately quoted as **ranges and classes** — never a
single point. If pressed for precision, say the range is the honest answer and
a site-specific study narrows it.

---

## 5. Architecture — Disclose Progressively

Only open this section if the room asks. Stop at the level that satisfies them.

### 5.1 Level one: the shape

Agents sit on Google Cloud, read the operation's data warehouse directly, and
answer in natural language with citations. Two agent patterns are in use:
**Pattern A (60 agents)** for focused single-domain analysis, **Pattern B (40)**
for departmental analysts that compose multiple tools.

### 5.2 Level two: coordination

Twelve swarms (S01–S12) group agents under coordinators that consult live
teammate engines. A coordinator does not simulate its team — it calls them.

### 5.3 Level three: control and safety

- **14 agents require human-in-the-loop** for any consequential action, such as
  raising a purchase order. The remaining 86 are advisory-only.
- Every agent has an explicit **data scope** — a whitelist of readable objects.
  It cannot read outside it.
- Guardrails per agent cover input/output size, rate limit, timeout, and
  concurrency.
- The showcase workspace runs privately behind **IAP**; recordings stream from
  storage through the application, so the browser never touches the bucket and
  access control lives in exactly one place.

**Speaker note.** The HITL split is the answer to *"what stops it doing
something stupid?"* Name the number: 14 of 100 can act, and only with a human.

---

## 6. Running the Demo

### 6.1 The latency truth — read this before you present

Agents answer in **seconds via the API** but typically **2–4 minutes through the
chat UI**. Under sustained load the wait lands *before* the agent starts work,
so a longer timeout does not help.

**Mitigations, in order:**
1. **Pre-warm** the specific agent you plan to show.
2. **Narrate the tool trace** while it works — it is the proof of grounding and
   the most interesting part to talk over.
3. Have the recording ready.

### 6.2 Fallback order — do not improvise this

1. **Play the recording first.** It is verified and it cannot stall.
2. **Go live only on request**, and only for an agent you pre-warmed.
3. **If the UI is queuing, drop to the API** — it answers in seconds and shows
   the same grounding without the chat surface.

**Speaker note.** Never open a demo by gambling on live latency. Losing ninety
seconds to a spinner costs more credibility than a recording ever does. The
recordings show real, unedited agent output — you are not hiding anything.

### 6.3 Assets available

- **100 recordings**, one per agent, each opening on the operational question,
  showing the live data read, then the answer at reading pace.
- **Sales companion document** with a Situation / Agent Action / Logic script
  per agent, written so a reader who has never seen the system can follow it.
- **Four deep-dive scenario recordings** for the flagship demos in §4.

---

## 7. Honest Positioning — Say These Things First

Credibility here is the product. Volunteer these before a prospect finds them.

| Reality | How to say it |
|---|---|
| The dataset is **synthetic**, purpose-built to be realistic and internally consistent. | "This is a reference operation, not a customer's live site. The value is that the agents are genuinely reading it — swap the data and the agents work unchanged." |
| Impact figures are **classes and ranges**, not commitments. | "Order-of-magnitude framing. A site-specific study narrows it." |
| The chat UI is **slow under load**. | Covered proactively in §6.1 — never let them discover it during your demo. |
| Lead time is a **physical constraint** no agent compresses. | "For long-lead parts the gain is earlier detection, not eliminating the stock-out. We set the targets that way deliberately." |
| Agents are **advisory by default**. | "86 of 100 cannot act at all. The 14 that can require a human." |

**Speaker note.** The lead-time row is a real credibility win. It shows we set
targets a planner would sign off on, rather than the most flattering number.
Experienced operators notice this and it buys trust for everything else.

---

## 8. Objection Handling

**"How do I know it isn't making the numbers up?"**
Every claim cites its source table, and the tool trace is visible. Ask it
something unanswerable — it declines rather than guessing.

**"We already have BI dashboards."**
Dashboards report state to whoever already owns that state. None crosses an
ownership boundary. §4.3 and §4.4 are the questions no dashboard answers.

**"What happens when our data changes?"**
Nothing. Constants live in the data, not the prompts. When a grounded table
grew by a third, 19 agents picked up the new figures with **zero rebuilds**.

**"Why 100 agents and not one big one?"**
Scope control. Each agent has a whitelist of readable tables and a single
responsibility, which is what makes the citation mandate enforceable and the
blast radius of any change small.

**"Is this production-ready?"**
It is a **reference implementation and showcase**, verified end-to-end: 1,404
automated tests green, plus a functional gate that checks every recording the
application advertises actually exists and streams. Production deployment at a
customer site is a scoped engagement.

**Speaker note.** Answer the last one exactly as written. Overclaiming
production-readiness is the fastest way to lose a technical evaluator.

---

## 9. Appendix — Verification Record

| Check | Result | Date |
|---|---|---|
| Agents grounded to real tables/columns | 100 / 100 | 2026-08-29 |
| Unit test suite | 1,404 passed, 7 skipped — two consecutive clean runs | 2026-08-29 |
| Functional gate (recordings exist + stream, 404s behave) | PASS | 2026-08-29 |
| Recording ↔ script pairing | 100 / 100 matched to the capture each script quotes | 2026-08-29 |
| Agent instructions containing hardcoded baselines | 0 of 100 | 2026-08-29 |
| PRD business claims re-derived from BigQuery | PASS (enforced in CI) | 2026-08-29 |

**Known limitations, stated plainly.**
- IAP sign-in is verified by a human loading the page; it is deliberately not
  automated, because automating it would require a service-account key.
- The dataset is synthetic.
- Impact figures are classes, not measured savings at a customer site.
