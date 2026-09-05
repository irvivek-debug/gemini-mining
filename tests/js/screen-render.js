/* Run one screen the way a browser runs it, and print what it drew.
 *
 *   node tests/js/screen-render.js apps/workspace/handover.html
 *
 * There is no build step here: a screen is an HTML file and the classic script
 * tags it carries, in the order it carries them. So the only way to know what a
 * screen puts in front of a reader is to run it, and the only way to check a
 * claim about the *rendered* page — "exactly one collapsible" — is to have the
 * rendered page. Reading the source cannot answer it: one `'<details ...>'`
 * written in a loop is one occurrence in a file and fourteen on the screen.
 *
 * The environment is deliberately thin. Everything stubbed is stubbed toward
 * the state a headless reader is in — reduced motion on, no layout, no live
 * connection — so nothing here animates, measures or waits, and what is printed
 * is the markup the screen composed rather than a snapshot of an animation.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const { makeDom } = require("./screen-dom.js");

const ROOT = path.join(__dirname, "..", "..");

/* The runtime reply the screens are rendered against. Connected, because that
 * is the state with the most on screen: every block that asks paints its answer
 * rather than staying on "checking". */
const RUNTIME = {
  connected: true,
  expected: 52,
  deployed: Array.from({ length: 52 }, (_, i) => `A${i}`),
  missing: [],
  project: "example-project",
  region: "us-central1",
  /* The server's own words, not a stand-in for them.
   *
   * apps/workspace/workspace.js prints this field under the connection badge,
   * so it is body copy on a screen, and a placeholder here would hide whatever
   * the deployed server actually says. It said "Cloud Run scales to zero" and
   * no gate could see it, because the note this renderer substituted was the
   * one every gate read. Kept in step with apps/workspace/server.py. */
  note:
    "'Deployed' means each agent has an address and answers when it is " +
    "called. Between calls nothing is left running, and that is the intended " +
    "cost behaviour, not a fault.",
};

/* A stand-in for a third-party drawing library.
 *
 * apps/case/graph.html loads cytoscape, which mounts a WebGL canvas into a real
 * element and needs a real one. It is skipped here and this is put in its place,
 * which is honest for what this renderer is for: cytoscape draws into a canvas
 * and composes no markup, so nothing it would have produced is a disclosure, a
 * heading or a sentence. Everything the graph screen writes — the legend, the
 * estate table, the tooltip, the drawer — is written by apps/case/graph.js and
 * is rendered here as it is on every other screen.
 *
 * Chainable, because a graph library's API is chainable: `cy.elements()
 * .removeClass("hit").addClass("faded")` has to keep answering. */
const chainable = () =>
  new Proxy(function () {}, {
    // `then` must stay undefined or an await would treat this as a promise.
    get: (target, key) => (key === "then" ? undefined : chainable()),
    apply: () => chainable(),
  });

const VENDOR_STUBS = { "cytoscape.min.js": () => chainable() };

/** Load a screen, let its promises settle, and hand back everything it drew.
 *
 *  `search` is the query string the screen is opened with, and it defaults to
 *  none so every existing caller is unaffected. It matters because these
 *  screens are configuration, not content: `persona.html?p=P7` and
 *  `swarm.html?s=S12` run the same code over a different row of the catalogue
 *  and draw substantially different pages — one team files two table schemas
 *  inside its drawer and another files fourteen. A gate that only ever renders
 *  the default has checked one of seven roles and one of twelve teams, and has
 *  said nothing at all about the other seventeen.
 */
function renderScreen(screen, search = "") {
  const page = path.join(ROOT, screen);
  const pageHtml = fs.readFileSync(page, "utf8");
  const dir = path.dirname(page);
  const dom = makeDom(pageHtml);

  const noop = () => {};
  class Observer {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  const sandbox = {
    console,
    URLSearchParams,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    requestAnimationFrame: () => 0,
    cancelAnimationFrame: noop,
    IntersectionObserver: Observer,
    ResizeObserver: Observer,
    MutationObserver: Observer,
    EventSource: class {
      addEventListener() {}
      close() {}
    },
    // A reader who has asked not to be animated. Every motion path in these
    // screens has a reduced-motion branch that draws the finished state at
    // once, which is the state worth counting disclosures in.
    matchMedia: (query) => ({
      matches: /prefers-reduced-motion/.test(String(query)),
      addEventListener: noop,
      addListener: noop,
    }),
    document: dom.document,
    /* href carries the search too: a screen that reads its parameter out of
       the full address rather than out of location.search would otherwise see
       a default while location.search says otherwise, and the two would
       disagree inside one render. */
    location: { search, href: `http://localhost/${screen}${search}`, hash: "" },
    history: { pushState: noop, replaceState: noop },
    getComputedStyle: () => ({ getPropertyValue: () => "" }),
    addEventListener: noop,
    removeEventListener: noop,
    print: noop,
    devicePixelRatio: 1,
    innerWidth: 1280,
    innerHeight: 900,
    fetch: () =>
      Promise.resolve({ status: 200, json: () => Promise.resolve(RUNTIME) }),
  };

  const context = vm.createContext(sandbox);
  vm.runInContext("var window = globalThis;", context);
  for (const match of pageHtml.matchAll(/<script src="([^"]+)"><\/script>/g)) {
    const file = path.resolve(dir, match[1]);
    const stub = VENDOR_STUBS[path.basename(file)];
    if (stub) {
      sandbox[path.basename(file).replace(/\.min\.js$/, "")] = stub();
      continue;
    }
    vm.runInContext(fs.readFileSync(file, "utf8"), context, { filename: file });
  }

  /* The page's own markup first, then everything the scripts wrote into it.
   *
   * Mount points do not nest — each id in the markup is written to once, and a
   * node created inside another node's innerHTML gets its own entry only when
   * something later writes into it — so the join is the document. Each piece is
   * balanced markup on its own, which is what lets a reader of this output ask
   * whether one element is nested inside another. */
  return () =>
    [
      pageHtml.replace(/<script\b[\s\S]*?<\/script>/g, ""),
      ...[...dom.registry.values()].map((n) => n.innerHTML),
    ].join("\n");
}

async function main() {
  const screen = process.argv[2];
  if (!screen) {
    console.error(
      "usage: node tests/js/screen-render.js apps/<screen>.html [?p=P7]"
    );
    process.exitCode = 2;
    return;
  }
  const rendered = renderScreen(screen, process.argv[3] || "");
  // The connection blocks resolve through two chained thens; the drawer's
  // placeholder through a third. Draining lets the settled page be printed.
  for (let i = 0; i < 5; i += 1) await new Promise((r) => setImmediate(r));
  process.stdout.write(rendered());
  // Nothing on these screens needs to keep running once it has drawn itself,
  // and an interval left ticking would hold the process open.
  process.exit(0);
}

if (require.main === module) main();

module.exports = { renderScreen };
