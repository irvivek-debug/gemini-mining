# Persona workspace and plain language — implementation plan

> **For agentic workers:** implement this plan task-by-task, in order. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the workbench screen with a persona page whose left panel states what is true now from the record and whose right-hand sidecar streams a real conversation with that persona's own deployed agents, and rewrite the copy across all ten screens into plain language with the technical detail behind one collapsible per screen.

**Architecture:** Three pure browser modules (`plain.js` vocabulary, `router.js` agent selection, `persona-data.js` derivations) are written and tested first with `node --test`, because everything else consumes them. One new FastAPI route, `GET /api/stream/{agent_id}`, relays the agent container's `text/event-stream` unchanged so the browser's built-in `EventSource` can read it. The new screen and the copy rewrite are then built on top. No build step, no framework, no new dependency.

**Tech Stack:** Vanilla ES2020 in classic `<script>` tags; Node v24.15.0 `node --test` for the JS tests; FastAPI + httpx + `pytest` for the route; CSS custom properties already defined in `apps/shared/tokens.css`.

**Source spec:** `docs/specs/2026-08-13-persona-workspace-design.md`. Section references below (§4.2, §5.1 …) point into it.

## Global Constraints

Every task's requirements implicitly include this section.

**Toolchain**
- No build step, no framework, no bundler, no package.json, no CDN, no new runtime dependency. If a task seems to need one, it is the wrong task.
- Python is `python3`. Node is `node` (v24.15.0). Both are on this machine already.
- Repo root: `.`. Branch: `feat/agents-phase-5`.
- Run pytest as `python3 -m pytest`.
- **Never `git push`.** Commit locally as often as the plan says; pushing requires explicit go-ahead that has not been given.

**Testable JS modules** end with exactly this dual export so a classic `<script>` tag and `require()` both work:
```js
if (typeof module !== "undefined") module.exports = { /* named exports */ };
```
Declare anything another browser script must see with `function name() {}` (function declarations become properties of `window`; `const` at top level of a classic script does not).

**Truthfulness of numbers**
- Every number on screen comes from `apps/shared/data/bundle.js` (`window.MINING_DATA`) or is marked `[CLIENT INPUT REQUIRED]`. No number is typed into markup or JS.
- Ordinary-day → best-day figures come from `DATA.signals.gap.rows` **only**. Never compute a percentile from `signals.branch_evidence[Bx].points` — those are 64 bucket means and a percentile over them is not a percentile over the days (§4.2).
- `caption`, `method`, `caveat` and `excluded` strings render **verbatim**.
- Commodity-neutral: the copy says "contained metal". It never names a metal.
- Money is expressed as ranges. `DATA.facts.mill_downtime_usd_per_hour` (145000) is the only monetary figure the repository establishes; anything else is `[CLIENT INPUT REQUIRED]`.
- The catalogue holds **100 agents of which 52 are externally callable entrypoints**. Copy never says "100 agents you can talk to".

**Data shape hazards**
- `value_branch` is a string on P1–P3 and P5–P8 and a **list** on P4 (`["supply_chain","procurement"]`). Every read goes through `branchesOf()`.
- `source_tables` entries carry the `mining_data.` prefix (`"mining_data.telemetry_stream"`). The `plain.js` table map is keyed on the **bare** name; lookups strip the prefix and any backticks.
- P8 (Shift Supervisor) has exactly **one** agent and appears in **no** branch's `personas` list. Every function must return a defined, sensible result for P8, and the UI must not offer a "change agent" control with nothing to change to.
- P2, P3, P4 and P7 reach **zero** gap rows under the §4.2 rule. That is a fact about the catalogue, and the screen says so plainly.

**Copy rules (§6, §7)**
- Plain language and tables first; one `<details class="tbl">` titled **"Technical detail"**, closed by default, at the end of each screen holding agent ids, APQC codes, model tiers, table names, tool names, pattern letters and screen codes.
- Jargon substitutions, applied everywhere in body copy: entrypoint → "agent you can talk to"; HITL / human-in-the-loop → "needs your sign-off"; swarm → "agent team"; traversal → "connection trace"; Pattern A / Pattern B → "team agent" / "specialist agent"; value branch → "where the money is"; APQC code → "standard process area" (the code itself goes in the drawer); provenance → "where this came from"; p90 → "the best day"; median → "the ordinary day"; node / edge → "machine" / "link"; blast radius → "what else stops"; model tier / reasoning / flash → drawer only; SC-1 … SC-4 → removed from headings.

**Accessibility**
- Interactive controls are at least 44px in their smallest dimension.
- Every focusable control has a visible `:focus-visible` style.
- No content is reachable only by hover.
- Any animation is wrapped in `@media (prefers-reduced-motion: no-preference)`.
- Layouts work at 390px and at 1440px.

**Gates that must stay green**
- `tests/test_workspace_image.py` — the workspace container must still import with `google.adk` and `google.cloud.aiplatform` blocked, and must still report 52 entrypoints.
- The whole existing suite: `python -m pytest` from the repo root.

**Deviations from the spec, resolved here** (both are noted so a reviewer does not read them as drift):
1. §4.6 lists `starterQuestionsFor` in `persona-data.js`. It is implemented in `router.js` instead, because the guarantee that a starter routes back to the agent it came from (§5.1) requires calling `route()`, and putting it in `persona-data.js` would make that module depend on the router. The §9 assertion "`starterQuestionsFor` returns 3 questions for every persona" therefore lives in `tests/js/router.test.js`.
2. §5.3 shows the failure line abbreviated as *"Couldn't trace what else stops — that lookup failed."* The implementation composes from the §6 map verbatim and so produces *"Couldn't trace what else stops if this stops — that lookup failed."* The §6 map is authoritative; the §5.3 string was illustrative.

---

## File Structure

**New — browser modules**

| Path | Responsibility |
|---|---|
| `apps/shared/plain.js` | The vocabulary map: tool, traversal and table ids → plain phrases; jargon substitutions; composition of one activity-log line from one SSE part. Pure. No DOM. |
| `apps/workspace/router.js` | `route()` — pick one of a persona's agents for a question, with a reason and runners-up. `starterQuestions()` — three derived cold-start questions per persona. Pure. No DOM. |
| `apps/workspace/persona-data.js` | The four derivations behind the left panel: branch normaliser, branch codes, branch evidence, gap-row split. Pure. No DOM. Takes `DATA` as an argument. |
| `apps/workspace/agent-stream.js` | `EventSource` lifecycle for `/api/stream/{id}`: open, per-event callback, terminal event, abort. No DOM. |
| `apps/workspace/persona-panel.js` | Renders the five left-hand blocks. Calls `persona-data.js`; holds no rule of its own. |
| `apps/workspace/chat.js` | The sidecar: transcript, composer, router pick with visible reason, one-click change, activity log. |
| `apps/workspace/persona.js` | Page controller: persona selection, layout, live `/api/runtime`. |
| `apps/workspace/persona.html` | Markup and script tags only. |

**New — tests**

| Path | Runner | Task |
|---|---|---|
| `tests/js/plain.test.js` | `node --test` | 1 |
| `tests/js/router.test.js` | `node --test` | 2 |
| `tests/js/persona-data.test.js` | `node --test` | 3 |
| `tests/test_stream_route.py` | `pytest` | 4 |
| `tests/test_shared_drawer.py` | `pytest` | 5 |
| `tests/js/agent-stream.test.js` | `node --test` | 6 |
| `tests/test_persona_page.py` | `pytest` | 7 |
| `tests/js/chat.test.js` | `node --test` | 8 |
| `tests/test_runtime_honesty.py` | `pytest` | 9 |
| `tests/test_screen_copy.py` | `pytest` | 10 (red for the workspace screens until 11) |

**Modified**

| Path | Change |
|---|---|
| `apps/workspace/server.py` | `+ GET /api/stream/{agent_id}` |
| `apps/shared/app.css` | `+ details.tbl` component (moved out of `workspace.css`) |
| `apps/workspace/workspace.css` | `− details.tbl` base rules, `+` persona page and sidecar rules |
| `apps/shared/shell.js` | `WORK_NAV`: `workbench.html / "Workbench"` → `persona.html / "My role"` |
| `apps/workspace/workspace.js` | `notConnected()` reads the wire, not the build-time constant |
| `apps/workspace/handover.js` | `+` Run button and streamed brief; the four sections stop claiming NOT CONNECTED |
| `apps/index.html`, `apps/case/*.html` + `*.js`, `apps/workspace/index.html`, `apps/workspace/swarm.html`, `apps/workspace/handover.html` | Copy rewrite + technical drawer |

**Deleted:** `apps/workspace/workbench.html`, `apps/workspace/workbench.js`.

**Dependency order.** `plain.js` has no dependencies. `router.js` depends on `plain.js`. `persona-data.js` depends on nothing (the router dependency was removed by putting `starterQuestions` in `router.js`). `agent-stream.js` depends on nothing. `persona-panel.js` depends on `persona-data.js` and `plain.js`. `chat.js` depends on `router.js`, `agent-stream.js` and `plain.js`. Tasks are ordered to match.

---

## Task 1: `apps/shared/plain.js` — the vocabulary map

The hinge of the whole design (§6). One map serves the live activity log and the copy rewrite, so a screen and a stream can never disagree about what `graph_traverse` means.

**Files:**
- Create: `apps/shared/plain.js`
- Create: `tests/js/plain.test.js`

**Interfaces:**
- Consumes: nothing.
- Produces (all as `function` declarations, all exported):
  - `bareTable(id) -> string` — strips `mining_data.` and backticks: `` "`mining_data.telemetry_stream`" `` → `"telemetry_stream"`
  - `plainTable(id) -> string` — `"telemetry_stream"` → `"sensor readings"`; unknown → the bare id
  - `plainTool(id) -> string` — `"bq_query"` → `"looking up records"`; unknown → the raw id
  - `plainTraversal(id) -> string` — `"blast_radius"` → `"what else stops if this stops"`; unknown → the raw id
  - `plainJargon(term) -> string` — `"entrypoint"` → `"agent you can talk to"`; unknown → the raw term
  - `tableFromSql(sql) -> string` — first `mining_data.<name>` found, bare; `""` if none
  - `callLine(name, args) -> string` — one activity-log line for a `functionCall`
  - `failLine(name, args) -> string` — the line for a `functionResponse` whose `response.success === false`
  - `unmapped(DATA) -> { tables: string[], tools: string[], traversals: string[] }`
  - `TOOLS`, `TRAVERSALS`, `TABLES`, `JARGON` — the raw maps, for the copy rewrite

- [ ] **Step 1: Write the failing test**

Create `tests/js/plain.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const P = require("../../apps/shared/plain.js");

// The bundle is a browser file: `window.MINING_DATA = {...};`. Node has no
// window, so the object is cut out and parsed rather than required.
function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

test("bareTable strips the dataset prefix and backticks", () => {
  assert.equal(P.bareTable("mining_data.telemetry_stream"), "telemetry_stream");
  assert.equal(P.bareTable("`mining_data.telemetry_stream`"), "telemetry_stream");
  assert.equal(P.bareTable("telemetry_stream"), "telemetry_stream");
});

test("the map covers every tool, traversal and table in the catalogue", () => {
  const missing = P.unmapped(loadData());
  assert.deepEqual(missing, { tables: [], tools: [], traversals: [] });
});

test("a bq_query naming a table composes verb plus noun", () => {
  const line = P.callLine("bq_query", {
    sql: "SELECT * FROM `mining_data.telemetry_stream` LIMIT 10",
  });
  assert.equal(line, "Reading the sensor readings");
});

test("a graph_traverse names the traversal it runs", () => {
  assert.equal(
    P.callLine("graph_traverse", { traversal: "blast_radius" }),
    "Tracing what else stops if this stops"
  );
});

test("a call with no recognisable noun degrades to the tool verb alone", () => {
  assert.equal(P.callLine("operational_math", { expression: "1+1" }),
    "Working out the numbers");
  assert.equal(P.callLine("bq_query", {}), "Looking up records");
});

test("an unknown id renders its raw value rather than a guess", () => {
  assert.equal(P.plainTable("no_such_table"), "no_such_table");
  assert.equal(P.plainTool("no_such_tool"), "no_such_tool");
  assert.equal(P.plainTraversal("no_such_traversal"), "no_such_traversal");
  assert.equal(P.callLine("no_such_tool", {}), "no_such_tool");
});

test("a failed response names what failed", () => {
  assert.equal(
    P.failLine("graph_traverse", { traversal: "blast_radius" }),
    "Couldn't trace what else stops if this stops — that lookup failed."
  );
  assert.equal(
    P.failLine("bq_query", { sql: "SELECT 1 FROM `mining_data.assets`" }),
    "Couldn't read the machine register — that lookup failed."
  );
});

test("tableFromSql finds the first qualified table and nothing else", () => {
  assert.equal(
    P.tableFromSql("SELECT a FROM `mining_data.assets` JOIN `mining_data.maintenance_logs`"),
    "assets"
  );
  assert.equal(P.tableFromSql("SELECT 1"), "");
  assert.equal(P.tableFromSql(undefined), "");
});

test("jargon substitutions are available to the copy rewrite", () => {
  assert.equal(P.plainJargon("entrypoint"), "agent you can talk to");
  assert.equal(P.plainJargon("blast radius"), "what else stops");
  assert.equal(P.plainJargon("not a jargon term"), "not a jargon term");
});
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd . && node --test tests/js/plain.test.js`
Expected: FAIL — `Cannot find module '../../apps/shared/plain.js'`.

- [ ] **Step 3: Write the implementation**

Create `apps/shared/plain.js`:

```js
/* One vocabulary, two consumers.
 *
 * The live activity log (chat.js) and the static copy (every screen) both name
 * the same machinery. A screen that calls graph_traverse "a connection trace"
 * while the stream calls it "a traversal" would be worse than either alone, so
 * both read this file.
 *
 * Nothing here guesses. An id absent from a map renders as itself, and
 * unmapped() exists so a test can prove the maps still cover the catalogue as
 * the catalogue grows.
 */

/* The noun phrase for a tool, used in prose. */
var TOOLS = {
  bq_query: "looking up records",
  bqml_predict: "running a prediction",
  graph_traverse: "tracing connections",
  operational_math: "working out the numbers",
  request_approval: "asking for your sign-off",
};

/* The present-participle headline for a tool, used in the activity log where a
 * line reads as something happening now. */
var TOOL_DOING = {
  bq_query: "Looking up records",
  bqml_predict: "Running a prediction",
  graph_traverse: "Tracing connections",
  operational_math: "Working out the numbers",
  request_approval: "Asking for your sign-off",
};

/* The verb for the composed form, "Reading the sensor readings". Only the two
 * tools that take a noun need one. */
var TOOL_VERB = { bq_query: "Reading the", graph_traverse: "Tracing" };
var TOOL_FAILED = { bq_query: "Couldn't read the", graph_traverse: "Couldn't trace" };

var TRAVERSALS = {
  blast_radius: "what else stops if this stops",
  fatigue_to_incident: "how crew fatigue connects to incidents",
  stockout_exposure: "what runs out if this part runs out",
};

var TABLES = {
  asset_dependencies: "which machines depend on which",
  assets: "the machine register",
  bid_parts_edge: "which parts each supplier quoted",
  biometric_fatigue_logs: "crew fatigue readings",
  crusher_states: "crusher run states",
  drill_assay_logs: "drill sample assays",
  drill_holes: "drill hole records",
  erp_work_orders: "work orders in the ERP",
  fatigue_logs_node: "crew fatigue records",
  fleet_vehicles: "the truck and loader fleet",
  geological_block_models: "the ore body block model",
  haulage_routes: "haul routes",
  incident_involvements: "who was involved in each incident",
  inventory_levels: "parts on hand",
  maintenance_logs: "maintenance history",
  metallurgical_recovery: "plant recovery records",
  operator_vehicle_assignments: "who drove what",
  operators_node: "the operator roster",
  procurement_bids: "supplier bids",
  radio_communications: "radio traffic",
  rfp_items: "items out to tender",
  safety_incidents: "safety incidents",
  simulation_runs: "scenario simulation runs",
  telemetry_stream: "sensor readings",
  work_order_parts_edge: "parts each work order needs",
};

/* Used by the copy rewrite. Keys are lowercased as they appear on screen. */
var JARGON = {
  entrypoint: "agent you can talk to",
  hitl: "needs your sign-off",
  "human-in-the-loop": "needs your sign-off",
  swarm: "agent team",
  traversal: "connection trace",
  "pattern a": "team agent",
  "pattern b": "specialist agent",
  "value branch": "where the money is",
  "apqc code": "standard process area",
  provenance: "where this came from",
  p90: "the best day",
  median: "the ordinary day",
  node: "machine",
  edge: "link",
  "blast radius": "what else stops",
};

function bareTable(id) {
  if (!id) return "";
  return String(id).replace(/`/g, "").replace(/^mining_data\./, "");
}

