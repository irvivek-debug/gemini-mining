/* Screen 1.3 — what the gap is worth.
 *
 * The order of this screen is the argument, and it was deliberately inverted
 * from an earlier draft that opened with a 52-cell partition. A partition is a
 * proof of tidiness; it answers a question nobody has asked yet. So the price
 * of a recovery point goes first, the six pools that release it go second, and
 * the proof that the six do not overlap goes third — available to a reader who
 * wants it, out of the way of one who has already been convinced.
 *
 * The screen's discipline is that it never states a magnitude it cannot source.
 * One dollar figure in this repository is real. The calculator holds that line
 * by splitting itself in two: what this site's own record settles on the left,
 * what only the client holds on the right, and no arithmetic until the client
 * has typed. A CEO who is shown a number they did not supply stops trusting the
 * screen, and they are right to.
 */

mountNav("case", "value.html");

const tree = DATA.value_tree;
const catalog = DATA.catalog;
const personas = DATA.personas.personas;
const evidence = DATA.signals.branch_evidence;
const GAP = DATA.signals.gap;
const ROI = DATA.signals.roi;
const BENCH = DATA.benchmarks;

/* One hue per branch, used on the partition cell, the key, the card edge and
   the sparkline. The convergence agent takes the neutral, because it is
   deliberately not a seventh branch. Every coloured element also prints its
   code, so nothing on this screen depends on a reader distinguishing hues. */
const HUE = {};
tree.branches.forEach((b, i) => (HUE[b.code] = `var(--b${i + 1})`));
const CONV_HUE = "var(--bx)";

const TOTAL = catalog.counts.entrypoints;
const CONV = tree.convergence.agents;

/* Which measured gap belongs to which pool. Deliberately sparse: four of the
   six pools have no day-to-day gap this repository can measure, and the cards
   say so in words rather than leaving a tidy blank. */
const POOL_GAPS = {
  B3: ["recovery", "feed_rate", "conveyor_load"],
  B4: ["payload"],
};

/* The pool a published figure speaks to is recorded in the benchmarks file
   beside the figure itself, not in a second list kept here. A screen that held
   its own copy of that mapping could disagree with the source file without
   anything failing, which is exactly the class of drift this repository spends
   its build steps preventing. */
const POOL_BENCH = BENCH.by_pool || {};

tree.branches.forEach((b) => {
  if (!POOL_BENCH[b.code]) {
    throw new Error(`pool ${b.code} has no benchmark in ${BENCH.source}`);
  }
});

/* Which measured gap a pool leads with, where it has one. The pool holds three
   in one case, and a card that opened with all three would have no headline at
   all. */
const POOL_LEAD_GAP = { B3: "recovery", B4: "payload" };

/** Every published uplift for a pool, with same-metric figures from different
 *  publishers merged into one range.
 *
 *  Merging is the honest move where three houses have measured the same
 *  mechanism and disagree: printing 2–5% alone would be selective, and printing
 *  10–15% alone would be worse. The merged range keeps its sources so the card
 *  can name who is at each end.
 */
function poolUplifts(code) {
  const merged = [];
  (POOL_BENCH[code] || []).forEach((id) => {
    (BENCH.by_id[id].uplift || []).forEach((up) => {
      const hit = merged.find((m) => m.metric === up.metric);
      if (hit) {
        hit.low = Math.min(hit.low, up.low);
        hit.high = Math.max(hit.high, up.high);
        hit.sources.push(id);
      } else {
        merged.push({ ...up, sources: [id] });
      }
    });
  });
  return merged;
}

/** A range, or a single figure where the publishers happen to agree on a point.
 *  Bounds are printed at the precision they were published at — "2.40%" claims
 *  a decimal BCG did not write. */
function upliftRange(u) {
  const dp = Number.isInteger(u.low) && Number.isInteger(u.high) ? 0 : 1;
  if (u.low === u.high) return fig(u.high, u.unit, dp);
  return `${fig(u.low, "", dp)}–${fig(u.high, u.unit, dp)}`;
}

/** Who published a merged range, deduplicated and in file order. */
function upliftWho(u) {
  const seen = [];
  u.sources.forEach((id) => {
    const b = BENCH.by_id[id];
    const name = `${b.publisher.replace(/ & Company$/, "")} ${b.year}`;
    if (!seen.includes(name)) seen.push(name);
  });
  return seen.join(", ");
}

