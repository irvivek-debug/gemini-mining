"""Gate: every screen speaks plainly, and hides its machinery at the end.

The instruction was explicit — a functional reader gets plain language and
tables, and technical detail goes at the end behind a collapsible. Both halves
are checkable: the jargon is a fixed list, and the drawer is a fixed component.

The check is on the *visible* text of each screen — what the markup shows and
what the JS puts on the page — and it deliberately excludes two things.

The first is the technical drawer, which is where the jargon is supposed to be.
That means the ``technicalDrawer(...)`` call and the ``drawerBody()`` function
each screen writes to fill it. Excluding only the call, as an earlier draft of
this file did, was wrong in a way that mattered: every screen composes its
drawer as ``technicalDrawer(drawerBody(), hint)``, so the jargon the drawer is
built to hold lives in that function and nowhere near the call.

The second is everything that never reaches a reader — comments, and, in JS,
identifiers. ``row.p90``, ``g.traversal`` and ``catalog.by_apqc_code`` are field
names in window.MINING_DATA. A screen cannot rename them and a reader never
sees them, so the JS half of a screen is scanned through its string literals,
with ``${...}`` interpolations removed. HTML is scanned whole, because an id or
a class name there is cheap to keep plain and a title or a placeholder attribute
is read out loud by a screen reader.

Absence is only half a gate. A screen can satisfy "no jargon" by deleting the
fact, or by inventing a private synonym for it, and both are worse than the
jargon. So two further checks run alongside: the plain phrases must be the ones
apps/shared/plain.js publishes, and the drawer must still name what the body
gave up.
"""
import functools
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
APPS = REPO / "apps"
PLAIN_JS = APPS / "shared" / "plain.js"

SCREENS = {
    "apps/index.html": ["apps/landing.js"],
    "apps/case/index.html": ["apps/case/proposition.js"],
    "apps/case/scenario.html": ["apps/case/scenario.js"],
    "apps/case/value.html": ["apps/case/value.js"],
    "apps/case/solution.html": ["apps/case/solution.js"],
    "apps/case/graph.html": ["apps/case/graph.js"],
    # hitl.js is the sign-off sheet. It is raised from the agent-teams screen
    # and is never navigated to, so its copy has no screen of its own to be
    # checked on — and it was the one surface in this application still
    # explaining itself in column names.
    # workspace.js is on three of these four screens and writes a great deal of
    # what they show — the agent card, the roster, the scenario paragraph. Its
    # absence from this list is how "raises a mandatory HITL approval request"
    # reached the agent-teams screen with the suite green. Every script tag a
    # screen carries belongs here; the list is checked against the markup below.
    "apps/workspace/index.html": [
        "apps/workspace/workspace.js",
        "apps/workspace/cockpit.js",
    ],
    "apps/workspace/value.html": [
        "apps/workspace/agent-card.js",
        "apps/workspace/value.js",
    ],
    "apps/workspace/swarm.html": [
        "apps/workspace/workspace.js",
        "apps/workspace/hitl.js",
        "apps/workspace/swarm.js",
    ],
    # chat.js writes most of what a reader of the role page actually reads, and
    # persona-data.js writes the sentence under every agent on it.
    "apps/workspace/persona.html": [
        "apps/workspace/router.js",
        "apps/workspace/persona-data.js",
        "apps/workspace/agent-card.js",
        "apps/workspace/persona-panel.js",
        "apps/workspace/agent-stream.js",
        "apps/workspace/chat.js",
        "apps/workspace/persona.js",
    ],
    "apps/workspace/handover.html": [
        "apps/workspace/agent-stream.js",
        "apps/workspace/workspace.js",
        "apps/workspace/handover.js",
    ],
}

# Words a functional reader should not have to meet in body copy. Each is
# allowed inside the technical drawer, which is what the drawer is for.
JARGON = [
    # Both spellings. The spaced one is what actually reached a screen — "of 52
    # entry points placed" — while the gate reported the term gone because it
    # only knew the closed-up form.
    "entrypoint", "entry point", "entry points",
    "HITL", "human-in-the-loop", "traversal",
    "Pattern A", "Pattern B", "value branch", "APQC", "blast radius",
    "p90", "model tier",
]

# Which jargon each screen carried, and therefore which plain phrase from
# apps/shared/plain.js has to be doing that word's job now. Keys are the JARGON
# map's own keys, so the phrases are never retyped here: a screen that invents
# its own synonym fails, and so does a screen that simply deleted the idea.
PLAIN_INSTEAD = {
    "apps/index.html": ["p90", "median"],
    "apps/case/index.html": ["hitl"],
    "apps/case/scenario.html": ["p90", "median"],
    "apps/case/value.html": ["apqc code", "value branch"],
    "apps/case/solution.html": ["swarm", "pattern a", "pattern b", "hitl"],
    # "node" and "edge" were listed here and proved nothing: their plain words
    # are "machine" and "link", both of which occur in ordinary sentences on a
    # screen about mining equipment, so the check passed whatever the screen
    # did with the ontology. "blast radius" proved nothing either once the
    # screen stopped typing its phrase and started reading it out of plain.js.
    # All three are covered below by tests that can actually fail.
    "apps/case/graph.html": ["traversal"],
    "apps/workspace/index.html": ["entrypoint", "hitl", "apqc code", "value branch"],
    # "swarm" is not on the banned list above, because swarm.html is a file
    # name and by_swarm is a field of the catalogue. What can be demanded is
    # that the screen calls the thing what the nav calls it.
    "apps/workspace/swarm.html": ["swarm", "traversal", "hitl"],
    "apps/workspace/handover.html": ["swarm"],
}

