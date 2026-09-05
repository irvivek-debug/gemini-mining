/* Shared pieces of Application 2.
 *
 * The workspace is where a person does the work, so every screen has to answer
 * three questions the case application never had to: what does this agent
 * actually read, by what method, and what part of the answer is not settled.
 * The components below are the four answers, written once:
 *
 *   runState()   — whether the deployed agents are reachable at all
 *   agentCard()  — one entrypoint, at the level of detail a rail needs
 *   drawerMethod() — the formula, pattern or model behind a result
 *   drawerTables() — the tables and columns, named, with their gaps
 *
 * The "drawer" prefix is not decoration. It says the function writes technical
 * drawer copy and nothing else, which is what lets tests/test_screen_copy.py
 * read it as drawer copy: a screen builds its drawer in drawerBody(), and a
 * builder shared across screens announces itself the same way. Without that,
 * a shared builder is scanned as body copy on every screen that loads it, and
 * an expression like "GRAPH TRAVERSAL · blast_radius" is either a false alarm
 * or an untestable exemption.
 *
 * Nothing here composes prose on an agent's behalf. Where an agent's own words
 * would go, notConnected() goes instead.
 */

const CAT = DATA.catalog;
const WS = DATA.workspace;
const AGENTS = Object.fromEntries(CAT.agents.map((a) => [a.agent_id, a]));
const PERSONAS = DATA.personas.personas;

/* Run states, per docs/phase-2-ux.md: glyph AND word AND colour on every one,
   so none of the three is load-bearing alone. Colour is the third signal, not
   the first — P6 works in hearing protection and P3 in gloves under pit light,
   and neither can be assumed to resolve a hue. */
const STATE = {
  done: { glyph: "✓", word: "DONE", cls: "b-ok" },
  running: { glyph: "●", word: "RUNNING", cls: "b-info" },
  blocked: { glyph: "⚠", word: "BLOCKED", cls: "b-crit" },
  waiting: { glyph: "○", word: "WAITING", cls: "b-idle" },
};

function stateBadge(key, suffix) {
  const s = STATE[key];
  return (
    `<span class="badge ${s.cls}">${s.glyph} ${s.word}` +
    (suffix ? ` · ${esc(suffix)}` : "") +
    "</span>"
  );
}

/** Read a query-string parameter, falling back to a default. */
function param(name, fallback) {
  return new URLSearchParams(location.search).get(name) || fallback;
}

function agentName(id) {
  return AGENTS[id] ? AGENTS[id].display_name : id;
}

/* runtimeState() and connectionCopy() live in apps/shared/runtime.js: the role
   page asks the same question and there has to be one answer to it. The three
   renderers below are this application's three shapes for that answer. */

let _pendingBlocks = 0;

/* Whatever the wire says, say it in the frame that matches it.
 *
 *  A yes rendered inside the amber dashed box is a working system reporting
 *  itself broken, which is the fault this whole component exists to prevent
 *  pointed the other way; an unknown rendered in the same box states the
 *  pessimistic answer before one is available. So the class changes with the
 *  content, and never lags it. */
function paintConnection(node, what, state) {
  const copy = connectionCopy(state);
  node.className = `nc-block nc-${copy.key}`;
  node.innerHTML =
    `<div class="badge ${copy.cls}">${copy.badge}</div>` +
    `<p class="nc-what">${esc(what)}</p>` +
    copy.lines.map((line) => `<p class="nc-why">${esc(line)}</p>`).join("");
}

/** What the connection check reported, for the one drawer at the foot.
 *
 *  The stage the check stopped at and the exception it caught used to hang off
 *  each block that asked. The handover sheet asks in four places, so a refused
 *  check put four identical "Technical detail" boxes down one page — which is
 *  not disclosure, it is repetition, and it is the thing the reader asked to be
 *  spared. There is one connection and one answer, so there is one place to
 *  read it: the drawer every screen already ends with.
 *
 *  Written as a placeholder that fills itself, because the drawer is composed
 *  before the wire has answered. */
