# UX uplift — design

**Date:** 2026-08-13
**Scope:** two screens — `apps/index.html` (the chooser) and `apps/case/value.html`
(value unlock). If they land, the same language rolls across the other nine.

## The complaint and its cause

The screens were called "super static and boring". That is two faults, and the
second causes the first.

**Nothing moves and nothing responds.** Six of eleven screens carry zero event
listeners. Every element paints at once on load. Cards do not react to a cursor.
One accent colour does all the work, so a page of six branches looks like a page
of one thing repeated six times.

**Nothing is shown.** The repository holds 25,946 telemetry readings, 1,000
block-model cells, 3,340 fatigue readings and 500 work orders, and not one of
them reaches a screen. The value screen's only chart renders *agent counts* as
2px hairlines. A screen whose most interesting figure is "how many agents are in
this branch" will feel inert no matter what it is styled like, because the reader
is being shown an org chart when they came for a mine.

The fix is therefore substantive first and cosmetic second: put the real signal
on the screen, then let motion serve it.

## Principles

**Google and Apple design language, reconciled with the existing system.**
The system is matte, 1px-bordered, zero-radius, no drop shadows, and that stays.
What is added is what Material 3 and Apple actually contribute in a dark theme:

- **Radius scale.** `--r-sm 8px / --r-md 12px / --r-lg 20px`. Cards and surfaces
  soften; tables, consoles and the graph canvas stay square, because a square
  edge is what reads as "this is data, not chrome".
- **Tonal elevation, not shadow.** A raised surface is a lighter tone
  (`--surface` → `--surface-high`) plus a brighter border. No gloss, no gradient,
  no shadow. This is Material 3's dark-theme rule and it happens to be the rule
  the existing system already follows.
- **Emphasized easing.** `--ease-emph: cubic-bezier(0.2, 0, 0, 1)` for entrances
  and `--ease-std: cubic-bezier(0.4, 0, 0.2, 1)` for state changes; durations
  `--dur-1 180ms`, `--dur-2 320ms`, `--dur-3 560ms`. One curve family everywhere.
- **Motion is functional only.** Things enter in the reading order. Numbers count
  up so the eye lands on the figure changing. Bars grow from zero so the
  comparison is drawn rather than asserted. Nothing loops, nothing decorates,
  nothing moves that is not carrying meaning.
- **Six branch hues.** Six branches get six hues, so the value screen reads as a
  partition at a glance instead of a list. Hues are desaturated to sit on the
  matte background and each is used for exactly one branch on every surface it
  appears — bar, card edge, sparkline, legend.

**Every figure remains sourced.** No new number appears that is not counted from
`data/generated/*.parquet` or `mining_agents.catalog.definitions`. Unknown
magnitudes stay `[CLIENT INPUT REQUIRED]`. A sparkline appears only where a real
series exists; where the evidence is a proportion or a distribution it is drawn
as a proportion or a distribution and labelled as such. Inventing a trend line
for a figure that has no time axis would be exactly the failure this project
keeps refusing.

**Accessibility.** Every motion rule is wrapped in
`@media (prefers-reduced-motion: no-preference)`; the reduced-motion path is the
final state painted immediately, never a degraded one. Hue is never the only
carrier of meaning — every coloured element also carries its code as text.

## MECE: what the value screen actually argues

This is the centrepiece and the reason the screen exists.

**The value tree is a strict partition.** Six branches hold 13, 6, 7, 6, 10 and 9
entrypoints = 51. S12, the convergence agent, holds the 52nd. Every entrypoint
lands in exactly one place; nothing is counted twice and nothing is left over.
`build_value_tree` already refuses to emit a tree that does not reconcile, so the
claim is enforced by the build rather than asserted by the copy.

**The APQC view is deliberately not exclusive.** Seven entrypoints carry a
compound code spanning two processes and are counted under both, so that table
sums *above* 52 on purpose.