const gapRow = (id) => GAP.rows.find((r) => r.id === id);
const RECOVERY = gapRow("recovery");
const RDP = rowPlaces(RECOVERY);
/* The calculator multiplies by the gap the reader can see, not by the full
   float behind it. A panel that prints "1.96 points" and then returns a total
   the reader cannot reach by multiplying is a panel that has to be taken on
   trust, and the whole point of showing the working is that it need not be. */
const GAP_PTS = +RECOVERY.delta.toFixed(RDP);

el("value-lede").textContent =
  "Every pool below carries a magnitude and says where that magnitude came " +
  "from: this site's own record, or somebody else's published study, named. " +
  "None of them carries a dollar figure, because the volumes, the contracts " +
  "and the tariffs that turn a percentage into money are held by the reader " +
  "and not by this repository. The calculator does that conversion, once, " +
  "with the reader's own numbers and a price range rather than a spot quote.";

/* ---------- the prize ---------- */

el("roi-lede").textContent =
  "A recovery point is not money until three things are known: how much ore " +
  "goes through the mill, what that ore carries, and what the metal sells for. " +
  "This site's record settles the middle one — " +
  ROI.feed_grade_days +
  " days of concentrator feed assays — and is silent on the other two. So the " +
  "panel below stops exactly there. The metal is not named: the physical half " +
  "of this calculation is metallurgy and does not care which one it is.";

el("roi-known").innerHTML =
  '<div class="known"><span class="v">' +
  esc(fig(ROI.feed_grade_pct, "%")) +
  '</span><span>Metal in the mill feed, the median of ' +
  esc(ROI.feed_grade_days) +
  " days of assay<br><span class=\"dim\" style=\"color:var(--fg-dim);font-size:11.5px\">" +
  esc(ROI.feed_grade_source) +
  "</span></span></div>" +
  '<div class="known"><span class="v">' +
  esc(fig(RECOVERY.delta, "pts", RDP)) +
  '</span><span>Between the ordinary day and the best one<br>' +
  '<span class="dim" style="color:var(--fg-dim);font-size:11.5px">Measured here, ' +
  esc(RECOVERY.days) +
  " days — not a target</span></span></div>" +
  '<div class="known"><span class="v">' +
  esc(fig(ROI.t_per_mt_per_point, "t")) +
  '</span><span>Contained metal per million tonnes milled, ' +
  "for each point of recovery<br>" +
  '<span class="dim" style="color:var(--fg-dim);font-size:11.5px">' +
  esc(ROI.feed_grade_pct) +
  "% × 1% × 1,000,000 t</span></span></div>";

/* Price is asked for as a range, not a figure. A single price is a spot quote
   that is stale by the time a deck is read, and a planning team works in bands
   anyway — so a panel that demanded one exact number would be asking the reader
   to be more precise than their own business case is. */
el("roi-inputs").innerHTML =
  "<label>" +
  '<span class="name">Annual mill throughput' +
  '<span class="whose">your figure</span></span>' +
  '<input type="number" id="roi-mt" min="0" step="0.1" inputmode="decimal" ' +
  'placeholder="million tonnes per year">' +
  '<span class="hint">Not in this repository. The files hold one crusher\'s ' +
  "feed rate, which is not a plant figure and will not be presented as one." +
  "</span></label>" +
  "<label>" +
  '<span class="name">Realised metal price, low' +
  '<span class="whose">your figure</span></span>' +
  '<input type="number" id="roi-price-lo" min="0" step="100" inputmode="decimal" ' +
  'placeholder="US dollars per tonne">' +
  '<span class="hint">The bottom of the band you plan against, net of your own ' +
  "terms — not a spot quote this screen looked up.</span></label>" +
  "<label>" +
  '<span class="name">Realised metal price, high' +
  '<span class="whose">your figure</span></span>' +
  '<input type="number" id="roi-price-hi" min="0" step="100" inputmode="decimal" ' +
  'placeholder="US dollars per tonne">' +
  '<span class="hint">The top of the same band. The answer is returned as a ' +
  "range across the two, because that is the honest shape of it." +
  "</span></label>";

const mtInput = el("roi-mt");
const loInput = el("roi-price-lo");
const hiInput = el("roi-price-hi");

function money(v) {
  return (
    "$" +
    v.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  );
}

