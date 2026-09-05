/* Screen 2 — the gap, in this site's own record.
 *
 * The screen before this one makes a claim: the good day is already reachable,
 * because it already happened. This screen is where that claim has to survive
 * contact with the data, so it is built around one drawing repeated four times
 * rather than around a table of conclusions.
 *
 * The drawing sorts the days. That throws away the calendar deliberately — a
 * time series of the same numbers shows weather, and invites an argument about
 * which week was unusual. Sorted, the median day sits at the halfway mark and
 * the p90 day at the nine-tenths mark by construction, so the two figures the
 * whole business case rests on can be pointed at instead of asserted.
 */

mountNav("case", "scenario.html");

const facts = DATA.facts;
const GAP = DATA.signals.gap;
const BENCH = DATA.benchmarks;
const tree = DATA.value_tree;

/* One hue per value pool, assigned in the same order as the value screen, so a
   metric keeps its colour across the two screens. Recovery, feed rate and
   conveyor load belong to processing; payload to haulage. */
const HUE = {};
tree.branches.forEach((b, i) => (HUE[b.code] = `var(--b${i + 1})`));

const METRIC_POOL = {
  recovery: "B3",
  feed_rate: "B3",
  conveyor_load: "B3",
  payload: "B4",
};

/* A metric that stops being emitted must break the build, not quietly lose its
   colour and keep rendering as though nothing changed. */
GAP.rows.forEach((row) => {
  if (!METRIC_POOL[row.id]) {
    throw new Error(`gap metric ${row.id} has no value pool on this screen`);
  }
  if (!HUE[METRIC_POOL[row.id]]) {
    throw new Error(`gap metric ${row.id} points at pool ${METRIC_POOL[row.id]}, which is not in the value tree`);
  }
  if (!Array.isArray(row.ladder) || row.ladder.length !== row.days) {
    throw new Error(`gap metric ${row.id} carries ${row.ladder ? row.ladder.length : 0} days of ladder for ${row.days} days of gap`);
  }
});

const DAYS = GAP.rows[0].days;

el("hero-lede").innerHTML =
  `Below are ${esc(DAYS)} days of this plant's own operation. Every bar is a ` +
  "day the site actually ran, at the rate it actually ran. The distance " +
  "between the ordinary day and the best day is the whole of the argument " +
  "that follows: no new plant, no vendor claim, nothing that has to be taken " +
  "on trust.";

el("ladder-lede").innerHTML =
  "The days are sorted, not dated. A calendar view of the same numbers shows " +
  "weather and invites an argument about which week was unusual; sorted, the " +
  "ordinary day falls at the halfway mark and the best day at the nine-tenths " +
  "mark, because that is what those two words mean here. The coloured span " +
  "between them is the gap.";

/* One ladder.
 *
 *  Bars are drawn from the lowest recorded day rather than from zero. A
 *  recovery series running 90.9 to 95.1 plotted from zero is a flat grey
 *  block that shows nothing — but suppressing a baseline is a licence to
 *  exaggerate unless the suppression is stated, so every ladder prints the
 *  range it was drawn against, immediately beneath itself.
 */