Showing both, and naming which is which, is the argument. The screen therefore
gets a single **52-cell partition strip** as its hero: 52 cells, six colours plus
the convergence cell, filling left to right as the counts count up, with a
running total that lands on exactly 52. Underneath, the APQC table carries an
explicit "overlapping by design — sums to N, not 52" caption. A reader who sees
one exhaustive view and one overlapping view, each labelled, learns more than a
reader shown one tidy chart.

## UX flow

The chooser is the fork; each application owns its own path. The uplift makes the
path visible rather than adding to it.

- **Landing** — hero, then the site as it was actually recorded, then the two
  applications. A reader learns there is a real mine behind this before they are
  asked which door to take.
- **Case** — proposition → the mine today → **value unlock** → the solution →
  the graph. Value is screen 3, the pivot: everything before it is context and
  everything after is mechanism. The value screen's own order is therefore
  *partition first* (what the 52 are), *branch by branch* second (what each one
  does and what evidence exists for it), *process view* third (how it maps to the
  framework the client already runs).
- Each screen keeps its existing Back / Next pair. No new navigation.

## What gets built

### 1. Signal export — `scripts/build_app_data.py` → `signals.json`

New payload in the bundle. Nothing else in the export changes.

```
signals = {
  generated_at, source, window: {from, to, buckets},
  assets: [                      # the landing strip, five assets
    {asset_id, metric, unit, points: [...], min, max, readings, source}
  ],
  branch_evidence: {             # one entry per CEO_TREE branch code
    B1: {kind: "series",       label, unit, points, min, max, caption, source},
    B2: {kind: "distribution", label, unit, bins, edges, n,   caption, source},
    B3: {kind: "series",       ...},
    B4: {kind: "series",       ...},
    B5: {kind: "share",        label, part, whole,             caption, source},
    B6: {kind: "series",       ...}
  }
}
```

Series are downsampled by equal-width time bucketing with a mean per bucket —
stated in `caption` so nobody reads a 48-point line as 48 readings. Assignments:

| Branch | Evidence | Source |
|---|---|---|
| B1 Asset availability | MILL-01 `power_draw_mw`, series | `telemetry_stream.parquet` |
| B2 Ore realisation | `gold_grade_gpt_est` distribution over 1,000 blocks | `geological_block_models.parquet` |
| B3 Processing recovery | `recovery_rate_pct`, daily series | `metallurgical_recovery.parquet` |
| B4 Haulage | TRUCK-08 `payload_tons`, series | `telemetry_stream.parquet` |
| B5 Materials | 17 of 105 SKUs at or below reorder point, share | `inventory_levels.parquet` |
| B6 Safety | fatigue alerts per bucket, series | `fatigue_logs_node.parquet` |

B2 and B5 get a distribution and a share rather than a line because neither has a
time axis. That asymmetry is the honest shape of the data and is left visible.

### 2. Tokens — `docs/ux/tokens.css`

Radius, easing and duration tokens; six branch hues; `.card` gains radius and a
hover lift (tone + border, no shadow); a `.reveal` / `.reveal.in` pair for
scroll entrances; `.bar` grows from 2px hairline to a 24px track with a rounded
fill; `.metric` gains `font-variant-numeric: tabular-nums` so a counting number
does not jitter.

### 3. Motion helpers — `apps/shared/motion.js`

Three functions, shared by both screens and reusable by the other nine later:

- `reveal(root)` — IntersectionObserver adding `.in` to `.reveal` elements in
  document order with a small stagger.
- `countUp(node, to, opts)` — animates a number to its final value.
- `sparkline(values, opts)` — returns inline SVG for a series, with an
  optional draw-in animation.

All timing uses `setInterval`, not `requestAnimationFrame`: rAF does not fire in
the verification browser (`document.visibilityState === "hidden"`), so an
rAF-based animation is one that cannot be checked before it ships.

### 4. Landing — `apps/index.html` + `apps/landing.js`

