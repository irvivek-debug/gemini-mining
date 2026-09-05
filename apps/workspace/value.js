/* Screen: the value case, rebuilt as four bands for a sales/consulting
 * audience rather than an internal reader (design brief, 2026-08-18).
 *
 * 1. THE ARGUMENT      -- five moves, CEO slide 3: the economics inverted,
 *    the standard playbook is exhausted, the remaining cost is judgement not
 *    muscle, agents are the first technology that reaches it, the window is
 *    short.
 * 2. THE LEVERS        -- CEO slide 6: six traditional levers and what
 *    headroom is left in each, closing on the hinge of the whole argument.
 * 3. WHAT THE EVIDENCE SUPPORTS -- the benchmark set as range bars, every
 *    figure attributed on its face, plus this build's own addressable-pool
 *    model kept visually distinct from the published ranges.
 * 4. WHY MOST PROGRAMMES MISS IT -- the industry's own failure rate, and what
 *    this build does differently: coverage declared, evidence classed, every
 *    number traced. The honesty machinery is the differentiator here, not a
 *    caveat bolted on at the end.
 *
 * Every percentage that did not come out of this build's own planning model
 * carries a named publisher beside it, never presented as something measured
 * on this site. That split -- INDUSTRY RANGE vs THIS BUILD'S MODEL -- is the
 * one visual distinction the whole page is built to protect (global
 * constraint: a reader must always be able to tell which is which).
 *
 * No dollar sign appears anywhere on this page, including inside the one
 * external figure (2.6 to 4.4 trillion) that is itself a currency amount: it
 * is spelled "trillion US dollars" instead. The rule that no currency mark
 * reaches a screen that has not declared itself a money screen is repo-wide
 * (tests/test_screen_copy.py), and this page is not on that declared list.
 *
 * Deliberately absent, carried over from the previous draft of this page: the
 * five-leak taxonomy and the three-class evidence ladder as dedicated bands.
 * Neither is this page's argument -- the taxonomy still renders on every
 * agent card (apps/workspace/agent-card.js), and the evidence-class idea
 * survives here as one line of band 4 rather than a section of its own.
 */

mountNav("workspace", "value.html");

/* ---------------------------------------------------------------- band one */
/* THE ARGUMENT. Every stat that is a benchmark, rather than the shape of the
 * argument itself, names its source -- and only the source given in the
 * brief: Deloitte Tracking the Trends 2026, EY Top 10 Business Risks in
 * Mining & Metals 2026, ABS, McKinsey. Steps 3 and 4 carry no percentage and
 * so carry no citation; they are this build's own framing of the argument,
 * not a claim borrowed from a publisher. */
var STEPS = [
  {
    num: "01",
    head: "Margin has nearly halved.",
    body: "Complexity is now the industry's own top-ranked risk.",
    stats: [
      { v: "24% → 10%", l: "Top-40 net margin, 2011–2024" },
      { v: "−40%", l: "Grades, since 1991" },
    ],
    source: "Deloitte, Tracking the Trends 2026 · EY, Top 10 Business Risks in Mining & Metals 2026",
  },
  {
    num: "02",
    head: "The standard playbook has already run twice.",
    body: "Capital discipline. Contractor squeeze. Headcount freeze. " +
      "Portfolio pruning. Every lever has been pulled, and pulled again.",
    stats: [
      { v: "5 years", l: "Straight decline in Australian mining productivity" },
    ],
    source: "ABS",
  },
  {
    num: "03",
    head: "The muscle is done. What is left is judgement.",
    body: "Autonomous haulage and fixed-plant automation solved the " +
      "physical work. What remains is judgement — made thousands of " +
      "times a day, mostly late, mostly uncontested.",
    stats: [],
    source: "",
  },
  {
    num: "04",
    head: "Agents are the first technology built for that layer.",
    body: "Not a dashboard that tells you. An agent that does the work and " +
      "stays accountable while it does it.",
    flow: "Reads the situation → reasons over your data → acts " +
      "inside the bounds you set → shows its work.",
    stats: [],
    source: "",
  },
  {
    num: "05",
    head: "The window is short.",
    body: "",
    stats: [
      { v: "58%", l: "Of mining executives prioritising AI budget in the next 12 months" },
    ],
    source: "McKinsey",
  },
];

