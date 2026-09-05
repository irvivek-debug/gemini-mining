# Value framing and agent cards — implementation plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ship a business-framing screen and per-agent cards that carry the PRD's
leak / archetype / authority / financial-line framing, plus method packs for the
CFO deck's four proof-point agents, three of which honestly declare zero coverage.

**Architecture:** additive. `AgentDef` gains card fields; a new `value.html`
screen renders three bands derived at build time from the catalog; three new
`not_instrumented` packs declare the agents whose data does not exist yet.
Nothing about the existing five packs, the honesty machinery, or `PACKS` changes.

**Tech Stack:** Python 3.12, `google-adk`, BigQuery, vanilla JS (script-tag
globals, no bundler), `node --test`, pytest.

**Spec:** `docs/specs/2026-08-17-value-framing-and-agent-cards-design.md`

## Global Constraints

- Python is `python3`. Run pytest as `PYTHONPATH=. <python> -m pytest -q`.
- **JS tests need a quoted glob:** `node --test 'tests/js/*.test.js'`. Unquoted, the glob matches nothing and reports success.
- Commodity-neutral: say "contained metal", never name a specific metal.
- Money as ranges, never a single point figure. **No absolute currency figure may appear on the value page.**
- Every number surfaced anywhere comes from real data or is marked `[CLIENT INPUT REQUIRED]`.
- Nothing may reference this repo's data generator, "synthetic data", or the demo dataset — a customer forks this repo and inherits the text.
- A driver's `status` is only `instrumented` or `not_instrumented`. `instrumented` requires `sql`; `not_instrumented` forbids `sql` and `compare`. Driver ids unique. `compare`, if present, may only be `setting_band`.
- A **guard** is the method's caveat on a finding — true before any row is read. It must never contain the finding itself, and must never contain a verdict word ("too few", "too many", "unevidenced", "no signal", "insufficient").
- Diagnostic SQL uses named `@params` only; `assert_no_interpolation` enforces it. For a list, `x IN UNNEST(@values)`.
- `apps/shared/*.js` load as script tags into one shared global scope. A second `var` of an existing name is a SyntaxError that takes the whole screen down. Check for collisions before naming anything.
- **TESTS MUST BE ABLE TO FAIL.** No tautologies (assertions true by construction). No floors sitting at or below the value they guard. Both recurred repeatedly earlier in this branch and are rejected on sight.
- Authority is **declared, not enforced**. Nothing may imply the platform enforces an authority level.
- Nothing pushed to any remote.

---

### Task 1: Card fields on AgentDef

**Files:**
- Modify: `mining_agents/catalog/definitions.py`
- Modify: `mining_agents/catalog/loader.py` if it validates field presence
- Test: `tests/catalog/test_definitions.py`

**Interfaces:**
- Produces: an optional `card` structure on `AgentDef` carrying `decision`,
  `leaks` (list), `archetype`, `authority`, `financial_lines` (list of
  `{line, evidence_class}`), `honest_limit`, and optional `pack`.

- [ ] **Step 1:** Add the card structure to `AgentDef`. Model `financial_lines`
      as a list of records so evidence class attaches to the line, not the agent
      (PRD §7 allows one agent to carry an A line and a B line).
- [ ] **Step 2:** Populate cards for the agents that already hold method tools:
      S01-SP3 (AGT-11, Diagnostician, leaks Blind spot + Latency, authority
      L1, line "unplanned repair cost → C1 cash cost", class B),
      S06-SP1 (AGT-09-adjacent — see Task 4 note), S02-SP2, S05-SP2, S07-SP3.
      Use the PRD's own wording for `decision`; do not invent.
- [ ] **Step 3:** Validation — an agent that declares a `card` must carry every
      required field. A missing field raises at import, not at render.
- [ ] **Step 4:** Tests. Assert the archetype is one of the PRD's six. Assert
      `financial_lines` entries each carry a class in {A, B, C}. Assert a card
      missing a required field raises. **The archetype test must enumerate the
      six and reject a seventh** — a test that merely checks the field is a
      non-empty string cannot fail on a typo.
- [ ] **Step 5:** Commit.

---

### Task 2: The three declared packs

**Files:**
- Create: `method/agt13-warranty.yaml`
- Create: `method/agt14-contract-integrity.yaml`
- Create: `method/agt19-strategic-planning.yaml`
- Test: `tests/method/test_declared_packs.py`

**Interfaces:**
- Consumes: `load_pack` from `mining_agents.method.pack` (verified to accept a
  pack in which every driver is `not_instrumented`).
- Produces: three packs whose every driver is `not_instrumented`.

- [ ] **Step 1:** Author `agt14-contract-integrity.yaml`. Archetype Negotiator.
      Metric: recovered value from post-signature contract leakage. Root:
      transactions raised against terms nobody has read. 5–6 drivers, every one
      `not_instrumented`, and **each driver's `question` must name the table and
      columns it would need** — that is what makes this pack the generator's
      specification. Measured today: `procurement_bids` holds bids (vendor,
      proposed_cost, bid_status, technical_rating_score, compliance_checked) and
      `rfp_items` holds 3 rows; there is no contract, no terms, no clause text,
      no agreed price schedule.