function plainTable(id) {
  var bare = bareTable(id);
  return TABLES[bare] || bare;
}

function plainTool(id) {
  return TOOLS[id] || String(id || "");
}

function plainTraversal(id) {
  return TRAVERSALS[id] || String(id || "");
}

function plainJargon(term) {
  var key = String(term || "").toLowerCase();
  return JARGON[key] || String(term || "");
}

/* The observed bq_query argument is a literal SELECT naming its table in
 * backticks. Only the first qualified name is taken: a join names two, and the
 * first is the one the query is about. */
function tableFromSql(sql) {
  var found = /mining_data\.([a-z0-9_]+)/i.exec(String(sql || ""));
  return found ? found[1] : "";
}

/* The noun a call is about, if the arguments carry one. Any string argument may
 * hold the SQL, and any argument may name a traversal, because the argument
 * names differ by tool and guessing a key is how this breaks silently. */
function _noun(name, args) {
  var values = Object.keys(args || {}).map(function (k) { return args[k]; });
  var i;
  if (name === "bq_query") {
    for (i = 0; i < values.length; i++) {
      var table = tableFromSql(values[i]);
      if (table) return { kind: "table", plain: plainTable(table) };
    }
  }
  for (i = 0; i < values.length; i++) {
    if (typeof values[i] === "string" && TRAVERSALS[values[i]]) {
      return { kind: "traversal", plain: TRAVERSALS[values[i]] };
    }
  }
  return null;
}

function callLine(name, args) {
  var noun = _noun(name, args);
  if (noun && TOOL_VERB[name]) return TOOL_VERB[name] + " " + noun.plain;
  return TOOL_DOING[name] || String(name || "");
}

function failLine(name, args) {
  var noun = _noun(name, args);
  var head = noun && TOOL_FAILED[name]
    ? TOOL_FAILED[name] + " " + noun.plain
    : "Couldn't finish " + (TOOLS[name] || String(name || ""));
  return head + " — that lookup failed.";
}

/* The honesty check. Every tool, traversal and table the catalogue declares
 * must have a plain phrase, or the activity log will print an identifier at a
 * reader who came here to avoid identifiers. */
function unmapped(DATA) {
  var tables = {}, tools = {}, traversals = {};
  (DATA.catalog.agents || []).forEach(function (agent) {
    (agent.source_tables || []).forEach(function (t) {
      var bare = bareTable(t);
      if (!TABLES[bare]) tables[bare] = true;
    });
    (agent.tools || []).forEach(function (t) { if (!TOOLS[t]) tools[t] = true; });
    (agent.traversals || []).forEach(function (t) {
      if (!TRAVERSALS[t]) traversals[t] = true;
    });
  });
  return {
    tables: Object.keys(tables).sort(),
    tools: Object.keys(tools).sort(),
    traversals: Object.keys(traversals).sort(),
  };
}

