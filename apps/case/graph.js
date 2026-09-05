/* Screen 1.5 — following the connections.
 *
 * The claim this screen makes is narrow and checkable: the pattern it walks in
 * the browser is the pattern the deployed agent sends to BigQuery. So the SQL
 * is not retyped here — it is exported out of graph_traverse.py by the build —
 * and the walks below are written against the same edge labels and the same
 * direction of travel, one function per MATCH clause. Where the exported
 * subgraph is smaller than the warehouse table, the scope line says so rather
 * than the screen quietly implying it walked everything.
 *
 * What the reader sees is the walk in words: a starting point, a step, a count
 * of what the step reached. The query text, the graph names, the traversal ids
 * and the raw tool call are all still here, in the drawer at the foot, because
 * the argument this screen makes is that they agree with each other — and that
 * is not checkable if one half of the pair is missing.
 */

mountNav("case", "graph.html");

const G = DATA.graph;
const GRAPHS = G.graphs;
const ORDER = ["asset", "supply_chain", "safety"];

/* The record types, the links and the three traces are named by
   apps/shared/plain.js — NODE_TYPES, LINK_LABELS and TRAVERSALS — because one
   estate gets one vocabulary and this screen is not entitled to a private one.
   What stays here is the check: a record type or a link that stops having a
   plain name must break the screen, not quietly render its internal label at a
   reader who came here to avoid internal labels. */
ORDER.forEach((name) => {
  const g = GRAPHS[name];
  Object.keys(g.node_types).forEach((t) => {
    if (!NODE_TYPES[t]) throw new Error(`record type ${t} has no plain name in plain.js`);
  });
  Object.keys(g.edge_labels).forEach((l) => {
    if (!LINK_LABELS[l]) throw new Error(`link ${l} has no plain name in plain.js`);
  });
  if (!plainTraversal(g.traversal) || plainTraversal(g.traversal) === g.traversal) {
    throw new Error(`connection trace ${g.traversal} has no plain phrase in plain.js`);
  }
});

const css = getComputedStyle(document.documentElement);
const T = (name) => css.getPropertyValue(name).trim();

/* Colour carries node type, and only within one view at a time: no view shows
   more than four types, so four marks from the settled palette is enough and no
   new colour has to be invented for this screen. */
const TYPE_COLOR = {
  Asset: T("--accent"),
  WorkOrder: T("--fg-muted"),
  SparePart: T("--warning"),
  Operator: T("--accent"),
  Vehicle: T("--fg-muted"),
  Incident: T("--critical"),
  FatigueLog: T("--fg-dim"),
};
const TYPE_SIZE = { FatigueLog: 12, Incident: 30, default: 26 };
const TYPE_SHAPE = {
  Asset: "round-rectangle",
  WorkOrder: "rectangle",
  SparePart: "diamond",
  Operator: "ellipse",
  Vehicle: "round-rectangle",
  Incident: "triangle",
  FatigueLog: "ellipse",
};
/* The bulk layer of each graph carries no label until it is part of a result.
   126 work-order ids at this pitch overlap into a grey smear that reads as
   texture rather than text; the id returns the moment the node is a hit. */
const BULK = { WorkOrder: true, FatigueLog: true };

/* Both multi-type graphs are layered: one node type per level, every edge
   crossing from one level to the next in a single direction. Listed here in
   the direction the pattern walks them.

   A concentric layout drew them as rings, which put the 126 work orders on the
   outermost ring and crushed the 5 assets and 5 spare parts — the nodes that
   carry the meaning — into an unreadable knot at the centre. Banding by type
   restores the shape the query actually walks: five assets fan out to a
   hundred-odd work orders which converge back onto five parts. The funnel is
   the picture, and it is the reason the question needs a graph at all. */
const BAND = {
  supply_chain: ["Asset", "WorkOrder", "SparePart"],
  safety: ["FatigueLog", "Operator", "Vehicle", "Incident"],
};
const BAND_W = 1000; // model units; cytoscape fits this to the container
const BAND_GAP = 160;

/* Positions for a banded graph, in flow order so that each band can be sorted
   by where its parents landed in the band above. Without that sort the edges
   between two wide bands cross into a hatch that hides the fan; with it, one
   asset's work orders sit together. A node with parents in more than one place
   goes at their mean, which is the best a single row can do. */
