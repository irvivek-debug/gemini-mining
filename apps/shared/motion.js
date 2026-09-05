/* Motion primitives shared by every screen.
 *
 * Three rules govern everything here.
 *
 * One: motion is functional. Things enter in reading order so the eye is led
 * down the page; numbers count so the eye lands on the figure that changed;
 * lines draw so a shape is described rather than asserted. Nothing loops and
 * nothing decorates.
 *
 * Two: setInterval, never requestAnimationFrame. rAF does not fire while
 * document.visibilityState is "hidden", which is the state of every automated
 * browser this suite is checked in. An animation that cannot be verified before
 * it ships is an animation nobody has seen.
 *
 * Three: prefers-reduced-motion is honoured by jumping to the final state, not
 * by degrading to a lesser one. A reader who asked for less motion still gets
 * every number and every line.
 */

const REDUCED =
  window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Reveal elements as they scroll into view.
 *
 *  Polled rather than observed. IntersectionObserver delivers its callbacks
 *  from the rendering steps, which a hidden document does not run, so an
 *  observer-driven page renders blank in exactly the browser used to check it.
 *  A rect test on a handful of elements every 120ms costs nothing and works
 *  whether the document is painting or not.
 */
function reveal(root) {
  const nodes = Array.from((root || document).querySelectorAll(".reveal"));
  if (!nodes.length) return;
  if (REDUCED) {
    nodes.forEach((n) => n.classList.add("in"));
    return;
  }

  let stagger = 0;
  const tick = () => {
    const fold = window.innerHeight || document.documentElement.clientHeight;
    let pending = 0;
    nodes.forEach((node) => {
      if (node.classList.contains("in")) return;
      pending += 1;
      // 88% of the fold, not 100: an element revealed at the exact moment its
      // top edge crosses the bottom of the window animates off-screen and the
      // reader arrives after it has finished.
      if (node.getBoundingClientRect().top < fold * 0.88) {
        const delay = (stagger++ % 6) * 60;
        window.setTimeout(() => node.classList.add("in"), delay);
        pending -= 1;
      }
    });
    if (!pending) window.clearInterval(timer);
  };
  const timer = window.setInterval(tick, 120);
  tick();
}

/** Animate a number up to its final value.
 *
 *  opts.decimals, opts.prefix, opts.suffix, opts.duration. The final value is
 *  written by the last frame and also unconditionally at the end, so a tab
 *  that is throttled mid-count still finishes on the right figure rather than
 *  wherever the throttling stopped it.
 */
function countUp(node, to, opts) {
  const o = opts || {};
  const decimals = o.decimals || 0;
  const prefix = o.prefix || "";
  const suffix = o.suffix || "";
  const format = (v) =>
    prefix +
    v.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }) +
    suffix;

  if (REDUCED) {
    node.textContent = format(to);
    return;
  }

  const duration = o.duration || 900;
  const step = 40;
  const steps = Math.max(1, Math.round(duration / step));
  let i = 0;
  node.textContent = format(0);
  const timer = window.setInterval(() => {
    i += 1;
    if (i >= steps) {
      window.clearInterval(timer);
      node.textContent = format(to);
      return;
    }
    // Cubic ease-out: fast to most of the value, then settling. The eye reads
    // the settle as the number arriving rather than as the number stopping.
    const t = 1 - Math.pow(1 - i / steps, 3);
    node.textContent = format(to * t);
  }, step);
}

/** Every .count element under root, animated to its data-count value. */
function countAll(root) {
  Array.from((root || document).querySelectorAll("[data-count]")).forEach((n) =>
    countUp(n, Number(n.getAttribute("data-count")), {
      decimals: Number(n.getAttribute("data-decimals") || 0),
      prefix: n.getAttribute("data-prefix") || "",
      suffix: n.getAttribute("data-suffix") || "",
    })
  );
}

/** Inline SVG for a series. Returns markup; the caller decides where it lands.
 *
 *  values may contain nulls — a bucket of the source table that held no
 *  readings. The line breaks there rather than joining across it, because a
 *  straight segment drawn over a gap is a measurement the warehouse never
 *  returned.
 *
 *  pathLength="1" normalises the stroke so the draw-in animation is pure CSS
 *  and needs no getTotalLength call, which would mean measuring a node that is
 *  not in the document yet.
 */
function sparkline(values, opts) {
  const o = opts || {};
  const w = 100;
  const h = o.height || 34;
  const pad = 3;
  const colour = o.colour || "var(--accent)";
  const present = values.filter((v) => v !== null && v !== undefined);
  if (present.length < 2) return "";

  const lo = o.min !== undefined ? o.min : Math.min(...present);
  const hi = o.max !== undefined ? o.max : Math.max(...present);
  const span = hi - lo || 1;
  const x = (i) => (values.length === 1 ? 0 : (i / (values.length - 1)) * w);
  const y = (v) => h - pad - ((v - lo) / span) * (h - pad * 2);

  let line = "";
  let open = false;
  values.forEach((v, i) => {
    if (v === null || v === undefined) {
      open = false;
      return;
    }
    line += `${open ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)} `;
    open = true;
  });

  // The area is a reading aid, not a second series: it is the same path closed
  // to the baseline at a tenth of the opacity. It is omitted when the line is
  // broken, because a fill across a gap would colour in data that is missing.
  const gaps = values.length !== present.length;
  const first = values.findIndex((v) => v !== null && v !== undefined);
  let last = -1;
  values.forEach((v, i) => {
    if (v !== null && v !== undefined) last = i;
  });
  const area = gaps
    ? ""
    : `<path class="area" d="${line}L${x(last).toFixed(2)},${h} L${x(first).toFixed(
        2
      )},${h} Z" fill="${colour}" opacity="0.10"></path>`;

  return (
    `<svg class="spark reveal" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" ` +
    `width="100%" height="${h}" role="img" aria-label="${o.label || "series"}">` +
    area +
    `<path class="line" pathLength="1" d="${line.trim()}" fill="none" ` +
    `stroke="${colour}"></path>` +
    "</svg>"
  );
}