if (typeof module !== "undefined") {
  module.exports = {
    TOOLS, TRAVERSALS, TABLES, JARGON,
    bareTable, plainTable, plainTool, plainTraversal, plainJargon,
    tableFromSql, callLine, failLine, unmapped,
  };
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `cd . && node --test tests/js/plain.test.js`
Expected: PASS, 9 tests.

If `unmapped` is non-empty, **do not edit the test to match**. Add the missing id to the map with a plain phrase written in the same register as its neighbours, or report it: a table in the catalogue with no plain name is a real gap.

- [ ] **Step 5: Commit**

```bash
cd .
git add apps/shared/plain.js tests/js/plain.test.js
git commit -m "feat(apps): name the machinery in one place, in plain words"
```

---

## Task 2: `apps/workspace/router.js` — pick an agent, say why

**Files:**
- Create: `apps/workspace/router.js`
- Create: `tests/js/router.test.js`

**Interfaces:**
- Consumes: `apps/shared/plain.js` — `TABLES`, `TRAVERSALS`, `TOOLS`, `bareTable`, `plainTable`, `plainTraversal`, `plainTool`.
- Produces:
  - `route(question, personaCode, DATA) -> { agent_id, reason, runners_up: [{agent_id, score}] }`
  - `starterQuestions(personaCode, DATA) -> string[]` — exactly 3
  - `branchesOf(x) -> string[]` — also exported from `persona-data.js` in Task 3; **`router.js` is the definition and `persona-data.js` re-implements nothing**, it requires this one.

Candidates are **only** `DATA.personas.personas[personaCode].agents`. A question asked from the Reliability Engineer's page must never route to a procurement agent — the persona page is a claim about scope, and silently leaving scope breaks it (§5.1).

- [ ] **Step 1: Write the failing test**

Create `tests/js/router.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const R = require("../../apps/workspace/router.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();
const CODES = Object.keys(DATA.personas.personas).sort();

test("there are eight personas, so the table-driven tests below cover them all", () => {
  assert.deepEqual(CODES, ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]);
});

test("branchesOf normalises a bare string and a list alike", () => {
  assert.deepEqual(R.branchesOf("asset_reliability"), ["asset_reliability"]);
  assert.deepEqual(R.branchesOf(["supply_chain", "procurement"]),
    ["supply_chain", "procurement"]);
  assert.deepEqual(R.branchesOf(undefined), []);
});

test("every persona's routing stays inside that persona's own agents", () => {
  const questions = [
    "Which assets are most at risk right now?",
    "What runs out if this part runs out?",
    "Show me crew fatigue against incidents",
    "How is recovery tracking against the ordinary day?",
    "What should I sign off before the shift ends?",
  ];
  for (const code of CODES) {
    const allowed = new Set(DATA.personas.personas[code].agents);
    for (const q of questions) {
      const pick = R.route(q, code, DATA);
      assert.ok(allowed.has(pick.agent_id),
        `${code} routed "${q}" to ${pick.agent_id}, which is not one of its agents`);
      assert.ok(pick.reason.length > 0, `${code} gave no reason for "${q}"`);
      for (const up of pick.runners_up) {
        assert.ok(allowed.has(up.agent_id));
        assert.notEqual(up.agent_id, pick.agent_id);
      }
    }
  }
});

test("P8 has one agent, so it names it and offers nothing to change to", () => {
  assert.deepEqual(DATA.personas.personas.P8.agents, ["S12"]);
  const pick = R.route("What happened on the last shift?", "P8", DATA);
  assert.equal(pick.agent_id, "S12");
  assert.ok(pick.reason.length > 0);
  assert.deepEqual(pick.runners_up, []);
});

test("P4's list-valued value_branch does not throw", () => {
  assert.deepEqual(DATA.personas.personas.P4.value_branch,
    ["supply_chain", "procurement"]);
  const pick = R.route("Which suppliers quoted for this part?", "P4", DATA);
  assert.ok(DATA.personas.personas.P4.agents.includes(pick.agent_id));
});

test("a question of pure stop-words still returns a valid agent", () => {
  for (const code of CODES) {
    const pick = R.route("the and of a to is it", code, DATA);
    assert.ok(DATA.personas.personas[code].agents.includes(pick.agent_id));
    assert.ok(pick.reason.length > 0);
  }
});

test("an empty question returns a valid agent", () => {
  const pick = R.route("", "P1", DATA);
  assert.ok(DATA.personas.personas.P1.agents.includes(pick.agent_id));
});

test("identical inputs give identical output", () => {
  const a = R.route("Which assets are most at risk right now?", "P1", DATA);
  const b = R.route("Which assets are most at risk right now?", "P1", DATA);
  assert.deepEqual(a, b);
});

test("every persona gets exactly three starter questions", () => {
  for (const code of CODES) {
    const starters = R.starterQuestions(code, DATA);
    assert.equal(starters.length, 3, `${code} produced ${starters.length}`);
    assert.equal(new Set(starters).size, 3, `${code} repeated a starter`);
    for (const q of starters) assert.ok(q.trim().length > 0);
  }
});

test("a starter always routes to the agent it was derived from", () => {
  for (const code of CODES) {
    for (const q of R.starterQuestions(code, DATA)) {
      const pick = R.route(q, code, DATA);
      assert.ok(DATA.personas.personas[code].agents.includes(pick.agent_id),
        `${code}: starter "${q}" routed outside the persona`);
    }
  }
});

test("a starter never names a capability its agent does not have", () => {
  const P = require("../../apps/shared/plain.js");
  for (const code of CODES) {
    for (const q of R.starterQuestions(code, DATA)) {
      const pick = R.route(q, code, DATA);
      const agent = DATA.catalog.agents.find((a) => a.agent_id === pick.agent_id);
      const owned = new Set(
        (agent.source_tables || []).map((t) => P.plainTable(t))
          .concat((agent.traversals || []).map((t) => P.plainTraversal(t)))
          .concat((agent.tools || []).map((t) => P.plainTool(t)))
      );
      const phrases = Object.values(P.TABLES)
        .concat(Object.values(P.TRAVERSALS))
        .concat(Object.values(P.TOOLS));
      for (const phrase of phrases) {
        if (q.toLowerCase().includes(phrase.toLowerCase())) {
          assert.ok(owned.has(phrase),
            `${code}: starter "${q}" names "${phrase}", which ${pick.agent_id} does not have`);
        }
      }
    }
  }
});
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd . && node --test tests/js/router.test.js`
Expected: FAIL — `Cannot find module '../../apps/workspace/router.js'`.

- [ ] **Step 3: Write the implementation**

Create `apps/workspace/router.js`:

```js
/* Which of this persona's agents should take this question, and why.
 *
 * Deterministic string matching over catalogue metadata, not comprehension. It
 * will sometimes be wrong, which is why route() returns the reason and the
 * runners-up: being wrong in the open with a one-click fix is the recovery
 * path, and a hidden wrong decision is not.
 *
 * The candidate set is the persona's own agents and nothing else. The persona
 * page is a claim about scope; a router that quietly left scope would make the
 * page a lie.
 */
var PLAIN = typeof require !== "undefined"
  ? require("../shared/plain.js")
  : window;

/* A traversal match is the strongest signal — three traversals exist across the
 * whole catalogue, so naming one is nearly an address. A table match is next: 25
 * tables, still specific. A tool match is weakest: five tools, shared widely. */
var WEIGHT = { traversal: 4, table: 3, apqc: 2, name: 2, tool: 1 };

var STOP = new Set((
  "a an and are as at be by can could did do does for from get give had has have how i " +
  "if in into is it its me my of on or our right should show so tell that the their them " +
  "then there these they this to us was we what when where which who why will with would you your now"
).split(" "));

function branchesOf(x) {
  if (!x) return [];
  return Array.isArray(x) ? x.slice() : [x];
}

function tokens(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(function (t) { return t && !STOP.has(t); });
}

/* Every phrase this agent answers to, with the weight of naming it. */
function termsFor(agent) {
  var terms = [];
  (agent.traversals || []).forEach(function (t) {
    terms.push({ kind: "traversal", id: t, plain: PLAIN.plainTraversal(t),
                 weight: WEIGHT.traversal });
  });
  (agent.source_tables || []).forEach(function (t) {
    var bare = PLAIN.bareTable(t);
    terms.push({ kind: "table", id: bare, plain: PLAIN.plainTable(t),
                 weight: WEIGHT.table });
  });
  (agent.apqc_names || []).forEach(function (n) {
    terms.push({ kind: "apqc", id: n, plain: n, weight: WEIGHT.apqc });
  });
  terms.push({ kind: "name", id: agent.agent_id, plain: agent.display_name || "",
               weight: WEIGHT.name });
  (agent.tools || []).forEach(function (t) {
    terms.push({ kind: "tool", id: t, plain: PLAIN.plainTool(t), weight: WEIGHT.tool });
  });
  branchesOf(agent.value_branch).forEach(function (b) {
    terms.push({ kind: "tool", id: b, plain: b.replace(/_/g, " "), weight: WEIGHT.tool });
  });
  return terms;
}

/* A term scores when the question shares a content word with it. Score is the
 * term's weight times the number of distinct shared words, so "crew fatigue
 * readings" beats "fatigue records" on a question that says both. */
function scoreAgent(qTokens, agent) {
  var asked = new Set(qTokens);
  var total = 0;
  var best = null;
  var matched = [];
  termsFor(agent).forEach(function (term) {
    var hits = 0;
    tokens(term.plain).concat(tokens(term.id)).forEach(function (word) {
      if (asked.has(word)) { hits += 1; asked.delete(word); }
    });
    if (!hits) return;
    var points = term.weight * hits;
    total += points;
    matched.push({ term: term, points: points });
    if (!best || points > best.points) best = { term: term, points: points };
  });
  matched.sort(function (a, b) { return b.points - a.points; });
  return { score: total, best: best, matched: matched };
}

/* Total and stable: ties break toward the swarm coordinator, then toward the
 * lowest agent id, so a question of pure stop-words still names an agent. */
function _better(a, b) {
  if (a.score !== b.score) return a.score > b.score;
  var aCoord = a.agent.swarm_role === "coordinator";
  var bCoord = b.agent.swarm_role === "coordinator";
  if (aCoord !== bCoord) return aCoord;
  return a.agent.agent_id < b.agent.agent_id;
}

function _reason(scored, agent) {
  if (!scored.matched.length) {
    return "Nothing in the question named a capability, so it goes to " +
      (agent.display_name || agent.agent_id) + ", the agent this role leads with.";
  }
  var phrases = scored.matched.slice(0, 2).map(function (m) {
    if (m.term.kind === "table") return "reads " + m.term.plain;
    if (m.term.kind === "traversal") return "traces " + m.term.plain;
    if (m.term.kind === "tool") return m.term.plain;
    return "covers " + m.term.plain.toLowerCase();
  });
  return "It " + phrases.join(" and ") + ".";
}

function route(question, personaCode, DATA) {
  var persona = DATA.personas.personas[personaCode];
  var byId = {};
  DATA.catalog.agents.forEach(function (a) { byId[a.agent_id] = a; });
  var candidates = (persona.agents || [])
    .map(function (id) { return byId[id]; })
    .filter(Boolean);

  var qTokens = tokens(question);
  var scored = candidates.map(function (agent) {
    var s = scoreAgent(qTokens, agent);
    return { agent: agent, score: s.score, detail: s };
  });

  var winner = scored[0];
  scored.forEach(function (row) { if (_better(row, winner)) winner = row; });

  var runners = scored
    .filter(function (r) { return r.agent.agent_id !== winner.agent.agent_id && r.score > 0; })
    .sort(function (a, b) {
      return b.score - a.score || (a.agent.agent_id < b.agent.agent_id ? -1 : 1);
    })
    .slice(0, 3)
    .map(function (r) { return { agent_id: r.agent.agent_id, score: r.score }; });

  return {
    agent_id: winner.agent.agent_id,
    reason: _reason(winner.detail, winner.agent),
    runners_up: runners,
  };
}

/* Cold start. No example questions exist anywhere in the catalogue, so these are
 * derived rather than authored: each is built from one capability an agent
 * actually declares, and then checked by routing it back. A starter that did not
 * route to the agent it came from would teach the reader the wrong thing about
 * what the page does, so it is discarded rather than shipped. */
function _candidateQuestions(agent) {
  var out = [];
  (agent.traversals || []).forEach(function (t) {
    out.push({ agent: agent, q: "Show me " + PLAIN.plainTraversal(t) + "." });
  });
  (agent.source_tables || []).forEach(function (t) {
    out.push({ agent: agent, q: "What do " + PLAIN.plainTable(t) + " show right now?" });
  });
  return out;
}

function starterQuestions(personaCode, DATA) {
  var persona = DATA.personas.personas[personaCode];
  var byId = {};
  DATA.catalog.agents.forEach(function (a) { byId[a.agent_id] = a; });
  var agents = (persona.agents || []).map(function (id) { return byId[id]; }).filter(Boolean);

  // Round-robin over the agents so three starters do not all come from one.
  var pools = agents.map(_candidateQuestions);
  var queue = [];
  for (var depth = 0; depth < 30; depth++) {
    pools.forEach(function (pool) { if (pool[depth]) queue.push(pool[depth]); });
  }

  var chosen = [];
  var seen = {};
  queue.forEach(function (item) {
    if (chosen.length >= 3 || seen[item.q]) return;
    if (route(item.q, personaCode, DATA).agent_id !== item.agent.agent_id) return;
    seen[item.q] = true;
    chosen.push(item.q);
  });

  // Backstop, for a persona whose agents share every capability: a question that
  // names no capability at all routes to the persona's lead agent by the same
  // tie-break every empty question uses, so it is honest by construction.
  var generic = [
    "What should I look at first?",
    "What changed since yesterday?",
    "What needs my attention?",
  ];
  generic.forEach(function (q) {
    if (chosen.length >= 3 || seen[q]) return;
    seen[q] = true;
    chosen.push(q);
  });
  return chosen.slice(0, 3);
}

if (typeof module !== "undefined") {
  module.exports = { route, starterQuestions, branchesOf, tokens, scoreAgent };
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `cd . && node --test tests/js/router.test.js`
Expected: PASS, 11 tests.

If "a starter never names a capability its agent does not have" fails, the round-trip filter is admitting a question whose phrase belongs to a sibling agent. Tighten `_candidateQuestions` to skip capabilities shared by more than one of the persona's agents — do not relax the assertion.

- [ ] **Step 5: Commit**

```bash
cd .
git add apps/workspace/router.js tests/js/router.test.js
git commit -m "feat(workspace): route a question to one of the role's own agents, in the open"
```

---

## Task 3: `apps/workspace/persona-data.js` — the left panel's derivations

Blocks 2a and 2b are two derivation rules with an edge case in almost every persona (§4.6). They live in one pure module so a test can drive them directly rather than through the DOM.

**Files:**
- Create: `apps/workspace/persona-data.js`
- Create: `tests/js/persona-data.test.js`

**Interfaces:**
- Consumes: `apps/workspace/router.js` — `branchesOf`. (`persona-data.js` re-exports it for `persona-panel.js`'s convenience; it does not re-implement it.)
- Produces:
  - `branchesOf(x) -> string[]`
  - `branchCodesFor(personaCode, DATA) -> string[]` — reverse lookup through `DATA.value_tree.branches[Bx].personas`
  - `branchEvidenceFor(personaCode, DATA) -> [{ code, branch, evidence }]` — `evidence.kind ∈ {series, distribution, share}`
  - `gapRowsFor(personaCode, DATA) -> { reached: row[], other: row[] }` — the §4.2 source-table rule

**The rule that governs `gapRowsFor` (§4.2):** a gap row belongs to a persona when **at least one of that persona's agents declares the row's `source` table in its `source_tables`**. Gap rows carry no branch or persona field, so any other mapping would be invention. `reached ∪ other` is always all four rows and the two are disjoint.

**Expected results, computed against the live catalogue** — the test asserts these exactly:

| Persona | reached |
|---|---|
| P1 | `feed_rate`, `payload`, `conveyor_load` |
| P2 | *(none)* |
| P3 | *(none)* |
| P4 | *(none)* |
| P5 | `recovery` |
| P6 | all four |
| P7 | *(none)* |
| P8 | all four |

- [ ] **Step 1: Write the failing test**

Create `tests/js/persona-data.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const D = require("../../apps/workspace/persona-data.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();
const CODES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"];

test("branchesOf normalises both shapes value_branch takes", () => {
  assert.deepEqual(D.branchesOf(DATA.personas.personas.P1.value_branch),
    ["asset_reliability"]);
  assert.deepEqual(D.branchesOf(DATA.personas.personas.P4.value_branch),
    ["supply_chain", "procurement"]);
});

test("every persona gets a defined branch-evidence result", () => {
  for (const code of CODES) {
    const rows = D.branchEvidenceFor(code, DATA);
    assert.ok(Array.isArray(rows), `${code} returned a non-array`);
  }
});

test("seven personas have branch evidence and P8 has none", () => {
  const withEvidence = CODES.filter((c) => D.branchEvidenceFor(c, DATA).length > 0);
  assert.deepEqual(withEvidence, ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]);
  assert.deepEqual(D.branchEvidenceFor("P8", DATA), []);
});

test("every evidence declares a kind, and carries that kind's fields", () => {
  for (const code of CODES) {
    for (const row of D.branchEvidenceFor(code, DATA)) {
      assert.ok(row.code && row.branch && row.evidence, `${code} returned a partial row`);
      const e = row.evidence;
      assert.ok(["series", "distribution", "share"].includes(e.kind),
        `${code}/${row.code} has kind ${e.kind}`);
      if (e.kind === "series") {
        for (const f of ["points", "min", "max", "readings"]) {
          assert.ok(e[f] !== undefined, `${row.code} series is missing ${f}`);
        }
      } else if (e.kind === "distribution") {
        for (const f of ["bins", "edges", "n"]) {
          assert.ok(e[f] !== undefined, `${row.code} distribution is missing ${f}`);
        }
      } else {
        for (const f of ["part", "whole"]) {
          assert.ok(e[f] !== undefined, `${row.code} share is missing ${f}`);
        }
      }
      assert.ok(typeof e.caption === "string" && e.caption.length > 0,
        `${row.code} has no caption, and the caption must render verbatim`);
    }
  }
});

test("gapRowsFor reproduces the source-table rule exactly", () => {
  const expected = {
    P1: ["feed_rate", "payload", "conveyor_load"],
    P2: [],
    P3: [],
    P4: [],
    P5: ["recovery"],
    P6: ["recovery", "feed_rate", "payload", "conveyor_load"],
    P7: [],
    P8: ["recovery", "feed_rate", "payload", "conveyor_load"],
  };
  for (const code of CODES) {
    const split = D.gapRowsFor(code, DATA);
    assert.deepEqual(split.reached.map((r) => r.id).sort(), expected[code].slice().sort(),
      `${code} reached the wrong rows`);
  }
});

test("no gap row is dropped or double-counted, for any persona", () => {
  const all = DATA.signals.gap.rows.map((r) => r.id).sort();
  for (const code of CODES) {
    const split = D.gapRowsFor(code, DATA);
    const reached = split.reached.map((r) => r.id);
    const other = split.other.map((r) => r.id);
    assert.deepEqual(reached.concat(other).sort(), all, `${code} lost or repeated a row`);
    for (const id of reached) {
      assert.ok(!other.includes(id), `${code} put ${id} in both groups`);
    }
  }
});

test("an unknown persona code returns empty results rather than throwing", () => {
  assert.deepEqual(D.branchCodesFor("P99", DATA), []);
  assert.deepEqual(D.branchEvidenceFor("P99", DATA), []);
  const split = D.gapRowsFor("P99", DATA);
  assert.deepEqual(split.reached, []);
  assert.equal(split.other.length, DATA.signals.gap.rows.length);
});
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd . && node --test tests/js/persona-data.test.js`
Expected: FAIL — `Cannot find module '../../apps/workspace/persona-data.js'`.

- [ ] **Step 3: Write the implementation**

Create `apps/workspace/persona-data.js`:

```js
/* What the left panel may say about a role, derived rather than asserted.
 *
 * Two of the five blocks are derivation rules with an edge case in almost every
 * persona, and a rule that lives inside a render function is only testable
 * through the DOM. These take DATA as an argument, touch no globals and return
 * plain objects, so a test drives them directly.
 *
 * Nothing here invents a mapping. Where the record does not connect a persona to
 * a signal, these functions return an empty result and the panel says so.
 */
/* branchesOf is defined in router.js and is deliberately NOT redefined here.
 *
 * In the browser these are classic scripts sharing one global scope, so a second
 * `function branchesOf` in this file would overwrite the router's on window —
 * and a body of `return window.branchesOf(x)` would then call itself forever.
 * router.js is loaded before this file, so the name is already in scope; under
 * Node it arrives through require. */
var ROUTER = typeof require !== "undefined" ? require("./router.js") : null;
var _branchesOf = ROUTER ? ROUTER.branchesOf : branchesOf;

/* The one signal that maps to a persona from the data rather than from a guess:
 * each branch names its own personas, so the lookup is a reverse index over
 * value_tree, not an interpretation of the persona's value_branch string.
 *
 * value_tree.branches is a LIST of branch objects, each carrying its own `code`
 * and `title` — not a dictionary keyed B1..B6, which is what the shape of
 * signals.branch_evidence invites you to assume. Read as a dictionary it yields
 * the array indices "0".."5" and every lookup after it silently misses. */
function _branchList(DATA) {
  var branches = (DATA.value_tree && DATA.value_tree.branches) || [];
  return Array.isArray(branches)
    ? branches
    : Object.keys(branches).map(function (k) { return branches[k]; });
}

function branchCodesFor(personaCode, DATA) {
  return _branchList(DATA)
    .filter(function (branch) {
      return (branch.personas || []).indexOf(personaCode) !== -1;
    })
    .map(function (branch) { return branch.code; })
    .sort();
}

function branchEvidenceFor(personaCode, DATA) {
  var byCode = {};
  _branchList(DATA).forEach(function (branch) { byCode[branch.code] = branch; });
  var evidence = (DATA.signals && DATA.signals.branch_evidence) || {};
  return branchCodesFor(personaCode, DATA)
    .filter(function (code) { return evidence[code]; })
    .map(function (code) {
      return { code: code, branch: byCode[code], evidence: evidence[code] };
    });
}

/* Gap rows carry asset_id, column and source — no branch and no persona. A row
 * is this persona's when one of its agents declares the row's source table.
 * That is checkable against the catalogue, and it is the same field the router
 * scores on, so the page and the chat agree about what a role can see.
 *
 * Four of the eight personas reach nothing. The panel renders the remainder
 * under "Also recorded at this site" rather than promoting a site-wide row into
 * a personal one. */
function gapRowsFor(personaCode, DATA) {
  var persona = (DATA.personas && DATA.personas.personas &&
                 DATA.personas.personas[personaCode]) || null;
  var rows = (DATA.signals && DATA.signals.gap && DATA.signals.gap.rows) || [];
  if (!persona) return { reached: [], other: rows.slice() };

  var byId = {};
  (DATA.catalog.agents || []).forEach(function (a) { byId[a.agent_id] = a; });

  var readable = {};
  (persona.agents || []).forEach(function (id) {
    var agent = byId[id];
    if (!agent) return;
    (agent.source_tables || []).forEach(function (t) {
      readable[String(t).replace(/`/g, "").replace(/^mining_data\./, "")] = true;
    });
  });

  var reached = [];
  var other = [];
  rows.forEach(function (row) {
    var source = String(row.source || "").replace(/`/g, "").replace(/^mining_data\./, "");
    (readable[source] ? reached : other).push(row);
  });
  return { reached: reached, other: other };
}

if (typeof module !== "undefined") {
  module.exports = {
    branchesOf: _branchesOf, branchCodesFor, branchEvidenceFor, gapRowsFor,
  };
}
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `cd . && node --test tests/js/persona-data.test.js`
Expected: PASS, 7 tests.

If the `gapRowsFor` expectations do not match, **check `row.source` first** — it may or may not carry the `mining_data.` prefix, and the normaliser above handles both. Do not change the expected table without confirming against the catalogue; the numbers in it were computed from this data.

- [ ] **Step 5: Run every JS test together and commit**

```bash
cd .
node --test 'tests/js/*.test.js'
git add apps/workspace/persona-data.js tests/js/persona-data.test.js
git commit -m "feat(workspace): derive what a role may claim, instead of asserting it"
```

Expected: all three files pass, 27 tests.

---

## Task 4: `GET /api/stream/{agent_id}` — relay the agent's event stream

A real question against S01 took **103.8 seconds across 26 SSE events** (§5.2). A request/response spinner over that is indistinguishable from a hang, so the browser needs the events as they happen.

**Files:**
- Modify: `apps/workspace/server.py` (add `RUN_SSE_PATH`, `_agent_client()`, `GET /api/stream/{agent_id}`; route `/api/invoke` through `_agent_client()` too)
- Create: `tests/test_stream_route.py`

**Interfaces:**
- Consumes: the existing `_entrypoints()`, `_services()`, `_identity_token()`, `NotConnected`, `SESSION_PATH`.
- Produces:
  - `GET /api/stream/{agent_id}?prompt=…&user_id=…&session_id=…` → `StreamingResponse(media_type="text/event-stream")`
  - `_agent_client(base, token) -> httpx.AsyncClient` — the single place an agent-facing client is built, so a test can substitute a transport.
  - Two proxy-only SSE events the browser depends on:
    - `event: proxy-error` with `data: {"connected": false, "stage": …, "detail": …}` — a failure **after** the stream opened, which cannot change the status code
    - `event: proxy-done` with `data: {}` — sent once, after the upstream stream ends

**Why `GET`, not `POST`:** so the browser's built-in `EventSource` can read it and no streaming-fetch parser is needed (§5.2).

**Why `proxy-done` matters:** `EventSource` **automatically reconnects** when the connection closes. Without an explicit terminal event the client would silently re-ask the agent the same 100-second question, forever. The client closes the connection when it sees `proxy-done`.

**The request body to the agent is unchanged snake_case** — `{app_name, user_id, session_id, new_message, streaming}` — verified against the deployed S12 and S01. ADK's OpenAPI advertises camelCase and the model accepts both; keeping snake_case stops the two routes disagreeing.

- [ ] **Step 1: Write the failing test**

Create `tests/test_stream_route.py`:

```python
"""Gate: /api/stream relays the agent's event stream without editing it.

A fake upstream, never Cloud Run. The two things worth proving here are that
chunks arrive byte-for-byte in order — a proxy that reframes SSE breaks the
browser's parser in ways that only show up under load — and that every failure
mode reaches the screen as something the screen can render, including the one
that happens after the status code has already been sent.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.workspace import server

CHUNKS = [
    b'data: {"content": {"parts": [{"text": "Looking"}]}}\n\n',
    b'data: {"content": {"parts": [{"functionCall": {"id": "1", "name": "bq_query", '
    b'"args": {"sql": "SELECT 1 FROM `mining_data.assets`"}}}]}}\n\n',
    b'data: {"content": {"parts": [{"text": " done."}]}}\n\n',
]


@pytest.fixture
def upstream(monkeypatch):
    """A fake agent container, plus a record of what the proxy asked it."""
    seen = {"requests": [], "closed": False, "session_status": 200, "run_status": 200}

    async def body():
        try:
            for chunk in CHUNKS:
                yield chunk
        finally:
            seen["closed"] = True

    def handle(request: httpx.Request) -> httpx.Response:
        seen["requests"].append((request.method, request.url.path))
        if request.url.path.endswith("/run_sse"):
            seen["run_body"] = json.loads(request.content)
            if seen["run_status"] != 200:
                return httpx.Response(seen["run_status"], text="upstream said no")
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream; charset=utf-8"},
                content=body(),
            )
        return httpx.Response(seen["session_status"], json={})

    def fake_client(base, token):
        return httpx.AsyncClient(
            base_url=base,
            timeout=None,
            headers={"Authorization": f"Bearer {token}"},
            transport=httpx.MockTransport(handle),
        )

    monkeypatch.setattr(server, "_agent_client", fake_client)
    monkeypatch.setattr(server, "_services", lambda: {"mag-s01": "https://fake.invalid"})
    monkeypatch.setattr(server, "_identity_token", lambda audience: "fake-token")
    return seen


@pytest.fixture
def client():
    return TestClient(server.app)


def test_the_chunks_arrive_byte_for_byte_in_order(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        assert reply.headers["content-type"].startswith("text/event-stream")
        body = b"".join(reply.iter_raw())
    assert b"".join(CHUNKS) in body


def test_the_stream_ends_with_one_terminal_event(client, upstream):
    """EventSource reconnects on close, so the client needs an explicit end."""
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        body = b"".join(reply.iter_raw())
    assert body.count(b"event: proxy-done") == 1
    assert body.endswith(b"event: proxy-done\ndata: {}\n\n")


def test_the_session_is_created_before_the_run(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        b"".join(reply.iter_raw())
    paths = [path for _, path in upstream["requests"]]
    assert paths[0].startswith("/apps/S01/users/")
    assert paths[1] == "/run_sse"
    assert upstream["run_body"]["app_name"] == "S01"
    assert upstream["run_body"]["new_message"]["parts"][0]["text"] == "hello"


def test_a_400_on_session_creation_is_not_an_error(client, upstream):
    """Re-creating an existing session answers 400. It means it is already there."""
    upstream["session_status"] = 400
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        body = b"".join(reply.iter_raw())
    assert b"".join(CHUNKS) in body


def test_no_credentials_answers_503_in_the_shape_invoke_uses(client, monkeypatch):
    def refuse():
        raise server.NotConnected("identity token", "no credentials here")

    monkeypatch.setattr(server, "_services", refuse)
    reply = client.get("/api/stream/S01?prompt=hello")
    assert reply.status_code == 503
    assert reply.json() == {
        "connected": False,
        "stage": "identity token",
        "detail": "no credentials here",
    }


def test_an_unknown_agent_is_refused_before_any_upstream_call(client, upstream):
    reply = client.get("/api/stream/S01-SP1?prompt=hello")
    assert reply.status_code == 404
    assert reply.json()["connected"] is False
    assert upstream["requests"] == []


def test_an_empty_prompt_is_refused(client, upstream):
    reply = client.get("/api/stream/S01?prompt=%20")
    assert reply.status_code == 400
    assert upstream["requests"] == []


def test_a_failure_after_the_stream_opened_arrives_as_an_event(client, upstream):
    """The status code is already sent by then, so the failure has to be data."""
    upstream["run_status"] = 500
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        assert reply.status_code == 200
        body = b"".join(reply.iter_raw())
    assert b"event: proxy-error" in body
    assert b"upstream said no" in body
    assert body.endswith(b"event: proxy-done\ndata: {}\n\n")


def test_a_client_that_leaves_closes_the_upstream_connection(client, upstream):
    with client.stream("GET", "/api/stream/S01?prompt=hello") as reply:
        next(reply.iter_raw())
    assert upstream["closed"] is True
```

- [ ] **Step 2: Run it to make sure it fails**

Run:
```bash
cd .
python3 -m pytest tests/test_stream_route.py -v
```
Expected: FAIL — `AttributeError: module 'apps.workspace.server' has no attribute '_agent_client'`.

- [ ] **Step 3: Write the implementation**

In `apps/workspace/server.py`, add the constant beside `RUN_PATH`:

```python
RUN_PATH = "/run"
# ADK's streaming twin of /run. Same body, same session requirement; the reply
# is text/event-stream instead of one JSON array, which is the whole reason
# /api/stream exists — a real question takes ~100 seconds and a reader watching
# a spinner for that long cannot tell it from a hang.
RUN_SSE_PATH = "/run_sse"
```

Add the client factory above `@app.post("/api/invoke/{agent_id}")`:

```python
def _agent_client(base: str, token: str) -> httpx.AsyncClient:
    """The one place an agent-facing client is built.

    A function rather than an inline constructor so a test can substitute a
    transport and exercise the streaming path without Cloud Run. `timeout=None`
    on the streaming path is deliberate: the ceiling that matters is the one the
    service is deployed with, and a shorter one here would cut off a working
    call and report it as a proxy failure.
    """
    return httpx.AsyncClient(
        base_url=base, timeout=None, headers={"Authorization": f"Bearer {token}"}
    )
```

Change `/api/invoke`'s client construction to use it — one line, so the two routes cannot drift apart in how they authenticate:

```python
    async with _agent_client(base, token) as client:
```

Add the route after `/api/invoke`:

```python
def _sse(event: str, payload: dict) -> bytes:
    """One server-sent event, framed. Named events, because the browser has to
    tell a message the agent sent from a message this proxy sent."""
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()


@app.get("/api/stream/{agent_id}")
async def stream(
    agent_id: str,
    prompt: str = "",
    user_id: str = "workspace",
    session_id: str = "workspace-session",
) -> Response:
    """Relay one agent's event stream to the browser, unedited.

    GET with query parameters rather than POST so the browser's own EventSource
    can read it; a POST would need a streaming-fetch parser in every screen.

    The reply is ADK's own stream, passed through byte for byte. Reshaping the
    events here would put a second opinion between the screen and the agent,
    which is the same objection /api/invoke already records.
    """
    expected = _entrypoints()
    if agent_id not in expected:
        return JSONResponse(
            {"connected": False, "stage": "catalog",
             "detail": f"{agent_id} is not an externally callable entrypoint"},
            status_code=404,
        )
    prompt = (prompt or "").strip()
    if not prompt:
        return JSONResponse(
            {"connected": False, "stage": "request", "detail": "prompt is required"},
            status_code=400,
        )

    # Everything that can fail with a status code fails here, before a single
    # byte of the stream is written. After that the status is spent.
    try:
        live = _services()
        base = live.get(expected[agent_id])
        if not base:
            raise NotConnected(
                "cloud run", f"service {expected[agent_id]} is not deployed in {REGION}"
            )
        token = _identity_token(base)
    except NotConnected as exc:
        return JSONResponse(
            {"connected": False, "stage": exc.stage, "detail": exc.detail},
            status_code=503,
        )

    async def relay():
        try:
            async with _agent_client(base, token) as client:
                # As in /api/invoke: a 400 here means the session already exists.
                await client.post(
                    SESSION_PATH.format(app=agent_id, user=user_id, session=session_id),
                    json={},
                )
                async with client.stream(
                    "POST",
                    RUN_SSE_PATH,
                    json={
                        "app_name": agent_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "new_message": {"role": "user", "parts": [{"text": prompt}]},
                        "streaming": False,
                    },
                ) as upstream:
                    if upstream.status_code != 200:
                        detail = (await upstream.aread()).decode(errors="replace")
                        yield _sse("proxy-error", {
                            "connected": False, "stage": "agent",
                            "detail": f"HTTP {upstream.status_code}: {detail[:800]}",
                        })
                    else:
                        async for chunk in upstream.aiter_raw():
                            yield chunk
        except Exception as exc:  # noqa: BLE001 - the text is the product here
            yield _sse("proxy-error", {
                "connected": False, "stage": "stream",
                "detail": f"{type(exc).__name__}: {exc}",
            })
        finally:
            # EventSource reconnects when a connection closes. Without an
            # explicit end the browser would silently re-ask the agent the same
            # hundred-second question, forever.
            yield b"event: proxy-done\ndata: {}\n\n"

    return StreamingResponse(
        relay(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

Add the imports the above needs, at the top of the file:

```python
import json
```
and extend the FastAPI import line:
```python
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
```

- [ ] **Step 4: Run the tests and make sure they pass**

Run:
```bash
cd .
python3 -m pytest tests/test_stream_route.py -v
```
Expected: PASS, 9 tests.

- [ ] **Step 5: Prove the container gate is still green**

The new route must not have pulled an agent SDK into the image.

Run:
```bash
cd .
python3 -m pytest tests/test_workspace_image.py -v
```
Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
cd .
git add apps/workspace/server.py tests/test_stream_route.py
git commit -m "feat(workspace): relay the agent's event stream so a long answer is legible"
```

---

## Task 5: the shared "Technical detail" drawer

The collapsible already exists — `details.tbl` in `workspace.css`, with a custom `▸`/`▾` marker, a 44px touch target and a focus ring, already opened before printing by `handover.js`. It lives in the wrong file: the case application does not load `workspace.css`, so five of the ten screens cannot use it (§7).

**Files:**
- Modify: `apps/shared/app.css` (add the `.tbl` base rules)
- Modify: `apps/workspace/workspace.css` (remove the same rules; keep `.tbl-desc`, `.cols`, `.col-meaning`, which are workspace-specific)
- Modify: `apps/shared/shell.js` (add `technicalDrawer()`; change `WORK_NAV`)
- Create: `tests/test_shared_drawer.py`

**Interfaces:**
- Produces: `technicalDrawer(bodyHtml, hint) -> string` in `shell.js` — the one way any screen in either application renders its end-of-page drawer.

- [ ] **Step 1: Write the failing test**

Create `tests/test_shared_drawer.py`:

```python
"""Gate: one collapsible component, shared by both applications.

The `details.tbl` rules were written in workspace.css, which apps/case never
loads. Moving them is the whole of this task, and the failure mode if they move
back is silent: the case screens keep working, they just render an unstyled
disclosure triangle and a 20px touch target. Asserting the location is cheaper
than noticing that on a phone.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
SHARED_CSS = REPO / "apps" / "shared" / "app.css"
WORKSPACE_CSS = REPO / "apps" / "workspace" / "workspace.css"
SHELL_JS = REPO / "apps" / "shared" / "shell.js"


def test_the_collapsible_lives_in_the_shared_stylesheet():
    css = SHARED_CSS.read_text()
    assert ".tbl > summary" in css
    assert "min-height: 44px" in css, "the touch target moved with the rules or was lost"
    assert ":focus-visible" in css, "the focus ring moved with the rules or was lost"


def test_the_workspace_stylesheet_no_longer_redefines_it():
    """Two definitions of one component is how they drift apart."""
    css = WORKSPACE_CSS.read_text()
    assert ".tbl > summary {" not in css
    assert "\n.tbl {" not in css
    # The genuinely workspace-specific parts stay.
    assert ".tbl-desc" in css
    assert ".col-meaning" in css


def test_both_applications_load_the_shared_stylesheet():
    for screen in sorted((REPO / "apps").glob("*/*.html")) + [REPO / "apps" / "index.html"]:
        assert "shared/app.css" in screen.read_text() or "app.css" in screen.read_text(), (
            f"{screen.relative_to(REPO)} does not load the shared stylesheet, so it "
            "cannot render the technical drawer"
        )


def test_one_helper_renders_the_drawer_for_every_screen():
    shell = SHELL_JS.read_text()
    assert "function technicalDrawer(" in shell
    assert "Technical detail" in shell


def test_the_workspace_nav_points_at_the_persona_page():
    shell = SHELL_JS.read_text()
    assert "workbench.html" not in shell
    assert '{ href: "persona.html", label: "My role" }' in shell
```

- [ ] **Step 2: Run it to make sure it fails**

Run:
```bash
cd .
python3 -m pytest tests/test_shared_drawer.py -v
```
Expected: FAIL on `test_the_collapsible_lives_in_the_shared_stylesheet`, `test_the_workspace_stylesheet_no_longer_redefines_it`, `test_one_helper_renders_the_drawer_for_every_screen` and `test_the_workspace_nav_points_at_the_persona_page`.

- [ ] **Step 3: Move the rules into `apps/shared/app.css`**

Cut these rules out of `apps/workspace/workspace.css` (they sit under the `/* ---------- input tables ---------- */` heading, around lines 78–96) and paste them into `apps/shared/app.css`, appended at the end under a new heading. Move exactly this much and no more — `.tbl-desc`, `.cols` and `.col-meaning` stay in `workspace.css`:

```css
/* ---------- the technical drawer ---------- */

/* Both applications use this. It began in workspace.css, where the case
   application could not reach it, which meant five of the ten screens had a
   disclosure triangle at the browser's default size instead of a 44px target.
   A component two readerships share belongs in the shared sheet. */
.tbl { border: 1px solid var(--border); margin-bottom: 8px; background: var(--bg); }
/* min-width: 0 because a flex item will not shrink below its content by
   default, and the label here is a fully-qualified table name — the longest in
   the catalog, mining_data.operator_vehicle_assignments, is wider than a
   phone. */
.tbl > summary {
  display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  min-height: 44px; padding: 8px 12px; cursor: pointer; font-size: 13px;
  min-width: 0;
}
.tbl > summary::-webkit-details-marker { display: none; }
.tbl > summary::before { content: "▸"; color: var(--fg-muted); font-size: 11px; }
.tbl[open] > summary::before { content: "▾"; }
.tbl > summary:focus-visible { outline: none; box-shadow: inset 0 0 0 1px var(--accent); }
.tbl > summary .dim { font-size: 10.5px; margin-left: auto; }

/* The end-of-page drawer specifically: separated from the body by a rule, so it
   reads as an appendix rather than as one more section. */
.drawer { margin-top: 20px; }
.drawer > summary { font-weight: 600; }
.drawer-body { padding: 0 12px 12px; font-size: 12.5px; }
.drawer-body dt { font-weight: 600; margin-top: 8px; }
.drawer-body dd { margin: 2px 0 0; color: var(--fg-muted); }
```

- [ ] **Step 4: Add the helper and change the nav in `apps/shared/shell.js`**

Replace the `WORK_NAV` block (lines 31–39) with:

```js
/* Application 2. The four destinations are the four standing screens; the
   approval sheet is deliberately absent because it is a modal raised from an
   agent team or a role page and never a place you navigate to on its own. */
const WORK_NAV = [
  { href: "index.html", label: "Cockpit" },
  { href: "swarm.html", label: "Agent teams" },
  { href: "persona.html", label: "My role" },
  { href: "handover.html", label: "Handover" },
];
```

Add the helper beside `provenance()`:

```js
/** The one collapsible every screen ends with.
 *
 *  The instruction was explicit: plain language and tables first, technical
 *  detail at the end, behind something the reader opens on purpose. One helper
 *  rather than ten hand-written <details> blocks, because ten of them is ten
 *  chances for one screen to call it something else and break the pattern the
 *  reader has just learned.
 */
function technicalDrawer(bodyHtml, hint) {
  return (
    '<details class="tbl drawer">' +
    "<summary>Technical detail" +
    (hint ? `<span class="dim">${esc(hint)}</span>` : "") +
    "</summary>" +
    `<div class="drawer-body">${bodyHtml}</div>` +
    "</details>"
  );
}
```

- [ ] **Step 5: Run the tests and make sure they pass**

Run:
```bash
cd .
python3 -m pytest tests/test_shared_drawer.py -v
```
Expected: PASS, 5 tests.

`test_the_workspace_nav_points_at_the_persona_page` passes now, before `persona.html` exists. That is intentional: the nav link is created here and the page it points at arrives in Task 7, which is two commits away and on the same branch.

- [ ] **Step 6: Commit**

```bash
cd .
git add apps/shared/app.css apps/shared/shell.js apps/workspace/workspace.css tests/test_shared_drawer.py
git commit -m "refactor(apps): share one collapsible between both applications"
```

---

## Task 6: `apps/workspace/agent-stream.js` — read the stream, name each step

**Files:**
- Create: `apps/workspace/agent-stream.js`
- Create: `tests/js/agent-stream.test.js`

**Interfaces:**
- Consumes: `apps/shared/plain.js` — `callLine`, `failLine`.
- Produces:
  - `eventToSteps(adkEvent, calls) -> [{ kind, text }]` — **pure**, no DOM, no network. `kind ∈ {"step", "step-failed", "text"}`. `calls` is a caller-owned `{callId: args}` map the function writes to on a `functionCall` and reads on the matching `functionResponse`; omit it and responses degrade to the tool's verb alone. This is the risky logic and it is tested directly.
  - `streamAgent(options) -> { close() }` — the `EventSource` lifecycle. `options`: `{ agentId, prompt, userId, sessionId, onStep(step), onError(detail), onDone() }`.

**The four part shapes, measured on the wire (§5.2):**
```
{ functionCall:     { id, name, args } }          // args.sql holds the SELECT
{ functionResponse: { id, name, response: { success, data } } }
{ text: "…" }
{ thoughtSignature: "…" }                          // rides alongside; not a step
```
`success` is nested **under `response`** — a plausible guess would put it at the top level and silently never report a failure.

**The model's own prose passes through unaltered.** S01 currently emits `The tool call \`graph_traverse\` failed with \`success=false\`` in its own text, because `blast_radius` is genuinely broken on S01. Filtering that string would put the frontend in the business of editing what the agent said. The honest fix is upstream and is logged as out of scope.

- [ ] **Step 1: Write the failing test**

Create `tests/js/agent-stream.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");

const S = require("../../apps/workspace/agent-stream.js");

test("a text part becomes answer text, not a step", () => {
  const steps = S.eventToSteps({ content: { parts: [{ text: "Hello." }] } });
  assert.deepEqual(steps, [{ kind: "text", text: "Hello." }]);
});

test("a function call becomes one named step", () => {
  const steps = S.eventToSteps({
    content: { parts: [{ functionCall: { id: "1", name: "bq_query",
      args: { sql: "SELECT * FROM `mining_data.telemetry_stream` LIMIT 10" } } }] },
  });
  assert.deepEqual(steps, [{ kind: "step", text: "Reading the sensor readings" }]);
});

test("a successful response is the same step, not a new one", () => {
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "1", name: "bq_query",
      response: { success: true, data: [] } } }] },
  });
  assert.equal(steps.length, 1);
  assert.equal(steps[0].kind, "step");
});

test("a failed response is named, not hidden", () => {
  // success is nested under response. At the top level it would read as
  // undefined, which is not false, and the failure would never be reported.
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "9", name: "graph_traverse",
      response: { success: false } } }] },
  });
  assert.equal(steps.length, 1);
  assert.equal(steps[0].kind, "step-failed");
  assert.match(steps[0].text, /Couldn't/);
});

test("a failure names what failed, recalled from the matching call", () => {
  // A functionResponse carries only {id, name, response} — no arguments. The
  // noun has to come from the functionCall that shares its id, or every failure
  // degrades to the tool's verb and the reader learns nothing.
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "7", name: "graph_traverse",
      args: { traversal: "blast_radius" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "7", name: "graph_traverse",
      response: { success: false } } }] },
  }, calls);
  assert.equal(
    steps[0].text,
    "Couldn't trace what else stops if this stops — that lookup failed."
  );
});

test("a successful response repeats the call's own line, not a generic one", () => {
  const calls = {};
  S.eventToSteps({
    content: { parts: [{ functionCall: { id: "3", name: "bq_query",
      args: { sql: "SELECT 1 FROM `mining_data.assets`" } } }] },
  }, calls);
  const steps = S.eventToSteps({
    content: { parts: [{ functionResponse: { id: "3", name: "bq_query",
      response: { success: true, data: [] } } }] },
  }, calls);
  assert.equal(steps[0].text, "Reading the machine register");
});

test("a thoughtSignature is not a step", () => {
  const steps = S.eventToSteps({
    content: { parts: [{ thoughtSignature: "abc" }, { text: "Right." }] },
  });
  assert.deepEqual(steps, [{ kind: "text", text: "Right." }]);
});

test("an event with no content yields nothing rather than throwing", () => {
  assert.deepEqual(S.eventToSteps({}), []);
  assert.deepEqual(S.eventToSteps({ content: {} }), []);
  assert.deepEqual(S.eventToSteps(null), []);
});

test("the model's own prose is passed through unaltered", () => {
  const leak = "The tool call `graph_traverse` failed with `success=false`";
  const steps = S.eventToSteps({ content: { parts: [{ text: leak }] } });
  assert.equal(steps[0].text, leak);
});

test("the stream url carries the prompt and the session as query parameters", () => {
  const url = S.streamUrl({
    agentId: "S01", prompt: "what now?", userId: "u", sessionId: "s",
  });
  assert.ok(url.startsWith("/api/stream/S01?"));
  assert.ok(url.includes("prompt=what+now%3F") || url.includes("prompt=what%20now%3F"));
  assert.ok(url.includes("user_id=u"));
  assert.ok(url.includes("session_id=s"));
});
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd . && node --test tests/js/agent-stream.test.js`
Expected: FAIL — `Cannot find module '../../apps/workspace/agent-stream.js'`.

- [ ] **Step 3: Write the implementation**

Create `apps/workspace/agent-stream.js`:

```js
/* One agent's event stream, turned into lines a reader can follow.
 *
 * A real question was measured at 103.8 seconds across 26 events. The point of
 * this module is that those 103 seconds read as work happening — reading the
 * sensor readings, tracing what else stops — rather than as a spinner that
 * cannot be told from a hang.
 *
 * The agent's own prose is never edited. The agents currently leak plumbing
 * into their answers, and filtering that here would put this file in the
 * business of deciding what the agent said. The honest fix is upstream.
 */
var PLAIN = typeof require !== "undefined" ? require("../shared/plain.js") : window;

/* The four part shapes, as measured on the wire.
 *
 * Two details here are worth more than they look. First, success is nested under
 * response — read at the top level it is undefined, which is not false, and a
 * failed lookup would then never be reported at all. Second, a functionResponse
 * carries only {id, name, response}: it has no arguments, so the noun the call
 * was about has to be remembered from the matching functionCall by id. Without
 * that, every failure reads "Couldn't finish tracing connections" instead of
 * naming what could not be traced, which is the whole point of the line.
 *
 * `calls` is that memory. It belongs to one conversation and is passed in, so
 * this function stays pure with respect to module state and a test can hand it
 * a fresh one.
 */
function eventToSteps(adkEvent, calls) {
  var parts = (adkEvent && adkEvent.content && adkEvent.content.parts) || [];
  var seen = calls || {};
  var steps = [];
  parts.forEach(function (part) {
    if (!part) return;
    if (typeof part.text === "string" && part.text.length) {
      steps.push({ kind: "text", text: part.text });
      return;
    }
    if (part.functionCall) {
      var args = part.functionCall.args || {};
      if (part.functionCall.id) seen[part.functionCall.id] = args;
      steps.push({ kind: "step", text: PLAIN.callLine(part.functionCall.name, args) });
      return;
    }
    if (part.functionResponse) {
      var reply = part.functionResponse.response || {};
      var recalled = seen[part.functionResponse.id] || {};
      var failed = reply.success === false;
      steps.push({
        kind: failed ? "step-failed" : "step",
        text: failed
          ? PLAIN.failLine(part.functionResponse.name, recalled)
          : PLAIN.callLine(part.functionResponse.name, recalled),
      });
    }
    // thoughtSignature rides alongside the other three and is not a step.
  });
  return steps;
}

function streamUrl(options) {
  var q = new URLSearchParams({
    prompt: options.prompt || "",
    user_id: options.userId || "workspace",
    session_id: options.sessionId || "workspace-session",
  });
  return "/api/stream/" + encodeURIComponent(options.agentId) + "?" + q.toString();
}

/* EventSource, with the one behaviour that would otherwise bite: it reconnects
 * by itself when the connection closes, so without the server's explicit
 * proxy-done event the browser would silently re-ask the agent the same
 * hundred-second question, forever. */
function streamAgent(options) {
  var source = new EventSource(streamUrl(options));
  var finished = false;
  // One call memory per stream, so a response can name what its call was about.
  var calls = {};

  function finish() {
    if (finished) return;
    finished = true;
    source.close();
    if (options.onDone) options.onDone();
  }

  source.onmessage = function (message) {
    var parsed;
    try {
      parsed = JSON.parse(message.data);
    } catch (err) {
      return; // A frame this module cannot read is not a frame worth guessing at.
    }
    eventToSteps(parsed, calls).forEach(function (step) {
      if (options.onStep) options.onStep(step);
    });
  };

  source.addEventListener("proxy-error", function (message) {
    var detail = message.data;
    try {
      detail = JSON.parse(message.data).detail || message.data;
    } catch (err) { /* the raw text is better than nothing */ }
    if (options.onError) options.onError(detail);
  });

  source.addEventListener("proxy-done", finish);

  source.onerror = function () {
    // Reached when the connection drops before proxy-done — a dropped network
    // or a proxy that died. Reconnecting would re-run the agent, so it stops.
    if (finished) return;
    if (options.onError) options.onError("The connection to the agent dropped.");
    finish();
  };

  return { close: finish };
}

if (typeof module !== "undefined") {
  module.exports = { eventToSteps, streamUrl, streamAgent };
}
```

`URLSearchParams` is global in Node 24 and in every browser this targets, so `streamUrl` is testable without a DOM.

- [ ] **Step 4: Run the tests and make sure they pass**

Run: `cd . && node --test tests/js/agent-stream.test.js`
Expected: PASS, 10 tests.

- [ ] **Step 5: Commit**

```bash
cd .
git add apps/workspace/agent-stream.js tests/js/agent-stream.test.js
git commit -m "feat(workspace): turn each agent event into a line a reader can follow"
```

---

## Task 7: the persona page and its left panel

The screen the reader lands on for their role. Five blocks, all rendered synchronously from `window.MINING_DATA` — no spinner, no fetch, no empty state caused by the network (§4). The chat sidecar arrives in Task 8; this task builds the page, the panel and the empty sidecar column.

**Files:**
- Create: `apps/workspace/persona.html`
- Create: `apps/workspace/persona-panel.js`
- Create: `apps/workspace/persona.js`
- Modify: `apps/workspace/workspace.css` (persona layout)
- Delete: `apps/workspace/workbench.html`, `apps/workspace/workbench.js`
- Create: `tests/test_persona_page.py`

**Interfaces:**
- Consumes: `persona-data.js` (`branchEvidenceFor`, `gapRowsFor`), `shell.js` (`esc`, `fig`, `num`, `rowPlaces`, `mountNav`, `provenance`, `technicalDrawer`, `el`), `plain.js` (`plainTable`, `plainTraversal`).
- Produces: `renderPanel(personaCode, DATA) -> string` in `persona-panel.js` — the whole left column as HTML. `persona.js` mounts it.

**The five blocks (§4):**

| # | Heading on screen | Source | Empty case |
|---|---|---|---|
| 1 | "What you're answerable for" | `persona.accountable_for` | never empty |
| 2a | "What your part of the mine is doing" | `branchEvidenceFor()` | P8 → "No single part of the site is this role's; the figures below are the whole site's." |
| 2b | "An ordinary day against the best day" | `gapRowsFor()` | four personas reach nothing → the first group says so and "Also recorded at this site" carries all four |
| 3 | "The five machines this site instruments" | `DATA.signals.assets` | never empty |
| 4 | "Waiting on your sign-off" | `persona.hitl_agents` | P5, P8 → "Nothing on this role's list needs a sign-off." |
| 5 | "What you're trying to get done" | `persona.jobs_to_be_done`, in a closed `<details>` | never empty |

**Block 2a renders three kinds and must switch on `evidence.kind`** — an assumption that everything is a line breaks P2 (a distribution) and P4 (a share):
- `series` → inline-SVG sparkline from `points`, plus `min`, `max`, `readings`, `from`, `to`
- `distribution` → inline-SVG histogram from `bins` and `edges`, plus `n`
- `share` → `part` of `whole`, as a bar and as a sentence

**`caption` renders verbatim under every one of them.** A bucketed mean drawn without saying it is bucketed invites a precision that is not there.

**Block 2b renders `gap.method` above the table and `gap.caveat` and `gap.excluded` verbatim below it.** Figures print through `fig(v, unit, rowPlaces(row))` so the three numbers in a row survive the reader subtracting them.

**Block 3's heading says "this site", not "yours".** No persona→asset mapping exists in the repository, and assigning MILL-01 to the Reliability Engineer would be a plausible guess presented as a fact (§4.3).

- [ ] **Step 1: Write the failing test**

Create `tests/test_persona_page.py`:

```python
"""Gate: the persona page exists, replaces the workbench, and claims nothing extra.

This is a static check of the page's sources, not of its rendering — the
rendering is checked in a browser at the end of the plan. What is worth pinning
here is the set of claims the markup and the panel are allowed to make, because
those are the ones that go wrong quietly: a heading that says "your machines"
when no persona-to-asset mapping exists, or a screen that outlives the workbench
it replaced.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "apps" / "workspace"


def test_the_persona_page_and_its_two_scripts_exist():
    for name in ("persona.html", "persona.js", "persona-panel.js"):
        assert (WORKSPACE / name).is_file(), f"{name} is missing"


def test_the_workbench_is_gone_and_nothing_still_links_to_it():
    assert not (WORKSPACE / "workbench.html").exists()
    assert not (WORKSPACE / "workbench.js").exists()
    for source in sorted((REPO / "apps").rglob("*.html")) + sorted((REPO / "apps").rglob("*.js")):
        assert "workbench" not in source.read_text(), (
            f"{source.relative_to(REPO)} still refers to the workbench"
        )


def test_the_page_loads_every_module_the_panel_needs():
    html = (WORKSPACE / "persona.html").read_text()
    for script in ("../shared/shell.js", "../shared/plain.js", "persona-data.js",
                   "router.js", "persona-panel.js", "persona.js"):
        assert script in html, f"persona.html does not load {script}"
    # Order matters: these are classic scripts, and a module that calls into
    # another must be loaded after it.
    assert html.index("../shared/plain.js") < html.index("router.js")
    assert html.index("router.js") < html.index("persona-data.js")
    assert html.index("persona-data.js") < html.index("persona-panel.js")


def test_the_machines_block_does_not_claim_the_machines_are_the_readers():
    """No persona-to-asset mapping exists, so the heading says "this site"."""
    panel = (WORKSPACE / "persona-panel.js").read_text()
    assert "this site instruments" in panel
    assert "your machines" not in panel.lower()


def test_the_panel_handles_all_three_evidence_kinds():
    panel = (WORKSPACE / "persona-panel.js").read_text()
    for kind in ("series", "distribution", "share"):
        assert f'"{kind}"' in panel, (
            f"the panel does not switch on the {kind} evidence kind, so at least "
            "one persona renders nothing"
        )


def test_the_panel_renders_the_gap_caveats_verbatim():
    panel = (WORKSPACE / "persona-panel.js").read_text()
    for field in ("caveat", "excluded", "method", "caption"):
        assert field in panel, f"gap.{field} is never rendered"


def test_the_page_ends_with_one_technical_drawer():
    panel = (WORKSPACE / "persona-panel.js").read_text() + (WORKSPACE / "persona.js").read_text()
    assert panel.count("technicalDrawer(") == 1


def test_no_measurement_is_typed_into_the_page():
    """Every figure comes from the bundle. A literal here is a number nobody can check.

    The two shapes a measurement takes in this data are a decimal (92.32,
    1149.552, 8.5433) and a magnitude of four digits or more (145000, 1996,
    3340). Neither has any business in rendering code. Small integers do — SVG
    geometry, percentages, array bounds — so they are left alone.
    """
    import re

    for name in ("persona.js", "persona-panel.js"):
        source = (WORKSPACE / name).read_text()
        body = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith(("*", "//", "/*"))
        )
        decimals = re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", body)
        assert decimals == [], (
            f"{name} contains the decimal literal(s) {decimals}; every measurement "
            "on this screen must come from window.MINING_DATA"
        )
        big = [n for n in re.findall(r"(?<![\w.])\d{4,}(?![\w.])", body)]
        assert big == [], (
            f"{name} contains the literal magnitude(s) {big}; every figure on this "
            "screen must come from window.MINING_DATA"
        )
```

- [ ] **Step 2: Run it to make sure it fails**

Run:
```bash
cd .
python3 -m pytest tests/test_persona_page.py -v
```
Expected: FAIL — `persona.html is missing`.

- [ ] **Step 3: Write `apps/workspace/persona-panel.js`**

The whole left column. It calls `persona-data.js` and holds no rule of its own.

```js
/* The left column: what is true right now for this role, from the record.
 *
 * Rendered synchronously from window.MINING_DATA, so there is no spinner and no
 * empty state that the network can cause. Every rule this file appears to have
 * lives in persona-data.js instead; this file decides only how a result looks.
 *
 * The headings are careful in one specific way. Block 3 says "this site
 * instruments", not "your machines", because no persona-to-asset mapping exists
 * anywhere in the repository and inventing one is the failure this project
 * keeps refusing.
 */

function _sparkline(points) {
  if (!points || points.length < 2) return "";
  var lo = Math.min.apply(null, points);
  var hi = Math.max.apply(null, points);
  var span = hi - lo || 1;
  var step = 100 / (points.length - 1);
  var path = points
    .map(function (v, i) {
      return (i ? "L" : "M") + (i * step).toFixed(2) + " " +
        (28 - ((v - lo) / span) * 26).toFixed(2);
    })
    .join(" ");
  return (
    '<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" ' +
    'role="img" aria-hidden="true" focusable="false">' +
    '<path d="' + path + '" fill="none" stroke="var(--accent)" stroke-width="1"/>' +
    "</svg>"
  );
}

function _histogram(bins) {
  if (!bins || !bins.length) return "";
  var hi = Math.max.apply(null, bins) || 1;
  var w = 100 / bins.length;
  var bars = bins
    .map(function (v, i) {
      var h = (v / hi) * 26;
      // Four fifths of the slot, so the bars read as bars rather than as a
      // filled area. Written as a fraction of integers because this file must
      // hold no decimal literal — see test_no_measurement_is_typed_into_the_page.
      return '<rect x="' + (i * w).toFixed(2) + '" y="' + (28 - h).toFixed(2) +
        '" width="' + ((w * 4) / 5).toFixed(2) + '" height="' + h.toFixed(2) +
        '" fill="var(--accent)"/>';
    })
    .join("");
  return (
    '<svg class="spark" viewBox="0 0 100 28" preserveAspectRatio="none" ' +
    'role="img" aria-hidden="true" focusable="false">' + bars + "</svg>"
  );
}

function _shareBar(part, whole) {
  var pct = whole ? (part / whole) * 100 : 0;
  return (
    '<div class="share-bar" role="img" aria-hidden="true">' +
    '<span style="width:' + pct.toFixed(1) + '%"></span></div>'
  );
}

/* Three kinds, all of which must be handled: two of the eight personas would
 * render nothing if this assumed everything was a line. */
function _evidence(row) {
  var e = row.evidence;
  var body = "";
  if (e.kind === "series") {
    body =
      _sparkline(e.points) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      fig(e.min, e.unit) + " to " + fig(e.max, e.unit) +
      " over " + num(e.readings) + " readings</p>";
  } else if (e.kind === "distribution") {
    body =
      _histogram(e.bins) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      num(e.n) + " values</p>";
  } else if (e.kind === "share") {
    body =
      _shareBar(e.part, e.whole) +
      '<p class="ev-range">' + esc(e.label || row.branch.title) + " · " +
      num(e.part) + " of " + num(e.whole) + "</p>";
  }
  return (
    '<div class="ev">' + body +
    // Verbatim. A bucketed mean drawn without saying it is bucketed invites the
    // reader to read a precision that is not there.
    '<p class="ev-caption">' + esc(e.caption) + "</p></div>"
  );
}

function _blockBranch(code, DATA) {
  var rows = branchEvidenceFor(code, DATA);
  if (!rows.length) {
    return (
      '<section class="pblock"><h2>What your part of the mine is doing</h2>' +
      '<p class="pnote">No single part of the site belongs to this role, so there ' +
      "is no separate signal for it. The figures below are the whole site's.</p>" +
      "</section>"
    );
  }
  return (
    '<section class="pblock"><h2>What your part of the mine is doing</h2>' +
    rows.map(function (row) {
      return '<h3 class="ev-head">' + esc(row.branch.title) + "</h3>" + _evidence(row);
    }).join("") +
    "</section>"
  );
}

function _gapTable(rows) {
  return (
    '<table class="tbl-plain"><thead><tr>' +
    "<th>Measure</th><th>Machine</th><th>An ordinary day</th>" +
    "<th>The best day</th><th>The gap</th></tr></thead><tbody>" +
    rows.map(function (row) {
      var dp = rowPlaces(row);
      var gap = row.delta_kind === "points"
        ? fig(row.delta, "", dp) + " pts"
        : fig(row.delta_pct, "%", 1);
      return "<tr><td>" + esc(row.label) + "</td>" +
        "<td>" + (row.asset_id ? esc(row.asset_id) : "—") + "</td>" +
        "<td>" + fig(row.median, row.unit, dp) + "</td>" +
        "<td>" + fig(row.p90, row.unit, dp) + "</td>" +
        "<td>" + gap + "</td></tr>";
    }).join("") +
    "</tbody></table>"
  );
}

function _blockGap(code, DATA) {
  var split = gapRowsFor(code, DATA);
  var gap = DATA.signals.gap;
  var reached = split.reached.length
    ? "<h3>Your agents read these</h3>" + _gapTable(split.reached)
    : '<p class="pnote">None of this role\'s agents read the tables behind the ' +
      "figures below, so none of them is this role's to act on directly.</p>";
  var other = split.other.length
    ? "<h3>Also recorded at this site</h3>" + _gapTable(split.other)
    : "";
  return (
    '<section class="pblock"><h2>An ordinary day against the best day</h2>' +
    '<p class="pnote">' + esc(gap.method) + "</p>" +
    reached + other +
    '<p class="pcaveat">' + esc(gap.caveat) + "</p>" +
    // gap.excluded is a LIST of {asset_id, reason}. Excluding a series without
    // saying so is the same fault as inventing one, so every entry prints.
    gap.excluded.map(function (row) {
      return '<p class="pcaveat">' + esc(row.asset_id) + ": " + esc(row.reason) + "</p>";
    }).join("") +
    "</section>"
  );
}

function _blockAssets(DATA) {
  return (
    '<section class="pblock"><h2>The five machines this site instruments</h2>' +
    '<table class="tbl-plain"><thead><tr><th>Machine</th><th>What is measured</th>' +
    "<th>Unit</th></tr></thead><tbody>" +
    DATA.signals.assets.map(function (a) {
      return "<tr><td>" + esc(a.asset_id) + "</td><td>" + esc(a.label) +
        "</td><td>" + esc(a.unit) + "</td></tr>";
    }).join("") +
    "</tbody></table></section>"
  );
}

function _blockSignoffs(persona, DATA) {
  var byId = {};
  DATA.catalog.agents.forEach(function (a) { byId[a.agent_id] = a; });
  var ids = persona.hitl_agents || [];
  if (!ids.length) {
    return (
      '<section class="pblock"><h2>Waiting on your sign-off</h2>' +
      '<p class="pnote">Nothing on this role\'s list needs a sign-off.</p></section>'
    );
  }
  return (
    '<section class="pblock"><h2>Waiting on your sign-off</h2>' +
    '<ul class="signoffs">' +
    ids.map(function (id) {
      var agent = byId[id];
      if (!agent) return "";
      return "<li><span>" + esc(agent.display_name) + "</span>" +
        '<button class="ask" type="button" data-agent="' + esc(id) + '">Ask this one</button></li>';
    }).join("") +
    "</ul></section>"
  );
}

function _blockJobs(persona) {
  return (
    '<details class="tbl pblock-jobs"><summary>What you\'re trying to get done</summary>' +
    '<ul class="jobs">' +
    (persona.jobs_to_be_done || []).map(function (job) {
      return "<li>" + esc(job) + "</li>";
    }).join("") +
    "</ul></details>"
  );
}

function renderPanel(code, DATA) {
  var persona = DATA.personas.personas[code];
  return (
    '<section class="pblock"><h2>What you\'re answerable for</h2>' +
    '<p class="lede">' + esc(persona.accountable_for) + "</p></section>" +
    _blockBranch(code, DATA) +
    _blockGap(code, DATA) +
    _blockAssets(DATA) +
    _blockSignoffs(persona, DATA) +
    _blockJobs(persona)
  );
}
```

**The field names above were read off the live bundle and are correct as written.** For reference, so no read has to be guessed:

| Object | Fields |
|---|---|
| `value_tree.branches` | a **list**; each entry `{ code, title, apqc, branches, mechanism, anchored, agents, count, personas }` |
| `signals.branch_evidence[Bx]` | always `{ kind, label, unit, source, caption }`; plus `points, min, max, readings, from, to` (`series`), `bins, edges, n` (`distribution`), `part, whole` (`share`) |
| `signals.assets[]` | `{ asset_id, metric, label, unit, points, min, max, readings, from, to, source }` |
| `signals.gap` | `{ method, rows, caveat, excluded }`; `excluded` is a **list** of `{ asset_id, reason }` |
| `personas.personas[Px]` | `{ code, title, accountable_for, pain_points, jobs_to_be_done, journey, agents, value_branch, agent_count, hitl_agents }` |
| `catalog.counts` | `{ agent_nodes: 100, entrypoints: 52, swarms: 12, deep_agents: 40, hitl_entrypoints: 14 }` |

Note that `branch.title` is the branch's name — there is no `branch.name` — and that `signals.assets[]` carries a `metric` (`power_draw_mw`) as well as a `label` (`Power draw`). The block 3 table prints the label, not the metric.

- [ ] **Step 4: Write `apps/workspace/persona.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>My role · Mining Agents</title>
    <link rel="stylesheet" href="../shared/tokens.css" />
    <link rel="stylesheet" href="../shared/app.css" />
    <link rel="stylesheet" href="workspace.css" />
  </head>
  <body>
    <div class="wrap">
      <header class="head">
        <h1>My role</h1>
        <p class="lede" id="role-lede"></p>
        <label class="role-pick">
          <span>Role</span>
          <select id="role-select"></select>
        </label>
      </header>
      <div class="role-layout">
        <div id="panel"></div>
        <aside class="sidecar" id="sidecar"></aside>
      </div>
      <div id="foot"></div>
    </div>

    <script src="../shared/data/bundle.js"></script>
    <script src="../shared/shell.js"></script>
    <script src="../shared/plain.js"></script>
    <script src="router.js"></script>
    <script src="persona-data.js"></script>
    <script src="persona-panel.js"></script>
    <script src="chat.js"></script>
    <script src="agent-stream.js"></script>
    <script src="persona.js"></script>
  </body>
</html>
```

`chat.js` and `agent-stream.js` are loaded here and arrive in Task 8. Create both as empty placeholder files in this task so the page does not 404 two scripts:

```bash
cd .
printf '/* The chat sidecar. Built in the next commit. */\n' > apps/workspace/chat.js
```

(`agent-stream.js` already exists from Task 6.)

- [ ] **Step 5: Write `apps/workspace/persona.js`**

```js
/* The page: pick a role, render its panel, and say honestly whether the agents
 * are reachable.
 *
 * The connection state comes from /api/runtime, not from the build. The old
 * screens rendered DATA.workspace.runtime — a constant baked into bundle.js at
 * build time — and therefore printed NOT CONNECTED in production while the
 * service was connected to all 52. Being wrong in the pessimistic direction is
 * still being wrong.
 */
const PERSONAS = DATA.personas.personas;
const CODES = Object.keys(PERSONAS).sort();

function currentCode() {
  const asked = new URLSearchParams(location.search).get("p");
  return PERSONAS[asked] ? asked : CODES[0];
}

function mountPicker(code) {
  const select = el("role-select");
  select.innerHTML = CODES.map(
    (c) => `<option value="${esc(c)}"${c === code ? " selected" : ""}>${esc(PERSONAS[c].title)}</option>`
  ).join("");
  select.addEventListener("change", () => {
    location.search = `?p=${encodeURIComponent(select.value)}`;
  });
}

function drawerBody(code) {
  const persona = PERSONAS[code];
  const byId = {};
  DATA.catalog.agents.forEach((a) => (byId[a.agent_id] = a));
  const rows = (persona.agents || [])
    .map((id) => byId[id])
    .filter(Boolean)
    .map(
      (a) =>
        `<dt class="mono">${esc(a.agent_id)} · ${esc(a.display_name)}</dt>` +
        `<dd>Pattern ${esc(a.pattern)} · ${esc(a.model_tier)} · APQC ${esc(a.apqc_code)}<br>` +
        `<span class="mono">${esc((a.source_tables || []).join(", "))}</span><br>` +
        `<span class="mono">${esc((a.tools || []).concat(a.traversals || []).join(", "))}</span></dd>`
    )
    .join("");
  return (
    `<dl>${rows}</dl>` +
    `<p>${esc(persona.code)} · value branch ` +
    `<span class="mono">${esc(branchesOf(persona.value_branch).join(", "))}</span></p>`
  );
}

/* The honest answer to "can this page reach the agents", asked of the wire. */
async function showRuntime() {
  const box = document.createElement("div");
  box.className = "runtime-state";
  box.textContent = "Checking whether the agents are reachable…";
  el("sidecar").prepend(box);
  try {
    const reply = await fetch("/api/runtime");
    const state = await reply.json();
    if (state.connected) {
      box.className = "runtime-state ok";
      box.textContent =
        `Connected. ${state.deployed.length} of ${state.expected} agents are deployed ` +
        "and can be asked a question.";
    } else {
      box.className = "runtime-state warn";
      box.textContent = `Not connected: ${state.detail}`;
    }
  } catch (err) {
    // The one case where the build-time constant is the true answer: the page
    // is open off disk or behind a static file server, and there is no API.
    box.className = "runtime-state warn";
    box.textContent = DATA.workspace.runtime.reason;
  }
}

const CODE = currentCode();
mountNav("workspace", "persona.html");
mountPicker(CODE);
el("role-lede").textContent = PERSONAS[CODE].title;
el("panel").innerHTML = renderPanel(CODE, DATA);
el("foot").innerHTML = technicalDrawer(drawerBody(CODE), "agent ids, tables, model tiers") +
  provenance();
showRuntime();
```

- [ ] **Step 6: Add the layout to `apps/workspace/workspace.css`**

```css
/* ---------- the role page ---------- */

/* Panel on the left, sidecar on the right, and one breakpoint. Below 1000px the
   sidecar goes underneath rather than shrinking: a chat transcript in a 200px
   column is not a chat transcript. */
.role-layout {
  display: grid; grid-template-columns: minmax(0, 1fr) 380px;
  gap: 20px; align-items: start;
}
@media (max-width: 1000px) {
  .role-layout { grid-template-columns: 1fr; }
}
.role-pick { display: inline-flex; align-items: center; gap: 8px; margin-top: 10px; }
.role-pick select { min-height: 44px; padding: 0 10px; font: inherit;
  background: var(--bg); color: var(--fg); border: 1px solid var(--border); }
.role-pick select:focus-visible { outline: none; box-shadow: 0 0 0 1px var(--accent); }

.pblock { margin-bottom: 26px; }
.pblock h2 { font-size: 15px; margin: 0 0 8px; }
.pblock h3 { font-size: 12.5px; color: var(--fg-muted); margin: 16px 0 6px;
  text-transform: none; font-weight: 600; }
.pnote { font-size: 13px; color: var(--fg-muted); max-width: 76ch; margin: 0 0 10px; }
.pcaveat { font-size: 12px; color: var(--fg-muted); max-width: 80ch; margin: 10px 0 0; }

.tbl-plain { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl-plain th { text-align: left; font-weight: 600; font-size: 11.5px;
  color: var(--fg-muted); border-bottom: 1px solid var(--border); padding: 6px 8px 6px 0; }
.tbl-plain td { padding: 7px 8px 7px 0; border-bottom: 1px solid var(--border-soft); }

.ev { margin-bottom: 14px; }
.ev-head { margin-top: 14px; }
.spark { width: 100%; height: 28px; display: block; }
.ev-range { font-size: 12px; color: var(--fg-muted); margin: 4px 0 0; }
.ev-caption { font-size: 11.5px; color: var(--fg-muted); margin: 3px 0 0; max-width: 80ch; }
.share-bar { height: 10px; background: var(--border-soft); }
.share-bar span { display: block; height: 100%; background: var(--accent); }

.signoffs { list-style: none; margin: 0; padding: 0; }
.signoffs li { display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  padding: 8px 0; border-top: 1px solid var(--border-soft); font-size: 13px; }
.ask { min-height: 44px; padding: 0 14px; font: inherit; cursor: pointer;
  background: var(--bg); color: var(--fg); border: 1px solid var(--border); }
.ask:focus-visible { outline: none; box-shadow: 0 0 0 1px var(--accent); }

.runtime-state { font-size: 12px; padding: 8px 10px; margin-bottom: 12px;
  border: 1px solid var(--border); }
.runtime-state.warn { border-color: var(--warn, var(--border)); }
```

If `--warn` or `--accent` is not defined in `apps/shared/tokens.css`, use the token that is — check with `grep -o '\-\-[a-z-]*' apps/shared/tokens.css | sort -u` and do not invent a new one.

- [ ] **Step 7: Delete the workbench**

```bash
cd .
git rm apps/workspace/workbench.html apps/workspace/workbench.js
```

The department view goes with it. That is the decision already taken: the persona page addresses the same content from the reader's role rather than from the org chart.

- [ ] **Step 8: Run the tests and make sure they pass**

Run:
```bash
cd .
python3 -m pytest tests/test_persona_page.py tests/test_shared_drawer.py -v
```
Expected: PASS, 13 tests.

- [ ] **Step 9: Look at it**

```bash
cd .
python3 -m uvicorn apps.workspace.server:app --port 8807 &
```
Open `http://127.0.0.1:8807/workspace/persona.html?p=P1` and then `?p=P4`, `?p=P8`. Check with the browser console open, and fix anything it reports:
- P1 shows three reached gap rows and one under "Also recorded at this site"
- P4 shows a **share** in block 2a (a bar, not a line), and an empty reached group with the sentence explaining why
- P8 shows the "no single part of the site" sentence in 2a, all four rows reached, and "Nothing on this role's list needs a sign-off"
- No console errors on any of the eight roles

- [ ] **Step 10: Commit**

```bash
cd .
git add apps/workspace/persona.html apps/workspace/persona.js apps/workspace/persona-panel.js \
        apps/workspace/chat.js apps/workspace/workspace.css tests/test_persona_page.py
git commit -m "feat(workspace): give each role one screen of what is true now"
```

---

## Task 8: `apps/workspace/chat.js` — the sidecar that actually talks

The answer to "it just feels like static agents". A question typed here reaches a deployed agent, and the 100 seconds it takes read as work happening.

**Files:**
- Create (replacing the placeholder): `apps/workspace/chat.js`
- Modify: `apps/workspace/persona.js` (mount the sidecar, wire the "Ask this one" buttons)
- Modify: `apps/workspace/workspace.css` (sidecar rules)
- Create: `tests/js/chat.test.js`

**Interfaces:**
- Consumes: `router.js` (`route`, `starterQuestions`), `agent-stream.js` (`streamAgent`), `shell.js` (`esc`), `plain.js`.
- Produces:
  - `mountChat(node, personaCode, DATA) -> { ask(question), pick(agentId) }` — `pick()` is what the panel's "Ask this one" buttons call.
  - `pickLine(decision, DATA) -> string` — **pure**, tested: the sentence the sidecar prints above an answer, naming the agent and the reason.

**What the sidecar shows, in order:**
1. The three derived starter questions as buttons, on first load (§5.1 — no example questions exist in the catalogue, so these are generated from the persona's own agents' capabilities).
2. A composer: a textarea and an Ask button.
3. On ask: the router's pick, printed with its reason, and the runners-up as one-click "Ask <name> instead" buttons. The user chose visible reasoning over a hidden decision; when the router is wrong, being wrong in the open with a one-click fix is the recovery path.
4. An activity log beneath, one line per step, appended live.
5. The answer text, streamed in.

**Two rules that are easy to get wrong:**
- **P8 has one agent.** With an empty `runners_up` the sidecar renders no "ask instead" control at all — not a disabled one, and not an empty container.
- **Only one stream at a time.** Asking again while a stream is open closes the first. Two open `EventSource`s would interleave two agents' text into one answer body.

- [ ] **Step 1: Write the failing test**

Create `tests/js/chat.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const C = require("../../apps/workspace/chat.js");

function loadData() {
  const file = path.join(__dirname, "..", "..", "apps", "shared", "data", "bundle.js");
  const text = fs.readFileSync(file, "utf8");
  return JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
}

const DATA = loadData();

test("the pick line names the agent and gives the reason", () => {
  const line = C.pickLine(
    { agent_id: "S01", reason: "It reads sensor readings.", runners_up: [] },
    DATA
  );
  assert.ok(line.includes("Cascading Failure Impact & Recovery Coordinator"),
    `the line does not name the agent: ${line}`);
  assert.ok(line.includes("It reads sensor readings."));
});

test("the pick line survives an agent id the catalogue does not hold", () => {
  const line = C.pickLine({ agent_id: "NOPE", reason: "because", runners_up: [] }, DATA);
  assert.ok(line.includes("NOPE"));
});

test("every persona's sidecar opens with three starters and a valid first pick", () => {
  for (const code of Object.keys(DATA.personas.personas)) {
    const opening = C.opening(code, DATA);
    assert.equal(opening.starters.length, 3, `${code} opened with ${opening.starters.length}`);
    assert.ok(opening.title.length > 0);
  }
});

test("P8 is offered nothing to change to, because it has one agent", () => {
  const R = require("../../apps/workspace/router.js");
  const decision = R.route("what happened last shift?", "P8", DATA);
  assert.deepEqual(C.alternatives(decision, DATA), []);
});

test("a persona with several agents is offered named alternatives", () => {
  const R = require("../../apps/workspace/router.js");
  const decision = R.route("which assets are most at risk?", "P1", DATA);
  const alts = C.alternatives(decision, DATA);
  assert.equal(alts.length, decision.runners_up.length);
  for (const alt of alts) {
    assert.ok(alt.agent_id && alt.label,
      "an alternative must carry both the id it asks and the name it shows");
    assert.notEqual(alt.label, alt.agent_id,
      "the button shows the agent's name, not its id — the id is jargon");
  }
});
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `cd . && node --test tests/js/chat.test.js`
Expected: FAIL — `C.pickLine is not a function`.

- [ ] **Step 3: Write the implementation**

Replace `apps/workspace/chat.js` entirely:

```js
/* The sidecar: the part of the workspace that is not a document.
 *
 * Everything else on the page states what is already recorded. This asks a
 * deployed agent a question and shows the answer arriving. A real question was
 * measured at 103.8 seconds, so the wait is real and cannot be designed away —
 * what can be designed is whether those seconds read as work happening or as a
 * spinner that cannot be told from a hang. Hence the activity log.
 *
 * The router's pick is printed, not hidden, with its reason and a one-click
 * change. Deterministic string matching over catalogue metadata is not
 * comprehension and will sometimes be wrong; being wrong in the open with a
 * one-click fix is the recovery path.
 */
var CHAT_ROUTER = typeof require !== "undefined" ? require("./router.js") : window;
var CHAT_STREAM = typeof require !== "undefined" ? require("./agent-stream.js") : window;

function _agentsById(DATA) {
  var byId = {};
  DATA.catalog.agents.forEach(function (a) { byId[a.agent_id] = a; });
  return byId;
}

function _name(agentId, DATA) {
  var agent = _agentsById(DATA)[agentId];
  return agent ? agent.display_name : agentId;
}

function pickLine(decision, DATA) {
  return "Asking " + _name(decision.agent_id, DATA) + ". " + decision.reason;
}

/* The buttons offered instead of the pick. Empty for a persona with one agent:
 * a control with nothing to change to is worse than no control. */
function alternatives(decision, DATA) {
  return (decision.runners_up || []).map(function (up) {
    return { agent_id: up.agent_id, label: _name(up.agent_id, DATA) };
  });
}

function opening(personaCode, DATA) {
  return {
    title: DATA.personas.personas[personaCode].title,
    starters: CHAT_ROUTER.starterQuestions(personaCode, DATA),
  };
}

/* Everything below touches the DOM and is exercised in the browser, not here. */
function mountChat(node, personaCode, DATA) {
  var open = null;          // the one live stream, if any
  var sessionId = "persona-" + personaCode + "-" + Date.now();
  var start = opening(personaCode, DATA);

  node.innerHTML =
    '<div class="chat-head"><h2>Ask your agents</h2>' +
    '<p class="pnote">These agents belong to this role. A real answer takes ' +
    "a minute or two — each step it takes appears below as it happens.</p></div>" +
    '<div class="starters">' +
    start.starters.map(function (q) {
      return '<button class="starter" type="button">' + esc(q) + "</button>";
    }).join("") +
    "</div>" +
    '<div class="transcript" id="transcript" aria-live="polite"></div>' +
    '<form class="composer" id="composer">' +
    '<label class="sr-only" for="question">Your question</label>' +
    '<textarea id="question" rows="3" placeholder="Ask about this role\'s work…"></textarea>' +
    '<button class="ask primary" type="submit">Ask</button>' +
    "</form>";

  var transcript = node.querySelector("#transcript");

  function block(html, cls) {
    var div = document.createElement("div");
    div.className = cls;
    div.innerHTML = html;
    transcript.appendChild(div);
    div.scrollIntoView({ block: "nearest" });
    return div;
  }

  function run(question, forcedAgentId) {
    if (open) open.close();          // one stream at a time, or two agents
    open = null;                     // interleave their text into one answer

    var decision = CHAT_ROUTER.route(question, personaCode, DATA);
    if (forcedAgentId) {
      decision = {
        agent_id: forcedAgentId,
        reason: "You chose this one.",
        runners_up: [],
      };
    }

    block("<p>" + esc(question) + "</p>", "you");
    var head = block("<p>" + esc(pickLine(decision, DATA)) + "</p>", "pick");

    alternatives(decision, DATA).forEach(function (alt) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "ask alt";
      button.textContent = "Ask " + alt.label + " instead";
      button.addEventListener("click", function () { run(question, alt.agent_id); });
      head.appendChild(button);
    });

    var log = block("", "log");
    var answer = block("", "answer");

    open = CHAT_STREAM.streamAgent({
      agentId: decision.agent_id,
      prompt: question,
      userId: "workspace",
      sessionId: sessionId,
      onStep: function (step) {
        if (step.kind === "text") {
          answer.textContent += step.text;
          return;
        }
        var line = document.createElement("p");
        line.className = step.kind === "step-failed" ? "step failed" : "step";
        line.textContent = step.text;
        log.appendChild(line);
      },
      onError: function (detail) {
        block("<p>" + esc(detail) + "</p>", "error");
      },
      onDone: function () {
        open = null;
        if (!answer.textContent.trim()) {
          answer.textContent = "The agent finished without writing an answer.";
        }
      },
    });
  }

  node.querySelectorAll(".starter").forEach(function (button) {
    button.addEventListener("click", function () { run(button.textContent); });
  });
  node.querySelector("#composer").addEventListener("submit", function (event) {
    event.preventDefault();
    var field = node.querySelector("#question");
    var question = field.value.trim();
    if (!question) return;
    field.value = "";
    run(question);
  });

  return {
    ask: function (question) { run(question); },
    pick: function (agentId) {
      run("What should I know about this before I sign it off?", agentId);
    },
  };
}

if (typeof module !== "undefined") {
  module.exports = { pickLine, alternatives, opening, mountChat };
}
```

- [ ] **Step 4: Wire it into `apps/workspace/persona.js`**

Append, after `showRuntime();`:

```js
/* The sidecar is mounted after the panel so the "Ask this one" buttons in the
   sign-off block have something to call. */
const CHAT = mountChat(el("sidecar"), CODE, DATA);

el("panel").addEventListener("click", (event) => {
  const button = event.target.closest("button.ask[data-agent]");
  if (!button) return;
  CHAT.pick(button.dataset.agent);
  el("sidecar").scrollIntoView({ behavior: "smooth", block: "start" });
});
```

`showRuntime()` prepends its box to the sidecar, and `mountChat` sets `innerHTML` on the same node — which would erase it. Fix the order by making `showRuntime()` append to a dedicated child instead. Change `showRuntime` to:

```js
async function showRuntime() {
  const box = document.createElement("div");
  box.className = "runtime-state";
  box.textContent = "Checking whether the agents are reachable…";
  el("sidecar").appendChild(box);
  ...
}
```
and call it **after** `mountChat`.

- [ ] **Step 5: Add the sidecar rules to `apps/workspace/workspace.css`**

```css
/* ---------- the chat sidecar ---------- */

.sidecar { border: 1px solid var(--border); padding: 14px; position: sticky; top: 12px; }
@media (max-width: 1000px) { .sidecar { position: static; } }
.chat-head h2 { font-size: 14px; margin: 0 0 6px; }
.starters { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.starter { min-height: 44px; padding: 8px 12px; text-align: left; font: inherit;
  cursor: pointer; background: var(--bg); color: var(--fg-muted);
  border: 1px solid var(--border-soft); }
.starter:hover, .starter:focus-visible { color: var(--fg); border-color: var(--border); }
.starter:focus-visible { outline: none; box-shadow: 0 0 0 1px var(--accent); }

.transcript { max-height: 55vh; overflow-y: auto; font-size: 13px; }
.transcript .you { margin: 12px 0 6px; font-weight: 600; }
.transcript .pick { font-size: 12px; color: var(--fg-muted); margin-bottom: 8px; }
.transcript .log { margin: 6px 0; }
.transcript .step { font-size: 12px; color: var(--fg-muted); margin: 3px 0;
  padding-left: 14px; position: relative; }
.transcript .step::before { content: "·"; position: absolute; left: 2px; }
.transcript .step.failed { color: var(--fg); }
.transcript .step.failed::before { content: "×"; }
.transcript .answer { white-space: pre-wrap; margin: 8px 0 4px; }
.transcript .error { font-size: 12px; margin: 8px 0; padding: 8px;
  border: 1px solid var(--border); }

.composer { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.composer textarea { font: inherit; font-size: 13px; padding: 8px; resize: vertical;
  background: var(--bg); color: var(--fg); border: 1px solid var(--border); }
.composer textarea:focus-visible { outline: none; box-shadow: 0 0 0 1px var(--accent); }
.ask.primary { border-color: var(--accent); }
.ask.alt { margin-left: 8px; min-height: 44px; }

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }

@media print { .sidecar { display: none; } }
```

- [ ] **Step 6: Run the tests and make sure they pass**

Run:
```bash
cd .
node --test 'tests/js/*.test.js'
```
Expected: PASS, all five JS test files.

- [ ] **Step 7: Ask a real agent a real question**

```bash
cd .
python3 -m uvicorn apps.workspace.server:app --port 8807 &
```
Open `http://127.0.0.1:8807/workspace/persona.html?p=P1`, click the first starter, and watch it to completion. This will take one to two minutes and will spend real model tokens — that is approved. Confirm:
- the pick line names an agent and gives a reason
- activity lines appear one at a time, in plain words, before the answer text
- the answer streams in
- the stream **stops** when the agent finishes and does not restart (watch the network panel: exactly one `/api/stream/` request)

The last of those is the one that matters. `EventSource` reconnects on close, and a page that silently re-asks a hundred-second question is a page that bills for it.

- [ ] **Step 8: Commit**

```bash
cd .
git add apps/workspace/chat.js apps/workspace/persona.js apps/workspace/workspace.css tests/js/chat.test.js
git commit -m "feat(workspace): let the reader ask their own agents, and watch the answer arrive"
```

---

## Task 9: the handover Run button, and connection state from the wire

Two fixes that belong together because both are the same fault: a screen stating something about the runtime that it read from a build-time constant.

**Files:**
- Modify: `apps/workspace/workspace.js` (`notConnected()`)
- Modify: `apps/workspace/handover.js` (Run button, streamed brief, the four sections)
- Modify: `apps/workspace/handover.html` (a mount point for the brief)
- Create: `tests/test_runtime_honesty.py`

**The bug (§1, §5.4):** `notConnected()` renders from `DATA.workspace.runtime`, a constant baked into `bundle.js` at build time. Five call sites therefore print "NOT CONNECTED" in production, where `/api/runtime` reports `connected: true, 52 of 52`. The screen is not merely silent; it is wrong in the pessimistic direction.

**The fix:** `notConnected()` renders a neutral placeholder and registers itself for a live update. One `/api/runtime` call per page — cached in a module-level promise, not one call per call site — resolves every registered block. The baked constant is kept as the fallback for the one case where it is true: the page opened off disk or behind a static file server, where there is no API to ask.

**The Run button (§7.1):** `DATA.catalog.swarms.S12` is `{coordinator:"S12", specialists:["S12-SP1","S12-SP2","S12-SP3"], critic:"S12-CRITIC"}`, and of those five **only `S12` has `is_entrypoint: true`**. The four sections on the sheet are the swarm's internal decomposition, not four things the reader may invoke. So the button issues **one** streamed call to S12 through the same `/api/stream/S12` the sidecar uses.

- [ ] **Step 1: Write the failing test**

Create `tests/test_runtime_honesty.py`:

```python
"""Gate: no screen states the runtime from the build.

DATA.workspace.runtime is written when bundle.js is generated. In production the
service is connected to all 52 agents and that constant still says it is not, so
five screens printed NOT CONNECTED at a reader looking at a working system.

This is a source check rather than a rendering check because the failure is
structural: the moment any screen reads that constant as its answer, the bug is
back, and it is invisible until someone opens the deployed page.
"""
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "apps" / "workspace"


def test_the_runtime_constant_is_only_ever_a_fallback():
    """Reading it is allowed. Reading it without asking the wire first is not."""
    for source in sorted(WORKSPACE.glob("*.js")):
        text = source.read_text()
        if "workspace.runtime" not in text and "WS.runtime" not in text:
            continue
        assert "/api/runtime" in text, (
            f"{source.name} reads the build-time runtime constant but never asks "
            "/api/runtime, so it will claim NOT CONNECTED in production"
        )


def test_the_handover_can_be_run():
    handover = (WORKSPACE / "handover.js").read_text()
    assert "/api/stream/S12" in handover or "streamAgent" in handover, (
        "the handover sheet has no way to run the brief it describes"
    )


def test_the_handover_runs_only_the_one_agent_the_catalogue_allows():
    """Four sections, one entrypoint. The other four are internal to the swarm."""
    handover = (WORKSPACE / "handover.js").read_text()
    for internal in ("S12-SP1", "S12-SP2", "S12-SP3", "S12-CRITIC"):
        assert f'"{internal}"' not in handover, (
            f"{internal} is not an externally callable entrypoint and must not be invoked"
        )


def test_the_run_control_and_the_activity_log_do_not_print():
    css = (WORKSPACE / "workspace.css").read_text()
    assert "@media print" in css
    assert ".run-brief" in css, "the Run button has no print rule, so it prints"


def test_the_four_sections_no_longer_claim_to_be_disconnected():
    handover = (WORKSPACE / "handover.js").read_text()
    assert "It has not run." not in handover
```

- [ ] **Step 2: Run it to make sure it fails**

Run:
```bash
cd .
python3 -m pytest tests/test_runtime_honesty.py -v
```
Expected: FAIL on all five.

- [ ] **Step 3: Fix `notConnected()` in `apps/workspace/workspace.js`**

Replace the function (currently lines 58–69) with:

```js
/* One /api/runtime call per page, shared by every block that needs the answer.
 *
 * This used to render DATA.workspace.runtime — a constant baked into bundle.js
 * when it was generated — so five call sites printed NOT CONNECTED in
 * production while the service was connected to all 52 agents. Being wrong in
 * the pessimistic direction is still being wrong, and it is the more expensive
 * kind here: it says the thing does not work.
 */
let _runtimePromise = null;

function runtimeState() {
  if (!_runtimePromise) {
    _runtimePromise = fetch("/api/runtime")
      .then((reply) => reply.json())
      // The one case where the baked constant is the true answer: no API to
      // ask, because the page is open off disk or behind a static file server.
      .catch(() => ({ connected: false, ...WS.runtime, offline: true }));
  }
  return _runtimePromise;
}

let _pendingBlocks = 0;

/** A block whose content depends on an agent having run. Renders neutral, then
 *  corrects itself from the wire. */
function notConnected(what) {
  const id = `nc-${(_pendingBlocks += 1)}`;
  runtimeState().then((state) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = state.connected
      ? '<div class="badge b-ok">READY</div>' +
        `<p class="nc-what">${esc(what)}</p>` +
        `<p class="nc-why">${esc(state.deployed.length)} of ${esc(state.expected)} ` +
        "agents are deployed and can be asked to write this.</p>"
      : '<div class="badge b-warn">⚠ NOT CONNECTED</div>' +
        `<p class="nc-what">${esc(what)}</p>` +
        `<p class="nc-why">${esc(state.detail || state.reason || "")}</p>` +
        (state.consequence ? `<p class="nc-why">${esc(state.consequence)}</p>` : "");
  });
  return (
    `<div class="not-connected" id="${id}">` +
    '<div class="badge">CHECKING…</div>' +
    `<p class="nc-what">${esc(what)}</p></div>`
  );
}
```

If `badge b-ok` is not a class the stylesheet defines, use the one it does — check `grep -n 'b-ok\|b-warn' apps/workspace/workspace.css` and do not invent a variant.

- [ ] **Step 4: Add the Run button to `apps/workspace/handover.js`**

Change `section(id, index)` so its `notConnected(...)` call no longer says "It has not run." — it names the tables that summariser is entitled to draw on, which is what the block was already documenting minus the false claim. Then add the Run control:

```js
/* One streamed call, to the one agent the catalogue permits.
 *
 * The sheet has four sections, and it is tempting to run four things. The
 * catalogue does not allow it: DATA.catalog.swarms.S12 names a coordinator,
 * three specialists and a critic, and only the coordinator carries
 * is_entrypoint. The other four are the swarm's internal decomposition, not
 * four things a reader may invoke.
 */
function mountRun() {
  const host = el("brief");
  host.innerHTML =
    '<div class="run-brief">' +
    '<button class="ask primary" id="run-brief" type="button">Write this brief now</button>' +
    '<p class="pnote">One agent writes the whole sheet. It takes a minute or two, ' +
    "and each step it takes appears below as it happens.</p></div>" +
    '<div class="brief-out" id="brief-out" aria-live="polite"></div>';

  let open = null;
  el("run-brief").addEventListener("click", () => {
    if (open) open.close();
    const out = el("brief-out");
    out.innerHTML = '<div class="log" id="brief-log"></div><div class="answer" id="brief-answer"></div>';
    const log = el("brief-log");
    const answer = el("brief-answer");
    open = streamAgent({
      agentId: "S12",
      prompt:
        "Write the shift handover brief for this site: what changed, what is at " +
        "risk, what the next shift must pick up, and what was left unsaid.",
      userId: "workspace",
      sessionId: `handover-${Date.now()}`,
      onStep: (step) => {
        if (step.kind === "text") {
          answer.textContent += step.text;
          return;
        }
        const line = document.createElement("p");
        line.className = step.kind === "step-failed" ? "step failed" : "step";
        line.textContent = step.text;
        log.appendChild(line);
      },
      onError: (detail) => {
        const line = document.createElement("p");
        line.className = "step failed";
        line.textContent = detail;
        log.appendChild(line);
      },
      onDone: () => { open = null; },
    });
  });
}
```

Call `mountRun()` where the page mounts its other sections.

Add the mount point to `apps/workspace/handover.html`, immediately after the page header and before the four sections:

```html
      <div id="brief"></div>
```

Add the two script tags the run control needs, before `handover.js`:

```html
    <script src="../shared/plain.js"></script>
    <script src="agent-stream.js"></script>
```

- [ ] **Step 5: Keep the Run control off paper**

Add to `apps/workspace/workspace.css`:

```css
/* The button and the step-by-step log are how the brief got here; the brief is
   what goes on paper. The beforeprint hook already opens every <details>, so
   the drawer prints in full. */
@media print {
  .run-brief { display: none; }
  .brief-out .log { display: none; }
  .brief-out .answer { white-space: pre-wrap; }
}
```

- [ ] **Step 6: Run the tests and make sure they pass**

Run:
```bash
cd .
python3 -m pytest tests/test_runtime_honesty.py -v
```
Expected: PASS, 5 tests.

- [ ] **Step 7: Watch it run, and watch it print**

With the local server up, open `http://127.0.0.1:8807/workspace/handover.html`. Confirm:
- the four sections say READY, not NOT CONNECTED (the local server has credentials)
- "Write this brief now" streams a brief, with steps in plain words
- the browser's print preview shows the brief and hides the button and the log

- [ ] **Step 8: Commit**

```bash
cd .
git add apps/workspace/workspace.js apps/workspace/handover.js apps/workspace/handover.html \
        apps/workspace/workspace.css tests/test_runtime_honesty.py
git commit -m "fix(workspace): read the connection from the wire, and let the handover run"
```

---

## Task 10: the copy rewrite — the case application

Five screens: the chooser and the four case screens plus the graph. Rule 1, the first screenful is plain. Rule 2, one `<details class="tbl">` titled "Technical detail" at the end of each.

**Files:**
- Modify: `apps/index.html`, `apps/landing.js`
- Modify: `apps/case/index.html`, `apps/case/proposition.js`
- Modify: `apps/case/scenario.html`, `apps/case/scenario.js`
- Modify: `apps/case/value.html`, `apps/case/value.js`
- Modify: `apps/case/solution.html`, `apps/case/solution.js`
- Modify: `apps/case/graph.html`, `apps/case/graph.js`
- Create: `tests/test_screen_copy.py`

**Interfaces:**
- Consumes: `technicalDrawer(bodyHtml, hint)` from Task 5, and the `JARGON` map in `apps/shared/plain.js` from Task 1.
- Produces: nothing other tasks consume.

**The substitutions, applied to every heading, lede and table header in these five screens:**

| on screen today | plain replacement |
|---|---|
| entrypoint | agent you can talk to |
| HITL / human-in-the-loop | needs your sign-off |
| swarm | agent team |
| traversal | connection trace |
| Pattern A / Pattern B | team agent / specialist agent |
| value branch | where the money is |
| APQC code | standard process area (the code itself moves to the drawer) |
| provenance | where this came from |
| p90 | the best day |
| median | the ordinary day |
| node / edge | machine / link |
| blast radius | what else stops |
| SC-1 … SC-4 | removed from headings entirely |
| model tier / reasoning / flash | drawer only |

**What must not change:** the numbers, the `caption`/`method`/`caveat` strings, the provenance footer, and the commodity neutrality. The copy still says "contained metal" and still expresses money as ranges.

- [ ] **Step 1: Write the failing test**

Create `tests/test_screen_copy.py`:

```python
"""Gate: every screen speaks plainly, and hides its machinery at the end.

The instruction was explicit — a functional reader gets plain language and
tables, and technical detail goes at the end behind a collapsible. Both halves
are checkable: the jargon is a fixed list, and the drawer is a fixed component.

The check is on the visible sources of each screen — its HTML and the JS that
renders into it — and it deliberately excludes the drawer's own contents, which
is where the jargon is supposed to be.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
APPS = REPO / "apps"

SCREENS = {
    "apps/index.html": ["apps/landing.js"],
    "apps/case/index.html": ["apps/case/proposition.js"],
    "apps/case/scenario.html": ["apps/case/scenario.js"],
    "apps/case/value.html": ["apps/case/value.js"],
    "apps/case/solution.html": ["apps/case/solution.js"],
    "apps/case/graph.html": ["apps/case/graph.js"],
    "apps/workspace/index.html": ["apps/workspace/cockpit.js"],
    "apps/workspace/swarm.html": ["apps/workspace/swarm.js"],
    "apps/workspace/persona.html": ["apps/workspace/persona.js", "apps/workspace/persona-panel.js"],
    "apps/workspace/handover.html": ["apps/workspace/handover.js"],
}

# Words a functional reader should not have to meet in body copy. Each is
# allowed inside the technical drawer, which is what the drawer is for.
JARGON = [
    "entrypoint", "HITL", "human-in-the-loop", "traversal",
    "Pattern A", "Pattern B", "value branch", "APQC", "blast radius",
    "p90", "model tier",
]


def visible_text(paths):
    """Everything the screen shows, minus what is inside a technical drawer."""
    text = "\n".join((REPO / p).read_text() for p in paths)
    # technicalDrawer(...) calls and <details class="tbl"> blocks are the
    # sanctioned home for every term below.
    text = re.sub(r"technicalDrawer\(.*?\n\s*\);", "", text, flags=re.S)
    text = re.sub(r"<details[^>]*class=\"[^\"]*tbl[^\"]*\".*?</details>", "", text, flags=re.S)
    return text


def test_every_screen_ends_with_exactly_one_technical_drawer():
    for screen, scripts in SCREENS.items():
        sources = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        count = sources.count("technicalDrawer(")
        assert count == 1, f"{screen} has {count} technical drawers; it must have exactly one"


def test_no_jargon_survives_outside_the_drawer():
    problems = []
    for screen, scripts in SCREENS.items():
        text = visible_text([screen] + scripts)
        for term in JARGON:
            if re.search(rf"\b{re.escape(term)}\b", text, re.I):
                problems.append(f"{screen}: {term}")
    assert not problems, "jargon left in body copy:\n" + "\n".join(problems)


def test_the_screen_codes_are_gone_from_headings():
    for screen, scripts in SCREENS.items():
        text = visible_text([screen] + scripts)
        assert not re.search(r"\bSC-[1-4]\b", text), f"{screen} still labels itself SC-n"


def test_the_copy_stays_commodity_neutral():
    metals = ["copper", "gold", "nickel", "iron ore", "bauxite", "zinc", "lithium"]
    for screen, scripts in SCREENS.items():
        text = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        for metal in metals:
            assert not re.search(rf"\b{metal}\b", text, re.I), (
                f"{screen} names {metal}; the copy says 'contained metal'"
            )


def test_the_only_money_figure_is_the_one_the_repository_establishes():
    """Every other magnitude is [CLIENT INPUT REQUIRED], and ranges, not points."""
    for screen, scripts in SCREENS.items():
        text = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        for hit in re.findall(r"\$[\d,]+", text):
            assert False, f"{screen} prints the literal money figure {hit}"
```

- [ ] **Step 2: Run it to make sure it fails**

Run:
```bash
cd .
python3 -m pytest tests/test_screen_copy.py -v
```
Expected: FAIL — jargon in every screen, and no drawers.

The workspace screens are in the table too and are fixed in Task 11. Until then this file is red for them. That is deliberate: it is the same list, and splitting it into two files would let one half's rules drift from the other's.

- [ ] **Step 3: Read each screen and rewrite its body copy**

For each of the six case-side screens in turn:

```bash
cd .
python3 -m pytest tests/test_screen_copy.py::test_no_jargon_survives_outside_the_drawer -v 2>&1 | head -60
```

The failure output names each screen and each term. Work through it screen by screen. For each term:
- If it is a **label the reader needs**, replace it with its plain form from the table above.
- If it is a **fact the reader does not need on first read** — an agent id, an APQC code, a model tier, a table name, a pattern letter — move it into that screen's drawer.
- Never delete a fact. The drawer exists so nothing has to be dropped to make the page plain.

Prefer a table to a paragraph wherever the content is comparative. The instruction was explicit that a functional reader reads tables.

- [ ] **Step 4: Add one drawer to each screen**

At the end of each screen's render, before `provenance()`:

```js
document.getElementById("foot").innerHTML =
  technicalDrawer(drawerBody(), "agent ids, standard process codes, tables") +
  provenance();
```

`drawerBody()` is written per screen and holds exactly what was stripped from the body. For `apps/case/graph.html`, that is the node and edge type names, the three traversal ids and the table names behind them; for `apps/case/solution.html`, the pattern letters, the swarm ids and the model tiers.

- [ ] **Step 5: Run the tests for the case screens**

```bash
cd .
python3 -m pytest tests/test_screen_copy.py -v 2>&1 | tail -30
```
Expected: the four case-side assertions report only workspace screens. `test_the_copy_stays_commodity_neutral` and `test_the_only_money_figure_is_the_one_the_repository_establishes` must be fully green — they were green before this task and must not regress.

- [ ] **Step 6: Look at all six screens**

Open each at `http://127.0.0.1:8807/`, at a 390px viewport and at 1440px. Confirm the first screenful of each is plain, the drawer is closed on arrival, and opening it reveals the machinery. No console errors.

- [ ] **Step 7: Commit**

```bash
cd .
git add apps/index.html apps/landing.js apps/case tests/test_screen_copy.py
git commit -m "feat(case): say it in the reader's words, and keep the machinery at the end"
```

---

## Task 11: the copy rewrite — the workspace application

The same two rules, applied to the cockpit, the agent-teams screen and the handover sheet. The persona page was written plainly in Tasks 7 and 8 and needs only its drawer verified.

**Files:**
- Modify: `apps/workspace/index.html`, `apps/workspace/cockpit.js`
- Modify: `apps/workspace/swarm.html`, `apps/workspace/swarm.js`
- Modify: `apps/workspace/handover.html`, `apps/workspace/handover.js`
- Modify: `apps/workspace/hitl.js` (the approval modal's copy, raised from both)

**Interfaces:** the same as Task 10. No new module.

**Three points specific to these screens:**
- The nav label is already "Agent teams" (Task 5). The screen's own headings must match it — a nav that says one thing and a heading that says another teaches the reader that the words are arbitrary.
- The corner pill reads `52 entrypoints · 100 agents`. It becomes **"52 agents you can talk to · 100 in the teams behind them"**, which is the same two numbers from `DATA.catalog.counts` and is the distinction the reader actually needs.
- `hitl.js` is the sign-off modal. "HITL" becomes "needs your sign-off" throughout, including in the two `notConnected()` call sites at lines 111 and 209, which Task 9 already changed to correct themselves from the wire.

- [ ] **Step 1: Run the failing test to get the list**

```bash
cd .
python3 -m pytest tests/test_screen_copy.py -v 2>&1 | tail -40
```
Expected: FAIL, naming only workspace screens.

- [ ] **Step 2: Change the corner pill in `apps/shared/shell.js`**

```js
  workspace: {
    items: WORK_NAV,
    brand: "Mining Agents · Site workspace",
    pill: () => ({
      text:
        `${DATA.catalog.counts.entrypoints} agents you can talk to · ` +
        `${DATA.catalog.counts.agent_nodes} in the teams behind them`,
      title: "Source of every figure on this page",
    }),
  },
```

- [ ] **Step 3: Rewrite the three screens' body copy**

Same method as Task 10, Step 3: work the failure list term by term, replacing what the reader needs and moving what they do not into the drawer. Never delete a fact.

- [ ] **Step 4: Add one drawer to each of the three screens**

Same shape as Task 10, Step 4. The persona page already has one from Task 7; confirm rather than add.

- [ ] **Step 5: Run the whole suite**

```bash
cd .
python3 -m pytest -q
node --test 'tests/js/*.test.js'
```
Expected: everything green, including `tests/test_workspace_image.py` and `tests/test_screen_copy.py` in full.

- [ ] **Step 6: Look at all ten screens**

At 390px and at 1440px, through the local server. Every screen: plain first screenful, exactly one closed drawer at the end, no console errors, nav and headings agreeing.

- [ ] **Step 7: Commit**

```bash
cd .
git add apps/shared/shell.js apps/workspace
git commit -m "feat(workspace): say it in the reader's words across the remaining screens"
```

---

## Task 12: deploy, and verify against the deployed article

Nothing counts until it has been seen working on the deployed revision. A static file server on this laptop shows the same pages and proves nothing about the deploy.

**Files:** none changed. This task ships and checks.

- [ ] **Step 1: Run every gate one more time**

```bash
cd .
python3 -m pytest -q
node --test 'tests/js/*.test.js'
```
Expected: all green. Do not deploy over a red suite.

- [ ] **Step 2: Deploy**

```bash
cd .
python3 scripts/deploy_apps.py
```

This rebuilds and redeploys `mag-workspace` in `us-central1` on project `your-gcp-project-id`. It is approved. If the script needs a flag this plan does not name, read its `--help` rather than guessing.

- [ ] **Step 3: Open the deployed revision**

The service is deployed `--no-allow-unauthenticated` because the org policy `constraints/iam.allowedPolicyMemberDomains` refuses the `allUsers` binding, so the URL cannot simply be opened. The proxy is the way in:

```bash
cd .
python3 scripts/proxy_workspace.py --port 8805 \
  --target https://YOUR-WORKSPACE-SERVICE.a.run.app
```

Open `http://127.0.0.1:8805/`.

- [ ] **Step 4: Check the runtime is honestly reported**

```bash
curl -s http://127.0.0.1:8805/api/runtime | python3 -m json.tool | head -20
```
Expected: `"connected": true` and 52 deployed. Then open `http://127.0.0.1:8805/workspace/handover.html` and confirm the four sections say READY rather than NOT CONNECTED. That single line is the bug this whole plan started from.

- [ ] **Step 5: Ask a real agent a real question, on the deployed revision**

Open `http://127.0.0.1:8805/workspace/persona.html?p=P1`, click a starter, and watch it to completion. Confirm:
- the activity log fills with plain lines while the answer is still coming
- the answer streams in
- exactly one `/api/stream/` request in the network panel — no reconnect
- the whole thing completes without a console error

Repeat once on `?p=P6`, which reaches all four gap rows and so exercises a different panel.

- [ ] **Step 6: Walk all ten screens, at both sizes**

At 390px and 1440px, through the proxy. For each: first screenful plain, exactly one closed "Technical detail" drawer at the end, no console errors, no horizontal scroll at 390px.

- [ ] **Step 7: Push**

```bash
cd .
git push origin feat/agents-phase-5
```

Explicitly approved for this branch, this once.

- [ ] **Step 8: Clean up the scratch left from the design work**

```bash
rm -rf /tmp/slimcheck-1 /tmp/idtok /tmp/s12url /tmp/sse_probe.txt /tmp/plan-part2.md /tmp/plan-part3.md
```

---

## What is deliberately not in this plan

- **Fixing `blast_radius` on S01.** It returns `success=false`, which is a real backend defect. The frontend names the failure honestly and does not filter it. The fix is upstream and is tracked separately.
- **Filtering or rewriting model output.** The agents currently leak plumbing into their prose. Editing it here would put the frontend in the business of deciding what the agent said.
- **Any change to the 52 agent services, the catalogue, or BigQuery.**
- **Making the deployed URL publicly reachable.** The org policy still blocks it; `scripts/proxy_workspace.py` remains the way in, and this is not to be touched without a separate go-ahead.
- **A build step, a framework, or any external dependency.**
