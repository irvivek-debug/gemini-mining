/* One agent's business-framing card: the decision it owns, the leak(s) it
 * closes, its archetype and authority, what it moves on the metrics a
 * mining client already tracks, the financial line(s) it can move and at
 * what evidence class, how much of its method pack is actually
 * instrumented, and its own rigour statement.
 *
 * Shared between the persona page (one card per agent that carries one,
 * rendered beneath the role's governing question) and the value page (AGT-19's
 * card, which has no persona to render it on). One renderer, so the two
 * screens cannot draw the same field two different ways -- see design doc
 * docs/specs/2026-08-17-value-framing-and-agent-cards-design.md
 * section 2.
 *
 * AUTHORITY IS DECLARED, NOT ENFORCED. See AgentCard's own docstring in
 * mining_agents/catalog/definitions.py. Every card says so in words next to
 * the authority line, not as a footnote a reader can miss: the failure mode
 * this guards against is a reader assuming the platform stops an agent at its
 * stated level, and it does not -- there is no authority engine in this build.
 * The caveat is framed as the governance strength it actually is -- advisory
 * by default, every recommendation lands with a named human -- rather than as
 * an apology, while still saying plainly that nothing here enforces it (plan
 * 2026-08-18, "re-cut authority positively" -- both halves have to survive in
 * the same line, or the positive framing becomes an overclaim).
 *
 * COVERAGE MUST READ AS WHAT IT IS. A card at 0 of N drivers instrumented
 * renders the same row, in the same place, as a card at 5 of 7 -- never
 * blank, never styled as a fault. That is the distinction
 * mining_agents/tools/run_diagnostic.py already draws for a single
 * not_instrumented driver ("a SUCCESSFUL call, not a failure"); this is the
 * same distinction at the level of a whole pack, said the positive way round
 * ("N diagnostics proven, M scoped") rather than the fraction-of-a-target way
 * round ("N of N+M instrumented") -- the two counts still add back to the
 * total, so a card at 2 of 5 stays readable as 2 of 5 by anyone who adds them.
 *
 * METRIC IMPACT IS A BENCHMARK, NEVER A MEASUREMENT. `card.metric_impacts` is
 * a list of published, sourced ranges (mining_agents/catalog/definitions.py,
 * MetricImpact) -- an industry firm's claim about what agents like this one
 * move, never a number this build measured on the client's own data. Every
 * range renders with its source on its own face (the INDUSTRY RANGE badge
 * plus the firm's name), because an unattributed percentage on a card headed
 * for a mining client is the line that ends the conversation. A card whose
 * `metric_impacts` is empty (S03, S05 today) is not missing anything -- the
 * plan is explicit that this is a deliberate honesty decision, not a gap --
 * and it renders that as a stated fact beside the badge that never lies for
 * it, in the same "declared, not silently dropped" register the coverage row
 * already uses.
 */
if (typeof require !== "undefined" && typeof window === "undefined") {
  Object.assign(globalThis, require("../shared/shell.js"));
}

/** The share bar plus its own label, present whichever way the numbers fall.
 *
 *  A card with no pack at all (no `coverage` field) renders no coverage row —
 *  that is a different fact ("this agent has no method pack") from a pack that
 *  exists and instruments none of its drivers, which renders the row with
 *  "0 diagnostics proven". The two must not collapse into the same blank.
 *
 *  Worded positively (plan 2026-08-18): "N diagnostics proven, M scoped"
 *  rather than "N of N+M instrumented". The fact does not change -- proven
 *  plus scoped is still the pack's total driver count, so a reader who adds
 *  the two numbers back together recovers exactly what "N of T" used to say
 *  in one step, and nothing here rounds, hides or inflates a proven count
 *  that happens to be zero.
 */
function _coverageRow(coverage) {
  if (!coverage) return "";
  var pct = coverage.total ? (coverage.instrumented / coverage.total) * 100 : 0;
  var scoped = coverage.total - coverage.instrumented;
  var zero = coverage.instrumented === 0;
  return (
    '<div class="ac-row ac-coverage">' +
    '<span class="ac-label">Coverage</span>' +
    '<div class="ac-coverage-body">' +
    '<div class="share-bar" role="img" aria-hidden="true">' +
    '<span style="width:' + pct.toFixed(1) + '%"></span></div>' +
    '<p class="ac-coverage-label' + (zero ? " ac-coverage-zero" : "") + '">' +
    num(coverage.instrumented) + " diagnostic" + (coverage.instrumented === 1 ? "" : "s") +
    " proven · " + num(scoped) + " scoped" +
    "</p></div></div>"
  );
}

/** A nice round bound for a range bar, with headroom so the widest published
 *  figure this card shows does not sit flush against the edge of its own bar.
 *  Computed from the range itself rather than hand-tuned per metric, the same
 *  reason coverage is computed from the pack rather than typed by hand: a
 *  scale someone chose by eye is a scale that quietly stops fitting the day a
 *  benchmark changes. */
