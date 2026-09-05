/* The shift handover brief. One agent team, two buttons, and a document.
 *
 * Every other screen in this application is a place to ask something. This one
 * is a thing to read: the Shift Supervisor reads it at the change of shift,
 * decides what to carry forward, and often walks away with it on paper. So
 * there is no rail and no parameter — nothing that changes what the sheet is
 * about — and the whole document is written to survive being printed. The two
 * controls it does carry are the two things the reader does with it: write it,
 * and print it.
 *
 * The brief has four parts because four agents write it. Three each own a
 * subject — availability, production, safety — and the fourth reads what they
 * produced and names what they did not cover. That band renders on every load,
 * including when it has nothing to report, and the reason is in the
 * supervisor's own words further down the page: a brief that was useless
 * because it missed the crusher event is indistinguishable, to its reader, from
 * a brief that had nothing to miss. A band that appears only when there is
 * something to say cannot be trusted to be silent for the right reason.
 *
 * The agent ids, the process code, the model tiers and the real table names are
 * all in the technical detail at the foot. They are what an auditor checks the
 * sheet against; they are not what the supervisor reads at 6am.
 */

mountNav("workspace", "handover.html");

const S12 = AGENTS.S12;
const swarm = CAT.swarms.S12;
const members = ["S12", ...swarm.specialists, swarm.critic];
const supervisor = PERSONAS[S12.persona] || {};

document.title = `${S12.display_name} — Mining Agents workspace`;
el("title").textContent = "Shift handover brief";

/* What each specialist covers, read off its own name. The sentence below binds
   a count to a list of subjects, and the two have to be the same list: "3 of
   them cover availability, production and safety" was typed underneath a
   derived number and would have gone on reading true, and wrong, the day a
   fourth specialist joined the team. Every one of them is named "<subject>
   Summariser" in the catalogue, so the subject is the name without its trade;
   a member that stops being one stops this screen, exactly as the cockpit and
   the solution screen stop when the teams change shape under them. */
const COVERS = swarm.specialists.map((id) => {
  const name = AGENTS[id].display_name;
  if (!/\sSummariser$/.test(name)) {
    throw new Error(`${id} is "${name}"; this sheet says its specialists summarise a subject`);
  }
  return name.replace(/\sSummariser$/, "").toLowerCase();
});

/* The serial comma is load-bearing: two of the three subjects are compound
   ("production & recovery"), and without it the last two run together. */
const COVERED =
  COVERS.length > 1
    ? COVERS.slice(0, -1).join(", ") + ", and " + COVERS[COVERS.length - 1]
    : COVERS[0];

/* The lede is the one place the reader is told what they are holding, so it is
   said in the words they would use: how many agents write it, what each of them
   covers, and whether anything on it commits the site to anything. The agent id
   that used to open this sentence is in the drawer, where a reader who wants to
   check the sheet can find it and a reader who wants to read it need not. */
el("lede").textContent =
  "What the last shift leaves the next one. A team of " +
  members.length +
  " writes it — " +
  COVERS.length +
  " covering " +
  COVERED +
  ", one more reporting what they left out. " +
  (S12.hitl_required
    ? "It needs your sign-off before it is issued."
    : "It commits nothing and needs no sign-off: it is read, not actioned.");

/* The shift window is a site fact, not a repository fact. Nobody here knows
   whether this mine runs two twelves or three eights, and inventing 06:00–18:00
   because it is the common case would put a fabricated number at the top of the
   one screen that leaves the building on paper. */
function window_() {
  return (
    '<div class="card"><div class="card-cap">Shift window</div>' +
    '<div class="run-state">' +
    clientInput() +
    "<div><div>The shift pattern this brief covers.</div>" +
    '<div class="dim" style="font-size:12.5px;margin-top:4px">Whether this site ' +
    "runs two twelve-hour shifts or three eights, and when they change, is a " +
    "site roster fact. This repository does not hold one, and a plausible " +
    "window printed here would be read as the real one.</div></div>" +
    "</div></div>"
  );
}