/* The equation is printed whether or not it can be evaluated. A calculator that
   shows only its answer asks to be trusted; one that shows its working can be
   checked, and this one is meant to be checked. */
function renderRoi() {
  const mt = parseFloat(mtInput.value);
  const a = parseFloat(loInput.value);
  const b = parseFloat(hiInput.value);
  const eq =
    '<div class="eq">throughput (Mt/yr) × ' +
    esc(fig(ROI.t_per_mt_per_point, "t")) +
    " per Mt per point × " +
    esc(fig(GAP_PTS, "points", RDP)) +
    " × price ($/t)<br>" +
    esc(ROI.basis) +
    "</div>";

  const priced = Number.isFinite(a) && a > 0 && Number.isFinite(b) && b > 0;
  if (!(Number.isFinite(mt) && mt > 0 && priced)) {
    el("roi-out").innerHTML =
      clientInput() +
      '<div class="metric-sub">A throughput and a price band short of an ' +
      "answer, and this screen will not supply either</div>" +
      eq;
    return;
  }

  // The two price fields are a band, so which box the larger figure went in is
  // not information. Sorting them here means a reader who fills them the other
  // way round gets the same answer rather than a negative range.
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  const tonnesPerPoint = mt * ROI.t_per_mt_per_point;
  const tonnesAtGap = tonnesPerPoint * GAP_PTS;
  /* Tonnes are exact and money is a range, and that split is the point of the
     panel. The physical side is metallurgy — a grade, a recovery point and a
     throughput, all of them measured. The money side is a market, and a market
     is quoted in bands. Printing one figure for both halves would present the
     weaker half with the confidence of the stronger one. */
  const band = (t) =>
    lo === hi ? money(t * lo) : `${money(t * lo)} – ${money(t * hi)}`;

  el("roi-out").innerHTML =
    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));' +
    'gap:20px;margin-bottom:14px">' +
    "<div>" +
    `<div class="metric">${esc(band(tonnesPerPoint))}</div>` +
    '<div class="metric-sub">A year, for one point of recovery — ' +
    esc(fig(tonnesPerPoint, "t")) +
    " of contained metal</div></div>" +
    "<div>" +
    // The accent goes on the gap, not on the unit rate: the unit rate is the
    // arithmetic, the gap is the finding.
    `<div class="metric accent">${esc(band(tonnesAtGap))}</div>` +
    '<div class="metric-sub">A year, at the ' +
    esc(fig(GAP_PTS, "point", RDP)) +
    " gap this site already reached — " +
    esc(fig(tonnesAtGap, "t")) +
    " of contained metal, exactly</div></div></div>" +
    eq;
}

[mtInput, loInput, hiInput].forEach((node) =>
  node.addEventListener("input", renderRoi)
);
renderRoi();

el("roi-note").innerHTML =
  '<div class="note"><strong>What this figure is not</strong><br>' +
  esc(GAP.caveat) +
  " The tonnes above are contained metal, whichever metal your assay is of: " +
  "smelter payability and treatment and refining charges take a cut for which " +
  "this repository holds no terms, so the money is an upper bound on the " +
  "concentrate, not a number to put in a board paper without your commercial " +
  "team on it.</div>";

/* ---------- the six pools ---------- */

el("pools-lede").textContent =
  "Each pool leads with one number and a badge saying who established it. Two " +
  "of the six are measured in this plant's own record and are badged so; the " +
  "other four carry a published range and name the houses at each end of it. " +
  "Where three publishers have measured the same mechanism and disagree, the " +
  "range spans all three rather than quoting the flattering end.";

/** Round a range label to the precision the instrument plausibly has. The
 *  export keeps four decimals because it is a mean and rounding is the
 *  screen's business; a header reading "3.6429 – 4.5323 MW" claims a mill
 *  power meter resolves to a hundred watts. */
function round(v) {
  // Counts are already exact. "0.00 – 7.00 alerts" invents a fractional alert.
  if (Number.isInteger(v)) return v.toLocaleString("en-US");
  return fig(v);
}

/** The measurement this repository holds for a branch, drawn as what it is.
 *
 *  A series gets a line. A block model gets a distribution, because it is
 *  spatial and has no time axis. A stock level gets a share of its whole,
 *  because it is a position rather than a history. Drawing all three as
 *  sparklines would make five identical cards and two false claims.
 */