function ladder(row) {
  const pool = tree.branches.find((b) => b.code === METRIC_POOL[row.id]);
  const hue = HUE[pool.code];
  const dp = rowPlaces(row);
  const unit = row.unit;
  const lo = row.ladder[0];
  const hi = row.ladder[row.ladder.length - 1];
  // A flat series would divide by zero. It cannot happen in this data, but a
  // ladder that renders as a row of stubs is a better failure than NaN heights.
  const span = hi - lo || 1;
  const n = row.ladder.length;

  const bars = row.ladder
    .map((v, i) => {
      const at = i / (n - 1);
      // Below the median: the days the site is being asked to stop having.
      // Between median and p90: the gap itself. Above p90: real days, shown
      // because they happened, dimmed because the case does not claim them.
      const cls = at < 0.5 ? "" : at <= 0.9 ? "in" : "over";
      // A floor of 6% so the lowest day is still a mark on the page rather
      // than an absence, which would read as a day with no production.
      const h = 6 + 94 * ((v - lo) / span);
      return `<i class="${cls}" style="height:${h.toFixed(2)}%"></i>`;
    })
    .join("");

  const up =
    row.delta_kind === "points"
      ? `+${fig(row.delta, "pts", dp)}`
      : `+${fig(row.delta_pct, "%", 1)}`;

  return (
    `<div class="card c6 reveal" style="--hue:${hue}">` +
    // The pool is named beside the title because it is the only thing on this
    // screen that explains why one ladder is a different colour from the other
    // three. A hue that means something nowhere stated is decoration.
    //
    // Two flex items rather than the floated span the persona caps use. A pool
    // title is forty characters, and at 360px a float that wide drops out of
    // the cap and shrinks the flex row underneath it to nothing, because a flex
    // container establishes a block formatting context and gets out of a
    // float's way rather than sitting under it.
    '<div class="card-cap ladder-cap">' +
    `<span>${esc(row.label)}${row.asset_id ? ` · ${esc(row.asset_id)}` : ""}</span>` +
    `<span class="pool">${esc(pool.title)}</span></div>` +
    '<div class="ladder-head">' +
    `<span class="move">${esc(fig(row.median, unit, dp))} &rarr; ${esc(
      fig(row.p90, unit, dp)
    )}</span>` +
    `<span class="move"><em>${esc(up)}</em></span>` +
    "</div>" +
    '<div class="ladder">' +
    `<div class="ladder-strip">${bars}` +
    // "Ordinary day" and "best day" are the words the method note, the landing
    // and the value screen all use for the median and the p90. The two ends of
    // the axis are the raw extremes of the drawing range and are named
    // differently on purpose: the best day is at nine tenths, not at the end,
    // and a reader who mistakes the last bar for it has been misled by us.
    '<span class="ladder-mark ordinary" style="left:50%"><b>Ordinary day</b></span>' +
    '<span class="ladder-mark best" style="left:90%"><b>Best day</b></span>' +
    "</div>" +
    '<div class="ladder-axis"><span>Lowest day recorded</span>' +
    "<span>Highest day recorded</span></div>" +
    `<div class="ladder-scale">${esc(n)} days, drawn from ${esc(
      fig(lo, unit, dp)
    )} at the foot of the bars to ${esc(fig(hi, unit, dp))} at the top — not from zero.` +
    "</div></div></div>"
  );
}

el("ladders").innerHTML = GAP.rows.map(ladder).join("");

el("method").innerHTML =
  '<div class="note info"><strong>How the two marks were taken</strong><br>' +
  esc(GAP.method) +
  "<br><br>" +
  esc(GAP.caveat) +
  "</div>";

/* The excluded asset is printed, not omitted. PUMP-104A has the widest gap in
   the data and it is a bearing failing, not a crew doing well; a screen that
   quietly dropped it would be indistinguishable from one that never noticed. */
el("excluded").innerHTML = GAP.excluded.length
  ? '<div class="note"><strong>Deliberately excluded</strong><br>' +
    GAP.excluded
      .map((x) => `<b>${esc(x.asset_id)}.</b> ${esc(x.reason)}`)
      .join("<br>") +
    "</div>"
  : "";

/* External figures, in their own typographic register behind a left rule: from
   here on, somebody else is talking, and the reader should be able to see the
   handover without reading the citation. */
const GAP_BENCH = BENCH.order.filter((id) => BENCH.by_id[id].theme === "gap");

el("bench-lede").innerHTML =
  "The two figures above are this site's. These are not — they are published " +
  "cross-mine benchmarks, quoted as written and attributed. They are here " +
  "because a gap that only shows up in one operator's data is a measurement " +
  "error, and a gap two independent studies find in the same place is a " +
  "condition of the industry.";

el("bench").innerHTML = GAP_BENCH.map((id) => {
  const b = BENCH.by_id[id];
  return (
    '<div class="card c6 reveal">' +
    `<div class="card-cap">${esc(b.publisher)} · ${esc(b.year)}</div>` +
    `<h3 style="margin-top:0">${esc(b.headline)}</h3>` +
    '<div class="benchline">' +
    `<span class="claim">&ldquo;${esc(b.figure)}&rdquo;</span>` +
    `<span class="cite">${esc(b.title)}</span>` +
    "</div>" +
    `<p style="color:var(--fg-dim);font-size:12.5px;margin-bottom:0">${esc(b.scope)}</p>` +
    `<div class="mono" style="font-size:10px;color:var(--fg-dim);margin-top:10px;overflow-wrap:anywhere">${esc(
      b.url
    )}</div>` +
    "</div>"
  );
}).join("");