- [ ] **Step 2:** Author `agt13-warranty.yaml`. Archetype Negotiator. Metric:
      recovered value from warranty and OEM claims. 4–5 drivers, all
      `not_instrumented`. Measured today: no warranty table exists;
      `maintenance_logs` (152 rows) records repairs with no entitlement or claim
      state.
- [ ] **Step 3:** Author `agt19-strategic-planning.yaml`. Archetype Optimiser.
      Metric: value lost to a group plan re-tested on the calendar rather than
      on the world. 4–5 drivers, all `not_instrumented`. Measured today: no
      price deck, capital pipeline or NPV model exists. The pack must state
      that this agent is permanently L1 with no promotion path (PRD §8.1).
- [ ] **Step 4:** Tests. Every pack loads. Every driver is `not_instrumented`.
      No driver carries `sql` or `compare`. No guard contains a verdict word.
      No guard or comment contains "in this dataset" (the marker of a guard
      describing data rather than measurement — see
      `tests/method/test_p3_pack.py::test_no_guard_describes_the_data`).
      **Assert each pack has at least 4 drivers** so an empty pack cannot pass.
- [ ] **Step 5:** Commit.

---

### Task 2b: Generate the contract, warranty and capital data

**Added mid-execution.** The user's instruction: "if there is no data then you
need to create realistic data." This supersedes the spec's out-of-scope note
that generation was the next piece of work — it is now in this workstream, and
the three packs from Task 2 become instrumented rather than shipping at zero
coverage.

**Files:**
- Create: `data/generator/contracts.py`
- Create: `data/generator/warranty.py`
- Create: `data/generator/capital.py`
- Modify: `data/generator/run_all.py` (`GENERATORS` list)
- Modify: `data/generator/config.py` (`REWRITE_TABLES`)
- Test: `data/generator/tests/test_contracts.py`, `test_warranty.py`, `test_capital.py`
- Test: `data/generator/tests/test_realism.py` (new realism properties)

**Interfaces:**
- Consumes: the table and column names written into the Task 2 packs' driver
  questions. Those questions are the specification — read them, do not invent a
  schema.
- Consumes existing tables it must join to: `procurement_bids`, `rfp_items`,
  `inventory_levels`, `maintenance_logs`, `erp_work_orders`, `assets`,
  `fleet_vehicles`.
- Produces: new BigQuery tables in `mining_data`, loaded by the existing loader.

**Conventions to follow exactly** (read `data/generator/supply_chain.py` first):
seeded deterministic RNG via `_rng(*parts)` off `config.SEED`, a `write_parquet()`
entry point, registration in `run_all.py::GENERATORS` in dependency order, and
`_stable_hash` rather than the salted built-in `hash()`.

- [ ] **Step 1:** Contracts. Terms a transaction can be checked against —
      vendor, part, agreed unit price, volume-break tiers, rebate entitlement,
      validity window — plus the transactions themselves so a discrepancy is
      computable. Some transactions must reference no live contract at all;
      that absence is one of AGT-14's drivers.
- [ ] **Step 2:** Warranty. Coverage per asset or component with an OEM,
      a period, and claim state, joinable to `maintenance_logs` so a repair
      inside a warranty window that was paid for out of own cost is derivable.
- [ ] **Step 3:** Capital and price. A contained-metal price series with
      scenarios, and a capital project set carrying the assumptions a plan was
      approved against. **Commodity-neutral: the series is "contained metal",
      never a named metal.**
- [ ] **Step 4:** Realism properties, in the style of `test_realism.py`'s
      R1–R8. Not row counts — statistical properties. At minimum: leakage exists
      but is not trivially visible (a minority of transactions priced above
      their contract, not all and not none); warranty expiry produces a real
      cliff rather than a uniform distribution; the price series has plausible
      autocorrelation rather than white noise. **Each property must state the
      band it asserts and fail outside it.**
- [ ] **Step 5:** Load to BigQuery, confirm row counts and that every join the
      packs need actually resolves.
- [ ] **Step 6:** Commit.

Per the user's standing preference, generator work ships on passing tests and
thresholds — no review/fix/re-review loop on the generators themselves.

---

### Task 2c: Instrument the three packs

**Files:**
- Modify: `method/agt13-warranty.yaml`, `method/agt14-contract-integrity.yaml`, `method/agt19-strategic-planning.yaml`
- Create: `method/sql/agt13/`, `method/sql/agt14/`, `method/sql/agt19/`
- Modify: `mining_agents/tools/method_lookup.py` (`PACKS`)
- Test: `tests/method/test_declared_packs.py` (extend to integration)

- [ ] **Step 1:** For each driver whose data now exists, write the fixed
      diagnostic SQL, flip `status` to `instrumented`, and add the `guard`.
- [ ] **Step 2:** Validate every query against live BigQuery and pin the
      measured magnitudes in the tests, as `test_p6_pack.py` does with its
      `[23, 116, 28]` day counts. A test that only checks the query runs is not
      a reproduction.
