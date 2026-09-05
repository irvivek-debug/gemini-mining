/* The agent teams. One shape, twelve of them.
 *
 * The reading this screen has to get right is the shape of a team. Four agents
 * run under a lead, but they are not four peers: the specialists work the
 * question at the same time and the reviewer works on what they produced.
 * Drawing the reviewer beside the specialists — which is what a flat roster
 * does — says it is one more opinion, when what it actually is is the stage
 * that challenges the other three. So the stages are rows, only the specialist
 * row fans sideways, and the reviewer sits below what it reads.
 *
 * The configuration is entirely catalog-driven: swap ?s= and the same code
 * renders a different team, because there is no per-team content here to go
 * stale.
 */

mountNav("workspace", "swarm.html");

const SWARM_IDS = CAT.agents
  .filter((a) => a.swarm_role === "coordinator")
  .map((a) => a.agent_id)
  .sort();

const current = SWARM_IDS.includes(param("s")) ? param("s") : SWARM_IDS[0];
const coord = AGENTS[current];
const swarm = CAT.swarms[coord.swarm_id];
const members = [current, ...swarm.specialists, swarm.critic];

/* A7: P7 reads the control room's overhead display from several metres back,
   where the audit measured 14px body text as illegible. Their configurations —
   and only theirs — step the whole screen up 1.5×. Applying it by persona
   rather than by a toggle is the point: the person does not have to know to
   ask for it. */
if (coord.persona === "P7") {
  el("wrap").classList.add("scale-lg");
  el("scale-note").textContent =
    "Overhead type scale (1.5×) — this configuration serves the Mine Controller, " +
    "who reads it from the control room display rather than at a desk.";
}

el("rail-cap").textContent = SWARM_IDS.length + " agent teams";
el("rail").innerHTML = SWARM_IDS.map((id) =>
  agentRow(id, "swarm.html?s=" + encodeURIComponent(id), current)
).join("");

const persona = PERSONAS[coord.persona] || {};
document.title = `${coord.display_name} — Mining Agents workspace`;
el("title").textContent = coord.display_name;
el("lede").textContent =
  "You ask one agent. Behind it: " +
  swarm.specialists.length +
  " specialists and a reviewer — " +
  members.length +
  " in all. Answerable for this team: " +
  (persona.title || coord.persona) +
  ". " +
  (coord.hitl_required
    ? "Needs your sign-off before anything reaches a system of record."
    : "This team reports; it commits nothing.");

/* Every member is WAITING, and that is the truthful state rather than a
   placeholder: nothing has run because nothing can be reached. The state
   vocabulary is still exercised in full here — glyph, word and colour on every
   badge — so that a reader learns it now and recognises it when a real run
   fills it in.

   What each member can do is said in words. The tool ids, the trace ids and the
   model names are all in the drawer at the foot; up here what matters is that
   this one looks up records and that one traces connections. */
function nodeCard(id, cls) {
  const a = AGENTS[id];
  const can = a.tools.map(plainTool);
  const traces = a.traversals.map(plainTraversal);
  return (
    `<div class="node${cls ? " " + cls : ""}">` +
    `<div class="node-id">${esc(id)}</div>` +
    `<div class="node-name">${esc(a.display_name)}</div>` +
    stateBadge("waiting", "not connected") +
    `<div class="node-tools" style="margin-top:8px">Can: ${esc(can.join(", "))}</div>` +
    (traces.length
      ? `<div class="node-tools">Traces ${esc(traces.join("; "))}</div>`
      : "") +
    (a.models.length
      ? '<div class="node-tools">Uses a trained prediction model</div>'
      : "") +
    "</div>"
  );
}

const blockers = flagsFor(members);