function connectionDetail() {
  const id = `cd-${(_pendingBlocks += 1)}`;
  const paint = (state) => {
    const node = document.getElementById(id);
    if (!node) return;
    const copy = connectionCopy(state);
    node.innerHTML =
      copy.detail ||
      "<dl><dt>Connection check</dt><dd class=\"mono\">/api/runtime answered; " +
        "there was nothing to report</dd></dl>";
  };
  runtimeState()
    .then(paint)
    .catch((err) => {
      console.error("the connection check could not be rendered:", err);
      paint({ connected: false, unreadable: true, stage: "/api/runtime", detail: String(err) });
    });
  return (
    `<div id="${id}"><dl><dt>Connection check</dt>` +
    '<dd class="mono">waiting for /api/runtime</dd></dl></div>'
  );
}

/** The block every screen shows where an agent's generated text would appear.
 *
 *  Renders neutral and then corrects itself from the wire. Writing a plausible
 *  transcript here would be the single most damaging thing this artifact could
 *  do: everything else on the screen is checkable against the catalog, and one
 *  invented paragraph would put all of it in doubt. Stating that the agents are
 *  unreachable when they are reachable is the same fault pointed the other way,
 *  and until the wire answers, neither sentence is available. */
function notConnected(what) {
  const id = `nc-${(_pendingBlocks += 1)}`;
  const paint = (state) => {
    const node = document.getElementById(id);
    if (node) paintConnection(node, what, state);
  };
  runtimeState()
    .then(paint)
    .catch((err) => {
      /* A fault in the rendering above must not leave every block on the page
         reading CHECKING… for good. Unknown is the honest place to fail to: it
         is the state where nothing has been established either way. */
      console.error("the connection check could not be rendered:", err);
      paint({ connected: false, unreadable: true, detail: String(err) });
    });
  return (
    `<div class="nc-block nc-checking" id="${id}">` +
    '<div class="badge b-idle">○ CHECKING…</div>' +
    `<p class="nc-what">${esc(what)}</p></div>`
  );
}

/** The same answer in one line, for the provenance row at the foot of a screen.
 *
 *  A footer asserting that the estate is unreachable, on a page served by the
 *  proxy that just reached it, is the same untruth in smaller type.
 *
 *  Every one of these sentences is in the past tense and scoped to the load,
 *  because that is the only moment any of them describes: the page asks once
 *  and never asks again, so "are reachable" would be a claim about a present
 *  this line has no way of standing behind. */
function runtimeNote() {
  const id = `rt-${(_pendingBlocks += 1)}`;
  const paint = (state) => {
    const node = document.getElementById(id);
    if (!node) return;
    if (state.connected) {
      node.textContent =
        `${state.deployed.length} of ${state.expected} agents were deployed and ` +
        "reachable when this page loaded.";
    } else if (state.unreadable) {
      node.textContent =
        "Whether the deployed agents could be reached was not established when " +
        "this page loaded.";
    } else if (state.offline) {
      node.textContent =
        "These screens are being served without the workspace server, so " +
        "nothing on this page has asked the deployed agents anything.";
    } else {
      node.textContent = "Not connected to the deployed agents when this page loaded.";
    }
  };
  runtimeState()
    .then(paint)
    .catch((err) => {
      console.error("the connection check could not be rendered:", err);
      paint({ connected: false, unreadable: true });
    });
  return `<span id="${id}">Checking the connection to the deployed agents…</span>`;
}

/** The live runtime band. Asks the server which of the 52 services exist.
 *
 *  Auditor finding A8 asked for a running count on the cockpit. The honest
 *  version of that count is not a number of running agents — Cloud Run scales
 *  to zero, so between calls the true answer is nearly always none, and a
 *  dashboard printing a fabricated "7 running" would be inventing exactly the
 *  figure the architecture guarantees is zero. What can be stated is whether
 *  the estate is reachable and how many services are deployed, so that is what
 *  this asks for and what it prints. */
