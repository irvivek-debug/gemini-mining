/* Guards on the increment that added persona portraits, agent launch links,
 * business logic + decision flow on the deep dive, and the Screen 5 logical
 * and data architecture.
 *
 * These read the generated and hand-authored data files directly rather than
 * booting the page: the failures worth catching here are data failures --
 * an agent with no invoke URL, a chip token nothing substitutes, a graph edge
 * pointing at a table that is not in the graph -- and each of those renders as
 * a plausible-looking screen rather than an error.
 */
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const FRONTEND = path.join(__dirname, "..", "..", "apps", "frontend");

function loadFrontendGlobals() {
  const sandbox = { window: {}, document: undefined };
  vm.createContext(sandbox);
  for (const file of ["data.js", "data-static.js", "data-graph.js"]) {
    vm.runInContext(fs.readFileSync(path.join(FRONTEND, file), "utf8"), sandbox, { filename: file });
  }
  return sandbox.window;
}

const W = loadFrontendGlobals();
const AGENTS = Object.values(W.agentCatalogData);
const read = (f) => fs.readFileSync(path.join(FRONTEND, f), "utf8");

/* -------------------------------------------------- agent launch links -- */

test("every agent carries both a workspace link and its own invoke endpoint", () => {
  assert.equal(AGENTS.length, 101);
  for (const a of AGENTS) {
    assert.ok(/^https:\/\//.test(a.geminiUrl), `${a.id} has no Gemini Enterprise URL`);
    assert.ok(/^https:\/\//.test(a.invokeUrl), `${a.id} has no invoke URL`);
  }
});

test("the invoke URL addresses the agent it sits on, and the workspace URL does not", () => {
  // The whole reason both links exist: one is per-agent, one is shared. If the
  // invoke URL ever stopped carrying the agent's own id, the launch button
  // would quietly become a second copy of the workspace button.
  for (const a of AGENTS) {
    assert.ok(a.invokeUrl.endsWith("/" + a.id.toLowerCase()),
      `${a.id} invoke URL does not end in its own id: ${a.invokeUrl}`);
  }
  const workspaces = new Set(AGENTS.map((a) => a.geminiUrl));
  assert.equal(workspaces.size, 1, "the Gemini Enterprise workspace should be one shared URL");
});

test("the deep dive states that the workspace link is shared, so nobody reads it as per-agent", () => {
  const app = read("app.js");
  assert.match(app, /Gemini Enterprise opens the shared workspace/);
});

/* ------------------------------------------------------ business logic -- */

const BIZ_KEYS = ["owns", "boardStake", "answersTo", "plMove", "cannot", "onFailure"];

test("every agent has a complete business-logic block", () => {
  for (const a of AGENTS) {
    assert.ok(a.business, `${a.id} has no business block`);
    for (const k of BIZ_KEYS) {
      assert.ok(a.business[k] && a.business[k].length > 15,
        `${a.id}.business.${k} is missing or too short to be a sentence`);
    }
  }
});

test("the business block reads as business language, not as enum values", () => {
  // A regression here means a lexicon lookup was replaced by a raw field and
  // the card is showing L2_BOUNDED_ACTION to a chief executive.
  for (const a of AGENTS) {
    for (const k of BIZ_KEYS) {
      assert.doesNotMatch(a.business[k], /[A-Z]{2,}_[A-Z]/,
        `${a.id}.business.${k} leaks a raw enum: ${a.business[k]}`);
    }
  }
});

test("what an agent cannot do always names the limit, never leaves it implied", () => {
  for (const a of AGENTS) {
    assert.match(a.business.cannot, /cannot|no write access|Recommends only/i,
      `${a.id} does not state a limit: ${a.business.cannot}`);
  }
});

/* ------------------------------------------------------- decision flow -- */

test("every agent has the same five-stage decision flow, in order", () => {
  const expected = ["trigger", "reads", "decides", "approval", "lands"];
  for (const a of AGENTS) {
    assert.deepEqual((a.flow || []).map((s) => s.key), expected, `${a.id} flow is wrong`);
    for (const stage of a.flow) {
      assert.ok(stage.value && stage.detail, `${a.id} stage ${stage.key} is incomplete`);
    }
  }
});

test("the flow's reads stage lists the tables the agent actually declares", () => {
  for (const a of AGENTS) {
    const reads = a.flow.find((s) => s.key === "reads");
    const declared = a.provenance.map((p) => p.name);
    assert.match(reads.value, new RegExp("^" + declared.length + " grounding table"),
      `${a.id} reads stage disagrees with its provenance count`);
    for (const t of declared) {
      assert.ok(reads.detail.includes(t), `${a.id} reads stage omits ${t}`);
    }
  }
});

test("an agent needing human release says so in both the approval and the landing stage", () => {
  for (const a of AGENTS) {
    const approval = a.flow.find((s) => s.key === "approval");
    const lands = a.flow.find((s) => s.key === "lands");
    if (a.hitl) {
      assert.match(approval.value, /Human release required/, `${a.id}`);
      assert.match(lands.value, /ERP staging buffer/, `${a.id}`);
    } else {
      assert.match(approval.value, /Advisory/, `${a.id}`);
    }
    assert.match(lands.detail, /Never a PLC|Nothing reaches plant control/, `${a.id}`);
  }
});

test("every flow stage carries a business reading as well as the mechanism", () => {
  for (const a of AGENTS) {
    for (const stage of a.flow) {
      assert.ok(stage.business, `${a.id} stage ${stage.key} has no business line`);
      assert.ok(stage.business.length > 40,
        `${a.id} stage ${stage.key} business line is too short to say anything`);
      assert.notEqual(stage.business, stage.detail,
        `${a.id} stage ${stage.key} repeats the mechanism instead of translating it`);
    }
  }
});

test("the business reading never prints a table name or a service account at the reader", () => {
  // The whole point of this line is that it is readable without knowing the
  // schema. A snake_case identifier leaking into it means a lexicon lookup was
  // skipped -- except on the trigger stage, where naming the human group that
  // can call the agent is the useful fact.
  for (const a of AGENTS) {
    for (const stage of a.flow) {
      if (stage.key === "trigger") continue;
      assert.doesNotMatch(stage.business, /[a-z]+_[a-z]+/,
        `${a.id} stage ${stage.key} leaks an identifier: ${stage.business}`);
    }
  }
});

test("the reads line names every table in plain English, and counts them consistently", () => {
  for (const a of AGENTS) {
    const reads = a.flow.find((s) => s.key === "reads");
    // Checked against the emitted list rather than by parsing the sentence: a
    // plain name can contain the word "and" ("vessel and berth schedules"), so
    // counting separators in prose is not a sound way to count sources.
    assert.equal(reads.sources.length, a.provenance.length,
      `${a.id} names a different number of sources than it declares tables`);
    for (const name of reads.sources) {
      assert.doesNotMatch(name, /_/, `${a.id} source "${name}" is not plain English`);
      assert.ok(reads.business.includes(name),
        `${a.id} omits "${name}" from its reads line`);
    }
  }
});

test("a claim about a critic is only made where a critic exists", () => {
  // The coordinator and specialist lines promise the swarm's critic will attack
  // the finding. Every swarm has one today; if that ever stopped being true the
  // line would be a false assurance on a sales screen.
  const ids = new Set(AGENTS.map((a) => a.id));
  for (const a of AGENTS) {
    const decides = a.flow.find((s) => s.key === "decides");
    if (!/critic/i.test(decides.business)) continue;
    if (a.pattern === "A_CRITIC") continue; // it is the critic
    const swarm = a.id.split("-")[0];
    assert.ok(ids.has(swarm + "-R-CRITIC"),
      `${a.id} promises a critic, but ${swarm} has none`);
  }
});

test("a solver claim is only made where the agent actually holds tools", () => {
  for (const a of AGENTS) {
    const decides = a.flow.find((s) => s.key === "decides");
    const claimsSolver = /runs in a named solver/.test(decides.business);
    assert.equal(claimsSolver, a.tools.length > 0,
      `${a.id} solver claim disagrees with its tool list`);
  }
});

test("the human-caller line is only used for agents a person can actually reach", () => {
  for (const a of AGENTS) {
    const trigger = a.flow.find((s) => s.key === "trigger");
    if (!/A person can ask for this directly/.test(trigger.business)) continue;
    assert.equal(a.endpoint_type || a.endpoint, "cloud_run",
      `${a.id} claims direct human access but is not reachable over HTTPS`);
    assert.match(trigger.detail, /@/, `${a.id} names no caller`);
  }
});

test("every stage's business line is rendered, not just carried in the data", () => {
  const app = read("app.js");
  assert.match(app, /flow-business/);
  assert.match(read("app.css"), /\.flow-business \{/);
});

/* --------------------------------------------------- persona portraits -- */

test("every persona has a portrait and no two personas share one", () => {
  const personas = Object.entries(W.personaPRDData);
  assert.equal(personas.length, 8);
  const seen = new Map();
  for (const [key, p] of personas) {
    assert.ok(p.avatar && /^https:\/\//.test(p.avatar), `${key} has no portrait`);
    assert.ok(!seen.has(p.avatar), `${key} reuses ${seen.get(p.avatar)}'s portrait`);
    seen.set(p.avatar, key);
  }
});

test("the portrait has an initials fallback behind it, because it loads from a remote host", () => {
  assert.match(read("index.html"), /id="persona-hero-initials"/);
  assert.match(read("app.css"), /\.persona-avatar-fallback/);
});

/* ------------------------------------------- Screen 5: logical stack ---- */

test("the architecture runs the whole way from the screen to the source", () => {
  const keys = W.architectureModel.layers.map((l) => l.key);
  assert.equal(keys[0], "experience", "the stack must start where a person is");
  assert.equal(keys[keys.length - 1], "sources", "the stack must end at the data's origin");
  assert.ok(keys.includes("platform"), "the data platform layer is missing");
});

test("every layer declares both directions of traffic", () => {
  for (const l of W.architectureModel.layers) {
    assert.ok(l.request && l.evidence, `${l.key} does not say what travels through it`);
    assert.ok(l.chips.length > 0, `${l.key} has no chips`);
  }
});

test("every chip token has something to substitute it", () => {
  // An unsubstituted {token} renders its own braces onto a customer-facing
  // screen. The renderer's token set is the contract; this is the check that
  // the content and the renderer still agree.
  const supplied = new Set(
    (read("app.js").match(/^\s{8}(\w+):/gm) || []).map((m) => m.trim().replace(":", ""))
  );
  for (const l of W.architectureModel.layers) {
    for (const chip of l.chips) {
      for (const m of chip.matchAll(/\{(\w+)\}/g)) {
        assert.ok(supplied.has(m[1]), `chip token {${m[1]}} on layer ${l.key} has no source`);
      }
    }
  }
});

test("the controls are cross-cutting, and the OT boundary is one of them", () => {
  const controls = W.architectureModel.controls;
  assert.ok(controls.length >= 4);
  const boundary = controls.find((c) => c.key === "boundary");
  assert.ok(boundary, "the OT boundary is not declared as a control");
  assert.match(boundary.rule, /no agent holds write access/i);
  for (const c of controls) {
    assert.match(c.spans, /→/, `${c.key} does not say which layers it spans`);
  }
});

test("Screen 5 no longer carries the retired governance blocks", () => {
  const html = read("index.html");
  for (const dead of ["gov-stack-steps", "gov-staging-steps", "gov-provenance-steps"]) {
    assert.ok(!html.includes(dead), `${dead} survived the Screen 5 rewrite`);
  }
  assert.match(html, /id="arch-stack"/);
  assert.match(html, /id="datagraph-svg"/);
});

/* -------------------------------------------- Screen 5: data graph ------ */

test("the graph is built from the real dataset, not an illustration", () => {
  const m = W.dataGraph.meta;
  assert.equal(m.dataset, "mining_data");
  assert.ok(m.tableCount > 30, "too few tables to be the real dataset");
  assert.equal(m.tableCount, W.dataGraph.nodes.length);
  assert.equal(m.edgeCount, W.dataGraph.edges.length);
});

test("snapshot and probe copies are excluded and counted, never silently dropped", () => {
  const ids = W.dataGraph.nodes.map((n) => n.id);
  for (const id of ids) {
    assert.doesNotMatch(id, /_original_\d{8}$/, `${id} is a snapshot copy`);
    assert.doesNotMatch(id, /_probe$/, `${id} is a probe table`);
  }
  assert.ok(W.dataGraph.meta.excludedCount > 0);
  assert.equal(W.dataGraph.meta.excluded.length, W.dataGraph.meta.excludedCount);
});

test("every edge joins two tables that are in the graph", () => {
  const ids = new Set(W.dataGraph.nodes.map((n) => n.id));
  for (const e of W.dataGraph.edges) {
    assert.ok(ids.has(e.source), `edge references missing table ${e.source}`);
    assert.ok(ids.has(e.target), `edge references missing table ${e.target}`);
    assert.ok(e.keys.length > 0, `${e.source}->${e.target} has no join key`);
  }
});

test("every node carries the columns and counts the detail panel reads", () => {
  for (const n of W.dataGraph.nodes) {
    assert.equal(n.columns.length, n.columnCount, `${n.id} column count disagrees with its columns`);
    assert.ok(typeof n.rows === "number", `${n.id} has no row count`);
    assert.ok(n.layerLabel && n.domainLabel, `${n.id} is unclassified`);
    assert.ok(Array.isArray(n.readBy), `${n.id} has no readBy list`);
  }
});

test("every layer and domain the chrome offers has at least one table behind it", () => {
  const layers = new Set(W.dataGraph.nodes.map((n) => n.layer));
  const domains = new Set(W.dataGraph.nodes.map((n) => n.domain));
  for (const l of W.dataGraph.layers) assert.ok(layers.has(l.key), `layer ${l.key} has no tables`);
  for (const d of W.dataGraph.domains) assert.ok(domains.has(d.key), `domain ${d.key} has no tables`);
});

test("at least one table records which agents declare it", () => {
  // A generator that silently failed to import the catalogue produced a graph
  // where nothing was read by anything, which looked fine on screen.
  const withReaders = W.dataGraph.nodes.filter((n) => n.readBy.length > 0);
  assert.ok(withReaders.length > 0, "no table names a single agent that reads it");
});

/* ------------------------------------------------- interaction guards --- */

test("a press only becomes a drag after travelling, so a click can still inspect", () => {
  // Without the threshold the drag handler captured the pointer and the click
  // landed on the canvas, deselecting instead of opening the table.
  const app = read("app.js");
  assert.match(app, /DRAG_THRESHOLD/);
  assert.match(app, /if \(pending && !dragging\)/);
});

test("a deep dive asked for an unknown agent shows nothing rather than a stranger", () => {
  const app = read("app.js");
  assert.match(app, /var a = agentId \? all\[agentId\] : all\[ids\[0\]\];/);
});

test("squad members the registry does not hold are labelled, not linked", () => {
  // Two personas name L1 arbiters that are not registered agents. A launch
  // link on those cards would point at an endpoint that does not exist.
  const app = read("app.js");
  assert.match(app, /Not in the agent registry/);
  const squadIds = Object.values(W.personaPRDData).flatMap((p) => p.squad.map((s) => s.id));
  const unregistered = squadIds.filter((id) => !W.agentCatalogData[id]);
  assert.ok(unregistered.length > 0,
    "no unregistered squad member left -- if the registry gained them, drop this guard");
});

/* ----------------------------------------- the fifth screen's rename ----- */

test("the fifth screen is Logical Architecture, routed at #architecture", () => {
  const html = read("index.html");
  assert.match(html, /id="tab-architecture"[^>]*>Logical Architecture</);
  assert.match(html, /id="pane-architecture"/);
  assert.match(read("app.js"), /"ecosystem", "architecture"\]/);
});

test("no id or route still says governance", () => {
  const html = read("index.html");
  for (const stale of ["tab-governance", "pane-governance", "gov-audit-line",
                       "Governance &amp; Safety"]) {
    assert.ok(!html.includes(stale), `${stale} survived the rename`);
  }
});

test("links already shared as #governance still land on the right screen", () => {
  // The screen was called governance when its URL went out to people. A rename
  // that silently drops them onto the first screen is a broken link that looks
  // like a working one.
  const app = read("app.js");
  assert.match(app, /LEGACY_SCREEN\s*=\s*\{\s*governance:\s*"architecture"\s*\}/);
  // Applied on both entry points: a click-through and a cold load.
  const uses = app.match(/LEGACY_SCREEN\[\w+\]/g) || [];
  assert.ok(uses.length >= 2,
    `the legacy map is read ${uses.length} time(s); both go() and init() need it`);
});

/* ----------------------------------------------------------- motion ----- */

const CSS = read("app.css");

test("entry animations are scoped to a class that gets removed", () => {
  // Held on, the class re-applies its own opacity:0 every time the pane is
  // shown again -- display:none restarts CSS animations -- which made the
  // stack replay and briefly vanish on every tab click.
  for (const rule of [".arch-stack.motion-playing", ".decision-flow.motion-playing",
                      "#datagraph-svg.motion-playing"]) {
    assert.ok(CSS.includes(rule), `${rule} is not scoped to the removable class`);
  }
  assert.ok(!/motion-in/.test(CSS), "the old always-on class is still in the stylesheet");
  assert.match(read("app.js"), /node\.classList\.remove\("motion-playing"\)/);
});

test("the motion stays subtle: nothing travels more than 5px", () => {
  // "Very subtle" is the requirement, so it is measured rather than trusted.
  const travels = [...CSS.matchAll(/translateY\((-?[\d.]+)px\)/g)].map((m) => Math.abs(+m[1]));
  assert.ok(travels.length > 0, "no translateY found — has the motion section moved?");
  for (const t of travels) {
    assert.ok(t <= 5, `a ${t}px translate is not subtle`);
  }
});

test("the motion stays subtle: no entry animation runs longer than 0.4s", () => {
  const section = CSS.slice(CSS.indexOf("   MOTION"));
  const durations = [...section.matchAll(/animation:\s*\w+\s+([\d.]+)s/g)].map((m) => +m[1]);
  assert.ok(durations.length > 0, "no animation durations found in the motion section");
  for (const d of durations) {
    // The seam drift is the one continuous animation and is deliberately slow;
    // everything else is an entry and must be brief.
    assert.ok(d <= 0.4 || d === 3.4, `a ${d}s animation is not subtle`);
  }
});

test("only one animation on the page repeats", () => {
  const infinite = [...CSS.matchAll(/animation:[^;]*infinite[^;]*;/g)].map((m) => m[0]);
  // pulseAlert on the critical schematic node predates this work; the seam
  // drift is the only one added. Anything beyond those two is ambient noise.
  assert.ok(infinite.length <= 3, `${infinite.length} looping animations is too many`);
  assert.ok(infinite.some((r) => /seamDrift/.test(r)), "the seam drift is missing");
});

test("prefers-reduced-motion switches off every class the motion section animates", () => {
  const guard = CSS.slice(CSS.indexOf("@media (prefers-reduced-motion: reduce)"));
  assert.ok(guard.length > 100, "the reduced-motion guard is missing");
  for (const cls of ["motion-playing", "arch-seam-down", "arch-seam-up", "flow-stage"]) {
    assert.ok(guard.includes(cls), `${cls} is animated but not covered by the guard`);
  }
  // It must neutralise inherited animations too, not just the new ones.
  assert.match(guard, /animation-iteration-count:\s*1\s*!important/);
  assert.match(guard, /animation-duration:\s*0\.001ms\s*!important/);
});

test("the fourth screen is called Agent Ecosystem everywhere it is named", () => {
  // "Agent Studio" was a second name for the same screen. One screen, one name.
  const html = read("index.html");
  assert.ok(!/Agent Studio/.test(html), "'Agent Studio' is still on a screen");
  assert.match(html, /Open in Agent Ecosystem/);
  assert.match(html, /id="tab-ecosystem"[^>]*>Agent Ecosystem</);
});