el("work").innerHTML =
  journeyFor(current) +

  '<div class="card" style="margin-top:16px"><div class="card-cap">How the question moves</div>' +
  '<div class="stage"><div class="stage-cap">1 · The lead — the one you ask</div>' +
  `<div class="fan">${nodeCard(current)}</div></div>` +
  '<div class="flow">↓ hands the same question to all of them at once</div>' +
  `<div class="stage"><div class="stage-cap">2 · ${swarm.specialists.length} specialists, working together</div>` +
  `<div class="fan">${swarm.specialists.map((id) => nodeCard(id)).join("")}</div></div>` +
  '<div class="flow">↓ then one agent reads what they produced</div>' +
  '<div class="stage"><div class="stage-cap">3 · The reviewer — what did they miss?</div>' +
  `<div class="fan">${nodeCard(swarm.critic, "critic")}</div></div>` +
  (coord.hitl_required
    ? '<div class="flow">↓ and there it stops, until a person decides</div>' +
      '<div class="stage"><div class="stage-cap">4 · Your sign-off</div>' +
      '<div class="fan"><div class="node" style="border-color:var(--warning)">' +
      '<div class="node-id">You</div>' +
      `<div class="node-name">${esc(persona.title || coord.persona)} approves, changes or refuses</div>` +
      stateBadge("waiting", "nothing waiting on you") +
      '<div class="node-tools" style="margin-top:8px">Your decision, and who made it, ' +
      "is recorded</div>" +
      "</div></div></div>"
    : "") +
  "</div>" +

  /* Blocked is a first-class state, so its band is a standing part of the
     screen rather than something that appears when a run fails. It renders
     even when empty, for the same reason the reviewer's band does on the
     handover sheet: a band that only appears when there is something to say
     cannot be trusted to be silent for the right reason. */
  '<div class="card" style="margin-top:16px"><div class="card-cap">What stands between this team and a run</div>' +
  (blockers.length
    ? "<ul class='tight'>" +
      blockers
        .map(
          (b) =>
            `<li>${stateBadge("blocked")} <strong>${esc(b.what)}</strong>` +
            `<div class="dim mono" style="font-size:11.5px">${esc(b.detail)}</div>` +
            `<div class="remedy">Remedy: ${esc(b.remedy)}</div></li>`
        )
        .join("") +
      "</ul>"
    : `<p>${stateBadge("done")} Nothing outstanding. Every source table is ` +
      "present, every model is verified, and the endpoint answers.</p>") +
  "</div>" +

  '<div class="card" style="margin-top:16px"><div class="card-cap">What this team actually did</div>' +
  notConnected("Every step will be listed here, in order. It has not been run.") +
  "</div>" +

  '<div class="card" style="margin-top:16px"><div class="card-cap">What it reads</div>' +
  `<p>Between them, the ${members.length} members of this team draw on ` +
  `${readsPlainly()}.</p>` +
  (tracesPlainly()
    ? "<p>Some of them do not stop at one record. They run a connection trace — " +
      "following the links out from a machine, a part or a person to see " +
      `${tracesPlainly()} — which is the question no single table answers.</p>`
    : "") +
  "</div>" +

  '<div style="margin-top:16px">' +
  unverified(members) +
  "</div>" +

  (coord.hitl_required
    ? '<div class="btn-row" style="margin-top:16px">' +
      `<button class="btn primary" id="review">See what this team would ask you to sign off</button>` +
      "</div>"
    : "");

/* What the team reads, in the words the vocabulary publishes, as one sentence
   rather than thirteen qualified table names. The raw list is in the drawer. */
function readsPlainly() {
  const names = [...new Set(members.flatMap((id) => AGENTS[id].source_tables))]
    .map(plainTable)
    .sort();
  if (!names.length) return "no stored records at all — they compute";
  if (names.length === 1) return names[0];
  return names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
}

/* The traces this team can follow, in the same words. Empty for a team that
   only reads, which is most of them. */
function tracesPlainly() {
  const traces = [...new Set(members.flatMap((id) => AGENTS[id].traversals))].map(
    plainTraversal
  );
  if (!traces.length) return "";
  if (traces.length === 1) return traces[0];
  return traces.slice(0, -1).join(", ") + " and " + traces[traces.length - 1];
}

/* Every table the team reads, as one list rather than one list per member: the
   specialists overlap, and a reader checking the sheet wants the boundary, not
   four copies of most of it. */
function swarmInputs() {
  return drawerTables(
    [...new Set(members.flatMap((id) => AGENTS[id].source_tables))].sort()
  );
}

if (coord.hitl_required) {
  el("review").addEventListener("click", () => openApproval(current));
}

/* Everything the copy above says in words, said again in the catalogue's own
   terms: who each member is and what part it plays, the code the team is filed
   under, the tier each member runs on, the formulas and statements behind an
   answer, and every table by its real name. The body says what this team does;
   this says how, and how it can be checked. */
function drawerBody() {
  const roles = members
    .map((id) => {
      const a = AGENTS[id];
      return (
        `<dt class="mono">${esc(id)}</dt>` +
        `<dd>${esc(a.display_name)} — ${esc(a.swarm_role)}, ` +
        `pattern ${esc(a.pattern)}, ${esc(a.model_tier)}<br>` +
        `<span class="mono">${esc(
          a.tools.concat(a.traversals, a.models).join(", ") || "no tools declared"
        )}</span></dd>`
      );
    })
    .join("");
  return (
    `<dl>${roles}` +
    `<dt>Filed under</dt><dd class="mono">${esc(coord.apqc_code)} · ${esc(
      coord.apqc_names.join(" / ")
    )}</dd>` +
    `<dt>Where the money is</dt><dd class="mono">${esc(
      [].concat(coord.value_branch).join(", ")
    )}</dd>` +
    (coord.hitl_required
      ? `<dt>Sign-off is written to</dt><dd class="mono">${esc(WS.approval.table)}</dd>`
      : "") +
    "</dl>" +
    "<h4>How an answer is worked out</h4>" +
    (drawerMethod(current) || "<p>Nothing deterministic is declared for this team.</p>") +
    "<h4>Every table these members read</h4>" +
    swarmInputs() +
    "<h4>What would close each gap the band above reports</h4>" +
    drawerFlags(members) +
    connectionDetail()
  );
}

el("prov").innerHTML =
  technicalDrawer(drawerBody(), "agent ids, process codes, statements, tables") +
  provenance(`<dt>Runtime</dt><dd>${runtimeNote()}</dd>`);