Hero; a **recorded-window strip** showing the five assets with their real series
and a playhead that sweeps the 2026-01-01 → 2026-06-16 window on an interval,
updating each asset's value to its real reading at that point. It is labelled
"recorded window · replaying" — a scrubber over history, never presented as live.
Then the two application cards, which lift on hover and count their figures up.

### 5. Value — `apps/case/value.html` + `apps/case/value.js`

The 52-cell partition strip as hero, with the running total counting to 52 and
the convergence cell called out. Six branch cards in six hues, each carrying its
mechanism, its magnitude (`$145,000/hr` for B1, `[CLIENT INPUT REQUIRED]` for the
rest, unchanged) and its evidence chart with the source underneath. The APQC
table gains its "overlapping by design" caption and a hue-matched code column.

## Verification

Both screens loaded in the browser at 360 / 414 / 768 / 1024 / 1440, asserting no
container overflow, no console errors, and that every animated value reaches its
final state. `prefers-reduced-motion: reduce` checked separately. Screenshots at
1440 and 414. The build re-run and the bundle regenerated before any of it.

## Out of scope

Rolling the language across the other nine screens; any change to the workspace
application; any new data generation; any change to the catalog or the value
tree's membership.

---

# Revision — messaging and positioning

**Date:** 2026-08-13, after review of the two built screens.

The build landed but the copy argues like an architect. "100 agent nodes", "52
callable entrypoints", "APQC 11.0.3", "3 property graphs" prove the estate
exists; none of them say why it is worth owning. The reader is a mining CEO, and
they are being handed the evidence that convinced the engineer.

## The thesis

**Best practice. Every shift.**

Not "the best performing worker". A worker is a headcount claim, and a headcount
claim in mining is a union and political conversation that this screen cannot
win and does not need to have. Best practice is a *standard*, and unlike a worker
it has a number attached in the client's own data.

The mechanism line is **optimal decisions, 24/7**: the same standard applied at
3am, across a handover, and on the days the best people are not on site.

## Why the thesis is defensible rather than a slogan

The gap between this site's p90 day and its median day, measured over the 167
days the warehouse actually covers, sits inside the range the published research
gives as the available prize:

| Quantity | p90 day vs median day, this site | Published |
|---|---|---|
| Metallurgical recovery | +1.96 pp (92.32 → 94.28 %) | +1–3 pp |
| Crusher feed rate | +8.5 % | throughput +4–8 % |
| Truck payload | +9.1 % | AHS productivity +20 % (WA) |
| Conveyor load | +10.7 % | — |

So the argument runs: the best day is not a capability that has to be bought. It
is already on record, achieved by this site, with this plant and these people.
What is missing is repetition. That reframes the sale from *buy a new capability*
to *stop losing the one you already have*, which is a materially easier thing for
a CEO to believe and a materially harder thing for a competitor to dispute.

**The honesty constraint.** Not all of the gap is capturable — some of it is ore
variability, weather and scheduled work. The screen therefore presents the gap as
the size of the opportunity space, never as a promised recovery, and says so in
the copy. PUMP-104A is excluded from the gap table: its +45 % is a bearing
degrading, not a good day, and it belongs to the downtime story instead.

## External benchmarks

Every external figure carries its publication title, publisher and year on
screen, and lives in a reviewable source file rather than in prose, so a claim
can be traced to a document without reading the markup. Verified figures only:
anything that could not be confirmed against a primary source is recorded in the
source file as excluded, with the reason, so nobody re-adds it later.

Rendered so that external evidence is visibly distinct from the client's own
data. A benchmark is a third party's claim about the industry; a measurement is
this warehouse's claim about this site. Merging the two visually would let a
reader carry McKinsey's authority onto our number, which is the exact move that
makes a CEO stop trusting a deck.

## Progressive disclosure of technical detail

Technical specificity ramps across the five case screens rather than appearing at
full strength on screen 1:

| Screen | Carries | Does not carry |
|---|---|---|
| 1 Proposition | the thesis, the industry condition | any implementation noun |
| 2 The mine today | the measured gap, benchmarks | architecture |
| 3 Value unlock | six value pools, MECE, RoI | entrypoint counts above the fold |
| 4 The solution | swarms, human-in-the-loop, orchestration | SQL |
| 5 The graph | the property graph, the traversals, the SQL | — |

MECE survives the reframe unchanged, because MECE is the consultancy's own house
method rather than a technical artifact — a CEO reads a strict partition as
rigour. What changes is what the partition is *of*: value pools first, with the
entrypoint counts demoted to a supporting figure inside each pool.

## Screen changes

**Landing.** Hero carries the thesis. The three-fact list per door drops
`agent nodes`, `property graphs` and `callable entrypoints` in favour of value
language. The five-machine strip stays — it is the proof that a real plant is
being read — recaptioned as evidence rather than as a feature.

**Value.** Leads with the gap: the site's own number beside the published number.
Each of the six branches is recast as a value pool carrying its mechanism, its
measured gap, its benchmark and its RoI line. A small calculator lets the reader
supply throughput and price and see what one recovery point is worth to them —
every input labelled as theirs, so the screen still never asserts a magnitude it
cannot source. The 52-cell partition and the APQC table move below the value
argument as supporting detail.

**Case screen 1.** Hero states the problem rather than the estate: the knowledge
that produced the best day exists and does not arrive on time. Beneath it, the
four `condition`-themed benchmarks, ordered as an argument — productivity fell,
the data was already being collected and thrown away, the industry is behind its
peers for capital, and buying the technology has so far mostly not paid. The
`$145k` anchor and the discipline it stands for stay. The eight scale tiles and
the D01 latency measurement move to screen 4, which is where a reader has
actually asked how it is built.

**Case screen 2.** Becomes the evidence screen. The four gap metrics are drawn
as ladders rather than repeated as the landing's table, then the two
`gap`-themed benchmarks, then the counted site table and the verbatim persona
quotes as grounding.

**Case screen 4.** Receives the scale tiles and the latency note.

## The ladder

Screen 2 has to make the gap survive contact with the data, and a second table
of the same four numbers would not have. So each metric is drawn as every
recorded day, sorted worst to best.

Sorting discards the calendar deliberately. A time series of these numbers shows
weather, and invites an argument about which week was unusual. Sorted, the median
day falls at the halfway mark and the p90 day at the nine-tenths mark **by
construction** — so the two figures the entire business case rests on can be
pointed at rather than asserted, and the coloured span between the two rules is
the gap itself, drawn.

Constraints the drawing had to meet:

- **The baseline is suppressed and the suppression is printed.** A recovery
  series running 90.9 to 95.1 plotted from zero is a flat grey block. Every
  ladder prints the range it was drawn against, immediately beneath itself.
- **Days above the p90 are shown, dimmed.** They happened; the case does not
  claim them. Omitting them would flatter the drawing.
- **The colour is the value pool**, matched to screen 3, and each ladder names
  its pool beside the metric — a hue that means something stated nowhere is
  decoration.
- **No gaps between bars.** At 167 days a bar is one to four pixels wide, and a
  1px gap aliases into wide bands that read as a pattern in the data.

## The calculator, as built

The value screen prices a recovery point, and the design of that panel is where
the honesty constraint had to be made structural rather than editorial.

A recovery point is not money until three quantities are known: how much ore
goes through the mill, what the ore carries, and what the metal sells for. The
site's own record settles exactly one of them — 167 days of concentrator feed
assays give a median of 1.08 % copper — and is silent on the other two. So the
panel publishes the one conversion it can derive, **108 t of contained copper
per million tonnes milled per point of recovery**, and stops. Throughput and
price are entered by the reader, are never defaulted, and each carries a label
saying whose figure it is and why this repository does not hold it. Until both
are supplied the result reads `[CLIENT INPUT REQUIRED]`.

The panel is laid out in two columns for that reason and not for balance: *what
this site's record settles* on the left, *what only you hold* on the right. The
split is the argument.