# What each drawer must still name. These are the expressions that put the fact
# on the page, not the fact itself: asserting on "D01" or on "4.6.1" would pass
# on a comment, and asserting on a rendered figure would pin a measurement this
# repository is free to regenerate.
DRAWER_KEEPS = {
    "apps/index.html": ["r.source", "b.id"],
    "apps/case/index.html": ["b.url", "quote.source_line"],
    # u.why is the build's own sentence under each figure the local files cannot
    # settle. The block on the screen says it in the reader's words; the drawer
    # keeps the sentence it was rewritten from, so the rewrite is checkable.
    "apps/case/scenario.html": ["r.source", "p.code", "u.why"],
    "apps/case/value.html": ["b.apqc", "b.code", "info.agents"],
    "apps/case/solution.html": ["a.pattern", "a.model_tier", "a.agent_id", "s.specialists"],
    # G.source is the paragraph the build writes about where this graph came
    # from — two paths, the dataset and the product. The footer says it in the
    # reader's words; the drawer keeps it as written.
    "apps/case/graph.html": ["g.sql", "g.traversal", "g.bigquery_graph", "G.source"],
    "apps/workspace/index.html": ["a.persona", "a.apqc_code", "a.model_tier", "WS.approval.table"],
    "apps/workspace/swarm.html": [
        "coord.apqc_code", "a.model_tier", "drawerMethod(current)", "swarmInputs()",
        # The shell instruction, the semantics file and the model id that came
        # off the unverified band.
        "drawerFlags(members)",
    ],
    "apps/workspace/handover.html": [
        "S12.apqc_code", "a.model_tier", "a.source_tables", "drawerFlags(members)",
    ],
    "apps/workspace/persona.html": ["a.model_tier", "a.apqc_code", "branchesOf("],
}

# Counts belong to the catalogue, not to a heading. Spelling one out in an <h1>
# is the same defect as typing it as a digit, and harder to notice going stale.
# "one" is left out: "one point of recovery" is a unit, not a tally.
COUNT_WORDS = (
    "two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty "
    "fifty sixty seventy eighty ninety hundred"
).split()


# ---------------------------------------------------------------- extraction

def _strip_js_comments(text):
    """Block comments and whole-line // comments.

    Only lines that *begin* with // are taken, so the `https://` inside a
    benchmark URL survives — it is on screen, and it should be checked.
    """
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", " ", text)


def _strip_balanced_call(text, opener):
    """Remove every `opener…)` span, matching the parenthesis rather than guessing.

    A regex stopping at the first `)` would leave the arguments of
    `technicalDrawer(drawerBody(), hint)` behind, which is most of the point.
    """
    out = []
    i = 0
    while True:
        at = text.find(opener, i)
        if at < 0:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:at])
        depth = 0
        j = at + len(opener) - 1
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        i = j + 1


# The drawer's own contents. Each screen writes them in one top-level function,
# which in this codebase closes on a brace in column one. The name is the
# declaration: a function called drawerBody(), or drawerMethod() where the
# builder is shared across screens, writes drawer copy and nothing else. That
# convention is what lets a shared file like apps/workspace/workspace.js be
# scanned as body copy on three screens while the block of SQL it renders into
# the drawer is read as what it is.
DRAWER_BUILDER = re.compile(r"(?ms)^function drawer[A-Z_]?\w*\s*\(.*?^\}")

STRING_LITERAL = re.compile(
    r"'(?:[^'\\\n]|\\.)*'"
    r"|\"(?:[^\"\\\n]|\\.)*\""
    r"|`(?:[^`\\]|\\.)*`",
    re.S,
)


def _interpolations_out(chunk):
    """`${esc(row.label)}` is an identifier, not a word the reader meets."""
    previous = None
    while previous != chunk:
        previous = chunk
        chunk = re.sub(r"\$\{[^{}]*\}", " ", chunk)
    return chunk


def visible_js(text):
    text = _strip_js_comments(text)
    text = _strip_balanced_call(text, "technicalDrawer(")
    text = re.sub(DRAWER_BUILDER, " ", text)
    # Joined on a single space, not on a newline. A sentence in this codebase is
    # routinely built as `"…records. The " + "best day is the …"`, and a
    # separator that breaks lines would hide every phrase that spans a `+`.
    return " ".join(
        _interpolations_out(m.group(0)[1:-1]) for m in STRING_LITERAL.finditer(text)
    )


DRAWER_OPEN = re.compile(r"<details\b[^>]*\bclass=\"[^\"]*\bdrawer\b[^\"]*\"[^>]*>")
DETAILS_TOKEN = re.compile(r"<details\b[^>]*>|</details>")


def _strip_drawer_markup(text):
    """Take out the technical drawer, and only the technical drawer.

    The exemption exists so the drawer may hold the jargon the body gave up. It
    used to be written as ``class="…tbl…"``, which is the class every
    collapsible in this codebase carries, so any collapsible anyone added became
    a jargon-free zone by virtue of being a collapsible. The drawer is the one
    that carries ``drawer``, which is technicalDrawer()'s own signature.

    Nested, because the drawer holds collapsibles of its own — the table schemas
    the agent-teams and handover screens file inside it — and a non-greedy match
    would stop at the first ``</details>`` and leave the rest of the drawer
    being read as body copy.
    """
    out = []
    at = 0
    while True:
        start = DRAWER_OPEN.search(text, at)
        if not start:
            out.append(text[at:])
            return "".join(out)
        out.append(text[at : start.start()])
        depth = 0
        for token in DETAILS_TOKEN.finditer(text, start.start()):
            depth += -1 if token.group(0).startswith("</") else 1
            if depth == 0:
                at = token.end()
                break
        else:
            return "".join(out)