function evidenceBlock(code, hue) {
  const e = evidence[code];
  if (!e) return "";
  const head = (left, right) =>
    `<div class="head"><span>${esc(left)}</span><span>${esc(right)}</span></div>`;
  const foot =
    `<div class="cap">${esc(e.caption)}</div>` +
    `<div class="src">${esc(e.source)}</div>`;

  let body = "";
  if (e.kind === "series") {
    body =
      head(e.label, `${round(e.min)} – ${round(e.max)} ${e.unit}`) +
      sparkline(e.points, { colour: hue, label: e.label });
  } else if (e.kind === "distribution") {
    const tallest = Math.max(...e.bins);
    body =
      head(
        e.label,
        `${round(e.edges[0])} – ${round(e.edges[e.edges.length - 1])} ${e.unit}`
      ) +
      '<div class="dist reveal">' +
      e.bins
        .map(
          (n) =>
            `<span style="--hue:${hue};height:${((n / tallest) * 100).toFixed(1)}%" ` +
            `title="${esc(n)} blocks"></span>`
        )
        .join("") +
      "</div>";
  } else if (e.kind === "share") {
    body =
      head(e.label, `${e.part} of ${e.whole}`) +
      `<div class="share"><span data-share="${((e.part / e.whole) * 100).toFixed(
        2
      )}" style="--hue:${hue}"></span></div>`;
  }
  return `<div class="evidence">${body}${foot}</div>`;
}

/** The gap rows this pool acts on, ordinary day to best day. */
function measuredBlock(code) {
  const ids = POOL_GAPS[code];
  if (!ids) {
    return (
      '<div class="pool-measured"><div class="row" style="color:var(--fg-dim)">' +
      "<span>No day-to-day gap this repository can measure</span>" +
      '<span class="move"></span><span class="up">—</span></div></div>'
    );
  }
  return (
    '<div class="pool-measured">' +
    ids
      .map((id) => {
        const r = gapRow(id);
        const dp = rowPlaces(r);
        const up =
          r.delta_kind === "points"
            ? `+${fig(r.delta, "pts", dp)}`
            : `+${fig(r.delta_pct, "%", 1)}`;
        return (
          '<div class="row">' +
          `<span>${esc(r.label)}${r.asset_id ? ` · ${esc(r.asset_id)}` : ""}</span>` +
          `<span class="move">${esc(fig(r.median, "", dp))} → ${esc(
            fig(r.p90, r.unit, dp)
          )}</span>` +
          `<span class="up">${esc(up)}</span></div>`
        );
      })
      .join("") +
    "</div>"
  );
}

/** What somebody other than us has published about the same mechanism. */
function benchBlock(code) {
  return (POOL_BENCH[code] || [])
    .map((id) => {
      const b = BENCH.by_id[id];
      return (
        '<div class="benchline">' +
        `<span class="claim">${esc(b.headline)}</span>` +
        `<span class="cite">${esc(b.publisher)}, ${esc(b.year)}</span></div>`
      );
    })
    .join("");
}

/** The pool's headline magnitude, and where it came from.
 *
 *  This slot used to hold a dollar figure or, in five cases out of six, the
 *  words [CLIENT INPUT REQUIRED] — which was honest but told a chief executive
 *  nothing at all about five of the six pools. A percentage is the right unit
 *  here: it is what both this site's own record and every published study
 *  actually measure, it needs no throughput and no price to be meaningful, and
 *  it survives the reader not having decided their commodity assumptions yet.
 *
 *  The badge is not decoration. "Measured here" and "Published elsewhere" are
 *  different classes of evidence and the difference is the whole argument of
 *  these screens — a number from this site's own 167 days cannot be waved away,
 *  and a number from somebody else's mine can. Marking which is which is what
 *  earns the right to print both on one card.
 */
