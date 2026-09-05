/* The front door. It argues one thing, and it argues it before it offers a door.
 *
 * There is no navigation bar here on purpose: this page is a fork in the road
 * and the two applications each own their own chrome. A third nav would imply a
 * place above them that a reader can return to, and there is nothing there.
 *
 * The order is the argument. The gap comes first, because it is the reason to
 * keep reading. The five machines come second, because a reader who has just
 * been given a number is entitled to see the plant it was taken from. The doors
 * come last, once there is a reason to open one.
 *
 * Nothing on this screen names a node, an entrypoint, a swarm or a graph. The
 * reader is a CEO; those are the architect's evidence, not theirs, and they are
 * disclosed further in.
 */

const C = DATA.catalog.counts;
const HITL = DATA.catalog.agents.filter((a) => a.is_entrypoint && a.hitl_required).length;
const SIG = DATA.signals;
const GAP = SIG.gap;
const BENCH = DATA.benchmarks;

/* places(), fig() and rowPlaces() are in shell.js: the value screen quotes the
   same recovery gap, and a measurement printed to one precision here and
   another there is the same defect rowPlaces() exists to prevent. */

/* ---------- the gap ---------- */

const RECOVERY = GAP.rows.find((r) => r.id === "recovery");

const RDP = rowPlaces(RECOVERY);

el("thesis").textContent =
  "Over " + RECOVERY.days + " days of recorded operation the concentrator's " +
  "best day recovered " + fig(RECOVERY.p90, "", RDP) + "% and its ordinary day " +
  fig(RECOVERY.median, "", RDP) + "%. That " + fig(RECOVERY.delta, "", RDP) +
  "-point spread is " +
  "not a target to be bought. It is a result this site has already produced, " +
  "and did not repeat. Agents exist here to make the ordinary day look like " +
  "the good one — optimal decisions, around the clock.";

el("gap-lede").textContent =
  "Each figure below is a daily mean drawn from this site's own records. The " +
  "ordinary day is the middle of that run. The best day is not the single " +
  "finest shift — one unusual shift is an anecdote and should not set a " +
  "target — but the level the plant reached or beat on one day in ten. " +
  "Beside each is what the published research says is available to a mine " +
  "that closes gaps of this kind, arrived at independently and landing in " +
  "the same range.";

/* External figures are rendered in a visibly different register from measured
   ones: muted, mono, and set behind a rule. A benchmark is a third party's
   claim about the industry and a measurement is this warehouse's claim about
   this site, and letting the two share a typeface would lend a consultancy's
   authority to our number. That is the move that makes a CEO stop reading. */
function benchCell(id) {
  if (!id) return '<td class="bench none">No verified benchmark held</td>';
  const b = BENCH.by_id[id];
  return (
    '<td class="bench">' +
    `<span class="claim">${esc(b.headline)}</span>` +
    `<span class="cite">${esc(b.publisher)}, ${esc(b.year)}</span></td>`
  );
}

el("gap").innerHTML =
  "<thead><tr>" +
  "<th>Quantity</th>" +
  '<th class="num">Ordinary day</th>' +
  '<th class="num">Best day</th>' +
  '<th class="num">The gap</th>' +
  "<th>What the research says is available</th>" +
  "</tr></thead><tbody>" +
  GAP.rows
    .map((r) => {
      const dp = rowPlaces(r);
      // Recovery is already a percentage, so its gap is stated in points. A
      // "+2.1%" against a 92.32% base would be read as 2.1 points by half the
      // room and as 1.96 points by the other half.
      const gap =
        r.delta_kind === "points"
          ? `+${fig(r.delta, "", dp)} pts`
          : `+${r.delta_pct.toFixed(1)}%`;
      return (
        "<tr>" +
        `<td><b>${esc(r.label)}</b>` +
        (r.asset_id ? `<span class="who-sub">${esc(r.asset_id)}</span>` : "") +
        "</td>" +
        `<td class="num">${esc(fig(r.median, r.unit, dp))}</td>` +
        `<td class="num">${esc(fig(r.p90, r.unit, dp))}</td>` +
        `<td class="num gain">${esc(gap)}</td>` +
        benchCell(r.benchmark) +
        "</tr>"
      );
    })
    .join("") +
  "</tbody>";