/* One section per agent. The section is the deliverable and the section is
   real: which agent writes it, and what it is entitled to read while writing
   it, are both facts of the deployed catalog. Only the sentences are missing,
   and the block that says so is the same one every other screen uses.

   What each one draws on is named in the words the shared vocabulary
   publishes — work orders, shift production, safety incidents — and nothing
   more. Each section used to end in one collapsible per source table, carrying
   the qualified BigQuery name, a column count and every column's type: ten of
   them down the one screen a shift supervisor reads at 6am, in front of the
   drawer at the foot that exists to hold exactly that. The schemas are in that
   drawer now, which is where the instruction put them. */
function section(id, index) {
  const a = AGENTS[id];
  return (
    '<div class="card" style="margin-top:16px">' +
    `<div class="card-cap">${index} · ${esc(a.display_name)}</div>` +
    `<div class="dim" style="font-size:12.5px;margin-bottom:12px">Writes this ` +
    `section from ${esc(whatItReads(a))}.</div>` +
    notConnected("Not yet written.") +
    "</div>"
  );
}

/* What one agent reads, as a phrase that fits inside a sentence. The
   agent-teams screen has a function of the same shape, deliberately not the
   same name: these are classic scripts sharing one global scope, and two
   top-level declarations of one name is silently the later one. That one folds
   together a whole team, this one takes a single agent. */
function whatItReads(a) {
  const names = a.source_tables.map(plainTable).sort();
  if (!names.length) return "nothing stored — it computes";
  if (names.length === 1) return names[0];
  return names.slice(0, -1).join(", ") + " and " + names[names.length - 1];
}

/* The sentence the band leads with before anyone has run anything. It is named
   because the run handler both replaces it and, when a run fails without
   writing a word, has to put it back exactly. */
const UNCHECKED = "Coverage has not been checked for this window.";

/* The agent that reports what the others missed, always drawn, never
 * conditional.
 *
 * It gets the loudest treatment on the page — the same 2px critical border the
 * sign-off sheet uses — because on a handover the thing that hurts is not the
 * item that was reported badly, it is the item that was not reported at all. */
function omission() {
  const critic = AGENTS[swarm.critic];
  return (
    '<div class="unverified" style="margin-top:16px">' +
    '<div class="unverified-cap"><span class="badge b-crit">⚠ WHAT THIS BRIEF LEFT OUT</span>' +
    `<span>${esc(critic.display_name)}</span></div>` +
    // The headline is a statement about right now, and the Run button below
    // changes right now. It is the one sentence on this sheet the reader can
    // falsify by clicking, so the run handler owns it and rewrites it.
    `<ul><li><strong id="omission-head">${esc(UNCHECKED)}</strong>` +
    '<div class="dim">' +
    runtimeNote() +
    "</div>" +
    '<div class="remedy">Write the brief above and this agent runs with the ' +
    "others. This band never hides an empty result — when it finds nothing, " +
    "it says so.</div></li>" +
    `<li><strong>What it checks the brief against</strong><div class="dim">${esc(
      whatItReads(critic)
    )}</div>` +
    '<div class="remedy">It goes back to the records themselves rather than ' +
    "reading the sections above, so something none of the other agents picked " +
    "up is still there to be found.</div></li></ul></div>"
  );
}

/* Why a fourth agent reads the other three at all, in the supervisor's own
   recorded words. The quote is transcribed with its source line, which is what
   makes it quotable: it is evidence from the interview, not a justification
   written afterwards to fit the design. */
function why() {
  const quote = (supervisor.pain_points || []).find((q) => /missed|useless/i.test(q.quote));
  if (!quote) return "";
  return (
    '<div class="card" style="margin-top:16px">' +
    '<div class="card-cap">Why a fourth agent checks the other three</div>' +
    '<blockquote class="verbatim">' +
    esc(quote.quote.trim()) +
    /* The document in an element of its own, as in workspace.js's journey
       citation: a file name standing alone is a citation, and a file name
       inside a line of prose is the machinery talking. */
    `<cite>${esc(supervisor.title || S12.persona)} · ` +
    "<span>docs/personas-and-value-tree.md</span> " +
    `line ${esc(quote.source_line)}</cite></blockquote>` +
    "</div>"
  );
}