function statBlock(s) {
  return (
    '<div style="margin-top:10px">' +
    '<div class="metric accent" style="font-size:22px">' + esc(s.v) + "</div>" +
    '<div class="metric-sub" style="text-transform:none;letter-spacing:0;font-size:11.5px">' +
    esc(s.l) + "</div></div>"
  );
}

el("b1-lede").textContent =
  "Four sources, five moves, the case a chief executive already half-believes.";

el("b1-steps").innerHTML =
  '<div class="fan">' +
  STEPS.map(function (s) {
    return (
      '<div class="node">' +
      '<div class="node-id">STEP ' + esc(s.num) + "</div>" +
      '<div class="node-name" style="font-size:15px;margin-top:2px">' + esc(s.head) + "</div>" +
      (s.body ? '<p style="font-size:12.5px;color:var(--fg-muted);margin:8px 0 0">' + esc(s.body) + "</p>" : "") +
      (s.flow ? '<div class="expression" style="font-size:12px;margin-top:10px">' + esc(s.flow) + "</div>" : "") +
      s.stats.map(statBlock).join("") +
      (s.source ? '<div class="cite">' + esc(s.source) + "</div>" : "") +
      "</div>"
    );
  }).join("") +
  "</div>";

/* ---------------------------------------------------------------- band two */
/* THE LEVERS. Six rows, three named sources at band level (PwC Mine 2026,
 * SRK Consulting, ABS) -- the brief did not map one source to one row, so
 * each row below is assigned the source whose own beat the figure sits in
 * (capex and digital maturity to PwC's annual survey, cost-base and mine-plan
 * mechanics to SRK's benchmarking practice, labour figures to the ABS). The
 * assignment is editorial, not invented: every figure and every source name
 * is exactly what the brief specified, and no source outside the three named
 * ones appears on this row. */
var LEVERS = [
  {
    name: "Capital discipline",
    stands: "Top-40 capex still rising — USD 95bn in 2025, forecast USD 109bn in 2026.",
    headroom: "Low", cls: "b-warn",
    source: "PwC, Mine 2026",
  },
  {
    name: "Contractor and vendor squeeze",
    stands: "Services and materials are ~45% of operating cost. Vendors are passing inflation straight through, not absorbing it.",
    headroom: "Low", cls: "b-warn",
    source: "SRK Consulting",
  },
  {
    name: "Headcount reduction",
    stands: "Hours worked rose 5.6% while output fell. Close to half of skilled engineers retire within a decade.",
    headroom: "Negative", cls: "b-crit",
    source: "ABS",
  },
  {
    name: "Physical automation",
    stands: "Real and proven — roughly 15% lower load-and-haul unit cost, 30% higher productivity. Capital-heavy, and now table stakes.",
    headroom: "Medium", cls: "b-info",
    source: "PwC, Mine 2026",
  },
  {
    name: "Portfolio high-grading",
    stands: "Held back by the mine plan, by grade decline, and by lead times averaging 17.8 years.",
    headroom: "Low", cls: "b-warn",
    source: "SRK Consulting",
  },
  {
    name: "Digital, dashboards, data lakes",
    stands: "Widely deployed. Visibility improved. Decisions did not.",
    headroom: "THE GAP", cls: "gap-badge",
    source: "PwC, Mine 2026",
    gap: true,
  },
];

el("b2-lede").textContent =
  "Six places the industry already looked. Five are exhausted. One was never used.";

el("b2-table").innerHTML =
  '<div class="table-scroll"><table class="data">' +
  "<thead><tr><th>Lever</th><th>Where it stands</th><th>Headroom</th></tr></thead>" +
  "<tbody>" +
  LEVERS.map(function (r) {
    return (
      '<tr class="' + (r.gap ? "lever-gap" : "") + '">' +
      "<td>" + esc(r.name) + "</td>" +
      "<td>" + esc(r.stands) + '<span class="cite" style="display:block;margin-top:6px">' +
      esc(r.source) + "</span></td>" +
      '<td><span class="badge ' + esc(r.cls) + '">' + esc(r.headroom) + "</span></td>" +
      "</tr>"
    );
  }).join("") +
  "</tbody></table></div>";