el("site").innerHTML = facts.site
  .map(
    (row) =>
      "<tr>" +
      `<td>${esc(row.label)}</td>` +
      `<td class="num">${num(row.value)}</td>` +
      `<td style="color:var(--fg-muted)">${esc(row.unit)}</td>` +
      "</tr>"
  )
  .join("");

el("window").innerHTML =
  '<div class="note info"><strong>Observation window</strong><br>' +
  `Telemetry runs ${esc(facts.window.from)} to ${esc(facts.window.to)}. ` +
  "Every trend an agent reports is bounded by that window, so a question about " +
  "last week is answerable and a question about last year is not." +
  "</div>";

/* The figures the local files cannot settle get their own block. Leaving them
   off the screen entirely would be the quieter choice and the worse one: the
   audience would have no way to know the table above is partial.

   The reason each one cannot be settled is written by the build, in the build's
   words — a file path, a table identifier and a product name in one sentence —
   and this screen used to print it whole. It goes through plainProse() like
   every other paragraph this application did not write; the sentence as the
   build wrote it is in the drawer at the foot, where a path is allowed. */
el("unknown").innerHTML = facts.not_locally_derivable.length
  ? '<div class="note"><strong>Not derivable from local files</strong><br>' +
    facts.not_locally_derivable
      .map((u) => `<b>${esc(u.figure)}.</b> ${esc(plainProse(u.why))}`)
      .join("<br>") +
    "</div>"
  : "";

/* Personas in catalog order, sized by how many agents answer to them, because
   the ordering is itself a claim about where the work is. */
const personas = Object.values(DATA.personas.personas).sort(
  (a, b) => b.agent_count - a.agent_count || a.code.localeCompare(b.code)
);

el("pain").innerHTML = personas
  .map(
    (p) =>
      '<div class="card c6">' +
      '<div class="card-cap">' +
      `${esc(p.title)}` +
      `<span style="float:right;color:var(--fg-dim)">${esc(p.agent_count)} agent${
        p.agent_count === 1 ? "" : "s"
      }</span>` +
      "</div>" +
      p.pain_points
        .map((q) => `<blockquote class="verbatim">${esc(q.quote)}</blockquote>`)
        .join("") +
      "</div>"
  )
  .join("");

/* ---------- the machinery, at the end and closed ---------- */

/* Three things came off the page above. The warehouse file behind each ladder
   and each counted figure, which is what makes the gap checkable; and the
   short code each role is filed under, which is what the rest of this estate
   refers to it by. A supervisor reading the quotes does not need to know that
   they are P7; whoever goes looking for P7's agents does. */
function drawerBody() {
  const measured = GAP.rows
    .map(
      (r) =>
        `<dt class="mono">${esc(r.id)} · ${esc(r.column)}</dt>` +
        `<dd class="mono">${esc(r.source)}</dd>`
    )
    .join("");

  const counted = facts.site
    .map(
      (r) =>
        `<dt>${esc(r.label)}</dt>` +
        `<dd class="mono">${esc(r.source)}</dd>`
    )
    .join("");

  const roles = personas
    .map(
      (p) =>
        `<dt class="mono">${esc(p.code)}</dt>` +
        `<dd>${esc(p.title)} — ${esc(p.agent_count)} agent${
          p.agent_count === 1 ? "" : "s"
        }, quoted from <span class="mono">personas-and-value-tree.md</span></dd>`
    )
    .join("");

  /* And the reason each unsettled figure is unsettled, as the build wrote it.
     The block above says the same thing in the reader's words; this is the
     sentence it was rewritten from, with the file and the table named, so the
     rewrite can be checked rather than trusted. */
  const unsettled = facts.not_locally_derivable
    .map((u) => `<dt>${esc(u.figure)}</dt><dd class="mono">${esc(u.why)}</dd>`)
    .join("");

  return (
    "<p>Where each measurement was taken, where each count was taken, and the " +
    "code this estate files each role under.</p>" +
    `<dl>${measured}${counted}${roles}${unsettled}</dl>` +
    `<p class="mono">${esc(GAP.method)}</p>`
  );
}

el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "warehouse files, role codes"
) + provenance(
  `<dt>Benchmarks</dt><dd>${esc(BENCH.source)}</dd>` +
    `<dt>Personas</dt><dd>${esc(DATA.personas.source)}</dd>` +
    `<dt>Site figures</dt><dd class="mono">${esc(facts.generated_at)}</dd>`
);

reveal();
