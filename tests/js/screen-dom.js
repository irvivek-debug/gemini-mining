/* A document small enough to reason about, for running a screen's own scripts.
 *
 * These screens are classic <script src> tags with no build step, so the only
 * honest way to find out what one of them puts on the page is to run it. This
 * is not a browser and does not pretend to be: it resolves ids, keeps text, and
 * forgets the ids belonging to a node whose innerHTML was replaced — which is
 * exactly the fault that would occur if two mounts shared one element.
 *
 * It lives in its own file because two callers need it. tests/js/handover.test.js
 * runs the workspace pages against a fake EventSource to watch the stream
 * lifecycle, and tests/js/screen-render.js runs any screen once and prints what
 * it drew, which is what tests/test_screen_copy.py counts disclosures in.
 */

/** Every tag carrying an id, with the class it was written with.
 *
 *  The class comes along because on the workspace pages it is load-bearing: the
 *  block that says whether the agents are reachable is read as much from its
 *  frame as from its badge, and a harness that dropped the class on the floor
 *  would let a ✓ READY render inside the amber absence box and call it passing.
 */
function tagsIn(html) {
  return [...String(html).matchAll(/<[a-zA-Z][^>]*>/g)]
    .map((match) => {
      const id = /\bid="([^"]+)"/.exec(match[0]);
      const cls = /\bclass="([^"]*)"/.exec(match[0]);
      return id ? { id: id[1], className: cls ? cls[1] : "" } : null;
    })
    .filter(Boolean);
}

function idsIn(html) {
  return tagsIn(html).map((tag) => tag.id);
}

function makeDom(pageHtml) {
  const registry = new Map();
  const owned = new Map();

  function node(id) {
    const self = {
      id,
      className: "",
      tagName: "DIV",
      style: {},
      dataset: {},
      _html: "",
      _text: "",
      children: [],
      handlers: {},
      get innerHTML() {
        return self._html;
      },
      set innerHTML(value) {
        // Replacing a node's contents destroys whatever ids were in them. A
        // real DOM does this; a harness that did not would let two mounts share
        // one element and call it working.
        (owned.get(self) || []).forEach((id_) => registry.delete(id_));
        const tags = tagsIn(value);
        owned.set(
          self,
          tags.map((tag) => tag.id)
        );
        tags.forEach((tag) => (ensure(tag.id).className = tag.className));
        self._html = String(value);
        // A browser reparses on assignment, so setting innerHTML changes what
        // textContent reads back. Code that writes markup and then reads text
        // must see the same fact both ways, or a stub would pass on behaviour
        // a browser does not have.
        self._text = String(value).replace(/<[^>]*>/g, "");
        self.children = [];
      },
      get textContent() {
        return self._text;
      },
      set textContent(value) {
        self._text = String(value);
      },
      appendChild(child) {
        self.children.push(child);
        return child;
      },
      prepend(child) {
        self.children.unshift(child);
        return child;
      },
      addEventListener(type, fn) {
        (self.handlers[type] = self.handlers[type] || []).push(fn);
      },
      removeEventListener() {},
      click() {
        (self.handlers.click || []).forEach((fn) => fn({}));
      },
      focus() {},
      scrollIntoView() {},
      setAttribute() {},
      removeAttribute() {},
      getAttribute: () => null,
      classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
      getBoundingClientRect: () => ({
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: 0,
        height: 0,
      }),
      /* An id selector resolves; anything else does not. Screens reach for
       * `#composer` inside a panel they have just written, and answering null
       * there is the difference between a screen that renders and one that
       * throws. A class or tag selector is not resolvable from a registry keyed
       * by id, so it keeps saying so rather than guessing. */
      querySelector: (selector) =>
        /^#[\w-]+$/.test(String(selector))
          ? registry.get(String(selector).slice(1)) || null
          : null,
      querySelectorAll: () => [],
    };
    return self;
  }

  function ensure(id) {
    if (!registry.has(id)) registry.set(id, node(id));
    return registry.get(id);
  }

  tagsIn(pageHtml).forEach((tag) => (ensure(tag.id).className = tag.className));

  const body = node("body");
  const document = {
    title: "",
    body,
    documentElement: node("html"),
    getElementById: (id) => registry.get(id) || null,
    createElement: () => node(null),
    createTextNode: () => node(null),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
  };
  return { document, registry };
}

module.exports = { tagsIn, idsIn, makeDom };