def visible_html(text):
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S)
    return _strip_drawer_markup(text)


def visible_text(paths):
    """Everything the screen shows, minus what is inside a technical drawer.

    Whitespace is collapsed last, so a phrase broken across a line of markup
    reads as the one phrase it is on the page.
    """
    parts = []
    for path in paths:
        source = (REPO / path).read_text()
        parts.append(visible_html(source) if path.endswith(".html") else visible_js(source))
    return re.sub(r"\s+", " ", " ".join(parts))


def drawer_text(paths):
    """The other half: only what the drawer holds.

    Exactly the two regions visible_text() takes out — the drawerBody function
    and the technicalDrawer call — so the two halves cannot both be satisfied by
    a fact sitting in neither.
    """
    parts = []
    for path in paths:
        source = _strip_js_comments((REPO / path).read_text())
        parts.extend(DRAWER_BUILDER.findall(source))
        rest = DRAWER_BUILDER.sub(" ", source)
        for match in re.finditer(r"technicalDrawer\(", rest):
            depth = 0
            j = match.end() - 1
            while j < len(rest):
                if rest[j] == "(":
                    depth += 1
                elif rest[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            parts.append(rest[match.start() : j + 1])
    return "\n".join(parts)


def plain_block(name):
    """One `var NAME = {...};` map out of apps/shared/plain.js, parsed not retyped."""
    source = PLAIN_JS.read_text()
    block = re.search(rf"var {name} = \{{(.*?)\n\}};", source, re.S)
    assert block, f"apps/shared/plain.js no longer declares {name}"
    pairs = re.findall(r"(?m)^\s*\"?([A-Za-z0-9_ -]+?)\"?:\s*\"([^\"]+)\"", block.group(1))
    assert pairs, f"the {name} map parsed to nothing"
    return dict(pairs)


def graph_json():
    import json

    return json.loads((APPS / "shared" / "data" / "graph.json").read_text())


def plain_map():
    """The JARGON map out of apps/shared/plain.js, parsed rather than retyped."""
    source = PLAIN_JS.read_text()
    block = re.search(r"var JARGON = \{(.*?)\n\};", source, re.S)
    assert block, "apps/shared/plain.js no longer declares a JARGON map"
    pairs = re.findall(r"(?m)^\s*\"?([a-z0-9 -]+?)\"?:\s*\"([^\"]+)\"", block.group(1))
    assert pairs, "the JARGON map parsed to nothing"
    return dict(pairs)


# -------------------------------------------------------------------- checks

def test_the_screen_list_holds_every_script_a_screen_loads():
    """The omission that let jargon ship green, made impossible to repeat.

    workspace.js writes the agent card, the roster and the scenario paragraph on
    three of the four workspace screens, and it was not in SCREENS. Nothing in
    this file noticed, because everything in this file starts from SCREENS. So
    the list is checked against the markup: the screen's own scripts are read out
    of its <script src> tags, and any that this file does not scan is a hole.

    ``shared/`` is out of scope on purpose. plain.js is where the jargon is
    *defined* — the JARGON map's keys are the banned words — and shell.js is the
    chrome, which is checked by the nav and pill tests below rather than by
    reading it as one screen's copy.
    """
    problems = []
    for screen, scripts in SCREENS.items():
        markup = (REPO / screen).read_text()
        folder = pathlib.Path(screen).parent
        for src in re.findall(r'<script[^>]*\bsrc="([^"]+)"', markup):
            if src.lstrip("./").startswith("shared/"):
                continue
            path = str((folder / src).as_posix())
            if path not in scripts:
                problems.append(f"{screen}: loads {src} and this file never reads it")
    assert not problems, "screens loading unchecked copy:\n" + "\n".join(problems)


@functools.lru_cache(maxsize=None)
def rendered(screen, search=""):
    """What the screen actually draws, by running it.

    Counting the string ``technicalDrawer(`` in source text, as this file used
    to, cannot fail on the thing it exists to prevent: fourteen extra
    collapsibles pass it untouched because none of them is written by calling
    that function, and one ``'<details>'`` written inside a loop is one
    occurrence in a file and ten on the page. There is no build step here, so
    the screen is run — its own script tags, in its own order — and the markup
    it composed is what gets counted.

    ``search`` is the query string the screen is opened with. Two of these
    screens are configuration rather than content — the same code over a
    different row of the catalogue — so rendering only the default checked one
    of seven roles and one of twelve teams and said nothing about the other
    seventeen. ``?s=S12`` files fifteen table schemas inside its drawer where
    the default files five.
    """
    import subprocess

    result = subprocess.run(
        ["node", str(REPO / "tests" / "js" / "screen-render.js"), screen, search],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{screen}{search} did not render:\n{result.stderr[-2000:]}"
    )
    return result.stdout


@functools.lru_cache(maxsize=None)
def bundle():
    """window.MINING_DATA, out of the browser file the screens actually load."""
    import json

    text = (APPS / "shared" / "data" / "bundle.js").read_text()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


@functools.lru_cache(maxsize=None)
def parameterisations(screen):
    """Every query string a screen has to be checked at, read not retyped.

    The roles come from the personas the bundle declares and the teams from the
    agents filed as coordinators, which is exactly how persona.js and swarm.js
    decide what is a valid parameter. A role or a team added to the catalogue
    therefore joins these gates on its own; a list typed here would not.
    """
    if screen.endswith("persona.html"):
        return tuple(f"?p={code}" for code in sorted(bundle()["personas"]["personas"]))
    if screen.endswith("swarm.html"):
        return tuple(
            f"?s={a['agent_id']}"
            for a in sorted(bundle()["catalog"]["agents"], key=lambda a: a["agent_id"])
            if a.get("swarm_role") == "coordinator"
        )
    return ("",)


def renderings(screen):
    """(what to call it in a failure, what it drew) for every parameterisation."""
    return [
        (screen + search, rendered(screen, search))
        for search in parameterisations(screen)
    ]


def disclosures(html):
    """Every collapsible a reader meets, with its summary, outermost only.

    Depth matters. A screen's one technical drawer is allowed to hold whatever
    it likes, including further collapsibles — the agent-teams screen files
    every table the team reads inside it, which is exactly where the client
    asked for that material. What the instruction forbids is a second thing to
    open *beside* the drawer, so what is counted is the ones at the top.
    """
    found = []
    depth = 0
    for match in re.finditer(r"<details\b[^>]*>|</details>", html):
        if match.group(0).startswith("</"):
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            summary = re.search(
                r"<summary[^>]*>(.*?)</summary>", html[match.start() :], re.S
            )
            label = re.sub(r"<[^>]*>", " ", summary.group(1)) if summary else ""
            found.append((match.group(0), re.sub(r"\s+", " ", label).strip()))
        depth += 1
    return found


def test_every_screen_ends_with_exactly_one_technical_drawer():
    problems = []
    for screen in SCREENS:
        for opened, html in renderings(screen):
            found = disclosures(html)
            if len(found) != 1:
                listed = "\n".join(f"      {tag} — {label!r}" for tag, label in found)
                problems.append(
                    f"{opened} renders {len(found)} collapsibles; it must render one:\n{listed}"
                )
                continue
            tag, label = found[0]
            if "drawer" not in tag or not label.startswith("Technical detail"):
                problems.append(
                    f"{opened}: its one collapsible is not the technical drawer: {tag} — {label!r}"
                )
    assert not problems, "collapsibles a reader has to open:\n" + "\n".join(problems)


def test_the_drawer_is_the_last_thing_on_the_screen():
    """Concatenated with the footer, in one expression, so it cannot float up.

    Counting the drawers says nothing about where they are. The one structural
    fact worth pinning is that the drawer and the provenance footer are written
    together — a drawer emitted halfway up a screen is a screen that has put its
    machinery back in the reader's way.
    """
    for screen, scripts in SCREENS.items():
        sources = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        assert re.search(r"technicalDrawer\([^;]*provenance\(", sources, re.S), (
            f"{screen} does not render its drawer immediately before the footer"
        )


def test_only_the_technical_drawer_is_exempt_from_the_rules_below():
    """A collapsible is not a licence; the drawer is.

    The exemption was written as the class every collapsible in this codebase
    carries, so anything anyone hid behind a <details> stopped being read at
    all — which is the opposite of the instruction it was serving. It is the
    drawer, and its contents including any collapsible of its own, that the
    body-copy rules do not apply to.
    """
    body = "<p>p90 at the entry point</p>"
    drawer = (
        '<details class="tbl drawer"><summary>Technical detail</summary>'
        '<div class="drawer-body"><p>p90 at the entry point</p>'
        '<details class="tbl"><summary>a table</summary><p>traversal</p></details>'
        "</div></details>"
    )
    other = (
        '<details class="tbl pblock-jobs"><summary>What you are trying to get done</summary>'
        "<p>p90 at the entry point</p></details>"
    )
    assert "p90" not in visible_html(drawer), "the drawer stopped being exempt"
    assert "traversal" not in visible_html(drawer), (
        "a collapsible inside the drawer is still the drawer"
    )
    assert "p90" in visible_html(body + drawer), "the body around a drawer went missing"
    assert "p90" in visible_html(other), (
        "a collapsible that is not the drawer is exempt from the jargon rules"
    )


def test_no_jargon_survives_outside_the_drawer():
    problems = []
    for screen, scripts in SCREENS.items():
        text = visible_text([screen] + scripts)
        for term in JARGON:
            if re.search(rf"\b{re.escape(term)}\b", text, re.I):
                problems.append(f"{screen}: {term}")
    assert not problems, "jargon left in body copy:\n" + "\n".join(problems)


# --------------------------------------------------- the machine vocabulary
#
# JARGON above is fourteen hand-curated *concepts*. It cannot express, and no
# amount of adding to it will express, the class of thing that kept reaching
# these screens: the names the machinery calls itself. A shell instruction
# ("Re-run scripts/build_app_data.py with BigQuery credentials"), a dataset
# identifier ("a three-row sample of fleet_vehicles"), a product ("BigQuery
# settles it") — each one shipped with the suite green, because a curated word
# list only ever knows the words somebody already noticed.
#
# So this half of the gate is a shape, not a list:
#
#   path        anything with a slash and a file extension
#   identifier  anything carrying an underscore — snake_case is not English,
#               and a dotted tail comes with it so a qualified name
#               (mining_agents.catalog.definitions) is one token, not three
#   product     a short, explicit list; a brand has no shape to match on
#
# and it runs over the *rendered* screen rather than over source. That matters
# twice. It is how a token that arrives through a data field — facts.json's
# `why`, graph.json's `source`, the runtime reply's `note` — is seen at all, by
# the same channel that hid "HITL" in accountable_for. And it is what makes the
# false positives the finding warned about impossible by construction: a
# <script src>, a class name and an id are attributes, and attributes are gone
# with the tags; an HTML comment is gone with visible_html.
MACHINE = [
    ("path", re.compile(r"[\w*.-]+(?:/[\w*.-]+)+\.[a-z]{2,8}\b")),
    ("identifier", re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+(?:\.[A-Za-z][A-Za-z0-9_]*)*\b")),
    ("product", re.compile(
        r"\b(?:BigQuery ML|BigQuery|BQML|Vertex AI|Cloud Run|Cloud Storage|"
        r"Firestore|Dataform|Looker|Parquet|FastAPI|Cytoscape)\b"
    )),
]


def machine_tokens(run):
    """Every machine token in one run of text, and what is left around them.

    Blanked in place rather than removed, so what comes back is the sentence the
    token was sitting in with a hole where it was. That remainder is the whole
    test: a screen is allowed to *name* a file, and is not allowed to talk in
    file names.
    """
    found = []
    rest = run
    for kind, pattern in MACHINE:
        for match in pattern.finditer(rest):
            found.append((kind, match.group(0)))
        rest = pattern.sub(lambda m: " " * len(m.group(0)), rest)
    return found, rest


# A word left beside a token once the token is blanked. Two letters or fewer is
# a separator or an article, not a sentence — "of", "in", "at". Three is a
# sentence starting.
#
# Except for the handful that say *where inside* a named source: "…md line
# 1069", "…md section 1". Those are part of the citation, not prose around it,
# and the list is kept this short deliberately — none of it weakens the rule,
# because every sentence this gate exists to catch carries several other words.
CITATION_WORDS = {
    "line", "lines", "page", "pages", "row", "rows",
    "section", "sections", "column", "columns",
}
WORD = re.compile(r"[A-Za-z]{3,}")


def reads_as_prose(rest):
    """Is what surrounds the blanked token a sentence, or a citation?"""
    return any(word.lower() not in CITATION_WORDS for word in WORD.findall(rest))

TEXT_RUN = re.compile(r"<[^>]*>")


def body_runs(html):
    """The rendered screen as the runs of text a reader actually reads.

    Split on tags, which throws away every attribute — so a class name, an id
    and a <script src> are not body copy here, because they are not body copy on
    the page either. Entities are decoded first: `&amp;` is an ampersand to a
    reader and would otherwise read as a word.
    """
    import html as html_module

    return [
        run for run in TEXT_RUN.split(html_module.unescape(html)) if run.strip()
    ]


def test_no_machine_vocabulary_survives_outside_the_drawer():
    """A screen may name a file. It may not speak in file names.

    The rule is on the shape of the sentence, not on a list of words. A run of
    text that *is* a machine token — the provenance footer's `<dd>`, the source
    line under a chart — is a citation, and a citation is how this repository
    lets a sceptic go and look. A run that puts a machine token inside a
    sentence has handed a shift supervisor a developer's shell history, and the
    fix is always the same one: keep the fact in the reader's words, move the
    path into the drawer, where all of this is allowed.
    """
    problems = []
    for screen in SCREENS:
        for opened, html in renderings(screen):
            for run in body_runs(visible_html(html)):
                found, rest = machine_tokens(run)
                if not found or not reads_as_prose(rest):
                    continue
                said = ", ".join(sorted({f"{text} ({kind})" for kind, text in found}))
                problems.append(
                    f"{opened}: {said}\n      in body copy: {run.strip()[:160]!r}"
                )
    assert not problems, (
        "the machinery's own vocabulary in body copy:\n" + "\n".join(problems)
    )


def test_the_machine_vocabulary_rule_is_about_sentences_not_words():
    """What the rule above does and does not fire on, pinned so it stays honest.

    Written because a gate this broad is only useful if its edges are known. A
    bare citation passes; the same token in a sentence fails; the drawer is
    exempt whatever it holds; and an attribute is not body copy.
    """
    citation = '<dd class="mono">data/generated/telemetry_stream.parquet</dd>'
    sentence = "<p>Re-run scripts/build_app_data.py with BigQuery credentials.</p>"
    drawer = (
        '<details class="tbl drawer"><summary>Technical detail</summary>'
        '<div class="drawer-body"><p>Re-run scripts/build_app_data.py with '
        "BigQuery credentials.</p></div></details>"
    )
    attribute = '<link rel="stylesheet" href="shared/app.css"><p>Nothing here.</p>'

    def fires(markup):
        for run in body_runs(visible_html(markup)):
            found, rest = machine_tokens(run)
            if found and reads_as_prose(rest):
                return True
        return False

    assert not fires(citation), "a bare citation is not a sentence"
    assert fires(sentence), "the rule stopped seeing a path inside a sentence"
    assert not fires(drawer), "the drawer stopped being exempt"
    assert not fires(attribute), "the rule fired on a <script src>-style attribute"
    assert fires("<p>Only 5 of the fleet_vehicles are known.</p>"), (
        "the rule stopped seeing a bare snake_case identifier in a sentence"
    )
    assert not fires("<p>docs/personas-and-value-tree.md section 1</p>"), (
        "a citation may say where inside the source it points"
    )
    assert fires("<p>Rooted, in docs/personas-and-value-tree.md, on cost.</p>"), (
        "the citation words became a licence for a sentence"
    )


def test_the_plain_words_are_the_shared_ones():
    """Deleting an idea also removes its jargon. This is what stops that.

    The phrases are read out of apps/shared/plain.js, so a screen that reaches
    for its own wording — "agent squad", "impact trace" — fails here even though
    it passes the check above. Two vocabularies for one estate is the thing
    plain.js exists to prevent.
    """
    words = plain_map()
    problems = []
    for screen, keys in PLAIN_INSTEAD.items():
        text = visible_text([screen] + SCREENS[screen])
        for key in keys:
            assert key in words, f"plain.js has no entry for {key!r}"
            if words[key].lower() not in text.lower():
                problems.append(f"{screen}: says nothing about {key!r} ({words[key]!r})")
    assert not problems, "the plain phrase never replaced the jargon:\n" + "\n".join(problems)


def test_no_screen_retypes_a_phrase_plain_js_publishes():
    """One estate, one wording, and one copy of each sentence that carries it.

    "what else stops if this stops" was typed into the graph screen's lede, into
    the tool note on the solution screen, and declared in plain.js — three copies
    of one phrase, two of them free to drift and nothing to notice when they did.
    A screen that wants the phrase calls plainTraversal(); a screen that types it
    fails here. The phrases are read out of plain.js, so renaming one there moves
    this test with it rather than breaking it.
    """
    phrases = plain_block("TRAVERSALS")
    problems = []
    for screen, scripts in SCREENS.items():
        for path in [screen] + scripts:
            source = (REPO / path).read_text()
            for key, phrase in phrases.items():
                if phrase in source:
                    problems.append(f"{path}: types {phrase!r} instead of reading {key}")
    assert not problems, "the shared phrase copied into a screen:\n" + "\n".join(problems)


def test_every_record_type_and_link_the_graph_draws_has_a_plain_name():
    """The check the graph screen's own guard makes, made before the browser does.

    The estate table, the legend and the tooltip all print plainType() and
    plainLink(). A record type the build starts emitting and plain.js has never
    heard of renders as "FatigueLog" at a reader who came to this screen to avoid
    exactly that, and the same for a link as "REPLACED_PART" and a trace as
    "blast_radius". Reading the generated graph rather than the source is the
    point: this fails on a data change, which is when it would actually happen.
    """
    types = plain_block("NODE_TYPES")
    links = plain_block("LINK_LABELS")
    traces = plain_block("TRAVERSALS")
    problems = []
    for name, g in graph_json()["graphs"].items():
        for label in g["node_types"]:
            if label not in types:
                problems.append(f"{name}: record type {label} has no plain name")
        for label in g["edge_labels"]:
            if label not in links:
                problems.append(f"{name}: link {label} has no plain name")
        if g["traversal"] not in traces:
            problems.append(f"{name}: trace {g['traversal']} has no plain question")
    assert not problems, "the graph draws what plain.js cannot name:\n" + "\n".join(problems)


def test_the_scope_line_under_the_graph_is_rewritten_not_printed():
    """The build writes these lines in the build's words; the screen owes a rewrite.

    "All 5 assets and all 3 dependency edges. Nothing filtered." shipped verbatim
    because the screen's rewriter knew "traversal" and not "edge" or "node" — on
    the one screen whose whole subject is edges and nodes. So the rewriter is run
    here over the generated lines, and what comes out must contain none of the
    three structural words and must still say the shared replacement for each one
    the line used. A rewriter that deleted the sentence fails the second half.
    """
    import subprocess

    words = plain_map()
    lines = [g["scope"] for g in graph_json()["graphs"].values()]
    script = (
        "const P=require(%r);"
        "console.log(JSON.stringify(%s.map(P.plainScope)));"
        % (str(PLAIN_JS), repr(lines).replace("'", '"'))
    )
    got = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, check=True
    ).stdout
    import json

    rewritten = json.loads(got)
    problems = []
    for before, after in zip(lines, rewritten):
        for term in ("traversal", "edge", "node"):
            if re.search(rf"\b{term}s?\b", after, re.I):
                problems.append(f"{after!r} still says {term!r}")
            if re.search(rf"\b{term}s?\b", before, re.I) and words[term] not in after.lower():
                problems.append(f"{after!r} dropped {term!r} instead of saying {words[term]!r}")
    assert not problems, "the scope line still speaks the build's dialect:\n" + "\n".join(
        problems
    )


def test_the_drawer_keeps_what_the_body_gave_up():
    """Nothing is dropped to make a page plain; it is moved."""
    problems = []
    for screen, keeps in DRAWER_KEEPS.items():
        held = drawer_text([screen] + SCREENS[screen])
        for expression in keeps:
            if expression not in held:
                problems.append(f"{screen}: the drawer no longer renders {expression}")
    assert not problems, "facts lost rather than demoted:\n" + "\n".join(problems)


def test_the_screen_codes_are_gone_from_headings():
    for screen, scripts in SCREENS.items():
        text = visible_text([screen] + scripts)
        assert not re.search(r"\bSC-[1-4]\b", text), f"{screen} still labels itself SC-n"


def test_no_heading_counts_the_estate_for_itself():
    """A headline that says how many of a thing there are is a hardcoded figure.

    "Two patterns, a hundred agents, fifty-two doors" was three of them in one
    line, and none came from the catalogue. Spelled out, they read as prose and
    survive a rebuild that moves the count underneath them.

    Every screen, and every heading each one renders. This ran over the case
    screens' markup alone, which exempted the four workspace screens from a rule
    the other six were held to and missed every heading written by a script —
    which on those four is most of them. "The five machines this site
    instruments" was one, sitting directly on top of a table read from the
    signals build.
    """
    problems = []
    for screen in SCREENS:
        for opened, html in renderings(screen):
            html = visible_html(html)
            for heading in re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, re.S):
                words = re.findall(r"[a-z]+", heading.lower())
                for word in words:
                    if word in COUNT_WORDS:
                        problems.append(f"{opened}: <h> counts the estate — {heading.strip()!r}")
                        break
                if re.search(r"\d", heading):
                    problems.append(f"{opened}: <h> carries a digit — {heading.strip()!r}")
    assert not problems, "counts typed into headings:\n" + "\n".join(problems)


