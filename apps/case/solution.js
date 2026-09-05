/* Screen 1.4 — how the estate is assembled.
 *
 * This screen used to introduce itself with three counts spelled out in its own
 * headline and a body full of the words the build uses internally. A general
 * manager does not have a swarm; they have a question that needs arguing and a
 * question that needs answering, and those are the two things this screen is
 * actually about. The identifiers all still exist, and they are at the bottom.
 */

mountNav("case", "solution.html");

const catalog = DATA.catalog;
const byId = Object.fromEntries(catalog.agents.map((a) => [a.agent_id, a]));
const personas = DATA.personas.personas;

function name(id) {
  return byId[id] ? byId[id].display_name : id;
}

function personaTitle(code) {
  return personas[code] ? personas[code].title : "—";
}

/* The shape of a team is read off the catalog rather than typed into the prose,
   because the prose says it out loud and would otherwise be the one sentence on
   the screen a rebuild could quietly falsify. */
const TEAMS = Object.entries(catalog.swarms);
const SPECIALISTS = TEAMS[0][1].specialists.length;

TEAMS.forEach(([id, s]) => {
  if (s.specialists.length !== SPECIALISTS) {
    throw new Error(
      `team ${id} carries ${s.specialists.length} specialists where the first ` +
        `carries ${SPECIALISTS}; the copy on this screen claims one shape for all`
    );
  }
});

const SPELL = ["no", "one", "two", "three", "four", "five", "six"];
const spell = (n) => (SPELL[n] !== undefined ? SPELL[n] : String(n));

/* The scale tiles. They were on screen one until the case was reordered around
   the value argument: a reader who has not yet been shown the gap has no reason
   to care how many agents close it. Here, four screens in, the question has
   actually been asked. Each tile reads a counted field; none carries a literal,
   so a catalog change moves the screen rather than contradicting it. */
const TILES = [
  { n: catalog.counts.agent_nodes, label: "Agents deployed",
    sub: "Leads, specialists, reviewers and standalone agents together" },
  { n: catalog.counts.entrypoints, label: "Agents you can talk to",
    sub: "A specialist is reached through its team lead, never directly" },
  { n: catalog.counts.swarms, label: "Agent teams",
    sub: `A lead, ${spell(SPECIALISTS)} specialists and a reviewer apiece` },
  { n: catalog.counts.deep_agents, label: "Specialist agents",
    sub: "One role, one process, one question at a time" },
  { n: catalog.counts.hitl_entrypoints, label: "Need your sign-off",
    sub: "The agent proposes; a named person commits" },
  { n: Object.keys(personas).length, label: "Roles served",
    sub: "Each with the agents they own and the pool they answer for" },
  // Not "value branches": these are the nine domain tags the catalog carries,
  // which the value tree rolls up into six pools plus the agent above them.
  // Labelling them as pools puts a 9 on this screen against the 6 on screen
  // three, and leaves a reader to decide which of the two we meant.
  { n: Object.keys(catalog.by_value_branch).length, label: "Operational domains",
    sub: "Rolled up into the pools on the screen before this one" },
  { n: Object.keys(catalog.apqc_names).length, label: "Standard process areas",
    sub: "The framework a mining client already runs their operating model against" },
];

el("scale").innerHTML = TILES.map(
  (t) =>
    '<div class="card c3 stat"><div>' +
    `<div class="metric">${num(t.n)}</div>` +
    `<div class="metric-sub">${esc(t.label)}</div></div>` +
    `<div style="color:var(--fg-muted);font-size:12.5px;margin-top:10px">${esc(t.sub)}</div>` +
    "</div>"
).join("");

/* ---------- where a question needs arguing ---------- */

el("team-lede").textContent =
  "An agent team is one lead you put the question to, " +
  spell(SPECIALISTS) +
  " specialists working the same problem from different evidence, and a " +
  "reviewer whose only job is to find what the others missed. You never " +
  "address the specialists. The lead is the only part of the team that answers " +
  "you, and it answers with what the review survived.";

/* A table rather than twelve cards: the interesting thing is that the shape
   repeats exactly, and a table shows repetition where a grid of cards hides it.
   The member ids are in the drawer — a reader who wants to know which four
   agents argued a case can have them, and nobody else needs a column of them. */