/* The caveat is not a disclaimer in small print at the bottom. It sits directly
   under the table because a CEO who works out for themselves that some of this
   gap is weather trusts the next number less, and one who was told so first
   trusts it more. */
const PUMP = GAP.excluded[0];
el("gap-note").innerHTML =
  '<div class="note"><strong>What this gap is, and is not</strong><br>' +
  esc(GAP.caveat) +
  " The honest claim is that the distance between an ordinary day and a good " +
  "one is where the money is, and that nobody currently manages it because " +
  "nobody sees it until the month-end report." +
  "</div>" +
  '<div class="note" style="margin-top:10px"><strong>' +
  esc(PUMP.asset_id) +
  " is deliberately not in the table</strong><br>" +
  esc(PUMP.reason) +
  "</div>";

/* ---------- the recorded-window strip ---------- */

/* Criticality comes off the asset graph, which is the same record the blast
   radius traversal reads. It is shown as a badge and not as the colour of the
   trace: a criticality rating is a standing property of the machine, and
   drawing three of five traces in the alarm colour would say those three
   machines are in trouble right now, which none of these readings claim. The
   six-hue palette is likewise not used here — those hues are bound to value
   branches, and a branch is not what this row is about. */
const ASSET_META = {};
DATA.graph.nodes.forEach((n) => {
  if (n.type === "Asset" && n.graph === "asset") ASSET_META[n.id] = n.detail;
});
const RATING = { CRITICAL: "b-crit", HIGH: "b-warn", MEDIUM: "b-info", LOW: "b-idle" };

const FROM = new Date(SIG.window.from.replace(" ", "T"));
const TO = new Date(SIG.window.to.replace(" ", "T"));
const STEPS = SIG.buckets;

function stamp(i) {
  const at = new Date(FROM.getTime() + ((TO - FROM) * i) / (STEPS - 1));
  return at.toISOString().slice(0, 10);
}

el("strip-lede").textContent =
  "The numbers above were taken from these " +
  SIG.assets.length +
  " machines. The window runs " +
  stamp(0) +
  " to " +
  stamp(STEPS - 1) +
  ", reduced to " +
  STEPS +
  " points of equal duration. It is recorded history on a scrubber, not a live " +
  "feed — drag it and the five figures move to what those machines actually " +
  "read that day. The variation you are watching is the gap.";

el("scrub").innerHTML =
  "<span>Recorded window</span>" +
  `<span class="mono">${esc(stamp(0))}</span>` +
  `<input type="range" id="play" min="0" max="${STEPS - 1}" value="0" ` +
  'aria-label="Scrub the recorded telemetry window">' +
  `<span class="mono">${esc(stamp(STEPS - 1))}</span>` +
  '<span>At <span class="at" id="at"></span></span>';

el("strip").innerHTML = SIG.assets
  .map((a) => {
    const meta = ASSET_META[a.asset_id] || {};
    const rating = meta.criticality
      ? `<span class="badge ${RATING[meta.criticality] || "b-idle"}">${esc(
          meta.criticality
        )}</span>`
      : '<span class="badge b-idle">rating not held locally</span>';
    return (
      '<div class="card asset reveal">' +
      '<div style="display:flex;gap:8px;align-items:center;justify-content:space-between">' +
      `<span class="who">${esc(a.asset_id)}</span>${rating}</div>` +
      `<div class="val"><span id="v-${esc(a.asset_id)}">—</span>` +
      `<span class="u">${esc(a.unit)}</span></div>` +
      `<div class="what">${esc(a.label)}</div>` +
      `<div class="plot"><div id="p-${esc(a.asset_id)}" class="playhead" style="left:0"></div>` +
      // 46px rather than the 34 a branch card uses: these are 2-hourly sensor
      // readings and they are genuinely noisy, and at 34 the noise collapses
      // into a smudge that reads as texture instead of as a signal.
      sparkline(a.points, { height: 46, label: a.asset_id + " " + a.metric }) +
      "</div>" +
      `<div class="what" style="text-transform:none;letter-spacing:0;margin-top:8px">${esc(
        meta.name || ""
      )}</div>` +
      "</div>"
    );
  })
  .join("");

