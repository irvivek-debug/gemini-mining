"""Gate: a persona's governing metric reaches the screen that leads with it.

The persona page's starter questions are derived, not authored, and they were
derived from the only two things the export carried about an agent: its tables
and its traversals. So the landing screen for the Metallurgist opened with
"What's in the sensor readings right now?" — the natural-language-to-SQL framing
this whole branch exists to replace, printed in the customer's own words at the
top of the page that argues against it.

The method pack already knows what the role is trying to improve. Carrying that
one field into the export is what lets the page open with a problem instead of
a table, and carrying it from the pack rather than typing it into a screen is
what keeps the two from drifting apart.
"""
from mining_agents.tools.method_lookup import PACKS
from scripts.build_app_data import build_catalog, build_personas

PERSONAS = build_personas(build_catalog())["personas"]


def test_a_persona_with_a_pack_carries_its_governing_metric():
    assert PERSONAS["P6"]["method"]["metric"] == (
        "unit cost per tonne of contained metal"
    )


def test_a_persona_with_no_pack_is_untouched():
    # The starter questions fall back to today's behaviour for these, so an
    # empty method block would be worse than none: the screen would have to
    # decide what an absent metric means.
    for code, entry in PERSONAS.items():
        if code in PACKS:
            continue
        assert "method" not in entry, f"{code} has no pack but carries a method"


def test_every_persona_with_a_pack_is_covered_and_no_other():
    # Reads the loader rather than a second list of personas, so adding a pack
    # cannot leave the export behind.
    assert {c for c, e in PERSONAS.items() if "method" in e} == set(PACKS)


def test_the_governing_metric_names_no_commodity():
    # It is now user-facing copy on the persona page, and this estate says
    # "contained metal" everywhere rather than naming a metal.
    metals = ("copper", "gold", "nickel", "iron", "zinc", "silver", "cobalt")
    for code in PACKS:
        said = PERSONAS[code]["method"]["metric"].lower()
        for metal in metals:
            assert metal not in said, f"{code}: the metric names {metal}"