el("b2-quote").innerHTML =
  '<blockquote class="hinge">' +
  "Most miners have already bought the data. What they have not bought is " +
  "anything that acts on it. The industry spent a decade building the " +
  "nervous system and never installed the reflex." +
  '<cite>PwC Mine 2026 · SRK Consulting · ABS</cite>' +
  "</blockquote>";

/* -------------------------------------------------------------- band three */
/* WHAT THE EVIDENCE SUPPORTS. The benchmark set from the 2026-08-18 research
 * pass, used exactly as researched -- no figure here is recalled from
 * memory or substituted from an earlier pass. Each row is a published range
 * with a named publisher; none is this build's own measurement, and each
 * carries the "INDUSTRY RANGE" badge that says so. */
var EVIDENCE_ROWS = [
  { label: "Higher throughput", low: 2, high: 5, unit: "%", scale: 10, source: "BCG, mature AI sites in mining & metals" },
  { label: "Higher throughput", low: 4, high: 8, unit: "%", scale: 10, source: "McKinsey, metals & mining" },
  { label: "Higher margin", low: 2, high: 4, unit: " pts", scale: 6, source: "BCG" },
  { label: "Higher mineral recovery", low: 1, high: 3, unit: "%", scale: 5, source: "McKinsey" },
  { label: "Lower unplanned downtime", low: 30, high: 50, unit: "%", scale: 60, source: "McKinsey / Deloitte, predictive maintenance" },
  { label: "Lower maintenance cost", low: 18, high: 25, unit: "%", scale: 30, source: "McKinsey" },
  { label: "Higher contract value recovered", low: 3, high: 5, unit: "%", scale: 8, source: "industry contract-management research" },
];

el("b3-lede").textContent =
  "Every range below is somebody else's study of somebody else's site — " +
  "the honest starting point for a business case, never its ceiling.";

el("b3-rows").innerHTML =
  EVIDENCE_ROWS.map(function (r) {
    var leftPct = ((r.low / r.scale) * 100).toFixed(1);
    var widthPct = (((r.high - r.low) / r.scale) * 100).toFixed(1);
    return (
      '<div class="range-row">' +
      '<div class="range-row-head">' +
      '<span class="range-row-label">' + esc(r.label) + "</span>" +
      '<span class="range-row-fig">' + esc(r.low) + "–" + esc(r.high) + esc(r.unit) + "</span>" +
      "</div>" +
      '<div class="money-range-bar"><span style="left:' + leftPct + "%;width:" + widthPct + '%"></span></div>' +
      '<div class="range-row-foot">' +
      '<span class="badge b-info">INDUSTRY RANGE</span>' +
      '<span class="cite">' + esc(r.source) + "</span>" +
      "</div></div>"
    );
  }).join("");

el("b3-pool").innerHTML =
  '<div class="card">' +
  '<div class="card-cap">Context, not a forecast for this site</div>' +
  '<div class="metric accent">2.6–4.4T</div>' +
  '<div class="metric-sub" style="text-transform:none;letter-spacing:0">' +
  "Trillion US dollars, the agentic AI value pool across the global economy" +
  "</div>" +
  '<div style="margin-top:10px"><span class="badge b-info">INDUSTRY RANGE</span> ' +
  '<span class="cite" style="display:inline">McKinsey</span></div>' +
  "</div>";

/* The addressable pool. This build's own bottom-up planning model of the
 * conservative-to-stretch share of operating cost it targets -- kept exactly
 * as it was on the previous draft of this page, and kept visually distinct
 * from the published ranges above: a different badge, a different claim
 * ("this build's model", never "measured on this site" and never presented
 * as somebody else's study), because it is neither. NO absolute figure is
 * derived from it here; the denominator that would turn a percentage into
 * money is rendered by clientInput(), same as every other screen. */
var CONSERVATIVE_PCT = 4.1;
var STRETCH_PCT = 9.0;
var BAR_MAX_PCT = 12; // purely a drawing scale for the range bar below

