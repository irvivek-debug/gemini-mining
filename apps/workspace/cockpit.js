/* The site cockpit.
 *
 * The one job of this screen is to get a person to the right agent without them
 * having to know the catalog. Three groupings are offered rather than one
 * because the three are genuinely different questions: a supervisor arrives
 * knowing their role, a process owner arrives knowing their process area, and
 * an executive arrives knowing which part of the cost base is under pressure.
 * Picking one and calling it the taxonomy would serve one of the three and
 * quietly fail the others.
 *
 * Every group, count and roster below is read off DATA.catalog, which the build
 * derives from the module that constructs the agents. Nothing is typed here.
 */

mountNav("workspace", "index.html");
runState(el("runtime"));

const C = CAT.counts;

/* Every team is one lead, some specialists and one reviewer. The sentence below
   says so, so the shape is read rather than asserted — and if the catalogue
   ever holds two shapes, the screen stops rather than describing one of them as
   though it were both. */
const TEAM_SPECIALISTS = (() => {
  const sizes = [...new Set(Object.values(CAT.swarms).map((s) => s.specialists.length))];
  if (sizes.length !== 1) {
    throw new Error("the agent teams are no longer one shape; this screen says they are");
  }
  return sizes[0];
})();

el("lede").textContent =
  "Every agent you can talk to, backed by a team you never address " +
  "directly — grouped three ways below: by role, by process, by cost.";

el("counts").innerHTML = [
  [C.entrypoints, "agents you can talk to", "of " + C.agent_nodes + " in the teams behind them", true],
  [
    C.swarms,
    "agent teams",
    "a lead, " + TEAM_SPECIALISTS + " specialists and a reviewer",
    false,
  ],
  [C.deep_agents, "agents working alone", "one question each, no team behind them", false],
  [C.hitl_entrypoints, "need your sign-off", "before anything is committed", false],
]
  .map(
    ([value, label, sub, accent]) =>
      '<div class="card c3 stat">' +
      `<div class="metric${accent ? " accent" : ""}">${num(value)}</div>` +
      `<div><div style="font-size:13.5px;margin-top:8px">${esc(label)}</div>` +
      `<div class="metric-sub">${esc(sub)}</div></div></div>`
  )
  .join("");

/* Task C (plan 2026-08-18): the metrics this site's carded agents move, each
 * with its benchmark range and source, and this site's own measured position
 * where a comparable measurement exists.
 *
 * Grouped BY METRIC, not by agent. CAT.metric_impact_summary already arrives
 * grouped that way (scripts/build_app_data.py, _metric_impact_summary) --
 * this screen reads the already-deduplicated summary rather than re-deriving
 * it, so the two can never drift apart. The reason for the grouping itself
 * lives on that function's own docstring: several agents move the same
 * metric with the identical published range (S06 and S07 both cite
 * McKinsey's mineral-recovery figure), and an agent-first cockpit would
 * either repeat that range under two headings or need its own dedup pass to
 * notice the two agents agree. Grouping by metric gets the dedup for free.
 */
const IMPACTS = CAT.metric_impact_summary;

/* Which of this build's own measured gaps stands in for which benchmarked
 * metric. Recovery and crusher feed rate are the exact pairing the case
 * app's own evidence chart already draws -- crusher feed rate set beside the
 * published throughput uplift (docs/specs/2026-08-13-ux-uplift-
 * design.md) -- reused here rather than invented, so the two applications
 * never disagree about which of this site's own numbers stands in for which
 * published one. The other three benchmarked metrics (unplanned downtime,
 * maintenance cost, contract value recovered) have no comparable measurement
 * anywhere in this build's own data and are shown as industry ranges only --
 * never filled with an adjacent number to avoid looking incomplete, the same
 * rule that leaves S03 and S05 without a benchmark of their own. */
const SITE_GAP_FOR_METRIC = { "Mineral recovery": "recovery", Throughput: "feed_rate" };
const GAP = DATA.signals.gap;

function gapRowFor(metric) {
  const id = SITE_GAP_FOR_METRIC[metric];
  return id ? GAP.rows.find((row) => row.id === id) : null;
}

/* A gap row's own delta, read the same way persona-panel.js's gap table
 * already reads it: a "points" row (recovery) prints in points, a "percent"
 * row (crusher feed rate) prints in percent. The two are not the same unit
 * as each other, and neither is forced into the other's just to share one
 * bar -- see the comment above SITE_GAP_FOR_METRIC. */