def nav_labels():
    """The workspace nav, read out of apps/shared/shell.js rather than retyped.

    Reading it is the point. If the nav is renamed and the screens are not, the
    parse below moves with the nav and the screens fail, which is the failure
    worth having.
    """
    source = shell_js()
    block = re.search(r"const WORK_NAV = \[(.*?)\n\];", source, re.S)
    assert block, "apps/shared/shell.js no longer declares WORK_NAV"
    pairs = re.findall(r'href:\s*"([^"]+)".*?label:\s*"([^"]+)"', block.group(1))
    assert len(pairs) >= 4, f"WORK_NAV parsed to {pairs}"
    return dict(pairs)


def shell_js():
    return (APPS / "shared" / "shell.js").read_text()


def test_a_screen_calls_itself_what_the_nav_calls_it():
    """A nav that says one thing and a heading that says another.

    The tab reads "Agent teams" and the screen it opens read "Swarm console",
    which teaches a reader that the words on these screens are arbitrary — and
    once that is learned, every other plain phrase on them is discounted too.
    The nav label has to survive the click.
    """
    problems = []
    for href, label in nav_labels().items():
        screen = f"apps/workspace/{href}"
        if screen not in SCREENS:
            continue
        text = visible_text([screen] + SCREENS[screen])
        if label.lower() not in text.lower():
            problems.append(f"{screen}: the nav calls this {label!r} and the screen does not")
    assert not problems, "the nav and the screen disagree:\n" + "\n".join(problems)