el("swarms").innerHTML =
  '<table class="data"><thead><tr>' +
  "<th>The lead you talk to</th><th>Whose team it is</th>" +
  '<th style="text-align:right">In the team</th><th>Sign-off</th>' +
  "</tr></thead><tbody>" +
  TEAMS.map(([id, s]) => {
    const lead = byId[s.coordinator];
    const members = 1 + s.specialists.length + (s.critic ? 1 : 0);
    return (
      "<tr>" +
      `<td>${esc(name(s.coordinator))}</td>` +
      `<td>${esc(personaTitle(lead ? lead.persona : ""))}</td>` +
      `<td class="num">${esc(members)}</td>` +
      "<td>" +
      (lead && lead.hitl_required
        ? '<span class="badge b-warn">Needs yours</span>'
        : '<span style="color:var(--fg-dim)">Answers only</span>') +
      "</td></tr>"
    );
  }).join("") +
  "</tbody></table>";

/* ---------- where a question needs answering ---------- */

el("deep-lede").textContent =
  "The rest are single specialist agents: one role, one process, one question " +
  "at a time. Where the answer is a lookup and a calculation rather than an " +
  "argument, a team is the same overhead paid " +
  spell(1 + SPECIALISTS + 1) +
  " times over for an answer that does not change. The bars below are what " +
  "every agent on this screen is actually able to do, and there are only " +
  spell(Object.keys(catalog.tool_usage).length) +
  " of them.";

/* Sized by how many agents hold each. This is the honest summary of what these
   agents can do: mostly, they look things up. */
const TOOL_NOTE = {
  bq_query: "Reads the records. Every agent that answers with evidence uses it.",
  request_approval: "Stops and waits for a named person. Present on exactly the agents that need your sign-off.",
  operational_math: "Fixed arithmetic, so a rate or a ratio is computed rather than written out by a language model.",
  /* The three questions it can be asked come from the shared vocabulary. Typing
     them here as well would put a second copy of the graph screen's own list on
     a screen that cannot see when the first one changes. */
  graph_traverse:
    "Follows the links between records: " +
    Object.values(TRAVERSALS).join(", ") +
    ".",
  bqml_predict: "Calls a trained forecasting model rather than guessing the forecast.",
};

const toolMax = Math.max(...Object.values(catalog.tool_usage));
el("tools").innerHTML =
  '<div class="card c12"><div class="card-cap">What an agent is allowed to do, and how many hold it</div>' +
  Object.entries(catalog.tool_usage)
    .map(
      ([tool, n]) =>
        '<div class="bar-row">' +
        `<div class="name">${esc(plainTool(tool))}</div>` +
        `<div class="bar"><span style="width:${(n / toolMax) * 100}%"></span></div>` +
        `<div class="n">${esc(n)}</div>` +
        "</div>" +
        `<div style="font-size:12.5px;color:var(--fg-muted);margin:-4px 0 12px">${esc(
          TOOL_NOTE[tool] || ""
        )}</div>`
    )
    .join("") +
  "</div>";

/* ---------- the gate ---------- */

/* The gated agents, named by what they decide. "14 require approval" is a
   statistic; naming the decisions is a commitment someone can check. */
const gated = catalog.agents.filter((a) => a.is_entrypoint && a.hitl_required);

el("signoff-lede").innerHTML =
  `${esc(gated.length)} of the ${esc(catalog.counts.entrypoints)} agents you can ` +
  "talk to cannot act on their own conclusion. Each one assembles the case, " +
  "shows the evidence behind it, and then stops: it needs your sign-off before " +
  "anything moves. The other " +
  esc(catalog.counts.entrypoints - gated.length) +
  " answer questions. These change something, which is why the gate is on them " +
  "and not on the rest.";

el("signoff").innerHTML = gated
  .map(
    (a) =>
      "<tr>" +
      `<td>${esc(a.display_name)}</td>` +
      `<td>${esc(personaTitle(a.persona))}</td>` +
      (a.pattern === "A"
        ? '<td><span class="badge b-info">Team agent</span></td>'
        : '<td><span class="badge b-idle">Specialist agent</span></td>') +
      "</tr>"
  )
  .join("");