function runState(node) {
  node.innerHTML =
    '<div class="card"><div class="card-cap">Runtime</div>' +
    '<p class="dim mono" style="font-size:11px;margin:0">checking /api/runtime …</p></div>';

  const banner = (badge, cls, headline, detail) => {
    node.innerHTML =
      '<div class="card"><div class="card-cap">Runtime</div>' +
      '<div class="run-state">' +
      `<span class="badge ${cls}">${badge}</span>` +
      `<div><div>${esc(headline)}</div>` +
      `<div class="dim" style="font-size:12.5px;margin-top:4px">${esc(detail)}</div>` +
      "</div></div></div>";
  };

  /* The same promise every other block on this page waits on. It used to be its
     own fetch, which meant the cockpit asked twice and could in principle print
     two different answers to the same question in two places on one screen. */
  const paint = (r) => {
    if (r.offline) {
      /* Opened straight off disk, or the server is not running. Both are
         normal ways to read these screens and neither is an error worth
         alarming about — but neither can be described as connected either.
         This one keeps its own words: the reader of a page opened off disk is
         the person who can start the server, and the command is the remedy. */
      banner(
        "⚠ NOT CONNECTED",
        "b-warn",
        "No runtime to query.",
        "These screens are being served without apps/workspace/server.py, so " +
          "there is nothing to ask about the deployed services. Run " +
          "`python -m uvicorn apps.workspace.server:app` to check them."
      );
      return;
    }
    if (!r.connected) {
      /* The written sentences only. The card used to print r.detail as its body
         copy, which put a RefreshError stack line where the explanation
         belongs; it then printed the same stack line a second time in a drawer
         of its own, alongside the page's drawer at the foot. The exception is
         now filed once, where the rest of this screen's machinery is. */
      const copy = connectionCopy(r);
      banner(copy.badge, copy.cls, copy.lines[0], copy.lines[1] || "");
      return;
    }
    const n = r.deployed.length;
    node.innerHTML =
      '<div class="card"><div class="card-cap">Runtime</div>' +
      '<div class="run-state">' +
      `<span class="badge ${n === r.expected ? "b-ok" : "b-warn"}">` +
      `${n === r.expected ? "✓" : "⚠"} ${n} / ${r.expected} DEPLOYED</span>` +
      `<div><div>${esc(r.project)} · ${esc(r.region)}</div>` +
      `<div class="dim" style="font-size:12.5px;margin-top:4px">${esc(r.note)}</div>` +
      (r.missing.length
        ? `<div class="dim mono" style="font-size:11px;margin-top:4px">not deployed: ${esc(
            r.missing.join(" ")
          )}</div>`
        : "") +
      "</div></div></div>";
  };

  runtimeState()
    .then(paint)
    .catch((err) => {
      console.error("the connection check could not be rendered:", err);
      paint({ connected: false, unreadable: true, detail: String(err) });
    });
}

/** One entrypoint as a rail row: id, name, and the two facts that change how
 *  you approach it — whether it needs a human, and what it is built from.
 *
 *  Descriptions are inline and never on hover. Auditor finding A2: P3 works
 *  from a rugged tablet in gloves and P7 from a handheld, and neither device
 *  has a hover state, so content behind one is content those two personas
 *  cannot reach. Nothing in this suite hides behind hover. */
function agentRow(id, href, current) {
  const a = AGENTS[id];
  const kind =
    a.pattern === "A" ? `team of ${swarmSize(a.swarm_id)}` : "works on its own";
  return (
    `<a class="rail-row${id === current ? " on" : ""}" href="${href}">` +
    `<span class="rail-id mono">${esc(id)}</span>` +
    `<span class="rail-body"><span class="rail-name">${esc(a.display_name)}</span>` +
    `<span class="rail-sub">${esc(kind)} · ${esc(a.apqc_names.join(" / "))}</span></span>` +
    (a.hitl_required ? '<span class="badge b-warn">⚠ SIGN-OFF</span>' : "") +
    "</a>"
  );
}