function upliftBlock(code) {
  const ups = poolUplifts(code);
  const leadId = POOL_LEAD_GAP[code];
  let head;
  let rest;

  if (leadId) {
    const r = gapRow(leadId);
    const dp = rowPlaces(r);
    const value =
      r.delta_kind === "points"
        ? `+${fig(r.delta, "pts", dp)}`
        : `+${fig(r.delta_pct, "%", 1)}`;
    head =
      `<div class="uplift"><div class="metric accent">${esc(value)}</div>` +
      '<span class="badge b-info">Measured here</span></div>' +
      `<div class="metric-sub">${esc(r.label.toLowerCase())}, ordinary day to ` +
      `best day, across ${esc(r.days)} days of this plant's own record</div>`;
    // Every published range stays, underneath. Where a pool has both, setting
    // this site's measured figure directly against the outside range is the
    // strongest thing on the screen — 1.96 points sitting inside a published
    // one to four says the target is ordinary, which is the entire argument.
    rest = ups;
  } else if (ups.length) {
    head =
      `<div class="uplift"><div class="metric">${esc(upliftRange(ups[0]))}</div>` +
      '<span class="badge b-idle">Published elsewhere</span></div>' +
      `<div class="metric-sub">${esc(ups[0].metric)} — ${esc(upliftWho(ups[0]))}</div>`;
    rest = ups.slice(1);
  } else {
    return (
      clientInput() +
      '<div class="metric-sub">Baseline not held in this repository</div>'
    );
  }

  // The pool's remaining metrics, kept below the headline rather than beside
  // it. A card with three equally sized numbers has no finding on it.
  return (
    head +
    rest
      .map(
        (u) =>
          '<div class="metric-sub" style="margin-top:6px">' +
          `<b style="color:var(--fg)">${esc(upliftRange(u))}</b> ${esc(u.metric)} — ` +
          `${esc(upliftWho(u))}</div>`
      )
      .join("")
  );
}

/* Each pool states its mechanism, then a magnitude, then who established it.
   The one dollar rate this repository holds is carried as a footnote on the
   pool it belongs to rather than as that pool's headline: a rate per hour of
   downtime is a real figure, but it is not an uplift, and putting it in the
   slot where the other five pools print an uplift would compare two different
   kinds of thing across one row of cards. */
el("detail").innerHTML = tree.branches
  .map((b, i) => {
    const hue = HUE[b.code];
    const anchor = b.anchored
      ? '<div class="metric-sub" style="margin-top:6px">' +
        `<b style="color:var(--fg)">$${esc(
          num(DATA.facts.mill_downtime_usd_per_hour)
        )}</b> per hour of mill downtime — measured here, and the only dollar ` +
        "figure this repository establishes</div>"
      : "";

    const who = b.personas
      .map((c) => `${esc(c)} ${esc(personas[c] ? personas[c].title : "")}`)
      .join(" · ");

    return (
      `<div class="card c6 branch reveal" style="--hue:${hue}">` +
      // The counter, not the branch code. It says the set is closed, which is
      // the one thing about the partition worth carrying this far up.
      `<div class="card-cap">Pool ${esc(i + 1)} of ${esc(tree.branches.length)}</div>` +
      `<h3 style="margin-top:0">${esc(b.title)}</h3>` +
      `<p style="color:var(--fg-muted);margin-top:0">${esc(b.mechanism)}</p>` +
      '<div style="border-top:1px solid var(--border);padding-top:12px;margin-top:12px">' +
      upliftBlock(b.code) +
      anchor +
      "</div>" +
      measuredBlock(b.code) +
      benchBlock(b.code) +
      evidenceBlock(b.code, hue) +
      // The pool's place in the estate, kept to a footnote, and kept to the
      // part of it a reader can use. Whose pool it is, and how many decisions
      // sit in it. The pool's code and its process area are in the drawer.
      `<div class="mono" style="font-size:10.5px;color:var(--fg-dim);margin-top:12px;` +
      `text-transform:uppercase;letter-spacing:.06em">${esc(
        b.count
      )} agents you can talk to<br>${who}</div>` +
      "</div>"
    );
  })
  .join("");

/* ---------- the partition, demoted ---------- */

const ABOVE =
  CONV.length === 1
    ? "One more sits above all of them and belongs to no pool"
    : CONV.length + " more sit above all of them and belong to no pool";

el("mece-lede").textContent =
  "The pools above hold " +
  tree.branches.map((b) => b.count).join(", ") +
  " of the decisions this estate takes on. " +
  ABOVE +
  ", which makes " +
  TOTAL +
  " with no overlap and no remainder. The build refuses to emit a value tree " +
  "whose branches fail to reconcile against the catalog that deploys them, so " +
  "the claim is enforced upstream rather than asserted by this copy.";

const CELLS = [];
tree.branches.forEach((b) => {
  for (let i = 0; i < b.count; i += 1) CELLS.push({ code: b.code, hue: HUE[b.code] });
});
CONV.forEach((id) => CELLS.push({ code: id, hue: CONV_HUE }));