def test_the_corner_pill_names_the_two_counts_the_reader_needs():
    """52 and 100 are a distinction, not a pair of numbers.

    "52 entrypoints · 100 agents" invites the reading that there are a hundred
    things to talk to. The distinction the reader needs is that fifty-two of
    them take questions and the rest work behind those. Both figures still come
    from the catalogue: a pill that spells either one out has stopped being a
    reading of the estate and become a claim about it.
    """
    source = shell_js()
    block = re.search(r"workspace:\s*\{(.*?)\n  \},", source, re.S)
    assert block, "apps/shared/shell.js no longer declares the workspace nav"
    pill = re.search(r"pill:\s*\(\)\s*=>\s*\((.*?)\}\),", block.group(1), re.S)
    assert pill, "the workspace nav no longer builds a pill"
    text = pill.group(1)

    # The pill counts, so it says the published phrase in the plural. The
    # pattern is built from apps/shared/plain.js rather than retyped, so a pill
    # that invents its own wording still fails; only the plural 's' is forgiven.
    words = plain_map()
    head, rest = words["entrypoint"].split(" ", 1)
    phrase = re.compile(re.escape(head) + "s? " + re.escape(rest))
    said = phrase.search(text)
    assert said, f"the pill does not say {words['entrypoint']!r}; it says {text!r}"
    assert "in the teams behind them" in text, (
        "the pill counts the other agents without saying what they are"
    )
    # Order matters as much as wording: the phrase belongs to the smaller
    # figure, and swapping them says the estate has a hundred front doors.
    first = text.index("counts.entrypoints")
    second = text.index("counts.agent_nodes")
    assert first < second, "the pill puts the whole estate behind the plain phrase"
    assert first < said.start(), "the count and its phrase are the wrong way round"
    assert not re.search(r"\b(52|100)\b", text), "the pill types a count it could read"