const VALUE_NODES = SIG.assets.map((a) => ({
  asset: a,
  value: el("v-" + a.asset_id),
  head: el("p-" + a.asset_id),
  decimals: places(a.max),
}));

function showFrame(i) {
  el("at").textContent = stamp(i);
  const left = (i / (STEPS - 1)) * 100;
  VALUE_NODES.forEach((n) => {
    const v = n.asset.points[i];
    n.head.style.left = left + "%";
    n.value.textContent =
      v === null || v === undefined
        ? "—"
        : v.toLocaleString("en-US", {
            minimumFractionDigits: n.decimals,
            maximumFractionDigits: n.decimals,
          });
  });
}

/* Plays through once and stops, then the reader owns it. setInterval rather
   than requestAnimationFrame for the reason motion.js gives; a slider input
   cancels the playback rather than fighting it. */
const play = el("play");
let frame = 0;
showFrame(0);

const reduced =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let sweep = null;
if (reduced) {
  play.value = String(STEPS - 1);
  showFrame(STEPS - 1);
} else {
  sweep = window.setInterval(() => {
    frame += 1;
    if (frame >= STEPS) {
      window.clearInterval(sweep);
      sweep = null;
      return;
    }
    play.value = String(frame);
    showFrame(frame);
  }, 90);
}

play.addEventListener("input", () => {
  if (sweep) {
    window.clearInterval(sweep);
    sweep = null;
  }
  showFrame(Number(play.value));
});

/* ---------- the two doors ---------- */

/* The facts under each door are deliberately not counts of things we built.
   "100 agent nodes" answers a question nobody at this stage is asking. What a
   CEO wants to know from a front door is what it costs them today, how the
   value is cut, who it is for, and what stays under their control. */
const APPS = [
  {
    href: "case/index.html",
    eyebrow: "Read first · five screens",
    title: "The case for change",
    lede:
      "Where the gap comes from, what closing it is worth, and how the value " +
      "divides so that no part of it is claimed twice. Told in the order a " +
      "capital decision is actually made, with the mechanism named on every " +
      "line and the magnitude left to the people who hold the contracts.",
    facts: [
      [
        DATA.facts.mill_downtime_usd_per_hour,
        "an hour of mill downtime",
        "the one cost this repository can source outright",
        { prefix: "$" },
      ],
      [
        RECOVERY.delta,
        "points of recovery, best day to ordinary",
        "measured here across " + RECOVERY.days + " days, not modelled",
        // Same precision the gap table prints, so a reader who scrolls between
        // the two does not find the same measurement quoted two ways.
        { decimals: RDP },
      ],
      [
        DATA.value_tree.branches.length,
        "value pools",
        "mutually exclusive, collectively exhaustive — nothing double-counted",
      ],
    ],
    cta: "Read the case",
  },
  {
    href: "workspace/index.html",
    eyebrow: "Then this · five screens",
    title: "The site workspace",
    lede:
      "What the standard looks like once someone has to work it: the decisions " +
      "it makes, the ones it is not allowed to make alone, the person " +
      "accountable for each, and the handover it writes at shift change so the " +
      "next crew starts where the last one stopped.",
    facts: [
      [C.entrypoints, "decisions it takes on", "each one a call somebody makes today"],
      [HITL, "held back for a human", "the ones that cannot act on their own"],
      [
        Object.keys(DATA.personas.personas).length,
        "roles it works for",
        "from the pit and the plant up to the general manager",
      ],
    ],
    cta: "Open the workspace",
  },
];