/* One streamed call, to the one agent the catalogue permits.
 *
 * The sheet has four sections, and it is tempting to run four things. The
 * catalogue does not allow it: the team names a lead, three specialists and a
 * reviewer, and only the lead can be addressed. The other four are how the team
 * divides the work, not four things a reader may invoke.
 *
 * EventSource reconnects by itself whenever a connection closes, and this
 * question was measured at a little under two minutes of real model time. So
 * every path that could leave one open closes it: a second click, a stream that
 * breaks, and a reader who walks away mid-answer.
 */
function mountRun() {
  el("run").innerHTML =
    '<div class="run-brief">' +
    '<button class="ask primary" id="run-brief" type="button">Write this brief now</button>' +
    '<p class="pnote">One agent, its team writes the whole sheet — a minute or ' +
    "two. Asking again restarts it.</p></div>" +
    '<div class="brief-out" id="brief-out" aria-live="polite"></div>';

  let live = null;

  function stop() {
    const was = live;
    live = null;
    if (!was) return;
    was.abandoned = true; // so a late frame does not write into a dead answer
    if (was.handle) was.handle.close();
  }

  // Leaving the page stops the reader reading. It does not, on its own, stop
  // the stream costing anything.
  addEventListener("pagehide", stop);

  /* The omission band states, at the top of the sheet, that coverage has not
     been checked for this window. That is true of a sheet nobody has run and
     false a minute after they have, and the band is drawn once, before the
     button is ever pressed — so the run rewrites it rather than leaving a
     sentence on the page the page itself has just disproved. The band is in
     #brief, which is written after this function returns, so the node is
     looked up at click time and not held. */
  function coverage(text) {
    const head = document.getElementById("omission-head");
    if (head) head.textContent = text;
  }

  el("run-brief").addEventListener("click", () => {
    stop();
    el("brief-out").innerHTML =
      '<div class="log" id="brief-log"></div>' +
      '<div class="answer" id="brief-answer"></div>';
    const log = el("brief-log");
    const answer = el("brief-answer");

    function say(text, cls) {
      const line = document.createElement("p");
      line.className = cls;
      line.textContent = text;
      log.appendChild(line);
    }

    coverage("The brief is being written now.");

    /* The answer as the agent wrote it, kept whole.
     *
     * The pane used to append each frame to textContent, which is why a live
     * run printed ### and ** at a shift supervisor: there was no step at which
     * anything looked at the answer. It cannot be an append now either. A frame
     * boundary falls wherever the model put it — mid-word, mid-`**bold**`, mid
     * code span — so the only text it is safe to render is all of it, every
     * time. An 8,239-character answer re-rendered per frame is nothing next to
     * the hundred seconds the reader is already waiting. */
    let rawText = "";

    function render() {
      const said = plainAnswer(rawText);
      answer.innerHTML =
        said.html +
        (said.technical
          ? technicalDrawer(
              '<pre class="mono">' + esc(said.technical) + "</pre>",
              "the agent's own words for the steps that failed"
            )
          : "");
    }

    const mine = { abandoned: false, wrote: false, handle: null };
    live = mine; // assigned first: a stream can finish inside the call that
                 // starts it, and its onDone runs before streamAgent returns.
    mine.handle = streamAgent({
      agentId: "S12",
      prompt:
        "Write the shift handover brief for this site: what changed, what is at " +
        "risk, what the next shift must pick up, and what was left unsaid.",
      userId: "workspace",
      sessionId: `handover-${Date.now()}`,
      onStep: (step) => {
        if (mine.abandoned) return;
        if (step.kind === "text") {
          rawText += step.text;
          render();
          if (!mine.wrote) {
            mine.wrote = true;
            coverage(
              "The brief above has been written; the reviewer's findings are included."
            );
          }
          return;
        }
        say(step.text, step.kind === "step-failed" ? "step failed" : "step");
      },
      onError: (detail) => {
        if (mine.abandoned) return;
        say(detail, "step failed");
        // Nothing was written, so the sheet goes back to the sentence that is
        // true of a window nobody has covered.
        if (!mine.wrote) coverage(UNCHECKED);
      },
      onDone: () => {
        if (live === mine) live = null;
        // Only when the stream ran to its end with nothing to show.
        if (!mine.wrote && !rawText.trim()) {
          answer.textContent = "The agent finished without writing an answer.";
        }
      },
    });
    if (mine.abandoned && mine.handle) mine.handle.close();
  });
}