function swarmSize(swarmId) {
  const s = CAT.swarms[swarmId];
  return s ? 2 + s.specialists.length : 0;
}

/** The method behind an agent's answer, drawn from what the catalog grants it.
 *
 *  docs/phase-2-ux.md: "For deterministic agents the method is the provenance.
 *  Hiding it behind 'the agent calculated' is what makes an engineer distrust
 *  the whole suite." So a declared formula prints its expression, a declared
 *  traversal prints its SQL, a declared model prints its name — and an agent
 *  whose method is a query the model composes at runtime says exactly that,
 *  rather than implying a rigour it does not have. */
function drawerMethod(id) {
  const a = AGENTS[id];
  const parts = [];

  for (const [key, f] of Object.entries(WS.formulas.registry)) {
    if (!f.named_by.includes(id)) continue;
    parts.push(
      '<div class="method">' +
        `<div class="method-cap mono">FORMULA · ${esc(key)}</div>` +
        `<div class="expression mono">${esc(f.expression)}</div>` +
        `<div class="method-sub mono">inputs: ${esc(f.inputs.join(", "))}</div>` +
        "</div>"
    );
  }

  for (const t of a.traversals) {
    const spec = WS.traversals[t];
    if (!spec) continue;
    parts.push(
      '<div class="method">' +
        `<div class="method-cap mono">GRAPH TRAVERSAL · ${esc(t)}</div>` +
        `<div class="console">${esc(spec.sql)}</div>` +
        `<div class="method-sub mono">binds ${esc(spec.params.join(", "))} · returns ${esc(
          spec.columns.join(", ")
        )}</div>` +
        "</div>"
    );
  }

  for (const m of a.models) {
    parts.push(
      '<div class="method">' +
        '<div class="method-cap mono">BQML MODEL</div>' +
        `<div class="expression mono">${esc(m)}</div>` +
        '<div class="method-sub mono">called through bqml_predict; the prediction ' +
        "is the model's, not the language model's</div>" +
        "</div>"
    );
  }

  if (a.tools.includes("operational_math") && !parts.some((p) => p.includes("FORMULA"))) {
    parts.push(
      '<div class="method">' +
        '<div class="method-cap mono">DETERMINISTIC MATH</div>' +
        `<div class="method-sub">${esc(WS.formulas.note)} Available here: ` +
        `${esc(Object.keys(WS.formulas.registry).join(", "))}.</div>` +
        "</div>"
    );
  }

  if (a.tools.includes("bq_query")) {
    parts.push(
      '<div class="method">' +
        '<div class="method-cap mono">SQL, COMPOSED AT RUNTIME</div>' +
        '<div class="method-sub">bq_query takes whatever SELECT the model writes ' +
        "against the tables below. There is no fixed statement to print here, " +
        "which is why the tables and their columns are named instead — that " +
        "boundary is fixed and this one is not.</div>" +
        "</div>"
    );
  }

  return parts.join("");
}

/** The tables behind an answer, named to the column, with their gaps stated.
 *
 *  "The inputs panel names the table and the column, not 'inventory data'."
 *  Three statuses are kept apart on purpose: a table whose meaning is
 *  documented, one whose schema is known but whose business meaning is still
 *  being written, and one that BigQuery holds but this machine does not.
 *
 *  Drawer copy, and named so. This used to be inputs(), called from the body of
 *  the handover sheet once per section, which put ten raw BigQuery schemas in
 *  front of the shift supervisor and one technical drawer at the foot they no
 *  longer needed. Qualified names and column types are what an auditor checks a
 *  sheet against; the body says what each agent reads in the words the shared
 *  vocabulary publishes. So this takes the list of tables rather than an agent,
 *  because the two screens that file it are filing a team's tables, not one
 *  member's, and it is only ever reached from inside the one drawer. */