def test_the_copy_stays_commodity_neutral():
    metals = ["copper", "gold", "nickel", "iron ore", "bauxite", "zinc", "lithium"]
    for screen, scripts in SCREENS.items():
        text = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        for metal in metals:
            assert not re.search(rf"\b{metal}\b", text, re.I), (
                f"{screen} names {metal}; the copy says 'contained metal'"
            )


# Which screens put a currency figure on the page, and on what authority. A
# screen not named here may not print one at all, which is the half the previous
# version of this check was missing: it banned "$450,000" and had nothing to say
# about a screen that computed the same figure and printed it as a point.
#
#   "sourced" — the one hourly figure this repository can cite. The element that
#              carries the currency mark has to be filled from the fact itself.
#   "range"   — a magnitude the client owns. It is quoted as a band or not at
#              all, because a market is quoted in bands and a single number
#              presents an estimate with the confidence of a measurement.
MONEY_SCREENS = {
    "apps/index.html": "sourced",
    "apps/case/index.html": "sourced",
    "apps/case/value.html": "range",
}

SOURCED_FACT = "mill_downtime_usd_per_hour"


def money_sites(paths):
    """Every place a screen puts a currency mark on the page.

    Two forms exist: an element that declares ``data-prefix="$"`` for the
    count-up in apps/shared/motion.js, and a "$" written into a string the JS
    concatenates. Both are returned as the source line that carries them.
    """
    found = []
    for path in paths:
        source = (REPO / path).read_text()
        if path.endswith(".html"):
            for tag in re.findall(r"<[^>]*data-prefix=\"\$\"[^>]*>", source):
                found.append((path, tag))
            continue
        source = _strip_js_comments(source)
        for line in source.splitlines():
            if re.search(r"""(?<!\$)(["'])\$\1""", line):
                found.append((path, line.strip()))
    return found