function bandedPositions(graph) {
  const bands = BAND[graph];
  if (!bands) return null;

  const parents = new Map();
  const children = new Map();
  for (const e of edgesOf(graph)) {
    parents.set(e.target, (parents.get(e.target) || []).concat(e.source));
    children.set(e.source, (children.get(e.source) || []).concat(e.target));
  }

  const byId = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const pos = new Map();
  const placed = new Map();
  let y = 0;

  bands.forEach((type, band) => {
    const list = nodesOf(graph).filter((n) => n.type === type);
    /* Every band but the first aligns to where its parents landed above it.
       The first band has nothing above it, so it falls back to id order — with
       one exception. When the first band is the bulk layer, id order is hash
       order: 117 fatigue logs sorted by their own id hatch the LOGGED_FOR fan
       into noise. Those align downward instead, to the operator they belong
       to, which is what the edge bundle is trying to say. Five named assets do
       not want that treatment; a reader looking for MILL-01 wants it where the
       alphabet says it is. */
    const anchor = (n) => {
      const up = (parents.get(n.id) || [])
        .map((p) => placed.get(p))
        .filter((v) => v !== undefined);
      return up.length ? up.reduce((a, b) => a + b, 0) / up.length : Infinity;
    };
    const down = (n) => (children.get(n.id) || []).slice().sort(byId)[0] || "";
    list.sort((a, b) =>
      band
        ? anchor(a) - anchor(b) || byId(a.id, b.id)
        : (BULK[type] ? byId(down(a), down(b)) : 0) || byId(a.id, b.id)
    );

    const size = TYPE_SIZE[type] || TYPE_SIZE.default;
    const cols = Math.max(1, Math.min(list.length, Math.floor(BAND_W / (size + 10))));
    const rows = Math.ceil(list.length / cols);
    const rowGap = size + 22;
    const step = cols > 1 ? BAND_W / (cols - 1) : 0;

    list.forEach((n, i) => {
      const col = i % cols;
      pos.set(n.id, {
        x: cols > 1 ? col * step : BAND_W / 2,
        y: y + Math.floor(i / cols) * rowGap,
      });
      placed.set(n.id, i);
    });

    y += (rows - 1) * rowGap + BAND_GAP;
  });

  return pos;
}

const nodesOf = (g) => G.nodes.filter((n) => n.graph === g);
const edgesOf = (g) => G.edges.filter((e) => e.graph === g);
const edgeKey = (e) => `${e.graph}|${e.source}|${e.label}|${e.target}`;

function indexGraph(g) {
  const byId = new Map(nodesOf(g).map((n) => [n.id, n]));
  const out = new Map();
  const into = new Map();
  for (const e of edgesOf(g)) {
    const o = out.get(e.source) || new Map();
    o.set(e.label, (o.get(e.label) || []).concat(e));
    out.set(e.source, o);
    const i = into.get(e.target) || new Map();
    i.set(e.label, (i.get(e.label) || []).concat(e));
    into.set(e.target, i);
  }
  return {
    node: (id) => byId.get(id),
    all: (type) => nodesOf(g).filter((n) => n.type === type),
    out: (id, label) => (out.get(id) || new Map()).get(label) || [],
    in: (id, label) => (into.get(id) || new Map()).get(label) || [],
  };
}

/* ------------------------------------------------------------------ *
 * The three traversals, one function each, written against the same
 * MATCH clause the tool sends. Each returns the rows the COLUMNS list
 * names, plus the pattern broken into the segments the animation walks.
 * ------------------------------------------------------------------ */

function blastRadius(ix, params) {
  const origin = params.asset_id;
  const steps = [];
  const rows = [];
  let paths = [[origin]];
  /* -[:DEPENDS_ON]->{1,3} enumerates paths, not nodes: an asset reachable two
     ways is two rows. Bounding at three hops is the quantifier, and it is also
     what stops a cycle from running forever. */
  for (let hop = 1; hop <= 3; hop++) {
    const next = [];
    for (const path of paths) {
      for (const e of ix.out(path[path.length - 1], "DEPENDS_ON")) {
        next.push(path.concat(e.target));
      }
    }
    if (!next.length) break;
    steps.push({
      label: `${["", "One", "Two", "Three"][hop]} step${hop === 1 ? "" : "s"} out`,
      fragment: `-[:DEPENDS_ON]->{${hop}} (impacted:assets)`,
      nodes: next.map((p) => p[p.length - 1]),
      edges: next.map((p) =>
        edgeKey({ graph: "asset", source: p[p.length - 2],
                  label: "DEPENDS_ON", target: p[p.length - 1] })
      ),
    });
    for (const p of next) {
      const n = ix.node(p[p.length - 1]);
      rows.push({
        fail_origin: origin,
        impacted_asset: n.id,
        impacted_criticality: n.detail.criticality,
      });
    }
    paths = next;
  }
  return { seed: [origin], steps, rows };
}

