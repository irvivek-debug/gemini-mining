"""Gate: the persona page exists, replaces the workbench, and claims nothing extra.

This is a static check of the page's sources, not of its rendering — the
rendering is checked in a browser at the end of the plan. What is worth pinning
here is the set of claims the markup and the panel are allowed to make, because
those are the ones that go wrong quietly: a heading that says "your machines"
when no persona-to-asset mapping exists, or a screen that outlives the workbench
it replaced.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "apps" / "workspace"

# Borrowed rather than copied. Running a screen and counting the collapsibles it
# drew is one mechanism, and a second copy of it here would be a copy free to
# drift — this file would keep passing while the real gate moved. The explicit
# path insert is so this works when pytest is pointed at this file alone.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_screen_copy import bundle, disclosures, rendered  # noqa: E402


def test_the_persona_page_and_its_two_scripts_exist():
    for name in ("persona.html", "persona.js", "persona-panel.js"):
        assert (WORKSPACE / name).is_file(), f"{name} is missing"


def test_the_workbench_is_gone_and_nothing_still_links_to_it():
    assert not (WORKSPACE / "workbench.html").exists()
    assert not (WORKSPACE / "workbench.js").exists()
    for source in sorted((REPO / "apps").rglob("*.html")) + sorted((REPO / "apps").rglob("*.js")):
        assert "workbench" not in source.read_text(), (
            f"{source.relative_to(REPO)} still refers to the workbench"
        )


def test_the_page_loads_every_module_the_panel_needs():
    html = (WORKSPACE / "persona.html").read_text()
    for script in ("../shared/shell.js", "../shared/plain.js", "persona-data.js",
                   "router.js", "persona-panel.js", "persona.js"):
        assert script in html, f"persona.html does not load {script}"
    # Order matters: these are classic scripts, and a module that calls into
    # another must be loaded after it.
    assert html.index("../shared/plain.js") < html.index("router.js")
    assert html.index("router.js") < html.index("persona-data.js")
    assert html.index("persona-data.js") < html.index("persona-panel.js")
    # The one that actually throws when it is wrong: persona.js is the only
    # file that *calls* renderPanel, at load, so it has to be last.
    assert html.index("persona-panel.js") < html.index("persona.js"), (
        "persona.js runs before persona-panel.js defines renderPanel"
    )


def test_every_script_the_page_loads_is_on_disk():
    """Load order is worth nothing if the file 404s. Nothing else checks this."""
    html = (WORKSPACE / "persona.html").read_text()
    srcs = re.findall(r'<script src="([^"]+)"', html)
    assert srcs, "persona.html loads no scripts at all"
    for src in srcs:
        assert (WORKSPACE / src).resolve().is_file(), (
            f"persona.html loads {src}, which does not exist"
        )


def test_the_machines_block_does_not_claim_the_machines_are_the_readers():
    """No persona-to-asset mapping exists, so the heading says "this site"."""
    panel = (WORKSPACE / "persona-panel.js").read_text()
    assert "this site instruments" in panel
    assert "your machines" not in panel.lower()


def test_the_panel_handles_all_three_evidence_kinds():
    panel = (WORKSPACE / "persona-panel.js").read_text()
    for kind in ("series", "distribution", "share"):
        assert f'"{kind}"' in panel, (
            f"the panel does not switch on the {kind} evidence kind, so at least "
            "one persona renders nothing"
        )


def test_the_panel_renders_the_gap_caveats_verbatim():
    """Assert on the calls, not on the words.

    A bare `"caveat" in panel` is satisfied by the CSS class `pcaveat`,
    `"caption"` by `ev-caption`, and `"excluded"` by the comment explaining why
    the list is printed — so three of the four fields could be deleted from the
    output with the test still green. What has to survive is the call that puts
    the string on the screen.
    """
    panel = (WORKSPACE / "persona-panel.js").read_text()
    for call in ("esc(gap.method)", "esc(gap.caveat)", "esc(e.caption)",
                 "gap.excluded.map("):
        assert call in panel, f"{call} is gone, so that text never reaches the screen"


def test_the_panel_applies_one_precision_to_both_ends_of_a_range():
    """Fix for "0.00 alerts to 7.00 alerts" — P3's evidence is a count.

    fig() left to itself reads magnitude alone, so each end of a range is
    rounded independently and anything under ten gets two decimals. The
    rendered proof is in tests/js/persona-panel.test.js; this pins the call
    shape, because passing `dp` to one end and not the other is the regression.
    """
    panel = (WORKSPACE / "persona-panel.js").read_text()
    assert "fig(e.min, e.unit, dp) + \" to \" + fig(e.max, e.unit, dp)" in panel, (
        "the two ends of the range are no longer printed at a shared precision"
    )


def test_the_mine_controller_keeps_the_overhead_type_scale():
    """A7. This screen replaced the workbench, which applied it and was deleted.

    P7 reads the page from a control-room display several metres back, where the
    audit measured 14px body text as illegible. The rule survives in
    workspace.css; what went missing with the workbench was anything applying it
    here.
    """
    page = (WORKSPACE / "persona.js").read_text()
    assert 'CODE === "P7"' in page, "nothing on the persona page tests for P7"
    assert 'classList.add("scale-lg")' in page, (
        "the P7 large-type accommodation is not applied on the role page"
    )
    assert ".scale-lg" in (WORKSPACE / "workspace.css").read_text()
    assert 'id="wrap"' in (WORKSPACE / "persona.html").read_text(), (
        "persona.js reaches for #wrap, which persona.html does not define"
    )


def test_the_runtime_check_is_the_one_the_other_screens_use():
    """One implementation of "is this reply an answer", not one per page.

    This page ran a fetch of its own, guarded on reply.ok, while the workspace
    screens guarded on the shape of the body — so a 500 carrying a JSON body was
    a not-connected runtime on this screen and an unreadable reply on the other
    five. Two answers to one question.

    Comments are stripped first: the sentence above is in persona.js too, and a
    raw substring search for `fetch(` would be satisfied by prose describing the
    fetch that was removed.
    """
    page = re.sub(r"/\*.*?\*/", "", (WORKSPACE / "persona.js").read_text(), flags=re.S)
    page = re.sub(r"(?m)^\s*//.*$", "", page)
    assert "runtimeState()" in page, "the role page no longer asks about the connection"
    assert "fetch(" not in page, (
        "the role page has its own runtime fetch again; there is one shared "
        "check in apps/shared/runtime.js and this is how the two drift apart"
    )
    assert "console.warn" in page, (
        "the raw cause is discarded, so a network failure and a malformed "
        "payload are the same event to whoever is debugging"
    )


def test_the_page_ends_with_one_technical_drawer():
    """Counted on the rendered page, for every role, not in the source text.

    This counted the string ``technicalDrawer(`` in two files, which cannot fail
    on the thing it exists to prevent: a collapsible written as a literal
    ``'<details>'`` is invisible to it, and one such literal written inside a
    loop is a single occurrence in a file and one per row on the screen. It also
    only ever described the default role, and this screen is configuration — the
    same code over a different row of the catalogue — so seven of the eight roles
    were never described at all.
    """
    problems = []
    for code in sorted(bundle()["personas"]["personas"]):
        found = disclosures(rendered("apps/workspace/persona.html", f"?p={code}"))
        if len(found) != 1:
            listed = "\n".join(f"      {tag} — {label!r}" for tag, label in found)
            problems.append(
                f"?p={code} renders {len(found)} collapsibles; it must render one:\n{listed}"
            )
            continue
        tag, label = found[0]
        if "drawer" not in tag or not label.startswith("Technical detail"):
            problems.append(f"?p={code}: its one collapsible is not the drawer: {tag} — {label!r}")
    assert not problems, "collapsibles on the role screen:\n" + "\n".join(problems)


def test_no_measurement_is_typed_into_the_page():
    """Every figure comes from the bundle. A literal here is a number nobody can check.

    The two shapes a measurement takes in this data are a decimal (92.32,
    1149.552, 8.5433) and a magnitude of four digits or more (145000, 1996,
    3340). Neither has any business in rendering code. Small integers do — SVG
    geometry, percentages, array bounds — so they are left alone.
    """
    import re

    for name in ("persona.js", "persona-panel.js"):
        source = (WORKSPACE / name).read_text()
        body = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith(("*", "//", "/*"))
        )
        decimals = re.findall(r"(?<![\w.])\d+\.\d+(?![\w.])", body)
        assert decimals == [], (
            f"{name} contains the decimal literal(s) {decimals}; every measurement "
            "on this screen must come from window.MINING_DATA"
        )
        big = [n for n in re.findall(r"(?<![\w.])\d{4,}(?![\w.])", body)]
        assert big == [], (
            f"{name} contains the literal magnitude(s) {big}; every figure on this "
            "screen must come from window.MINING_DATA"
        )
