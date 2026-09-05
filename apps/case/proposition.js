/* Screen 1 — the proposition.
 *
 * This screen holds the thesis and the industry condition, and nothing about
 * how the estate is built. A reader who has not yet been given a reason to
 * care how many agent nodes there are is not helped by being told. The counts
 * and the latency measurement live on screen four, where the question they
 * answer has actually been asked.
 */

mountNav("case", "index.html");

const facts = DATA.facts;
const BENCH = DATA.benchmarks;

el("anchor").setAttribute("data-count", facts.mill_downtime_usd_per_hour);
el("anchor-src").textContent = facts.mill_downtime_source;

/* The industry condition, in the order that makes the argument rather than the
   order the source file happens to hold.
 *
 *  The ore got harder. The information to work it was already being collected
 *  and thrown away. The industry knows it is behind — its own chief executives
 *  say so. And the obvious remedy has, so far, mostly not paid.
 *
 *  The last two are on this screen deliberately. A case that carries only
 *  upside reads as a brochure, and those are the figures a sceptical chief
 *  executive already has in mind before the meeting starts.
 *
 *  Four publishers, four different years, so the section cannot be read as one
 *  house's opinion restated four ways.
 */
const CONDITION = ["grade_decline", "data_unused", "pwc_ai_fitness", "ai_value_gap"];

CONDITION.forEach((id) => {
  const b = BENCH.by_id[id];
  if (!b) throw new Error(`this screen cites benchmark ${id}, which is not in the source file`);
  if (b.theme !== "condition") {
    throw new Error(`benchmark ${id} is themed ${b.theme}; this section is the industry condition`);
  }
});

el("condition-lede").innerHTML =
  "Four published findings, quoted as written and attributed. None of them is " +
  "ours, and none of them is about this site. They are here because the gap " +
  "on the next screen is easier to dismiss as a local measurement problem " +
  "than to face, and it is not one.";

el("condition").innerHTML = CONDITION.map((id) => {
  const b = BENCH.by_id[id];
  return (
    '<div class="card c6 reveal">' +
    `<div class="card-cap">${esc(b.publisher)} · ${esc(b.year)}</div>` +
    `<h3 style="margin-top:0">${esc(b.headline)}</h3>` +
    '<div class="benchline">' +
    `<span class="claim">&ldquo;${esc(b.figure)}&rdquo;</span>` +
    (b.aside ? `<span class="claim" style="margin-top:6px">&ldquo;${esc(b.aside)}&rdquo;</span>` : "") +
    `<span class="cite">${esc(b.title)}</span>` +
    "</div>" +
    `<p style="color:var(--fg-dim);font-size:12.5px;margin-bottom:0">${esc(b.scope)}</p>` +
    "</div>"
  );
}).join("");

el("condition-close").innerHTML =
  "Read together they say something narrower than &ldquo;mining needs AI&rdquo;. " +
  "They say the measurement already exists, the practice is already known, and " +
  "what has not worked is buying a technology and hoping the practice follows. " +
  "So the next screen does not argue from any of these. It argues from " +
  `${esc(DATA.signals.gap.rows[0].days)} days of your own record.`;

/* The "today" column quotes people, not marketing. Only quotes that are about
   the cost of assembling an answer belong on this screen; the rest of each
   persona's pain is on their own screen in application 2. */
const ORIENTATION_PAIN = [
  ["P1", "I need three systems open at once just to answer one question."],
  ["P1", "Half my day is data wrangling, not engineering."],
  ["P2", null],
  ["P4", null],
];

const picked = [];
for (const [code, wanted] of ORIENTATION_PAIN) {
  const persona = DATA.personas.personas[code];
  if (!persona) continue;
  const hit = wanted
    ? persona.pain_points.find((p) => p.quote === wanted)
    : persona.pain_points[0];
  if (hit) picked.push({ persona, quote: hit });
}

/* A quote that no longer exists in the source must not silently vanish: the
   screen would just look thinner and no one would know why.

   The placeholder is written in the same words as everything around it. It
   named a document and a build script, which is what a developer would want to
   read here — but this branch only ever fires in front of an audience, at which
   point the reader is whoever is in the room, and the fact they need is that a
   quotation has gone missing and this screen will not invent one. Where to go
   and look is the drawer's business, and the drawer at the foot of this screen
   already names the persona document by its path. */
if (picked.length !== ORIENTATION_PAIN.length) {
  picked.push({
    persona: { code: "—", title: "Missing quote" },
    quote: {
      quote:
        "A quotation this screen names is no longer in the persona document " +
        "it was lifted from, so nothing is shown in its place.",
      source_line: 0,
    },
  });
}

el("today").innerHTML = picked
  .map(
    (p) =>
      '<blockquote class="verbatim">' +
      esc(p.quote.quote) +
      `<cite>${esc(p.persona.title)}</cite></blockquote>`
  )
  .join("");

/* ---------- the machinery, at the end and closed ---------- */

/* Two things came off the cards above and one came off the quotes: the web
   address behind each study, and the line of the persona document each
   sentence was lifted from. Both exist so a sceptic can go and look, and
   neither is something a reader meets a claim with. */
function drawerBody() {
  const cited = CONDITION.map((id) => {
    const b = BENCH.by_id[id];
    return (
      `<dt class="mono">${esc(b.id)}</dt>` +
      `<dd>${esc(b.title)} — ${esc(b.publisher)}, ${esc(b.year)}<br>` +
      `<span class="mono">${esc(b.url)}</span></dd>`
    );
  }).join("");

  const quoted = picked
    .map(
      (p) =>
        `<dt class="mono">${esc(p.persona.code)}</dt>` +
        `<dd>${esc(p.persona.title)} — ` +
        (p.quote.source_line
          ? `<span class="mono">personas-and-value-tree.md:${esc(p.quote.source_line)}</span>`
          : "line not recorded") +
        "</dd>"
    )
    .join("");

  return (
    "<p>Where the four published findings above were read, and where each " +
    "quoted sentence sits in the persona document.</p>" +
    `<dl>${cited}${quoted}</dl>` +
    `<p class="mono">${esc(BENCH.source)} · ${esc(DATA.personas.source)}</p>`
  );
}

el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "study addresses, persona codes, line numbers"
) + provenance(
  `<dt>Benchmarks</dt><dd>${esc(BENCH.source)}</dd>` +
    `<dt>Site figures</dt><dd class="mono">${esc(facts.generated_at)}</dd>`
);

reveal();
countAll();