if (CELLS.length !== TOTAL) {
  throw new Error(
    `the partition drew ${CELLS.length} cells for ${TOTAL} entrypoints; ` +
      "the bundle's value tree and catalog disagree"
  );
}

el("partition").innerHTML = CELLS.map(
  (c, i) =>
    `<div class="cell" data-i="${i}" style="--hue:${c.hue}" ` +
    `title="${esc(c.code)}"></div>`
).join("");

el("mece-key").innerHTML =
  tree.branches
    .map(
      (b, i) =>
        '<div class="row">' +
        `<span class="chip" style="--hue:${HUE[b.code]}"></span>` +
        `<span><b>Pool ${esc(i + 1)}</b> ${esc(b.title)}</span>` +
        `<span class="n">${esc(b.count)}</span></div>`
    )
    .join("") +
  '<div class="row">' +
  `<span class="chip" style="--hue:${CONV_HUE}"></span>` +
  "<span><b>Above them all</b> The one decision that belongs to no pool</span>" +
  `<span class="n">${esc(CONV.length)}</span></div>`;

el("mece-sum").innerHTML =
  '<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">' +
  '<span class="metric" id="running">0</span>' +
  /* "entry points" was the last of the term on this screen, and the reader had
     already been given a better word for the same thing two paragraphs above:
     the lede, the process note and the cells themselves all count decisions. */
  `<span class="metric-sub" style="margin:0">of ${esc(TOTAL)} decisions placed in a pool</span>` +
  "</div>" +
  '<div class="mono" style="font-size:12px;margin-top:10px;color:var(--fg-muted)">' +
  tree.branches
    .map((b) => `<span style="color:${HUE[b.code]}">${esc(b.count)}</span>`)
    .join(" + ") +
  ` + <span style="color:${CONV_HUE}">${esc(CONV.length)}</span> = ` +
  `<b style="color:var(--fg)">${esc(TOTAL)}</b></div>`;

/* Cells fill in branch order while the total counts with them, so the reader
   watches the partition being assembled rather than being told it adds up.
   setInterval, not requestAnimationFrame: rAF does not fire in a hidden
   document, which is every browser this screen is checked in. */
const cellNodes = Array.from(el("partition").querySelectorAll(".cell"));
const running = el("running");
const reduced =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (reduced) {
  cellNodes.forEach((n) => n.classList.add("on"));
  running.textContent = String(TOTAL);
} else {
  let filled = 0;
  const fill = window.setInterval(() => {
    cellNodes[filled].classList.add("on");
    filled += 1;
    running.textContent = String(filled);
    if (filled >= cellNodes.length) window.clearInterval(fill);
  }, 26);
}

el("convergence").innerHTML =
  '<div class="note info"><strong>The layer above the pools</strong><br>' +
  esc(tree.convergence.note) +
  " It is the one decision that stands alone, and the one cell above that is " +
  "not a pool colour.</div>";

/* ---------- the process view, which deliberately does not partition ---------- */

const apqcTotal = Object.values(catalog.by_apqc_code).reduce(
  (sum, info) => sum + info.count,
  0
);

el("process-lede").textContent =
  "The same " +
  TOTAL +
  " decisions, grouped by the standard process areas a mining client already " +
  "runs their operating model against. This cut is not a partition and is not " +
  "meant to be: " +
  catalog.compound_apqc_codes.length +
  " of them belong to two process areas at once, because the work genuinely " +
  "spans both, and each is counted under each. The column below therefore " +
  "adds up to " +
  apqcTotal +
  " rather than " +
  TOTAL +
  ". A framework a client already owns is worth mapping onto even where it " +
  "overlaps; what is not worth doing is hiding that it does.";

el("process").innerHTML = Object.entries(catalog.by_apqc_code)
  .map(
    ([code, info]) =>
      "<tr>" +
      `<td>${esc(catalog.apqc_names[code] || "Unnamed in this catalog")}</td>` +
      `<td class="num">${esc(info.count)}</td>` +
      "</tr>"
  )
  .join("");

el("process-note").innerHTML =
  '<div class="note"><strong>Why the column adds up to more than the total</strong><br>' +
  `${esc(catalog.compound_apqc_codes.length)} of the ${esc(TOTAL)} decisions ` +
  "span two process areas and are counted under each, so the column above " +
  `reaches ${esc(apqcTotal)}. Nothing is duplicated in the pools on the way ` +
  "up this screen; it is this cut, and only this cut, that overlaps." +
  "</div>";