function _rangeScale(highPct) {
  var raw = highPct * 1.25;
  return Math.max(5, Math.ceil(raw / 5) * 5);
}

/** One MetricImpact, as a range bar with its attribution on its own face --
 *  never a sentence a reader has to parse to find the source. `+`/`−` on the
 *  figure carries direction, because "decrease 30-50%" reads as a smaller
 *  decrease than "-30-50%" reads as a bigger one, and the bar answers the
 *  same question a second way for a reader skimming rather than reading. */
function _impactRow(mi) {
  var scale = _rangeScale(mi.high_pct);
  var leftPct = ((mi.low_pct / scale) * 100).toFixed(1);
  var widthPct = (((mi.high_pct - mi.low_pct) / scale) * 100).toFixed(1);
  var sign = mi.direction === "decrease" ? "−" : "+";
  var dp = Number.isInteger(mi.low_pct) && Number.isInteger(mi.high_pct) ? 0 : 1;
  return (
    '<div class="range-row">' +
    '<div class="range-row-head">' +
    '<span class="range-row-label">' + esc(mi.metric) + "</span>" +
    '<span class="range-row-fig">' + sign + fig(mi.low_pct, "", dp) + "–" +
    fig(mi.high_pct, "%", dp) + "</span>" +
    "</div>" +
    '<div class="money-range-bar"><span style="left:' + leftPct + "%;width:" +
    widthPct + '%"></span></div>' +
    '<div class="range-row-foot">' +
    '<span class="badge b-info">INDUSTRY RANGE</span>' +
    '<span class="cite">' + esc(mi.source) + "</span>" +
    "</div></div>"
  );
}

/** The metric-impact block. Never blank and never an error state when a card
 *  carries no ranges (S03, S05 today) -- the empty case is rendered as its own
 *  stated fact, in the same register as a `0 diagnostics proven` coverage row,
 *  because both are the same shape of truth: this card's case rests on
 *  something other than a published percentage, and it says so rather than
 *  going quiet where the percentage would have gone. */
function _metricImpactsBlock(impacts) {
  var body = (impacts && impacts.length)
    ? impacts.map(_impactRow).join("")
    : '<p class="pnote ac-impact-empty">No industry range applies here — this ' +
      "card's case rests on its evidence class and coverage, stated below, " +
      "not on a published percentage.</p>";
  return (
    '<div class="ac-row ac-impacts">' +
    '<span class="ac-label">Metric impact</span>' +
    '<div class="ac-impacts-body">' + body + "</div>" +
    "</div>"
  );
}

function renderAgentCard(card) {
  var leaks = (card.leaks || [])
    .map(function (l) { return '<span class="badge b-info">' + esc(l) + "</span>"; })
    .join(" ");
  var lines = (card.financial_lines || [])
    .map(function (fl) {
      return (
        "<li>" + esc(fl.line) +
        ' <span class="badge b-idle">Class ' + esc(fl.evidence_class) + "</span></li>"
      );
    })
    .join("");
  return (
    '<div class="agent-card">' +
    '<div class="ac-head">' +
    '<span class="ac-id mono">' + esc(card.agent_id) + "</span>" +
    '<span class="ac-name">' + esc(card.display_name) + "</span>" +
    "</div>" +
    '<p class="ac-decision">' + esc(card.decision) + "</p>" +
    '<div class="ac-row"><span class="ac-label">Leak' +
    ((card.leaks || []).length > 1 ? "s" : "") + "</span>" + leaks + "</div>" +
    '<div class="ac-row"><span class="ac-label">Archetype</span>' +
    "<span>" + esc(card.archetype) + "</span></div>" +
    '<div class="ac-row"><span class="ac-label">Authority</span>' +
    "<span>" + esc(card.authority) +
    // The caveat sits on every card, not once on the page, so a reader who
    // meets only one card still meets it. Led by the governance strength the
    // fact actually is -- every recommendation lands with a named human --
    // and closed by the same true limit the old wording carried: this is a
    // stance the card declares, not a control any system in this build runs.
    ' <span class="ac-caveat">— advisory by default: every recommendation ' +
    "lands with a named human, a stance this card declares, not one the " +
    "platform runs</span></span></div>" +
    _metricImpactsBlock(card.metric_impacts) +
    '<div class="ac-row ac-lines"><span class="ac-label">Financial line' +
    ((card.financial_lines || []).length > 1 ? "s" : "") + "</span>" +
    "<ul>" + lines + "</ul></div>" +
    _coverageRow(card.coverage) +
    '<p class="ac-limit"><span class="ac-label">What we will not claim</span> ' +
    esc(card.honest_limit) + "</p>" +
    "</div>"
  );
}

if (typeof module !== "undefined") {
  module.exports = { renderAgentCard, _coverageRow, _metricImpactsBlock, _impactRow, _rangeScale };
}