def test_no_screen_types_a_money_figure():
    """A magnitude typed into the copy has no source and cannot be regenerated."""
    for screen, scripts in SCREENS.items():
        text = "\n".join((REPO / p).read_text() for p in [screen] + scripts)
        for hit in re.findall(r"\$[\d,]+", text):
            assert False, f"{screen} prints the literal money figure {hit}"


def test_only_the_declared_screens_print_money_at_all():
    problems = []
    for screen, scripts in SCREENS.items():
        sites = money_sites([screen] + scripts)
        if sites and screen not in MONEY_SCREENS:
            problems.append(f"{screen} prints a currency figure and declares no basis: {sites[0][1]}")
        if not sites and screen in MONEY_SCREENS:
            problems.append(f"{screen} is declared {MONEY_SCREENS[screen]!r} and prints no money")
    assert not problems, "money on an undeclared screen:\n" + "\n".join(problems)


def test_a_sourced_money_figure_is_filled_from_the_fact_it_cites():
    """The count-up element carrying the "$" must be fed the sourced fact.

    Not "the file mentions the fact somewhere" — the element that shows the
    currency mark is found by its id in the markup, and the statement that fills
    that id has to name mill_downtime_usd_per_hour. Repointing the anchor at any
    other number fails here, and so does an anchor filled with a constant.
    """
    problems = []
    for screen, form in MONEY_SCREENS.items():
        if form != "sourced":
            continue
        scripts = SCREENS[screen]
        js = "\n".join(_strip_js_comments((REPO / p).read_text()) for p in scripts)
        for path, site in money_sites([screen] + scripts):
            if path.endswith(".html"):
                ident = re.search(r'id="([^"]+)"', site)
                assert ident, f"{screen}: the currency element has no id to bind: {site}"
                fill = [
                    line
                    for line in js.splitlines()
                    if f'"{ident.group(1)}"' in line and SOURCED_FACT in line
                ]
                if not fill:
                    problems.append(
                        f"{screen}: #{ident.group(1)} shows a currency figure "
                        f"that is not {SOURCED_FACT}"
                    )
            elif SOURCED_FACT not in site:
                # A "$" written inline in JS. It is on the same entry as the
                # figure it prefixes, so the figure is right there to check.
                entry = _enclosing_entry(js, site)
                if SOURCED_FACT not in entry:
                    problems.append(f"{screen}: a currency figure with no source: {site}")
    assert not problems, "money without a source:\n" + "\n".join(problems)