el("apps").innerHTML = APPS.map(
  (a) =>
    '<div class="card c6 lift reveal">' +
    `<div class="card-cap">${esc(a.eyebrow)}</div>` +
    `<h2 style="margin:0 0 8px">${esc(a.title)}</h2>` +
    `<p style="font-size:14px;margin:0 0 16px">${esc(a.lede)}</p>` +
    a.facts
      .map(
        ([n, label, sub, opts]) =>
          '<div style="display:flex;gap:12px;align-items:baseline;padding:8px 0;' +
          'border-top:1px solid var(--border-soft)">' +
          `<span class="metric" style="font-size:22px" data-count="${esc(n)}"` +
          (opts && opts.prefix ? ` data-prefix="${esc(opts.prefix)}"` : "") +
          (opts && opts.decimals !== undefined
            ? ` data-decimals="${esc(opts.decimals)}"`
            : "") +
          "></span>" +
          `<span style="font-size:13px"><b>${esc(label)}</b><br>` +
          `<span class="dim" style="color:var(--fg-dim)">${esc(sub)}</span></span></div>`
      )
      .join("") +
    '<div class="btn-row" style="margin-top:16px">' +
    `<a class="btn primary" href="${a.href}">${esc(a.cta)}</a></div>` +
    "</div>"
).join("");

/* ---------- the machinery, at the end and closed ---------- */

/* What the page above deliberately does not say in its own voice: the two
   percentiles by name, the warehouse column each row was measured from, and
   the identifier and address of every study quoted beside it. A reader who
   wants to check the gap has to be able to find the file it came out of; a
   reader who wants to know what the gap is worth does not, and should not have
   to step over it on the way down. */
function drawerBody() {
  const rows = GAP.rows
    .map((r) => {
      const b = r.benchmark ? BENCH.by_id[r.benchmark] : null;
      return (
        `<dt class="mono">${esc(r.id)} · ${esc(r.column)}</dt>` +
        `<dd class="mono">${esc(r.source)}<br>` +
        (b ? `${esc(b.id)} · ${esc(b.url)}` : "no verified benchmark held") +
        "</dd>"
      );
    })
    .join("");
  return (
    "<p>The ordinary day is the median of the daily means; the best day is the " +
    "90th percentile of the same series. Both are computed over the window " +
    "below, and each row names the column and the file it was measured from.</p>" +
    `<dl>${rows}</dl>` +
    `<p class="mono">${esc(SIG.source)} · ${esc(SIG.window.from)} to ${esc(
      SIG.window.to
    )} · reduced to ${esc(SIG.buckets)} points per series</p>`
  );
}

/* Both kinds of number are sourced, and the two kinds are listed separately.
   A reader has to be able to tell at a glance which figures this warehouse
   measured and which ones somebody else published. */
el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "percentiles, warehouse columns, study addresses"
) + provenance(
  /* Each file is named in an element of its own rather than run into the
     sentence beside it. A citation is a citation; a file name inside a sentence
     is the machinery talking, and the footer is on the reader's side of the
     drawer. */
  "<dt>Applications</dt><dd>Both read one bundle; neither holds a figure of its own.</dd>" +
    `<dt>Signals</dt><dd>Reduced at build time to ${esc(
      SIG.buckets
    )} points per series. <span class="mono">${esc(SIG.source)}</span></dd>` +
    `<dt>The gap</dt><dd>${esc(GAP.method)} <span class="mono">${esc(
      GAP.rows.map((r) => r.source).filter((s, i, a) => a.indexOf(s) === i).join(", ")
    )}</span></dd>` +
    "<dt>Benchmarks</dt><dd>" +
    BENCH.order
      .map((id) => BENCH.by_id[id])
      .filter((b, i, a) => a.findIndex((o) => o.title === b.title) === i)
      .map((b) => `${esc(b.title)} (${esc(b.publisher)}, ${esc(b.year)})`)
      .join("; ") +
    `. Held in <span class="mono">${esc(BENCH.source)}</span>; ${esc(
      BENCH.excluded.length
    )} further figures were found and excluded there because they could not be ` +
    "traced to a primary source.</dd>"
);

reveal();
countAll();