function stockoutExposure(ix, params) {
  const wanted = new Set(params.below_rop_parts);
  const only = params.asset_id;
  const matched = [];
  for (const part of ix.all("SparePart")) {
    if (!wanted.has(part.id)) continue;
    for (const re of ix.in(part.id, "REPLACED_PART")) {
      const wo = ix.node(re.source);
      for (const hw of ix.in(wo.id, "HAS_WORK_ORDER")) {
        const asset = ix.node(hw.source);
        /* WHERE @asset_id IS NULL OR asset_id = @asset_id — applied before the
           steps are derived, so a filtered-out path is never lit up and then
           taken away again. */
        if (only && asset.id !== only) continue;
        matched.push({ part, wo, asset, re, hw });
      }
    }
  }
  matched.sort((a, b) =>
    a.part.id.localeCompare(b.part.id) || a.wo.id.localeCompare(b.wo.id)
  );
  return {
    seed: [...new Set(matched.map((m) => m.part.id))],
    steps: [
      {
        label: "Work orders that consumed the part",
        fragment: "<-[:REPLACED_PART]- (wo:WorkOrder)",
        nodes: matched.map((m) => m.wo.id),
        edges: matched.map((m) => edgeKey(m.re)),
      },
      {
        label: only ? `Machines, narrowed to ${only}` : "Machines those orders sit on",
        fragment: "<-[:HAS_WORK_ORDER]- (a:Asset)",
        nodes: matched.map((m) => m.asset.id),
        edges: matched.map((m) => edgeKey(m.hw)),
      },
    ],
    rows: matched.map((m) => ({
      part_number: m.part.id,
      work_order_id: m.wo.id,
      priority: m.wo.detail.priority,
      repair_cost: m.wo.detail.repair_cost,
      asset_id: m.asset.id,
      criticality_rating: m.asset.detail.criticality,
    })),
  };
}

function fatigueToIncident(ix, params) {
  const op = ix.node(params.operator_id);
  const logs = ix.in(op.id, "LOGGED_FOR");
  const matched = [];
  for (const oe of ix.out(op.id, "OPERATES")) {
    const vehicle = ix.node(oe.target);
    for (const ie of ix.out(vehicle.id, "INVOLVED_IN")) {
      const incident = ix.node(ie.target);
      for (const le of logs) matched.push({ le, vehicle, incident, oe, ie });
    }
  }
  return {
    seed: [op.id],
    steps: [
      {
        label: "Fatigue logs raised against this operator",
        fragment: "(f:FatigueLog) -[:LOGGED_FOR]-> (o:Operator)",
        nodes: matched.map((m) => m.le.source),
        edges: matched.map((m) => edgeKey(m.le)),
      },
      {
        label: "The vehicle they were driving",
        fragment: "-[:OPERATES]-> (v:Vehicle)",
        nodes: matched.map((m) => m.vehicle.id),
        edges: matched.map((m) => edgeKey(m.oe)),
      },
      {
        label: "Incidents that vehicle was involved in",
        fragment: "-[:INVOLVED_IN]-> (i:Incident)",
        nodes: matched.map((m) => m.incident.id),
        edges: matched.map((m) => edgeKey(m.ie)),
      },
    ],
    rows: matched.map((m) => ({
      log_id: m.le.source,
      operator_id: op.id,
      vehicle_id: m.vehicle.id,
      incident_id: m.incident.id,
      /* safety_incidents has no parquet and no entry in the calibration
         profile, so this column is null in the export by construction. It
         renders as a stated hole, never as blank. */
      severity_level: m.incident.detail.severity_level,
    })),
  };
}

const RUNNERS = {
  blast_radius: blastRadius,
  stockout_exposure: stockoutExposure,
  fatigue_to_incident: fatigueToIncident,
};

/* How many operators are actually behind a wheel in this data. Counted, not
   typed: the sentence below quotes both figures out loud, and a hardcoded pair
   would be the one claim on this screen a rebuild could quietly falsify. */
const SAFETY_IX = indexGraph("safety");
const OPERATORS = SAFETY_IX.all("Operator");
const DRIVERS = OPERATORS.filter((o) => SAFETY_IX.out(o.id, "OPERATES").length);

/* An empty result is a fact about the data, not a broken screen, so each trace
   says in its own terms why nothing came back. */