- [ ] **Step 3:** Any driver whose data still does not exist stays
      `not_instrumented`. Do not force a diagnostic that the data cannot
      support — that is the failure this whole product exists to avoid.
- [ ] **Step 4:** Commit.

---

### Task 3: Coverage computed from the pack

**Files:**
- Modify: `scripts/build_app_data.py`
- Modify: `apps/shared/data/personas.json` (regenerated, not hand-edited)
- Test: `tests/scripts/test_build_app_data.py`

**Interfaces:**
- Consumes: `AgentDef.card` from Task 1, the packs from Task 2.
- Produces: each card in the export carries `coverage: {instrumented, total}`
  read from its pack, and the card's authored fields.

- [ ] **Step 1:** Export cards. For a card naming a `pack`, compute
      `coverage` by loading that pack and counting drivers by status. Never
      author the numbers.
- [ ] **Step 2:** Test that coverage is computed, not authored: build the export
      and assert AGT-11's coverage equals the count derived from
      `p1-reliability.yaml` **read independently in the test**. A test that
      compares the export to itself cannot fail.
- [ ] **Step 3:** Test that a fully-uninstrumented pack reports
      `instrumented: 0` with `total` > 0 — not absent, not null. A card that
      omitted coverage would read as full coverage.
- [ ] **Step 4:** Commit.

---

### Task 4: The value page

**Files:**
- Create: `apps/workspace/value.html`
- Create: `apps/workspace/value.js`
- Modify: `apps/shared/shell.js` (`WORK_NAV`)
- Test: `tests/js/value.test.js`, `tests/test_screen_copy.py`

**Interfaces:**
- Consumes: the export from Task 3.
- Produces: a three-band screen. Nav label "Value", first item of `WORK_NAV`.

- [ ] **Step 1:** Band 1, leak taxonomy. Five leaks with the PRD's one-line
      definitions, each showing the count of agents in this build claiming it,
      **derived from the export**.
- [ ] **Step 2:** Band 2, where the money goes. The 4.1% conservative / 9.0%
      stretch range against an opex denominator rendered as
      `[CLIENT INPUT REQUIRED]`. **No absolute currency figure.**
- [ ] **Step 3:** Band 3, evidence ladder. Class A / B / C from PRD §7 and the
      rule that funding rests on A and B only.
- [ ] **Step 4:** Surface AGT-19's card here (it is group-level and has no
      persona in this build).
- [ ] **Step 5:** Tests. Assert the page's leak counts equal the catalog's, so
      page and build cannot disagree. Assert **no currency figure** matches on
      the rendered copy (regex for a currency symbol followed by digits).
      Assert every leak named is one of the PRD's five, and that all five
      appear. Check `apps/shared/shell.js` for a global name collision before
      declaring anything in `value.js`.
- [ ] **Step 6:** Commit.

---

### Task 5: The agent card on the persona page

**Files:**
- Modify: `apps/workspace/persona.js` or whichever module renders the persona body
- Modify: `apps/shared/plain.js` only if a phrase is needed
- Test: `tests/js/persona.test.js` (or the existing persona-page test file)

- [ ] **Step 1:** Render the card beneath the governing question, for each agent
      of that persona which declares one.
- [ ] **Step 2:** Coverage must read as what it is. An agent at 0-of-6 must say
      so plainly; it must not be blank, and it must not read as an error — the
      distinction this branch already drew for `not_instrumented` drivers.
- [ ] **Step 3:** Nothing may imply authority is enforced.
- [ ] **Step 4:** Tests. Assert a card renders every required field. Assert the
      0-of-6 case renders visibly rather than emptily — **that is the assertion
      most worth having**, because an empty coverage row reads as full coverage.
- [ ] **Step 5:** Commit.

---

### Task 6: Deploy and verify in a real browser

**Files:** none; this task verifies.

- [ ] **Step 1:** Full suite: `PYTHONPATH=. <python> -m pytest -q` and
      `node --test 'tests/js/*.test.js'`.
- [ ] **Step 2:** Deploy: `scripts/deploy_apps.py::apply(dry_run=False, confirm=CONFIRM_PHRASE)`
      where `CONFIRM_PHRASE = "yes-deploy-for-real"`. Confirm a new revision
      reaches Ready. **Editing `apps/**` changes nothing in the browser until
      this runs** — the proxy at `127.0.0.1:8804` is a reverse proxy to Cloud
      Run, not a local static server.
- [ ] **Step 3:** In the browser, fetch the export with `{cache: "reload"}` and
      confirm the served copy carries the cards. Verifying the file on disk
      proves nothing about what the browser runs.
- [ ] **Step 4:** Verify the value page renders all three bands, that the leak
      counts match the catalog, and that no currency figure appears.
- [ ] **Step 5:** Verify a card on P1 (5 of 7) and on P4 (0 of 6) — the two ends
      of the coverage range.
- [ ] **Step 6:** Record measured character counts and heading lists in
      a progress ledger, as was done for P6. Commit.
