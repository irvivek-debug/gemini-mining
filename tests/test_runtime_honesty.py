"""Gate: no screen states the runtime from the build.

DATA.workspace.runtime is written when bundle.js is generated. In production the
service is connected to all 52 agents and that constant still says it is not, so
five screens printed NOT CONNECTED at a reader looking at a working system.

This is a source check rather than a rendering check because the failure is
structural: the moment any screen reads that constant as its answer, the bug is
back, and it is invisible until someone opens the deployed page. What the
rendering actually does once it has the wire's answer is pinned from Node, in
tests/js/handover.test.js.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "apps" / "workspace"


def strip_comments(text: str) -> str:
    """Source with /* */ and // comments removed.

    Several assertions below are of the form "this file calls that". A comment
    naming the call satisfies a substring search and does not call anything, so
    the comments come out before the search goes in.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", text)


def media_print_block(css: str) -> str:
    """The body of @media print, brace-matched.

    A print rule that has drifted out of the print block still answers a
    whole-file substring search, and would then hide the Run button on screen.
    """
    start = css.index("@media print")
    open_brace = css.index("{", start)
    depth = 0
    for i in range(open_brace, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[open_brace + 1 : i]
    raise AssertionError("@media print is not closed")


def test_the_runtime_constant_is_only_ever_a_fallback():
    """Reading it is allowed. Reading it without asking the wire first is not.

    Both searches run over stripped source, and the second one is for the call
    rather than for the path. Against raw text a file could render the baked
    constant as its answer and still pass on the strength of a comment naming
    the endpoint — demonstrated by replacing the one real fetch with a throw and
    leaving the comments in place. Stripping comments is not enough on its own
    either: the path also appears as drawer copy, so a bare `"/api/runtime" in
    text` survives the same mutation. What has to be there is the call.

    The detection half runs over stripped source for the mirror reason: a
    commented-out mention of the constant must not drag a file that no longer
    reads it into the check.

    It walks every application, not just this one, because the shared shell is
    where the fetch now lives and a gate that cannot see the file it is about
    is not a gate.
    """
    checked = 0
    for source in sorted((REPO / "apps").rglob("*.js")):
        if source.name == "bundle.js":  # the data itself, not a screen
            continue
        text = strip_comments(source.read_text())
        if "workspace.runtime" not in text and "WS.runtime" not in text:
            continue
        checked += 1
        assert re.search(r"""fetch\(\s*["']/api/runtime["']""", text), (
            f"{source.name} reads the build-time runtime constant but never calls "
            "fetch('/api/runtime'), so it will claim NOT CONNECTED in production"
        )
    assert checked, "no file reads the constant at all; this gate has stopped gating"


def test_the_handover_can_be_run():
    handover = strip_comments((WORKSPACE / "handover.js").read_text())
    assert "streamAgent(" in handover, (
        "the handover sheet has no way to run the brief it describes"
    )
    assert 'agentId: "S12"' in handover, (
        "the run control does not name the agent the sheet is about"
    )


def test_the_handover_runs_only_the_one_agent_the_catalogue_allows():
    """Four sections, one entrypoint. The other four are internal to the swarm."""
    handover = (WORKSPACE / "handover.js").read_text()
    for internal in ("S12-SP1", "S12-SP2", "S12-SP3", "S12-CRITIC"):
        assert f'"{internal}"' not in handover, (
            f"{internal} is not an externally callable entrypoint and must not be invoked"
        )


def test_the_run_control_and_the_activity_log_do_not_print():
    css = (WORKSPACE / "workspace.css").read_text()
    printed = media_print_block(css)
    assert re.search(r"\.run-brief\s*\{[^}]*display:\s*none", printed), (
        "the Run button has no print rule, so it prints"
    )
    assert re.search(r"\.brief-out\s+\.log\s*\{[^}]*display:\s*none", printed), (
        "the activity log is how the brief arrived, not part of the brief"
    )
    assert ".brief-out .answer" in printed, "the brief itself has no print rule"


def test_the_four_sections_no_longer_claim_to_be_disconnected():
    handover = (WORKSPACE / "handover.js").read_text()
    assert "It has not run." not in handover


def test_the_handover_page_loads_what_the_run_control_needs():
    """agent-stream.js reads plain.js, and handover.js reads agent-stream.js.

    Load them in the wrong order and the page throws on the first line of the
    file that arrived early, which takes the whole sheet with it.
    """
    html = (WORKSPACE / "handover.html").read_text()
    order = [
        html.index('src="../shared/shell.js"'),
        html.index('src="../shared/plain.js"'),
        html.index('src="agent-stream.js"'),
        html.index('src="handover.js"'),
    ]
    assert order == sorted(order), "handover.html loads its scripts out of order"