const EMPTY_REASON = {
  blast_radius: (p) =>
    `Nothing in the records depends on ${p.asset_id}, so nothing stops behind ` +
    "it. No rows is the correct answer here, not a failure.",
  stockout_exposure: () =>
    "No work order in this extract consumed the selected part, once the machine " +
    "you narrowed to is taken into account. Widen it, or pick another part.",
  fatigue_to_incident: (p) =>
    `${p.operator_id} is not assigned to a vehicle, so the trail stops at the ` +
    `second step. ${DRIVERS.length} of the ${OPERATORS.length} operators in ` +
    `this data hold an assignment; the other ${OPERATORS.length - DRIVERS.length} ` +
    "come back empty, exactly like this one.",
};

/* ------------------------------------------------------------------ *
 * The estate table and the standing notes.
 * ------------------------------------------------------------------ */

/* What a trace walks, in the order the record types were counted. The internal
   graph name and the trace id are in the drawer; what a reader needs from this
   row is the question, the kinds of record it crosses, and how big it is. */
function walks(g) {
  return Object.keys(g.node_types).map(plainType).join(", ");
}

/* The three questions, read out of the shared vocabulary rather than retyped
   underneath the table that lists them. They were written out by hand here and
   again in the tool note on the solution screen, which is three copies of one
   sentence and two of them free to drift. */
const ASKS = ORDER.map((name) => plainTraversal(GRAPHS[name].traversal));

el("estate-lede").textContent =
  "The traces below are the ones the agents actually hold: " +
  ASKS.slice(0, -1).join(", ") +
  ", and " +
  ASKS[ASKS.length - 1] +
  ". Each was built because somebody at this site has to answer that question " +
  "under time pressure, and each is a walk across records that no single table " +
  "holds together.";

el("estate").innerHTML = ORDER.map((name) => {
  const g = GRAPHS[name];
  return (
    "<tr>" +
    `<td>${esc(g.question)}</td>` +
    `<td style="color:var(--fg-muted)">${esc(walks(g))}</td>` +
    `<td class="num">${num(g.nodes)}</td>` +
    `<td class="num">${num(g.edges)}</td>` +
    `<td class="num">${num(g.entrypoints.length)}</td>` +
    "</tr>"
  );
}).join("");

const traceHolders = new Set(ORDER.flatMap((n) => GRAPHS[n].entrypoints));
el("estate-note").innerHTML =
  '<div class="note"><strong>Most agents do not need this</strong><br>' +
  `${esc(traceHolders.size)} of the ${esc(DATA.catalog.counts.entrypoints)} ` +
  "agents you can talk to are allowed to follow connections at all. The rest " +
  "read records, which is the right way to answer the questions they are asked. " +
  "A fourth set of connections exists in the code and is granted to no agent; " +
  "drawing it here would be scenery, so it is named in the drawer at the foot " +
  "of this screen and left out of the table above." +
  "</div>";

el("run-note").innerHTML =
  '<div class="note info"><strong>Nothing here is a recording</strong><br>' +
  "Change the setting and the answer changes with it. The agent runs the same " +
  "walk against the full records; the drawing above walks the same links in the " +
  "same direction over the smaller extract described at the top of this section, " +
  "and the drawer at the foot holds the exact query both of them come from." +
  "</div>";

/* ---------- the machinery, at the end and closed ---------- */

/* Everything this screen took off the page, kept together: the name each set of
   connections has in BigQuery, the id the tool is called with, the query text
   itself, the tables behind it, the internal record and link labels the plain
   words above stand for, and the agents that hold the tool. The live call log
   is here too — it is the one artefact that proves the walk on screen and the
   query in the deployed container are the same walk, and it is of no use to a
   reader who is not checking that. */
