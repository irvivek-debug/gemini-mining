"""Gate: one collapsible component, shared by both applications.

The `details.tbl` rules were written in workspace.css, which apps/case never
loads. Moving them is the whole of this task, and the failure mode if they move
back is silent: the case screens keep working, they just render an unstyled
disclosure triangle and a 20px touch target. Asserting the location is cheaper
than noticing that on a phone.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
SHARED_CSS = REPO / "apps" / "shared" / "app.css"
WORKSPACE_CSS = REPO / "apps" / "workspace" / "workspace.css"
SHELL_JS = REPO / "apps" / "shared" / "shell.js"


def test_the_collapsible_lives_in_the_shared_stylesheet():
    css = SHARED_CSS.read_text()
    assert ".tbl > summary" in css
    # Scoped to the summary's own rules. app.css carries focus rings and sizes
    # for other controls, so searching the whole file would pass even if the
    # summary lost both.
    summary_rules = css[css.index(".tbl > summary") :]
    assert "min-height: 44px" in summary_rules[:400], (
        "the 44px touch target is not on .tbl > summary"
    )
    assert ".tbl > summary:focus-visible" in css, (
        "the summary has no focus ring of its own"
    )


def test_the_workspace_stylesheet_no_longer_redefines_it():
    """Two definitions of one component is how they drift apart."""
    css = WORKSPACE_CSS.read_text()
    assert ".tbl > summary {" not in css
    assert "\n.tbl {" not in css
    # The genuinely workspace-specific parts stay.
    assert ".tbl-desc" in css
    assert ".col-meaning" in css


def _screens():
    return sorted((REPO / "apps").glob("*/*.html")) + [REPO / "apps" / "index.html"]


def test_every_screen_using_the_shared_shell_loads_the_shared_stylesheet():
    """The drawer's markup comes from shell.js and its rules from app.css.

    Scoped by shell.js rather than by directory. `apps/frontend` is a third
    application with its own design language and no technical drawer, so a
    directory sweep asserted a stylesheet it has no reason to load. What
    actually matters is that nothing loads half the pair.
    """
    checked = 0
    for screen in _screens():
        text = screen.read_text()
        if "shared/shell.js" not in text:
            continue
        checked += 1
        # Must be the actual link. A bare "app.css" substring would also be
        # satisfied by a comment, a source map, or a file called myapp.css.
        # Screens one level down write "../shared/app.css"; apps/index.html
        # writes "shared/app.css".
        assert re.search(r'href="(?:\.\./)?shared/app\.css"', text), (
            f"{screen.relative_to(REPO)} loads the shared shell but not the shared "
            "stylesheet, so its technical drawer renders unstyled"
        )
    # Population pin — a scope that quietly matched nothing would pass.
    assert checked >= 10, (
        f"only {checked} screens load the shared shell — expected at least 10; "
        "the scope may have broken"
    )


def test_the_standalone_front_end_takes_neither_half_of_the_pair():
    """`apps/frontend` is exempt because it shares nothing, and that is checked.

    If it ever adopts the shared shell, the test above starts governing it. This
    guards the other direction: picking up the stylesheet alone, or the shell
    alone, is the half-adoption that leaves a drawer looking broken.
    """
    text = (REPO / "apps" / "frontend" / "index.html").read_text()
    uses_shell = "shared/shell.js" in text
    uses_css = bool(re.search(r'href="(?:\.\./)?shared/app\.css"', text))
    assert uses_shell == uses_css, (
        "apps/frontend loads one half of the shared shell/stylesheet pair. "
        "Take both or neither."
    )


def test_one_helper_renders_the_drawer_for_every_screen():
    shell = SHELL_JS.read_text()
    assert "function technicalDrawer(" in shell
    assert "Technical detail" in shell


def test_the_workspace_nav_points_at_the_persona_page():
    shell = SHELL_JS.read_text()
    assert "workbench.html" not in shell
    assert '{ href: "persona.html", label: "My role" }' in shell