function siteValue(row) {
  return row.delta_kind === "points" ? row.delta : row.delta_pct;
}
function siteFigureText(row) {
  const dp = rowPlaces(row);
  return row.delta_kind === "points"
    ? "+" + fig(row.delta, "", dp) + " pts"
    : "+" + fig(row.delta_pct, "%", 1);
}

/* A nice round bound for a range bar, with headroom so the widest published
 * figure a row shows does not sit flush against its own edge. Computed from
 * the range rather than hand-tuned per metric, for the same reason coverage
 * is computed from the pack rather than typed by hand. */
function impactScale(highPct) {
  return Math.max(5, Math.ceil((highPct * 1.25) / 5) * 5);
}

/* An agent chip for a metric card. AGENTS is built off ALL_AGENTS
 * (workspace.js), which AGT-19 is not in -- it has no AgentDef (design §3) --
 * so chip() alone would throw if a group-level agent ever earned a metric
 * impact. It does not today (AGT-19's metric_impacts is deliberately empty),
 * but this guards the day one does without the chip silently going dead. */
function impactChip(id) {
  return AGENTS[id] ? chip(id) : '<span class="chip" title="' + esc(id) + '">' + esc(id) + "</span>";
}

/** One range, as a bar with its attribution on its own face -- the industry
 *  badge and citation are never optional. `+`/`−` on the figure carries
 *  direction a second way, for a reader skimming rather than reading the
 *  metric name. A site-measured marker ticks the bar at this site's own
 *  position when one exists, but its number is stated once per metric card
 *  (below), not once per range -- Throughput carries two published ranges
 *  from two firms and one site measurement, and repeating that one
 *  measurement under both firms' rows would read as two facts instead of
 *  one repeated. */
function impactRangeRow(metric, range) {
  const scale = impactScale(range.high_pct);
  const leftPct = ((range.low_pct / scale) * 100).toFixed(1);
  const widthPct = (((range.high_pct - range.low_pct) / scale) * 100).toFixed(1);
  const sign = range.direction === "decrease" ? "−" : "+";
  const dp = Number.isInteger(range.low_pct) && Number.isInteger(range.high_pct) ? 0 : 1;
  const gapRow = gapRowFor(metric);
  const marker = gapRow
    ? '<span class="range-marker" style="left:' +
      Math.min(100, (siteValue(gapRow) / scale) * 100).toFixed(1) + '%"></span>'
    : "";
  return (
    '<div class="range-row">' +
    '<div class="range-row-head">' +
    '<span class="range-row-label">' + esc(metric) + "</span>" +
    '<span class="range-row-fig">' + sign + fig(range.low_pct, "", dp) + "–" +
    fig(range.high_pct, "%", dp) + "</span>" +
    "</div>" +
    '<div class="money-range-bar"><span style="left:' + leftPct + "%;width:" +
    widthPct + '%"></span>' + marker + "</div>" +
    '<div class="range-row-foot">' +
    '<span class="badge b-info">INDUSTRY RANGE</span>' +
    '<span class="cite">' + esc(range.source) + "</span>" +
    "</div></div>"
  );
}

/** The one site-measured line a metric card carries, stated once regardless
 *  of how many published ranges sit above it. Absent entirely for the three
 *  metrics with no comparable measurement in this build's own data -- never
 *  filled with an adjacent number to avoid looking incomplete. */
function siteMeasuredLine(metric) {
  const gapRow = gapRowFor(metric);
  if (!gapRow) return "";
  return (
    '<div class="range-row-foot" style="margin-top:10px">' +
    '<span class="badge b-ok">SITE MEASURED</span>' +
    '<span class="range-row-fig" style="font-size:13px">' + siteFigureText(gapRow) + "</span>" +
    '<span class="cite">' + esc(gapRow.label) +
    ", this site's best day against its ordinary day</span></div>"
  );
}

el("impacts").innerHTML = IMPACTS.map(
  (entry) =>
    '<div class="card c6">' +
    '<div class="card-cap">' + esc(entry.metric) + "</div>" +
    entry.ranges.map((r) => impactRangeRow(entry.metric, r)).join("") +
    siteMeasuredLine(entry.metric) +
    '<div class="chips" style="margin-top:10px">' + entry.agents.map(impactChip).join("") + "</div>" +
    "</div>"
).join("");

const SITE_MATCHED = IMPACTS.filter((entry) => gapRowFor(entry.metric)).length;

el("impact-lede").textContent =
  IMPACTS.length + " metrics this site's carded agents move — each a " +
  "sourced industry range, " + SITE_MATCHED + " with this site's own " +
  "measured position too.";

/* Every card in the build, persona-holding and group-level alike -- read the
 * same way agent-card.js's own test fixtures read it, so this count and that
 * one cannot silently diverge. */