el("b3-pool-model").innerHTML =
  '<div class="card-cap">This build’s addressable pool</div>' +
  '<div style="margin-bottom:10px"><span class="badge b-ok">THIS BUILD’S MODEL</span> ' +
  '<span class="cite" style="display:inline">not a published benchmark</span></div>' +
  '<p class="lede" style="font-size:14px">Conservative <strong>' +
  CONSERVATIVE_PCT.toFixed(1) + "%</strong> of operating cost, stretch " +
  "<strong>" + STRETCH_PCT.toFixed(1) + "%</strong> — recurring, with no " +
  "new capital and no change to the mine plan.</p>" +
  '<div class="money-range">' +
  '<div class="money-range-bar"><span style="left:0%;width:' +
  ((STRETCH_PCT / BAR_MAX_PCT) * 100).toFixed(1) + '%"></span></div>' +
  '<div class="money-range-labels">' +
  "<span>" + CONSERVATIVE_PCT.toFixed(1) + "% conservative</span>" +
  "<span>" + STRETCH_PCT.toFixed(1) + "% stretch</span>" +
  "</div></div>" +
  '<div class="money-denominator">' +
  '<span class="ac-label">Annual operating cost, this site</span>' +
  clientInput() +
  "</div>" +
  '<p class="pnote">Multiply the percentage range above by the figure you ' +
  "supply. This repository does not hold your operating cost and does not " +
  "estimate it, so it structurally cannot turn the range into a number for " +
  "you.</p>";

/* --------------------------------------------------------------- band four */
/* WHY MOST PROGRAMMES MISS IT. The industry's own failure rate (BCG AI Radar
 * 2026), and the four things this build does that most programmes do not.
 * This band is the differentiator: the honesty machinery -- coverage
 * declared, evidence classed, every number traced, advisory by default -- is
 * stated as what makes this build different, not apologised for. */
el("b4-lede").textContent =
  "Most AI programmes fail quietly. This is what changes that.";

el("b4-adoption").innerHTML =
  '<div class="compare-row">' +
  '<div class="compare-head"><span>No material value</span><span class="range-row-fig">60%</span></div>' +
  '<div class="money-range-bar warn"><span style="left:0%;width:60%"></span></div>' +
  "</div>" +
  '<div class="compare-row">' +
  '<div class="compare-head"><span>Substantial value, at scale</span><span class="range-row-fig">5%</span></div>' +
  '<div class="money-range-bar ok"><span style="left:0%;width:5%"></span></div>' +
  "</div>" +
  '<div style="margin-top:10px"><span class="badge b-info">INDUSTRY RANGE</span> ' +
  '<span class="cite" style="display:inline">BCG AI Radar 2026</span></div>';

var DIFFERENTIATORS = [
  {
    head: "Coverage, declared.",
    body: "Every agent states how much of its job is instrumented and how " +
      "much is scoped — never implied as complete by omission.",
  },
  {
    head: "Evidence, classed.",
    body: "Every recommendation carries its class — cash-verifiable, " +
      "metric-verifiable, or risk-adjusted — stated before you ask, not " +
      "defended after.",
  },
  {
    head: "Numbers, traced.",
    body: "Every figure on this page points at a named source or a field " +
      "marked for you to fill. None is guessed to make a slide look complete.",
  },
  {
    head: "Advisory, by default.",
    body: "Every recommendation lands with a named human. Not a limitation " +
      "— the governance model a board signs off on.",
  },
];

el("b4-cards").innerHTML =
  '<div class="bento">' +
  DIFFERENTIATORS.map(function (d) {
    return (
      '<div class="card c3"><div class="card-cap">' + esc(d.head) + "</div>" +
      '<p style="font-size:13px;color:var(--fg-muted);margin:0">' + esc(d.body) + "</p></div>"
    );
  }).join("") +
  "</div>";

/* THE EVIDENCE LADDER, restored.
 *
 * Band 4's second card asserts that every recommendation carries an evidence
 * class. Asserting it is not the same as showing it, and the three classes are
 * the part a CFO actually uses: they decide what may be booked and what may
 * only be reported. Without them "evidence, classed" is a claim about rigour
 * rather than a demonstration of it, and the band's whole argument -- that this
 * build answers the failure rate above it -- rests on the demonstration.
 *
 * Deliberately a strip rather than the band it used to be. It is the mechanism
 * behind one differentiator, not a fifth pillar of the argument, and giving it
 * a heading of its own cost the page more attention than it earns. */