function drawerTables(qualified_names) {
  if (!qualified_names.length) {
    return '<p class="dim">No table is read here; the answer is computed.</p>';
  }
  return qualified_names
    .map((qualified) => {
      const t = WS.tables.tables[qualified];
      if (!t) return `<div class="tbl"><div class="mono">${esc(qualified)}</div></div>`;
      const cols = t.columns
        .map(
          (c) =>
            `<li><span class="mono">${esc(c.name)}</span> ` +
            `<span class="dim mono">${esc(c.type)}</span>` +
            (c.meaning ? `<div class="col-meaning">${esc(c.meaning.trim())}</div>` : "") +
            "</li>"
        )
        .join("");
      return (
        '<details class="tbl">' +
        "<summary>" +
        `<span>${esc(plainTable(qualified))}</span>` +
        `<span class="dim mono">${esc(bareTable(qualified))} · ${esc(
          t.columns.length
        )} cols · ${num(t.rows_at_profile)} rows at profile</span>` +
        (t.local_parquet
          ? '<span class="badge b-ok">✓ LOCAL COPY</span>'
          : '<span class="badge b-idle">○ WAREHOUSE ONLY</span>') +
        "</summary>" +
        (t.description
          ? `<p class="tbl-desc">${esc(t.description)}</p>`
          : '<p class="tbl-desc dim">Business meaning for this table has not been ' +
            "written yet; the column names and types below are BigQuery's own.</p>") +
        `<ul class="cols">${cols}</ul>` +
        "</details>"
      );
    })
    .join("");
}

/** What this agent's answer cannot settle, derived rather than asserted.
 *
 *  Every screen that shows a result also shows this, and SC-4 makes it the
 *  loudest element on the sheet. The list is computed from three real
 *  conditions, so it shrinks on its own as the gaps close.
 *
 *  Four fields, and the fourth is the reason there are four. `what`, `detail`
 *  and `remedy` are read by a shift supervisor, so they are in the supervisor's
 *  words; `technical` is the same remedy as an engineer would carry it out, and
 *  it is rendered by drawerFlags() below and nowhere else. The remedy on this
 *  band used to read "Re-run scripts/build_app_data.py with BigQuery
 *  credentials" — a developer's shell instruction, in the loudest element of a
 *  handover sheet, to a reader who cannot act on it and would not know what it
 *  meant. Nothing is dropped: what the supervisor no longer reads, the drawer
 *  still names.
 */
function flagsFor(ids) {
  const list = [].concat(ids);
  const tables = [...new Set(list.flatMap((id) => AGENTS[id].source_tables))];
  const models = [...new Set(list.flatMap((id) => AGENTS[id].models))];
  const flags = [];

  const plainList = (list) => list.map(plainTable).join(", ");

  const remote = tables.filter((t) => !(WS.tables.tables[t] || {}).local_parquet);
  if (remote.length) {
    flags.push({
      what: `${remote.length} of the ${tables.length} sources this reads are not held on this machine`,
      detail: plainList(remote),
      remedy:
        "This build was made without a connection to the warehouse. Rebuilt " +
        "with one, it would hold them.",
      technical:
        "Not held locally: " + remote.join(", ") +
        ". Re-run scripts/build_app_data.py with BigQuery credentials.",
    });
  }

  const undocumented = tables.filter((t) => !(WS.tables.tables[t] || {}).description);
  if (undocumented.length) {
    flags.push({
      what: `${undocumented.length} of them have no written explanation of what their columns mean`,
      detail: plainList(undocumented),
      remedy:
        `Written explanations exist for ${WS.tables.documented.length} of the ` +
        `${WS.tables.documented.length + WS.tables.undocumented.length} tables ` +
        "this estate reads; the rest are still being written.",
      technical:
        `docs/column-semantics.yaml covers ${WS.tables.documented.length} of ` +
        `${WS.tables.documented.length + WS.tables.undocumented.length} tables. ` +
        "Undocumented: " + undocumented.join(", ") + ".",
    });
  }

  for (const m of models) {
    flags.push({
      what: "A trained prediction model this relies on was not checked by this build",
      // Not the model's own name: it is an identifier, it is in the drawer
      // below, and the sentence carries the same fact without it.
      detail:
        "Whether the model exists, and what it was trained on, is a fact about " +
        "the warehouse and not about this build.",
      remedy: "Ask the warehouse itself, with credentials.",
      technical: `${m} — query INFORMATION_SCHEMA.MODELS with credentials.`,
    });
  }

  /* Not "the agents are unreachable" — whether they are is a fact about right
     now, and this list is built before the wire has been asked. Nor "no
     sentence on this page was written by an agent", which the handover sheet's
     own Run button makes false the moment a reader uses it: the answer arrives
     above this band while the band still denies it exists. What is true before
     and after a run is that this build holds none of it. An answer on screen is
     live, is the agent's, and is gone when the page closes. */
  flags.push({
    what: "Nothing the agents themselves would say is recorded in this build",
    detail:
      "Structure, method and tables are read from the deployed catalog. The prose " +
      "an agent would write is not recorded anywhere in this repository, and this " +
      "build does not compose it on the agent's behalf.",
    remedy:
      "Ask the agent through the workspace server. What comes back is its own " +
      "words, on screen only, and is not kept when the page is closed.",
  });

  return flags;
}