/* ---------- as it actually runs ---------- */

/* The service account count and the platform are architecture decisions
   recorded in the engagement notes, not derivable from the catalog, so they are
   labelled as the stated design rather than as counted output. */
const DEPLOY = [
  { n: catalog.counts.entrypoints, label: "Services running",
    sub: "One for each agent you can talk to. A specialist runs inside its lead's." },
  { n: 3, label: "Identities to manage",
    sub: "One per tier, not one per agent. A hundred identities is a hundred things to rotate." },
  { n: Object.keys(catalog.tool_usage).length, label: "Things an agent can do",
    sub: "And it can do only what its own entry in the build file grants it." },
  { n: new Set(catalog.agents.flatMap((a) => a.source_tables)).size,
    label: "Sets of records read",
    sub: "Each agent is bound to its own subset at the moment it is built." },
];

el("deploy").innerHTML = DEPLOY.map(
  (d) =>
    '<div class="card c3 stat"><div>' +
    `<div class="metric">${num(d.n)}</div>` +
    `<div class="metric-sub">${esc(d.label)}</div></div>` +
    `<div style="color:var(--fg-muted);font-size:12.5px;margin-top:10px">${esc(d.sub)}</div>` +
    "</div>"
).join("");

/* ---------- the machinery, at the end and closed ---------- */

/* Four things came off the page above: which agents make up each team, the id
   and shape of every gated agent, the size of model each class of agent runs
   on, and the one end-to-end timing this repository has actually taken. The
   timing is here with its open defect attached — a screen that quotes its own
   speed and omits that half the calls are the agent working out what its tables
   contain has reported a result and buried the finding. */
function drawerBody() {
  const teams = TEAMS.map(
    ([id, s]) =>
      `<dt class="mono">${esc(id)}</dt>` +
      `<dd class="mono">${esc(s.coordinator)} · ${esc(s.specialists.join(" "))} · ` +
      `${esc(s.critic || "no critic")}</dd>`
  ).join("");

  const gates = gated
    .map(
      (a) =>
        `<dt class="mono">${esc(a.agent_id)}</dt>` +
        `<dd>${esc(a.display_name)} — Pattern ${esc(a.pattern)}, ${esc(a.persona)}, ` +
        `<span class="mono">${esc(a.model_tier)}</span></dd>`
    )
    .join("");

  const tiers = Object.entries(
    catalog.agents.reduce((acc, a) => {
      acc[a.model_tier] = (acc[a.model_tier] || 0) + 1;
      return acc;
    }, {})
  )
    .sort((a, b) => b[1] - a[1])
    .map(([tier, n]) => `<span class="mono">${esc(tier)}</span> ${esc(n)}`)
    .join(" · ");

  return (
    "<p>The members of each team, the gated agents by id, the model tier each " +
    "class of agent runs on, and the one latency this repository has measured " +
    "end to end.</p>" +
    `<dl>${teams}${gates}` +
    `<dt>Model tiers</dt><dd>${tiers} — across all ${esc(
      catalog.counts.agent_nodes
    )} agent nodes. A critic does not need the model a coordinator needs, and ` +
    "paying for one everywhere is how a demo becomes too expensive to run " +
    "twice.</dd>" +
    "<dt>Measured latency</dt><dd>D01, the telemetry anomaly detector, answers " +
    '<span class="mono">"Which assets show abnormal telemetry in the last 24 ' +
    'hours?"</span> in <span class="mono">48.0s</span> on a warm container, ' +
    "spending 5 of its 9 BigQuery calls working out what the tables contain. " +
    "Removing that orientation cost is an open workstream; the figure is what " +
    "it does today, before that fix. Timed end to end on 2026-08-12.</dd>" +
    "</dl>" +
    `<p class="mono">${esc(catalog.source)} · generated ${esc(catalog.generated_at)}</p>`
  );
}

el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "agent ids, team members, model tiers, timings"
) + provenance(
  "<dt>Service accounts</dt><dd>Three-tier model, an architecture decision recorded in " +
    "the engagement notes rather than counted from the catalog.</dd>" +
    "<dt>Latency</dt><dd>D01 timed end to end on 2026-08-12; see the working notes</dd>"
);