Three further constraints, each of which cost a defect before it was found:

- **Contained, not payable.** Smelter payability and treatment and refining
  charges take a cut this repository has no terms for. The figure is stated as
  contained metal and the omission is printed, because an upper bound that
  admits it is one is more useful to a CEO than a number that quietly is not.
- **The working is printed whether or not it evaluates.** A calculator that
  shows only its answer asks to be trusted; this one is meant to be checked.
- **The arithmetic on screen must reproduce.** The panel multiplies by the gap
  the reader can see, not by the float behind it — printing "1.96 points" and
  then returning a total that is not 1.96 × the unit rate is the same defect as
  a gap table whose columns do not subtract.

## Printed precision

Related, and the source of two defects caught in review: a figure's precision is
chosen so the reader's own arithmetic comes out.

Rounding by magnitude alone gave `92.3 %`, `94.3 %` and a gap of `+1.96 pts`,
which the first person to subtract the two columns catches. Where a gap is an
absolute difference, the gap sets the precision for the whole row, and the row
then widens until the displayed columns subtract to the displayed delta. This
lives in `shell.js` rather than per screen, because the landing and the value
screen quote the same recovery gap and a measurement printed two ways across two
screens is the same failure in slower motion.

---

# Revision — the uplift slot, and the evidence base re-verified

Dated 2026-08-13. Two changes, one prompted by the other.

## What the pool cards print

The pool card's headline slot used to hold either a dollar figure or the words
`[CLIENT INPUT REQUIRED]`. In practice that meant five of the six pools printed
the words, which was honest and told a chief executive nothing whatever about
five sixths of the argument. A reader who cannot see a magnitude cannot rank the
pools, and ranking them is the only thing they were going to do with the screen.

The slot now holds a **percentage**, and beside it a **badge naming the class of
evidence** behind it:

| Badge | Means | Pools |
|---|---|---|
| Measured here | this plant's own record, 167 days, ordinary day to best day | B3, B4 |
| Published elsewhere | a third party's study, publisher and year named | B1, B2, B5, B6 |

A percentage is the right unit for this slot for three reasons. It is what both
this site's record and every published study actually measure. It needs neither
a throughput nor a price to mean something, so the card carries a magnitude
without the screen asserting a dollar it cannot source. And it survives a reader
who has not yet settled their commodity assumptions — which, per the standing
instruction not to trip on the type of metal, is every reader on first pass.

The badge is not decoration. *Measured here* and *published elsewhere* are
different classes of evidence, and the difference is the entire argument of these
screens: a number from this site's own 167 days cannot be waved away, and a
number from somebody else's mine can. Marking which is which is what earns the
right to print both on one card.

Where a pool has both, the published range is printed **directly beneath** the
measured figure rather than in a separate block. B3 is the reason: `+1.96 pts`
measured here, sitting immediately above `1–4 pts recovery` published by two
houses. The site's best day is *inside* the range the industry publishes as an
achievable uplift — that is the whole case in two lines, and separating them
would have thrown it away.

Where several publishers measured the same mechanism and disagree, the range
**spans all of them**. B3's throughput reads `2–15%` because BCG's 2026 flagship
says 2–5%, McKinsey's 100-asset study says 8–10%, and McKinsey's own concentrator
case says 10–15%. Quoting only the low end would be selective; quoting only the
high end would be worse.

## Uplift ranges are derived, not typed

The numbers in that slot are not written in JavaScript. Each benchmark entry in
`docs/external-benchmarks.yaml` carries an optional `uplift:` list — the
machine-readable form of numbers that already exist inside its verbatim `figure`
— and the build refuses to emit an uplift whose bounds do not appear in the
quoted text, in digits or in English words. That check exists because a
restatement drifts from its original: somebody widens a range on a screen and
nobody re-reads the sentence it came from. Publishers write "one to three
percentage points" in the same paragraph as "8 to 10 percent", so the checker
reads both forms.