mountRun();

el("brief").innerHTML =
  '<div style="margin-top:16px">' +
  window_() +
  "</div>" +
  omission() +
  swarm.specialists.map((id, i) => section(id, i + 1)).join("") +
  why() +
  '<div style="margin-top:16px">' +
  unverified(members) +
  "</div>";

/* Print is one of the two ways this screen is read, so it is a control on the
   page and not something the reader has to know a keyboard shortcut for.
 *
 * A collapsed <details> prints as an empty box: its contents are not rendered,
 * so the technical detail at the foot — and every table filed inside it — would
 * come out as bordered rectangles with nothing in them. Every disclosure is
 * opened before the print dialog and restored afterwards, so the screen the
 * supervisor was reading is the screen they get back. The hook is on the events
 * rather than on the button because Ctrl-P is how most people will actually
 * print this. */
let reclose = [];

addEventListener("beforeprint", () => {
  reclose = [...document.querySelectorAll("details:not([open])")];
  reclose.forEach((d) => (d.open = true));
});

addEventListener("afterprint", () => {
  reclose.forEach((d) => (d.open = false));
  reclose = [];
});

el("print").addEventListener("click", () => window.print());

/* Everything the sheet above stopped naming, in the catalogue's own terms: who
   writes each section, the tier each of them runs on, the code the team is
   filed under, and every table by its real qualified name. The brief is what
   the supervisor reads; this is what an auditor checks it against, and it is
   one disclosure at the foot rather than one beside every claim. */
function drawerBody() {
  const roles = members
    .map((id) => {
      const a = AGENTS[id];
      return (
        `<dt class="mono">${esc(id)}</dt>` +
        `<dd>${esc(a.display_name)} — ${esc(a.swarm_role)}, ${esc(a.model_tier)}<br>` +
        `<span class="mono">${esc(
          a.source_tables.join(", ") || "no tables declared"
        )}</span></dd>`
      );
    })
    .join("");
  return (
    "<p>One row per member of the team that writes this brief: its id, the part " +
    "it plays, the model tier it runs on, and every table it is entitled to " +
    "read.</p>" +
    `<dl>${roles}` +
    `<dt>Filed under</dt><dd class="mono">${esc(S12.apqc_code)} · ${esc(
      S12.apqc_names.join(" / ")
    )}</dd>` +
    `<dt>Sign-off required</dt><dd class="mono">${S12.hitl_required ? "yes" : "no"}</dd>` +
    "</dl>" +
    "<h4>Every table this team reads</h4>" +
    "<p>One row above names the tables each member is entitled to read. These " +
    "are the same tables to the column: what BigQuery calls each one, how many " +
    "rows it held when this build profiled it, and what every column means " +
    "where that has been written down.</p>" +
    drawerTables(
      [...new Set(members.flatMap((id) => AGENTS[id].source_tables))].sort()
    ) +
    "<h4>What would close each gap the sheet reports as unverified</h4>" +
    drawerFlags(members) +
    connectionDetail()
  );
}

el("prov").innerHTML =
  technicalDrawer(drawerBody(), "agent ids, model tiers, process code, tables") +
  provenance(
    `<dt>Reader</dt><dd>${esc(supervisor.title || S12.persona)}</dd>` +
      `<dt>Runtime</dt><dd>${runtimeNote()}</dd>`
  );