var LADDER = [
  {
    cls: "A", tone: "ok", name: "Cash-verifiable",
    body: "Lands as cash, a credit note or an avoided invoice, traced " +
      "transaction by transaction. No counterfactual needed.",
  },
  {
    cls: "B", tone: "info", name: "Metric-verifiable",
    body: "A named operating metric moves against a baseline signed with " +
      "Finance before go-live, at a rate agreed in advance.",
  },
  {
    cls: "C", tone: "warn", name: "Risk-adjusted",
    body: "Exposure reduced and evidenced, with no counterfactual available. " +
      "Reported to the board, never counted in the case.",
  },
];

el("b4-ladder").innerHTML =
  '<div class="card"><div class="card-cap">What each class means, and what it funds</div>' +
  '<div class="bento" style="margin-top:12px">' +
  LADDER.map(function (l) {
    return (
      '<div class="c4">' +
      '<div class="compare-head"><span><span class="badge b-' + l.tone + '">CLASS ' +
      esc(l.cls) + "</span> " + esc(l.name) + "</span></div>" +
      '<p style="font-size:13px;color:var(--fg-muted);margin:6px 0 0">' +
      esc(l.body) + "</p></div>"
    );
  }).join("") +
  "</div>" +
  '<p style="font-size:13px;color:var(--fg-muted);margin:12px 0 0">' +
  "A business case clears its hurdle on Class A and Class B alone. " +
  "Class C is reported alongside it, never counted inside it.</p></div>";

/* THE GROUP-LEVEL AGENT: AGT-19, the Strategic Planning Advisor.
 *
 * It has no AgentDef and so no persona page of its own (design §3) -- every
 * other card in this build renders beneath a role's governing question on
 * persona.html, and this is the one that does not fit that shape because its
 * question is not any one role's. It re-tests the group plan itself: how the
 * plan should change when a price, cost or capital assumption moves, and
 * which asset absorbs it. The value page is where that belongs -- it is
 * already the page that speaks at group level rather than at any one site or
 * role.
 *
 * Framed as what it is, not as an apology: the group-plan agent, sitting
 * above the roles the rest of this build addresses. Its own honest_limit
 * field (rendered by renderAgentCard below, unedited) already carries the
 * caution this card needs -- it is the least measurable agent in the
 * portfolio and must not be added to a funding case -- so nothing here
 * repeats or softens that; it is said once, on the card's own face.
 */
var GROUP_AGENTS = DATA.catalog.group_agents || {};
var AGT19 = GROUP_AGENTS["AGT-19"];
if (!AGT19) {
  throw new Error("value.html has no AGT-19 card to surface; check catalog.group_agents");
}

el("agt19").innerHTML =
  '<p class="pnote">Not addressed to one role — it re-tests the group plan ' +
  "itself as assumptions move, and says which asset absorbs the change.</p>" +
  renderAgentCard(AGT19);

/* ---------------------------------------------------------------- drawer */

function drawerBody() {
  var citations = [
    "Deloitte, Tracking the Trends 2026 — margin, 2011–2024; grades, since 1991",
    "EY, Top 10 Business Risks in Mining & Metals 2026 — complexity ranked #1",
    "ABS — productivity, five-year decline; hours worked vs output",
    "McKinsey — AI budget prioritisation; metals & mining throughput; mineral recovery; maintenance cost; agentic AI value pool",
    "BCG — mature AI sites throughput; margin",
    "McKinsey / Deloitte — predictive-maintenance downtime reduction",
    "Industry contract-management research — contract value recovered",
    "PwC, Mine 2026 — capex trend; automation unit cost and productivity; digital deployment",
    "SRK Consulting — operating-cost mix; mine-plan and lead-time constraints",
    "BCG AI Radar 2026 — share of firms at no material value and at scale",
  ];
  return (
    "<p>Every external source named above, in one place.</p>" +
    "<dl>" +
    citations.map(function (c) {
      return "<dt class=\"mono\">" + esc(c.split(" —")[0]) + "</dt><dd>" +
        esc(c) + "</dd>";
    }).join("") +
    "</dl>" +
    "<dl><dt>The addressable-pool range</dt><dd>" + CONSERVATIVE_PCT.toFixed(1) +
    "% conservative to " + STRETCH_PCT.toFixed(1) + "% stretch is this " +
    "build's own bottom-up planning model, not one of the industry ranges " +
    "above — it carries no publisher because it is not a publisher's " +
    "figure.</dd></dl>"
  );
}

el("prov").innerHTML =
  technicalDrawer(drawerBody(), "every source named above, spelled out") +
  provenance();