The pool a figure speaks to is also recorded in that file, beside the figure,
rather than in a second map held by the screen. The screen's old `POOL_BENCH`
object could have disagreed with the source file without anything failing.

## Commodity neutrality, applied

Per the standing instruction: the value case names no metal, and money is a
range.

- **The calculator** asks for a throughput and a **price band** — low and high —
  and returns a band. The physical half stays exact, because tonnes of contained
  metal per point of recovery is metallurgy and is commodity-agnostic once the
  metal is not named. The money half is a market, and a market is quoted in
  bands. Printing one figure for both halves would present the weaker half with
  the confidence of the stronger one. The two price fields are sorted before use,
  so a reader who fills them the other way round gets the same answer.
- **The B2 evidence chart** plotted `gold_grade_gpt_est` in g/t while the
  calculator ran on a percent feed assay. It now plots the percent assay and is
  labelled "Estimated grade across the block model". Its caption explicitly
  refuses the comparison a reader might otherwise draw: the block model includes
  waste and the mill only ever sees ore above cut-off, so the two distributions
  are not the same population. That was checked numerically before the change —
  block-model median 0.486% against mill feed median 1.080% — and the difference
  is cut-off, not a discrepancy.
- **Headlines stay off the metal even where the quote cannot.** Deloitte's
  finding is about copper grades and is quoted verbatim; the headline set in
  display type reads "Head grades down ~40% in three decades", because the
  headline is what a reader takes away at a glance and the finding is true of the
  industry rather than of one commodity.

## The evidence base, re-verified

Every URL in `docs/external-benchmarks.yaml` was fetched and its quoted text read
on the publisher's own page on 2026-08-13. Seventeen figures are cited, thirteen
recorded as unverifiable, four recorded as **superseded** — a new category, kept
apart from the rejected ones because these were properly sourced when they were
printed and the distinction matters to anyone reviewing an older screenshot.

Retired at this pass:

- **BCG's 2021 digital-maturity gap (30–40%).** BCG's own January 2026 flagship
  says mining "has gone from near the bottom to the middle of the pack". Printing
  the 2021 gap alongside the 2026 publication would misrepresent the publisher.
- **McKinsey's 2015 productivity decline (3.5%/yr, 28% less efficient).**
  McKinsey's 2022 work restates the same period as "marginal growth of around 1
  percent". Both cannot be printed. Replaced by PwC's current and unambiguous
  finding that output per worker has fallen since 2020.
- **McKinsey's 2018 4–8% throughput / 1–3pp recovery.** Superseded within the
  range by three better-scoped and more recent sources. Its "roughly equivalent
  to opening a new mine without the capital cost" aside is deliberately not
  carried forward: it is the kind of line that makes a deck read as a brochure.
- **McKinsey's ~5% gen-AI EBIT figure.** Replaced by BCG's "60% of companies are
  reaping hardly any material value", which measures the same scepticism from the
  majority side and is the more recent survey.

Newly rejected, and recorded so nobody re-adds them:

- **McKinsey's "Performing under pressure" ($370bn/yr, 17% of the cost base) has
  been withdrawn by its publisher.** The page now reads "The article you are
  looking for is being revised". Not citable in any form until republished.
- **Bain** returns HTTP 403 behind Cloudflare to automated fetch and to a real
  browser alike. No Bain figure has ever been confirmed.
- **WEF is dropped entirely.** The 2017 DTI "$425bn" was rejected for the second
  time — the publisher's own PDF still redirects. The Lighthouse and MINDS cohort
  figures are operator-supplied and survivorship-biased by the award's design.
  One WEF case tagged Mining & Metals turns out to be a hydraulic-support
  *factory*, not a mine; it is recorded as a trap.
- **"Gen AI cut fleet fuel consumption by up to 10 percent"** — the figure is in
  the primary source but attributed there to *traditional* AI models. The
  circulating snippet misattributes it.

The condition section on case screen 1 now carries four publishers across four
different years, so it cannot be read as one house's opinion restated four times.