function drawerBody() {
  const blocks = ORDER.map((name) => {
    const g = GRAPHS[name];
    const types = Object.entries(g.node_types)
      .map(([t, n]) => `${t} ${n}`)
      .join(" · ");
    const links = Object.entries(g.edge_labels)
      .map(([l, n]) => `${l} ${n}`)
      .join(" · ");
    return (
      `<dt class="mono">${esc(g.bigquery_graph)} · ${esc(g.traversal)}</dt>` +
      `<dd><span class="mono">${esc(types)}</span><br>` +
      `<span class="mono">${esc(links)}</span><br>` +
      `<span class="mono">${esc(g.tables_read.join(" "))}</span><br>` +
      `<span class="mono">${esc(g.agents.join(" "))}</span> — of which ` +
      `<span class="mono">${esc(g.entrypoints.join(" "))}</span> are callable` +
      `<div class="console" style="margin-top:8px">${esc(g.sql)}</div></dd>`
    );
  }).join("");

  return (
    "<p>The query text below is lifted out of " +
    '<span class="mono">mining_agents/tools/graph_traverse.py</span> at build ' +
    "time rather than transcribed, so it cannot drift from the text in the " +
    "deployed container. The column names under the canvas are parsed from the " +
    "same string.</p>" +
    `<dl>${blocks}` +
    '<dt class="mono">MiningOntologyGraph · ontology_related</dt>' +
    "<dd>Exists in the tool code, granted to no agent, and therefore not drawn " +
    "on this screen.</dd></dl>" +
    "<p>And the exact tool call the button above makes, as it makes it. The " +
    "skeleton is written here rather than by the code that runs it, so the " +
    "vocabulary of this box belongs to the drawer and not to the screen:</p>" +
    '<div class="console"><span class="dim">graph_traverse(</span>\n' +
    '  traversal=<span class="ok" id="call-trace">—</span>,\n' +
    '  params=<span id="call-params">—</span>\n' +
    '<span class="dim">)</span>' +
    '<span id="call-log"></span></div>' +
    `<p class="mono">${esc(G.source)} · generated ${esc(G.generated_at)}</p>`
  );
}

el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "graph names, query text, tables, agent ids"
) + provenance(
  /* The build writes this line in the build's words — two file paths, the
     dataset and the product name, in one paragraph — and the footer sits on
     the reader's side of the drawer. plainProse() says the same two vintages
     and the same unreachable warehouse without them; the paragraph as the
     build wrote it is in the drawer above, at the foot of drawerBody(). */
  `<dt>Graph data</dt><dd>${esc(plainProse(G.source))}</dd>` +
    "<dt>The query</dt><dd>Read out of " +
    "<span class=\"mono\">mining_agents/tools/graph_traverse.py</span> by the " +
    "build, not transcribed. The column names under the canvas are parsed " +
    "from the same string, so a renamed column renames the table header.</dd>"
);

/* ------------------------------------------------------------------ *
 * Canvas, controls, animation.
 * ------------------------------------------------------------------ */

let current = ORDER[0];
let cy = null;
let ix = null;
let timers = [];

function tabs() {
  el("tabs").innerHTML = ORDER.map(
    (name) =>
      `<button role="tab" data-graph="${esc(name)}" aria-selected="${
        name === current
      }">${esc(plainTraversal(GRAPHS[name].traversal))}</button>`
  ).join("");
  el("tabs")
    .querySelectorAll("button")
    .forEach((b) =>
      b.addEventListener("click", () => {
        if (b.dataset.graph === current) return;
        current = b.dataset.graph;
        tabs();
        mount();
      })
    );
}

function controls() {
  const g = GRAPHS[current];
  const opt = (v, label, sel) =>
    `<option value="${esc(v)}"${sel ? " selected" : ""}>${esc(label)}</option>`;
  const field = (label, inner) =>
    `<label style="display:block;margin-bottom:12px">` +
    `<span class="metric-sub" style="margin:0 0 5px;display:block">${esc(
      label
    )}</span>${inner}</label>`;
  const selectStyle =
    'style="width:100%;min-height:44px;background:var(--surface-high);' +
    "color:var(--fg);border:1px solid var(--border);border-radius:0;" +
    'font-family:var(--mono);font-size:12.5px;padding:0 10px"';

  if (current === "asset") {
    const assets = ix.all("Asset");
    el("controls").innerHTML = field(
      "The machine that fails",
      `<select id="p-asset_id" ${selectStyle}>` +
        assets
          .map((a, i) => opt(a.id, `${a.id} · ${a.detail.name}`, i === 0))
          .join("") +
        "</select>"
    );
  } else if (current === "supply_chain") {
    const parts = ix.all("SparePart");
    const assets = ix.all("Asset");
    el("controls").innerHTML =
      field(
        "The parts running low, which is what the agent passes in",
        '<div style="display:grid;gap:6px">' +
          parts
            .map(
              (p) =>
                '<label style="display:flex;gap:8px;align-items:flex-start;' +
                'font-size:12.5px;min-height:44px;padding-top:3px">' +
                `<input type="checkbox" class="p-part" value="${esc(p.id)}"${
                  p.detail.below_reorder_point ? " checked" : ""
                } style="margin-top:4px">` +
                `<span><span class="mono">${esc(p.id)}</span><br>` +
                `<span style="color:var(--fg-muted);font-size:11.5px">` +
                `${num(p.detail.stock_level)} on hand · reorder at ` +
                `${num(p.detail.reorder_point_limit)} · ` +
                `${num(p.detail.lead_time_days)}d lead</span></span></label>`
            )
            .join("") +
          "</div>"
      ) +
      field(
        "Narrow it to one machine, if you want to",
        `<select id="p-asset_id" ${selectStyle}>` +
          opt("", "Every machine", true) +
          assets.map((a) => opt(a.id, a.id, false)).join("") +
          "</select>"
      );
  } else {
    /* The vehicle each operator drives is shown in the picker rather than
       withheld: a Mine Controller choosing an operator already knows who is
       assigned to what, and manufacturing a surprise out of an empty result
       would be theatre. The ratio is stated in the scope note above, and an
       unassigned operator still returns nothing, with the reason printed.

       The default is computed, not typed: the assigned operator carrying the
       most fatigue alerts, so the screen opens on a call that matches. */
    const ops = ix.all("Operator");
    const vehicleOf = (o) => (ix.out(o.id, "OPERATES")[0] || {}).target || null;
    const assigned = ops.filter(vehicleOf);
    const preferred = assigned.reduce(
      (best, o) =>
        !best || o.detail.alerts_triggered > best.detail.alerts_triggered ? o : best,
      null
    );
    el("controls").innerHTML = field(
      "Whose fatigue record to follow",
      `<select id="p-operator_id" ${selectStyle}>` +
        ops
          .map((o) => {
            const n = o.detail.alerts_triggered;
            const v = vehicleOf(o);
            return opt(
              o.id,
              `${o.id} · ${n} alert${n === 1 ? "" : "s"} · ${v || "no vehicle"}`,
              preferred ? o.id === preferred.id : false
            );
          })
          .join("") +
        "</select>"
    );
  }
}