const citedBench = Object.values(POOL_BENCH)
  .flat()
  .filter((id, i, all) => all.indexOf(id) === i)
  .map((id) => {
    const b = BENCH.by_id[id];
    return `${b.title} (${b.publisher}, ${b.year})`;
  })
  .join("; ");

/* ---------- the machinery, at the end and closed ---------- */

/* Four things came off the page above. The code each pool is filed under and
   the process code it maps to, which is how the rest of this estate refers to
   it; the agent ids inside each process area, which is what a reader who wants
   to check the overlap has to be able to count for themselves; and the seven
   compound codes spelled out, since "counted under each" is a claim that ought
   to be checkable rather than taken on trust. */
function drawerBody() {
  const pools = tree.branches
    .map(
      (b, i) =>
        `<dt class="mono">${esc(b.code)} · ${esc(b.apqc)}</dt>` +
        `<dd>Pool ${esc(i + 1)}, ${esc(b.title)} — ${esc(b.count)} entry points, ` +
        `value-tree branches <span class="mono">${esc(b.branches.join(", "))}</span></dd>`
    )
    .join("") +
    `<dt class="mono">${esc(CONV.join(", "))}</dt>` +
    "<dd>Above the pools, in no branch</dd>";

  const areas = Object.entries(catalog.by_apqc_code)
    .map(
      ([code, info]) =>
        `<dt class="mono">${esc(code)}</dt>` +
        `<dd>${esc(catalog.apqc_names[code] || "unnamed in this catalog")} — ` +
        `<span class="mono">${esc(info.agents.join(", "))}</span></dd>`
    )
    .join("");

  const compound =
    "<dt>Counted twice</dt>" +
    `<dd class="mono">${esc(catalog.compound_apqc_codes.join(" · "))}</dd>`;

  return (
    "<p>The code each pool is filed under, the APQC process code it maps to, " +
    "and the agent ids in each process area — so the overlap the note above " +
    "describes can be counted rather than believed.</p>" +
    `<dl>${pools}${areas}${compound}</dl>` +
    `<p class="mono">${esc(tree.root_source)} · ${esc(catalog.source)}</p>`
  );
}

el("prov").innerHTML = technicalDrawer(
  drawerBody(),
  "pool codes, process codes, agent ids"
) + provenance(
  /* Each file is named in an element of its own rather than run into the
     sentence beside it: a citation is a citation, and a file name inside a
     sentence is the machinery talking on the reader's side of the drawer. */
  `<dt>Value tree</dt><dd>Rooted on ${esc(tree.root)}. ` +
    `<span class="mono">${esc(tree.root_source)}</span></dd>` +
    `<dt>The calculation</dt><dd>Feed grade is the median of ${esc(
      ROI.feed_grade_days
    )} days of plant assays. <span class="mono">${esc(
      ROI.feed_grade_source
    )}</span> ${esc(GAP.method)} ${esc(
      ROI.basis
    )} Throughput and price are entered by the reader and are never defaulted.</dd>` +
    `<dt>Benchmarks</dt><dd>${esc(citedBench)}. Held in ` +
    `<span class="mono">${esc(BENCH.source)}</span> with a URL per figure; ${esc(
      BENCH.excluded.length
    )} further figures were found and are recorded there as unverifiable rather ` +
    "than printed.</dd>" +
    `<dt>Evidence</dt><dd>Reduced at build time to ${esc(
      DATA.signals.buckets
    )} points per series; each card names its own file. ` +
    `<span class="mono">${esc(DATA.signals.source)}</span></dd>` +
    "<dt>Correction</dt><dd>That document's branch table gives Branch 6 a count of 10 while " +
    "naming only 9 agents under it, which absorbs S12 into a branch its own prose places above all " +
    "six. The catalog settles it: safety holds 9, S12 stands alone. The build refuses to emit " +
    "a tree whose branches do not reconcile to the catalog.</dd>"
);

reveal();

/* The share bar grows from zero once it is in the document — the comparison is
   17 against 105, and a bar that is already full when the reader arrives has
   made that comparison for them. */
Array.from(document.querySelectorAll("[data-share]")).forEach((node) => {
  const to = node.getAttribute("data-share") + "%";
  if (reduced) node.style.width = to;
  else window.setTimeout(() => (node.style.width = to), 300);
});
