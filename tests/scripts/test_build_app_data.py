"""Tests that build_app_data correctly carries method pack metrics to the screens.

These tests read personas.json from the export, so they verify the full
pipeline: pack loaded, metric extracted, written into the export. They are
intentionally not re-testing the pack loader itself (test_persona_method.py
covers that). They test what screens see.

Note: build_app_data reads BigQuery for the graph export. These tests do not
invoke the build — they read the file it produced and check its content. If the
file is stale (BigQuery credentials have expired and the build cannot re-run),
re-run:

    PYTHONPATH=. python -m scripts.build_app_data

after restoring credentials.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_every_persona_with_a_pack_carries_its_metric_to_the_screens():
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code in PACKS:
        assert personas[code].get("method", {}).get("metric"), code


def test_a_persona_without_a_pack_carries_no_method_block():
    # A method block on a persona with no tree would put a problem-solving
    # question on a page that cannot answer it.
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code, persona in personas.items():
        if code not in PACKS:
            assert not persona.get("method"), code


def test_five_packs_means_five_personas_carry_a_metric():
    # Guards against the count silently shrinking. Five packs were authored;
    # five method blocks must appear. A future pack added without re-running the
    # build would leave this test failing, which is the correct outcome.
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    personas_with_method = [
        code for code, p in personas.items() if p.get("method", {}).get("metric")
    ]
    assert len(personas_with_method) == len(PACKS), (
        f"Expected {len(PACKS)} personas with a metric (one per pack), "
        f"got {len(personas_with_method)}: {sorted(personas_with_method)}"
    )


def test_each_metric_is_a_non_empty_string():
    # A metric of "" or None would cause the governing starter to silently fall
    # back to table questions, which is the problem the method pack exists to fix.
    from mining_agents.tools.method_lookup import PACKS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code in PACKS:
        metric = personas[code].get("method", {}).get("metric")
        assert isinstance(metric, str) and metric.strip(), (
            f"{code}: metric is {metric!r}, not a non-empty string"
        )


def test_metrics_match_what_the_packs_declare():
    # The metric on the screen must match what the pack actually says, not a
    # stale copy. This verifies the full pipeline: pack -> build -> export.
    from mining_agents.tools.method_lookup import PACK_DIR, PACKS
    from mining_agents.method.pack import load_pack
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code, pack_name in PACKS.items():
        pack = load_pack(PACK_DIR / pack_name)
        screen_metric = personas[code]["method"]["metric"]
        assert screen_metric == pack.metric, (
            f"{code}: screen shows {screen_metric!r} but pack declares {pack.metric!r}"
        )


# --------------------------------------------------------------------------
# Task 3: agent cards, and coverage computed from the pack, never authored.
#
# A parallel workstream is instrumenting agt13/agt14/agt19's packs while these
# tests run, so the exact numbers below are read out of the shipped export
# and cross-checked against an independent read of the pack file in the same
# test -- never pinned as a literal -- so these tests keep passing as that
# work lands and would fail the moment the export stopped tracking the pack.
# --------------------------------------------------------------------------

def _card(personas, code, agent_id):
    cards = personas[code].get("cards") or []
    found = [c for c in cards if c["agent_id"] == agent_id]
    assert found, f"{agent_id} carries no card under persona {code}"
    return found[0]


def test_every_card_field_reaches_the_export():
    # The card's authored fields (everything except coverage) must reach the
    # export unchanged from AgentDef.card -- read independently here, not
    # copied from build_app_data.py, so a field the export silently dropped
    # would be caught.
    from mining_agents.catalog.definitions import ALL_AGENTS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    checked = 0
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        checked += 1
        card = _card(personas, agent.persona, agent.agent_id)
        assert card["decision"] == agent.card.decision
        assert card["leaks"] == list(agent.card.leaks)
        assert card["archetype"] == agent.card.archetype
        assert card["authority"] == agent.card.authority
        assert card["honest_limit"] == agent.card.honest_limit
        assert card["financial_lines"] == [
            {"line": fl.line, "evidence_class": fl.evidence_class}
            for fl in agent.card.financial_lines
        ]
    # Nine, not seven: S04 (P7, Optimiser) and S12 (P8, Sentinel) were added
    # to close the two personas that had neither a card nor a pack. The number
    # is written out rather than derived from ALL_AGENTS, deliberately — a
    # count taken from the same source the loop walks would rise silently with
    # a card added by accident, and the point of this assertion is to notice.
    assert checked == 9, (
        f"expected the nine documented cards (S01, S02, S03, S04, S05, S06, "
        f"S07, S09, S12), found {checked}"
    )


def test_agt11_coverage_matches_the_pack_read_independently():
    # Not a tautology: this re-derives the count from p1-reliability.yaml
    # itself, in this test, rather than re-reading what build_app_data.py
    # already computed. A build that stopped computing coverage and started
    # copying a stale number would still pass a test that only compared the
    # export to itself; this one would not.
    from mining_agents.method.pack import load_pack
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    card = _card(personas, "P1", "S01")
    assert card["pack"] == "p1-reliability.yaml"

    pack = load_pack(ROOT / "method" / "p1-reliability.yaml")
    instrumented = sum(1 for d in pack.drivers if d.status == "instrumented")
    assert card["coverage"] == {"instrumented": instrumented, "total": len(pack.drivers)}

    # Guards against a coverage function that always reports "all" or
    # "none": the real pack has both statuses, so a broken computation that
    # returned total==instrumented or instrumented==0 would fail here.
    assert 0 < instrumented < len(pack.drivers), (
        "p1-reliability.yaml no longer mixes instrumented and not_instrumented "
        "drivers, so this test can no longer tell a real computation from a "
        "constant one -- re-derive the assertion against the pack's new shape"
    )


def test_a_fully_uninstrumented_pack_reports_zero_not_absent():
    """A pack with zero instrumented drivers must export instrumented: 0 with
    total > 0 -- not an absent or null coverage field, which would read on a
    card as full coverage.

    Proved against a synthetic pack, not against agt13/agt14/agt19 (design §3
    shipped these three at zero). Those three are a live workstream running in
    parallel with this one, so a real pack at zero coverage today may not be
    at zero by the time this test next runs -- see the coverage numbers this
    build actually measured for them: no single one of the three is a stable
    "always zero" fixture to pin a test against. The behaviour under test
    (zero is reported, not omitted) has to hold regardless of which pack it is
    asked about, so it is proved on a pack this test controls end to end.
    """
    import scripts.build_app_data as build
    from mining_agents.catalog.definitions import AgentCard, FinancialLine
    from types import SimpleNamespace

    fixture = ROOT / "tests" / "scripts" / "fixtures"
    fixture.mkdir(exist_ok=True)
    pack_path = fixture / "_tmp_zero_pack.yaml"
    try:
        pack_path.write_text(
            "metric: test metric\n"
            "root: test root\n"
            "drivers:\n"
            "  - id: d1\n"
            "    question: q1\n"
            "    controllable: false\n"
            "    status: not_instrumented\n"
            "  - id: d2\n"
            "    question: q2\n"
            "    controllable: false\n"
            "    status: not_instrumented\n"
        )

        coverage = build._coverage(pack_path)
        assert coverage == {"instrumented": 0, "total": 2}
        assert coverage["total"] > 0

        # And through the real card-record pipeline, not just the coverage
        # helper in isolation -- PACK_DIR is pointed at the fixtures
        # directory for the duration of the call, so _card_record resolves
        # card.pack exactly the way it resolves a real pack, without writing
        # anything under method/ (owned by the parallel workstream).
        card = AgentCard(
            decision="test decision", leaks=["Latency"], archetype="Optimiser",
            authority="L1 — Recommend",
            financial_lines=[FinancialLine(line="test line", evidence_class="C")],
            honest_limit="test limit", pack="_tmp_zero_pack.yaml",
        )
        fake_agent = SimpleNamespace(agent_id="TEST-0", display_name="Test Agent", card=card)
        original_pack_dir = build.PACK_DIR
        build.PACK_DIR = fixture
        try:
            record = build._card_record(fake_agent)
        finally:
            build.PACK_DIR = original_pack_dir

        assert "coverage" in record, "coverage is absent, which reads as full coverage"
        assert record["coverage"]["instrumented"] == 0
        assert record["coverage"]["total"] > 0
    finally:
        pack_path.unlink(missing_ok=True)


def test_coverage_is_computed_from_the_pack_file_not_memorised():
    """Mutation-style proof that the coverage helper reads the file it is
    pointed at, rather than returning a number decided in advance."""
    import scripts.build_app_data as build

    fixture = ROOT / "tests" / "scripts" / "fixtures"
    fixture.mkdir(exist_ok=True)
    pack_path = fixture / "_tmp_coverage_pack.yaml"
    try:
        pack_path.write_text(
            "metric: test metric\n"
            "root: test root\n"
            "drivers:\n"
            "  - id: d1\n"
            "    question: q1\n"
            "    controllable: false\n"
            "    status: instrumented\n"
            "    sql: sql/d1.sql\n"
            "  - id: d2\n"
            "    question: q2\n"
            "    controllable: false\n"
            "    status: not_instrumented\n"
            "  - id: d3\n"
            "    question: q3\n"
            "    controllable: false\n"
            "    status: not_instrumented\n"
            "  - id: d4\n"
            "    question: q4\n"
            "    controllable: false\n"
            "    status: not_instrumented\n"
        )
        assert build._coverage(pack_path) == {"instrumented": 1, "total": 4}

        # Rewrite the same file with a second driver instrumented and no
        # other change. A hardcoded {"instrumented": 1, "total": 4} would
        # fail this half; only a function that re-reads the file passes both.
        pack_path.write_text(
            pack_path.read_text().replace(
                "    status: not_instrumented\n",
                "    status: instrumented\n"
                "    sql: sql/d2.sql\n",
                1,
            )
        )
        assert build._coverage(pack_path) == {"instrumented": 2, "total": 4}
    finally:
        pack_path.unlink(missing_ok=True)


def test_agt19_card_is_exported_with_computed_coverage():
    # AGT-19 has no persona (design §3), so its card is not under personas.json
    # -- it is exported on the catalog for the value screen instead.
    from mining_agents.method.pack import load_pack
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    card = catalog["group_agents"]["AGT-19"]
    assert card["pack"] == "agt19-strategic-planning.yaml"
    pack = load_pack(ROOT / "method" / "agt19-strategic-planning.yaml")
    instrumented = sum(1 for d in pack.drivers if d.status == "instrumented")
    assert card["coverage"] == {"instrumented": instrumented, "total": len(pack.drivers)}


def test_leak_counts_are_derived_never_authored():
    # Independently recount every leak off the catalog's own agent cards plus
    # AGT-19, and compare against the exported leak_counts -- not a
    # tautology, because this rebuilds the tally from AgentDef.card rather
    # than reading what build_app_data.py already produced.
    from mining_agents.catalog.definitions import ALL_AGENTS, LEAKS
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())

    expected = {leak: 0 for leak in LEAKS}
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        for leak in agent.card.leaks:
            expected[leak] += 1
    for leak in catalog["group_agents"]["AGT-19"]["leaks"]:
        expected[leak] += 1

    assert catalog["leaks"] == list(LEAKS)
    assert catalog["leak_counts"] == expected
    # Every one of the five leaks is claimed by at least one card. A count of
    # zero would mean a leak from the taxonomy has no agent behind it at all.
    for leak in LEAKS:
        assert catalog["leak_counts"][leak] > 0, f"no card claims the {leak!r} leak"


# --------------------------------------------------------------------------
# Task C/D (plan 2026-08-18): metric_impacts on the export, and the cockpit's
# per-metric summary built from them.
# --------------------------------------------------------------------------

def test_metric_impacts_reach_the_export_unchanged():
    # Read independently off ALL_AGENTS, not copied from build_app_data.py,
    # so a field the export dropped, reordered or renamed would be caught --
    # the same discipline test_every_card_field_reaches_the_export already
    # applies to every other card field.
    from mining_agents.catalog.definitions import ALL_AGENTS
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    checked = 0
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        checked += 1
        card = _card(personas, agent.persona, agent.agent_id)
        assert card["metric_impacts"] == [
            {
                "metric": mi.metric, "direction": mi.direction,
                "low_pct": mi.low_pct, "high_pct": mi.high_pct,
                "source": mi.source,
            }
            for mi in agent.card.metric_impacts
        ]
    assert checked == 9


def test_a_card_with_no_metric_impacts_exports_an_empty_list_not_an_absent_field():
    """S03 and S05 are this plan's deliberate honesty decisions
    (mining_agents/catalog/definitions.py): no published benchmark applies to
    either, and the card says so by carrying an EMPTY list, never a missing
    key -- a missing key would force every reader of the export to
    special-case "field absent" as a second way of saying "field present and
    empty". AGT-19 (no AgentDef, hand-transcribed card) is held to the same
    rule."""
    personas = json.loads((ROOT / "apps/shared/data/personas.json").read_text())["personas"]
    for code, agent_id in [("P1", "S03"), ("P3", "S05")]:
        card = _card(personas, code, agent_id)
        assert "metric_impacts" in card, f"{agent_id}: metric_impacts key is absent, which reads as unknown, not empty"
        assert card["metric_impacts"] == []

    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    agt19 = catalog["group_agents"]["AGT-19"]
    assert "metric_impacts" in agt19
    assert agt19["metric_impacts"] == []


def test_metric_impact_summary_dedupes_two_agents_citing_an_identical_range():
    """S06 and S07 both cite McKinsey's identical 1-3% mineral-recovery range
    (definitions.py). The cockpit's summary must fold them into ONE range
    entry with both agents listed as contributors -- printing the identical
    range twice would read as two independent claims when it is one."""
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    summary = {e["metric"]: e for e in catalog["metric_impact_summary"]}
    recovery = summary["Mineral recovery"]
    assert recovery["agents"] == ["S06", "S07"]
    assert len(recovery["ranges"]) == 1, (
        f"expected one deduplicated range, found {len(recovery['ranges'])}: {recovery['ranges']}"
    )
    assert recovery["ranges"][0]["agents"] == ["S06", "S07"]
    assert recovery["ranges"][0]["low_pct"] == 1
    assert recovery["ranges"][0]["high_pct"] == 3
    assert recovery["ranges"][0]["source"] == "McKinsey"


def test_metric_impact_summary_keeps_two_different_sources_separate():
    """S07 alone cites TWO different firms' throughput ranges (BCG 2-5%,
    McKinsey 4-8%) -- genuinely different claims, unlike the identical
    mineral-recovery case above, and they must not merge into one."""
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    summary = {e["metric"]: e for e in catalog["metric_impact_summary"]}
    throughput = summary["Throughput"]
    assert throughput["agents"] == ["S07"]
    assert len(throughput["ranges"]) == 2
    sources = {r["source"] for r in throughput["ranges"]}
    assert sources == {"BCG, mature AI sites in mining & metals", "McKinsey, metals & mining"}
    for r in throughput["ranges"]:
        assert r["agents"] == ["S07"]


def test_metric_impact_summary_matches_an_independent_reconstruction():
    """The whole summary, rebuilt here from ALL_AGENTS rather than compared
    against what build_app_data.py already produced -- so a metric silently
    dropped, an agent silently added, or a dedup key computed wrong would
    fail this even though catalog.json is internally self-consistent."""
    from mining_agents.catalog.definitions import ALL_AGENTS
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())

    expected: dict = {}
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        for mi in agent.card.metric_impacts:
            bucket = expected.setdefault(mi.metric, {"agents": set(), "ranges": {}})
            bucket["agents"].add(agent.agent_id)
            key = (mi.direction, mi.low_pct, mi.high_pct, mi.source)
            bucket["ranges"].setdefault(key, set()).add(agent.agent_id)
    # AGT-19 has no AgentDef and its own metric_impacts is deliberately empty
    # (build_app_data.py, _AGT19_CARD), so it never contributes here either.

    got = {e["metric"]: e for e in catalog["metric_impact_summary"]}
    assert set(got) == set(expected), f"metrics differ: export has {sorted(got)}, expected {sorted(expected)}"
    for metric, bucket in expected.items():
        assert set(got[metric]["agents"]) == bucket["agents"], metric
        got_ranges = {
            (r["direction"], r["low_pct"], r["high_pct"], r["source"]): set(r["agents"])
            for r in got[metric]["ranges"]
        }
        assert got_ranges == bucket["ranges"], metric


def test_cards_with_no_metric_impacts_never_appear_as_a_contributor():
    """S03, S05 and AGT-19 are deliberate honesty decisions: no metric in
    metric_impact_summary may list any of them as a contributing agent."""
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    for entry in catalog["metric_impact_summary"]:
        for excluded in ("S03", "S05", "AGT-19"):
            assert excluded not in entry["agents"], (
                f"{excluded} is listed as a contributor to {entry['metric']!r}, "
                "but its metric_impacts is deliberately empty"
            )


def test_metric_impact_summary_is_sorted_by_metric_name():
    catalog = json.loads((ROOT / "apps/shared/data/catalog.json").read_text())
    metrics = [e["metric"] for e in catalog["metric_impact_summary"]]
    assert metrics == sorted(metrics)


def test_metric_impact_summary_is_computed_from_its_argument_not_memorised():
    """Mutation-style proof, the same discipline
    test_coverage_is_computed_from_the_pack_file_not_memorised already applies
    to coverage: two synthetic cards citing an identical range dedupe into
    one, two citing different sources for the same metric stay apart as two,
    and a card with no metric_impacts contributes nothing at all -- so this
    cannot be a function that returns a fixed shape regardless of its input."""
    import scripts.build_app_data as build

    def card(agent_id, source):
        return {
            "agent_id": agent_id,
            "metric_impacts": [
                {"metric": "Test metric", "direction": "increase", "low_pct": 1, "high_pct": 2, "source": source},
            ],
        }

    same_source = build._metric_impact_summary([card("X1", "McKinsey"), card("X2", "McKinsey")])
    assert len(same_source) == 1
    assert same_source[0]["agents"] == ["X1", "X2"]
    assert len(same_source[0]["ranges"]) == 1, "identical ranges from two agents did not dedupe"

    different_source = build._metric_impact_summary([card("X1", "McKinsey"), card("X2", "BCG")])
    assert len(different_source) == 1
    assert different_source[0]["agents"] == ["X1", "X2"]
    assert len(different_source[0]["ranges"]) == 2, "two different sources for the same metric merged into one"

    no_impacts = build._metric_impact_summary([{"agent_id": "X3", "metric_impacts": []}])
    assert no_impacts == [], "a card with no metric_impacts must contribute nothing, not an empty-range entry"