function readParams() {
  if (current === "asset") {
    return { asset_id: el("p-asset_id").value };
  }
  if (current === "supply_chain") {
    return {
      below_rop_parts: [...document.querySelectorAll(".p-part:checked")].map(
        (c) => c.value
      ),
      asset_id: el("p-asset_id").value || null,
    };
  }
  return { operator_id: el("p-operator_id").value };
}

function legend() {
  const types = [...new Set(nodesOf(current).map((n) => n.type))].sort();
  const labels = [...new Set(edgesOf(current).map((e) => e.label))].sort();
  el("legend").innerHTML =
    types
      .map(
        (t) =>
          `<span><span class="swatch" style="background:${TYPE_COLOR[t]}"></span>${esc(
            plainType(t)
          )}</span>`
      )
      .join("") +
    labels.map((l) => `<span>→ ${esc(plainLink(l))}</span>`).join("");
}

function mount() {
  timers.forEach(clearTimeout);
  timers = [];
  ix = indexGraph(current);
  const g = GRAPHS[current];

  el("scope").innerHTML =
    '<div class="note info" style="margin:0"><strong>What is drawn, and what is not</strong><br>' +
    esc(plainScope(g.scope)) +
    ` ${esc(g.entrypoints.length)} agent${g.entrypoints.length === 1 ? "" : "s"} ` +
    "you can talk to can run this one.</div>";

  el("inspect").innerHTML =
    '<div style="color:var(--fg-muted);font-size:13px">Click anything on the ' +
    "drawing to see what that record holds.</div>";

  const elements = [
    ...nodesOf(current).map((n) => ({
      data: { id: n.id, label: n.label, type: n.type, detail: n.detail },
    })),
    ...edgesOf(current).map((e) => ({
      data: {
        id: edgeKey(e),
        source: e.source,
        target: e.target,
        label: e.label,
      },
    })),
  ];

  /* The asset graph has one node type and takes its hierarchy from its own
     edges, so breadthfirst is the right reading of it. The other two take their
     hierarchy from the node type, which no force or ring layout can know, so
     their positions are computed once here. */
  const banded = bandedPositions(current);

  if (cy) cy.destroy();
  cy = cytoscape({
    container: el("cy"),
    elements,
    minZoom: 0.2,
    maxZoom: 3,
    wheelSensitivity: 0.2,
    style: [
      {
        selector: "node",
        style: {
          "background-color": T("--surface-high"),
          "border-width": 1,
          "border-color": (n) => TYPE_COLOR[n.data("type")] || T("--border"),
          shape: (n) => TYPE_SHAPE[n.data("type")] || "ellipse",
          width: (n) => TYPE_SIZE[n.data("type")] || TYPE_SIZE.default,
          height: (n) => TYPE_SIZE[n.data("type")] || TYPE_SIZE.default,
          label: (n) => (BULK[n.data("type")] ? "" : n.data("label")),
          color: T("--fg-muted"),
          "font-family": "JetBrains Mono, ui-monospace, monospace",
          "font-size": 8,
          "text-valign": "bottom",
          "text-margin-y": 3,
          "text-background-color": T("--bg"),
          "text-background-opacity": 0.75,
          "text-background-padding": 1,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1,
          "line-color": T("--border"),
          "target-arrow-color": T("--border"),
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.6,
          "curve-style": "bezier",
        },
      },
      {
        selector: "node.seed",
        style: {
          "background-color": (n) => TYPE_COLOR[n.data("type")],
          "border-width": 3,
          "border-color": T("--fg"),
          color: T("--fg"),
          "font-size": 11,
          "z-index": 20,
        },
      },
      {
        selector: "node.hit",
        style: {
          "background-color": (n) => TYPE_COLOR[n.data("type")],
          "border-width": 2,
          color: T("--fg"),
          /* A hit on the bulk layer still gets no label. Thirty-four work
             orders sit closer together than their ids are wide, and a 64-char
             log_id is wider than the canvas. What the canvas shows is the
             shape of the fan; the ids are in the results table below, in full,
             and in the inspector on click. */
          label: (n) => (BULK[n.data("type")] ? "" : n.data("label")),
          "z-index": 10,
        },
      },
      {
        selector: "edge.hit",
        style: {
          width: 2,
          "line-color": T("--accent"),
          "target-arrow-color": T("--accent"),
          "z-index": 10,
        },
      },
      { selector: ".faded", style: { opacity: 0.1 } },
    ],
    layout: banded
      ? { name: "preset", positions: (n) => banded.get(n.id()), padding: 24 }
      : { name: "breadthfirst", directed: true, spacingFactor: 1.5, padding: 30 },
  });

  cy.on("tap", "node", (evt) => inspect(evt.target));

  controls();
  legend();
  reset();
}