def _enclosing_entry(js, site):
    """The `[ … ]` a fact tuple is written as, around a line inside it.

    apps/landing.js writes each figure as `[value, label, note, {prefix: "$"}]`,
    so the prefix and the value it decorates are on the same entry and nowhere
    else. Reading the whole file instead would pass on any file that happens to
    mention the fact once.
    """
    at = js.index(site)
    start = js.rindex("[", 0, at)
    depth = 0
    for j in range(start, len(js)):
        if js[j] == "[":
            depth += 1
        elif js[j] == "]":
            depth -= 1
            if depth == 0:
                return js[start : j + 1]
    return js[start:]


def test_a_client_owned_magnitude_is_quoted_as_a_range():
    """The standing constraint, checked on the form rather than on a word.

    The value screen's calculator is the one place a figure the client owns is
    rendered, and it is rendered as "low – high". The check is that the money
    formatter is never reached except through the band that builds that string:
    a screen that dropped the band and printed `money(t * price)` would satisfy
    every other test in this file, and would be a point estimate presented as a
    measurement, which is the thing the constraint exists to stop.
    """
    for screen, form in MONEY_SCREENS.items():
        if form != "range":
            continue
        js = "\n".join(_strip_js_comments((REPO / p).read_text()) for p in SCREENS[screen])

        band = re.search(r"const band = \(([a-z]+)\) =>(.*?);", js, re.S)
        assert band, f"{screen} no longer builds its figures as a band"
        text = band.group(2)
        assert "lo" in text and "hi" in text, (
            f"{screen}: the band does not span the two ends of the price range: {text!r}"
        )
        assert "–" in text, (
            f"{screen}: the band prints no range between its two ends: {text!r}"
        )

        # Every other use of the formatter is a point figure. The definition and
        # the band are the two legitimate sites; anything else prints one number
        # where the screen promised two.
        definition = re.search(r"function money\(.*?\n\}", js, re.S)
        assert definition, f"{screen} no longer defines its money formatter"
        rest = js.replace(definition.group(0), " ").replace(band.group(0), " ")
        stray = re.findall(r"\bmoney\(", rest)
        assert not stray, (
            f"{screen} prints {len(stray)} money figure(s) outside the band; "
            "a client-owned magnitude is quoted as a range or not at all"
        )