const ALL_CARDED_AGENTS = [].concat(
  ...Object.values(PERSONAS).map((p) => p.cards || []),
  Object.values(CAT.group_agents || {})
).map((c) => c.agent_id);
const AGENTS_WITH_IMPACT = new Set();
IMPACTS.forEach((entry) => entry.agents.forEach((id) => AGENTS_WITH_IMPACT.add(id)));
const AGENTS_WITHOUT_IMPACT = ALL_CARDED_AGENTS.length - AGENTS_WITH_IMPACT.size;

el("impact-note").textContent =
  AGENTS_WITH_IMPACT.size + " of the " + ALL_CARDED_AGENTS.length + " agents " +
  "carrying a business case move a metric with a published range; the other " +
  AGENTS_WITHOUT_IMPACT + " earn their place on evidence class and coverage " +
  "— see My role.";

/* How many agents are filed under more than one process area. The old copy said
   "seven" and nothing checked it. */
const SPANNERS = CAT.agents.filter(
  (a) => a.is_entrypoint && a.apqc_names.length > 1
).length;

/* What a group's line under its heading says. It used to be a count and a
   fragment glued together — "12 you can talk to", and on the money axis "where
   the branches meet · 1 you can talk to" — which is a card with no article, no
   noun and no verb in it. Each group has something to say about what its agents
   have in common, so it says it, in a sentence that survives a group of one.
   The verb is given in the plural and takes its "s" for the singular, which is
   true of every verb these lines need. */
function agentsWhich(n, verb, rest) {
  return (n === 1 ? "One agent " + verb + "s" : n + " agents " + verb) + " " + rest + ".";
}

/* The three axes. Each names where its groups come from and what a group means,
   because "where the money is" is not self-explanatory to someone who has not
   seen the cost tree, and a tab whose contents surprise you is a tab you stop
   using. */
const AXES = [
  {
    key: "persona",
    tab: "By person",
    head: "By the person accountable",
    lede:
      "One group per role — the same grouping your own role page uses.",
    groups: () =>
      Object.entries(CAT.by_persona).map(([code, g]) => ({
        title: (PERSONAS[code] || {}).title || code,
        sub: agentsWhich(g.count, "take", "questions from this role"),
        /* The paragraph is the catalogue's, not this screen's, and it was
           written in the estate's own words. It is printed without a citation
           against it, so it is description rather than quotation, and it is
           said the way the rest of this screen says it. */
        detail: plainProse((PERSONAS[code] || {}).accountable_for),
        agents: g.agents,
        href: "persona.html?p=" + encodeURIComponent(code),
        hrefLabel: "Open this role's page",
      })),
  },
  {
    key: "process",
    tab: "By process",
    head: "By standard process area",
    lede:
      "The standard process area each agent works in. " + SPANNERS +
      " agents span two areas and are counted in both, so these groups add " +
      "up to more than the agent count.",
    groups: () =>
      Object.entries(CAT.by_apqc_code).map(([code, g]) => ({
        title: CAT.apqc_names[code] || code,
        sub: agentsWhich(g.count, "work", "in this process area"),
        detail: null,
        agents: g.agents,
      })),
  },
  {
    key: "branch",
    tab: "By where the money is",
    head: "By where the money is",
    lede:
      "Which part of the cost of running this site an agent works on, " +
      "rooted on all-in sustaining cost per tonne.",
    groups: () =>
      Object.entries(CAT.by_value_branch).map(([branch, g]) => {
        const b = DATA.value_tree.branches.find((x) => x.branches.includes(branch));
        return {
          title: branch.replace(/_/g, " "),
          sub: b
            ? agentsWhich(g.count, "work", "on this part of the cost")
            : agentsWhich(g.count, "sit", "above the parts, where they meet"),
          detail: b ? b.mechanism : DATA.value_tree.convergence.note,
          agents: g.agents,
        };
      }),
  },
];

let axis = AXES[0];

el("axes").innerHTML = AXES.map(
  (a) =>
    `<button role="tab" data-key="${a.key}" aria-selected="${a === axis}">${esc(a.tab)}</button>`
).join("");

el("axes").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  axis = AXES.find((a) => a.key === button.dataset.key);
  [...el("axes").children].forEach((b) =>
    b.setAttribute("aria-selected", String(b.dataset.key === axis.key))
  );
  renderAxis();
});

/* An agent that leads a team opens that team's page. An agent that works on its
   own has no page of its own — it is reached through the page of the role
   answerable for it, which is where a question can actually be put to it. The
   role is declared on every agent in the catalog, so this is a lookup, not a
   guess. */