function inspect(node) {
  const detail = node.data("detail") || {};
  const keys = Object.keys(detail);
  el("inspect").innerHTML =
    `<div class="mono" style="font-size:13px;color:var(--fg)">${esc(
      node.id()
    )}</div>` +
    `<div class="metric-sub" style="margin-top:2px">${esc(
      plainType(node.data("type"))
    )}</div>` +
    (keys.length
      ? '<dl class="kv" style="margin-top:10px">' +
        keys
          .map(
            (k) =>
              `<dt>${esc(k)}</dt><dd>${
                detail[k] === null || detail[k] === undefined
                  ? '<span class="mono" style="color:var(--fg-dim)">not in local files</span>'
                  : esc(
                      Array.isArray(detail[k]) ? detail[k].join(", ") : detail[k]
                    )
              }</dd>`
          )
          .join("") +
        "</dl>"
      : '<div style="color:var(--fg-dim);font-size:13px;margin-top:8px">' +
        "Nothing about this record is held in the local files.</div>");
}

/* The walk in words, beside the drawing, one line per step. The reader gets a
   sentence and a count; the raw call that produced them is in the drawer, and
   both are written by the same run so neither can describe a walk the other
   did not take. */
const STEP_LINES = [];

function renderTrace() {
  el("trace").innerHTML = STEP_LINES.length
    ? '<div style="font-size:13px;line-height:1.65;color:var(--fg-muted)">' +
      STEP_LINES.join("") +
      "</div>"
    : '<div style="color:var(--fg-muted);font-size:13px">Set it up, then run ' +
      "the trace.</div>";
}

function traceLine(text, count) {
  STEP_LINES.push(
    "<div>" +
      esc(text) +
      (count === undefined
        ? ""
        : ` — <b style="color:var(--fg)">${esc(num(count))}</b>`) +
      "</div>"
  );
  renderTrace();
}

function reset() {
  timers.forEach(clearTimeout);
  timers = [];
  cy.elements().removeClass("faded hit seed");
  STEP_LINES.length = 0;
  renderTrace();
  el("call-trace").textContent = "—";
  el("call-params").textContent = "—";
  el("call-log").innerHTML = "";
  renderRows(null, []);
}

function paramLiteral(params) {
  return JSON.stringify(params, null, 0);
}