function unverified(ids) {
  const flags = flagsFor(ids);
  return (
    '<div class="unverified">' +
    '<div class="unverified-cap"><span class="badge b-crit">⚠ UNVERIFIED</span>' +
    `<span>${flags.length} item${flags.length === 1 ? "" : "s"} this screen cannot settle</span></div>` +
    "<ul>" +
    flags
      .map(
        (f) =>
          `<li><strong>${esc(f.what)}</strong>` +
          `<div class="dim mono">${esc(f.detail)}</div>` +
          `<div class="remedy">Remedy: ${esc(f.remedy)}</div></li>`
      )
      .join("") +
    "</ul></div>"
  );
}

/** The same three gaps, as the person who would close them would carry it out.
 *
 *  One entry per flag that has a technical remedy — the ones that do not, the
 *  band above already states completely. The paths, the script name, the
 *  warehouse view and the model's own identifier live here and only here, which
 *  is what lets the band read as English on a printed handover sheet.
 *
 *  Named drawer* on purpose: that prefix is the convention this codebase's copy
 *  gate reads as "this function writes drawer copy", so the vocabulary below is
 *  scanned as the drawer's rather than as three screens' body text. */
function drawerFlags(ids) {
  const held = flagsFor(ids).filter((f) => f.technical);
  if (!held.length) return "";
  return (
    "<dl>" +
    held
      .map(
        (f) =>
          `<dt>${esc(f.what)}</dt>` +
          `<dd class="mono">${esc(f.technical)}</dd>`
      )
      .join("") +
    "</dl>"
  );
}

/** The persona whose journey names this agent, with the citation.
 *
 *  These summaries are transcribed from docs/personas-and-value-tree.md with
 *  the source line recorded, which is what lets a scenario appear on screen
 *  without anyone having written a scenario for the screen. Where the persona's
 *  journey does not name this agent, nothing is printed rather than a
 *  paraphrase stretched to fit. */
function journeyFor(id) {
  const a = AGENTS[id];
  const p = PERSONAS[a.persona];
  if (!p || !p.journey) return "";
  const named = new RegExp(`\\b${id}\\b`).test(p.journey.summary);
  if (!named) return "";
  return (
    '<div class="card"><div class="card-cap">The scenario this runs in</div>' +
    `<h3>${esc(p.journey.title)}</h3>` +
    `<p>${esc(p.journey.summary.trim())}</p>` +
    /* The document is named in an element of its own rather than run into the
       line. A file name inside a sentence is the pattern this application's
       copy gate exists to stop; a file name standing alone is a citation, which
       is what this line is for. */
    '<p class="cite mono">' +
    `${esc(p.title)} · <span>docs/personas-and-value-tree.md</span> line ${esc(
      p.journey.source_line
    )}` +
    "</p></div>"
  );
}