function chip(id) {
  const a = AGENTS[id];
  const href =
    a.pattern === "A"
      ? "swarm.html?s=" + id
      : "persona.html?p=" + encodeURIComponent(a.persona);
  return (
    `<a class="chip${a.hitl_required ? " signoff" : ""}" href="${href}" ` +
    `title="${esc(a.display_name)}${a.hitl_required ? " — needs your sign-off" : ""}">` +
    `${esc(id)}</a>`
  );
}

function renderAxis() {
  el("axis-head").textContent = axis.head;
  el("axis-lede").textContent = axis.lede;
  el("groups").innerHTML = axis
    .groups()
    .map(
      (g) =>
        '<div class="group c4">' +
        `<h3>${esc(g.title)}</h3>` +
        `<div class="group-sub">${esc(g.sub)}</div>` +
        (g.detail
          ? `<p style="font-size:13px;margin:0 0 12px">${esc(g.detail.trim())}</p>`
          : "") +
        `<div class="chips">${g.agents.map(chip).join("")}</div>` +
        (g.href
          ? `<div class="btn-row" style="margin-top:12px">` +
            `<a class="btn" href="${g.href}">${esc(g.hrefLabel)}</a></div>`
          : "") +
        "</div>"
    )
    .join("");
}

renderAxis();

const GATED = CAT.agents.filter((a) => a.is_entrypoint && a.hitl_required);

// A labelled bar, not a sentence describing a proportion: GATED.length / C.
// entrypoints is a share like any other on this suite, and this build already
// has one shape for "N of M, drawn" (agent-card.js's coverage row, the same
// .share-bar this reuses) -- so a reader who has learned to read that shape
// once reads this one the same way, rather than meeting an eleventh custom
// component for one number.
const SIGNOFF_PCT = C.entrypoints ? (GATED.length / C.entrypoints) * 100 : 0;

el("signoff-lede").innerHTML =
  '<div class="share-bar" role="img" aria-hidden="true" style="max-width:420px">' +
  '<span style="width:' + SIGNOFF_PCT.toFixed(1) + '%"></span></div>' +
  '<p class="lede" style="margin-top:8px">' + GATED.length + " of " + C.entrypoints +
  " agents advise rather than act: each puts its case together and needs " +
  "your sign-off before anything moves.</p>";

el("signoff").innerHTML = GATED.map((a) => a.agent_id).map(chip).join("");

/* Everything the copy above stopped naming, in one place: the code each agent
   is filed under, the process area it maps to, the part of the cost tree it
   serves, the model tier it runs on, and the table an approval is written to.
   None of it is needed to find an agent, and all of it is needed to check one. */
function drawerBody() {
  const rows = CAT.agents
    .filter((a) => a.is_entrypoint)
    .map(
      (a) =>
        `<dt class="mono">${esc(a.agent_id)}</dt>` +
        `<dd>${esc(a.display_name)}<br>` +
        `<span class="mono">${esc(a.persona)} · ${esc(a.apqc_code)} · ` +
        `${esc(branchList(a.value_branch).join(", "))} · ${esc(a.model_tier)}` +
        (a.hitl_required ? " · hitl_required" : "") +
        "</span></dd>"
    )
    .join("");
  return (
    "<p>One row per agent you can talk to: its id, the role it is filed " +
    "under, its process code, the branch of the cost tree it serves and the " +
    "model tier it runs on. An agent marked <span class=\"mono\">hitl_required" +
    "</span> is bound to the <span class=\"mono\">request_approval</span> tool, " +
    "which writes a single row with <span class=\"mono\">decision = PENDING</span> " +
    "and can write nothing else.</p>" +
    `<dl>${rows}</dl>` +
    `<dl><dt>Approvals are written to</dt><dd class="mono">${esc(WS.approval.table)}</dd>` +
    `<dt>Process codes</dt><dd class="mono">${esc(
      Object.keys(CAT.by_apqc_code).join(" · ")
    )}</dd></dl>` +
    connectionDetail()
  );
}

/* value_branch is a string on most agents and a list on a few. Reading it
   directly is how a screen comes to print "s,u,p,p,l,y". Named apart from
   persona-data.js's branchesOf on purpose: two top-level declarations of one
   name in classic scripts is the later one, silently. */
function branchList(value) {
  return [].concat(value || []);
}

el("prov").innerHTML =
  technicalDrawer(drawerBody(), "agent ids, process codes, model tiers") +
  provenance(`<dt>Runtime</dt><dd>${runtimeNote()}</dd>`);