function run() {
  const g = GRAPHS[current];
  const params = readParams();
  if (current === "supply_chain" && !params.below_rop_parts.length) {
    STEP_LINES.length = 0;
    traceLine(
      "No part is selected, so there is nothing to trace. The tool refuses the " +
        "call rather than quietly answering for every part in the store."
    );
    el("call-trace").textContent = `"${g.traversal}"`;
    el("call-params").textContent = paramLiteral(params);
    el("call-log").innerHTML =
      '\n<span class="warn">INVALID_ARGUMENT</span> ' +
      '<span class="dim">— the tool refuses the call rather than ' +
      "returning every part.</span>";
    renderRows(g, []);
    return;
  }

  const result = RUNNERS[g.traversal](ix, params);
  timers.forEach(clearTimeout);
  timers = [];

  /* Clear the previous run before fading: leaving hit and seed on would let a
     narrowed filter still show the wider result lit up underneath it, which is
     precisely the kind of stale screen this application must not have. */
  cy.elements().removeClass("hit seed").addClass("faded");
  const light = (ids, cls) => {
    ids.forEach((id) => {
      const e = cy.getElementById(id);
      if (e.length) e.removeClass("faded").addClass(cls);
    });
  };
  light(result.seed, "seed");

  STEP_LINES.length = 0;
  traceLine(`Starting from ${result.seed.join(", ")}`);

  el("call-trace").textContent = `"${g.traversal}"`;
  el("call-params").textContent = paramLiteral(params);
  let log = `\n<span class="dim">→ ${esc(g.bigquery_graph)}</span>`;
  el("call-log").innerHTML = log;

  result.steps.forEach((step, i) => {
    timers.push(
      setTimeout(() => {
        light([...new Set(step.nodes)], "hit");
        light([...new Set(step.edges)], "hit");
        const n = new Set(step.nodes).size;
        traceLine(step.label, n);
        log +=
          `\n  <span class="dim">${esc(step.fragment)}</span>\n` +
          `  ${esc(step.label)} · <span class="ok">${n}</span> record${
            n === 1 ? "" : "s"
          }`;
        el("call-log").innerHTML = log;
      }, 420 * (i + 1))
    );
  });

  timers.push(
    setTimeout(() => {
      const n = result.rows.length;
      traceLine("Rows handed back to the agent", n);
      log +=
        `\n<span class="dim">←</span> {"graph": "${esc(
          g.bigquery_graph
        )}", "rows": [` +
        (n
          ? `<span class="ok">${n}</span>`
          : `<span class="warn">0</span>`) +
        "]}";
      el("call-log").innerHTML = log;
      renderRows(g, result.rows, params);
    }, 420 * (result.steps.length + 1))
  );
}

function renderRows(g, rows, params) {
  if (!g) {
    el("rows-head-row").innerHTML = "";
    el("rows").innerHTML =
      '<tr><td style="color:var(--fg-muted)">Nothing has been run yet.</td></tr>';
    el("rows-lede").textContent =
      "These are the columns the agent asks for, in the order it asks for them " +
      "— not a summary written for this screen, and not a row more than the " +
      "walk actually reached.";
    return;
  }
  el("rows-head-row").innerHTML = g.columns
    .map((c) => `<th class="mono">${esc(c)}</th>`)
    .join("");
  el("rows-lede").textContent =
    `This trace asks for ${g.columns.length} columns. ` +
    (rows.length
      ? `This run reached ${rows.length} row${rows.length === 1 ? "" : "s"}.`
      : "This run reached nothing.");

  if (!rows.length) {
    el("rows").innerHTML =
      `<tr><td colspan="${g.columns.length}" style="color:var(--fg-muted)">` +
      // The only call that reaches here without parameters is one the tool
      // refused, so this is not the "nothing yet" case and must not read as it.
      esc(
        params
          ? EMPTY_REASON[g.traversal](params)
          : "The call was refused before it ran, so there is nothing to show."
      ) +
      "</td></tr>";
    return;
  }
  /* A 126-row result is the honest size of the answer; capping the table at 60
     and saying so beats silently truncating or freezing the page. */
  const CAP = 60;
  el("rows").innerHTML =
    rows
      .slice(0, CAP)
      .map(
        (r) =>
          "<tr>" +
          g.columns
            .map((c) =>
              r[c] === null || r[c] === undefined
                ? '<td class="mono" style="color:var(--fg-dim)">not in local files</td>'
                : `<td class="mono">${esc(num(r[c]))}</td>`
            )
            .join("") +
          "</tr>"
      )
      .join("") +
    (rows.length > CAP
      ? `<tr><td colspan="${g.columns.length}" style="color:var(--fg-muted)">` +
        `${rows.length - CAP} further rows matched and are not printed here. ` +
        "The agent receives all of them.</td></tr>"
      : "");
}

el("run").addEventListener("click", run);
el("reset").addEventListener("click", reset);

tabs();
mount();
