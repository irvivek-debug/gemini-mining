import re

import pydantic
import pytest
from mining_agents.catalog.definitions import (
    ALL_AGENTS,
    ARCHETYPES,
    BENCHMARK_SOURCES,
    DEEP,
    EVIDENCE_CLASSES,
    LEAKS,
    SWARMS,
    AgentCard,
    FinancialLine,
    MetricImpact,
)
from mining_agents.tools.bqml_predict import list_models
from mining_agents.tools.graph_traverse import TRAVERSALS

HITL_COORDINATORS = {"S01", "S02", "S04", "S05", "S07", "S08", "S09", "S10", "S11"}
HITL_DEEP = {"D07", "D14", "D25", "D30", "D37"}

#: The nine coordinators that carry a card as of Task F, and the pack file
#: each one's card references. Fixed set, not derived — a test that derives
#: its expectation from the same code it is checking cannot fail. S04 (P7,
#: Optimiser) and S12 (P8, Sentinel) were added in Task F to close the two
#: personas that previously had neither a card nor a method pack.
CARD_COORDINATORS = {
    "S01": "p1-reliability.yaml",
    "S02": "p2-planner.yaml",
    "S03": "agt13-warranty.yaml",
    "S04": "p7-mine-controller.yaml",
    "S05": "p3-hse.yaml",
    "S06": "p5-geologist.yaml",
    "S07": "p6-metallurgist.yaml",
    "S09": "agt14-contract-integrity.yaml",
    "S12": "p8-shift-supervisor.yaml",
}


def _minimal_card_kwargs() -> dict:
    """A valid AgentCard's fields, as a dict, so a single test can drop one."""
    return dict(
        decision="Which asset comes down, when, and on what evidence.",
        leaks=["Blind spot"],
        archetype="Diagnostician",
        authority="L1 — Recommend",
        financial_lines=[FinancialLine(line="x → y", evidence_class="B")],
        honest_limit="A stated limit.",
    )


@pytest.fixture(scope="module")
def live_models() -> set[str]:
    """The BQML models that actually exist, so a renamed or dropped one fails.

    A fixture rather than a module-level constant, deliberately. At module
    level the BigQuery call runs at COLLECTION time, and anything that makes it
    fail — expired credentials, a fork run against a project with no models yet
    — takes all twenty tests in this file down as a collection error. That
    reads as "the catalog is broken" when the truth is "I am not
    authenticated", and it hides nineteen assertions that need no credentials
    at all. As a fixture, the blast radius is the one test that needs it.
    """
    return set(list_models())


def test_the_build_has_exactly_one_hundred_agents():
    assert len(ALL_AGENTS) == 100


def test_the_pattern_split_is_sixty_forty():
    assert len([a for a in ALL_AGENTS if a.pattern == "A"]) == 60
    assert len([a for a in ALL_AGENTS if a.pattern == "B"]) == 40


def test_there_are_twelve_swarms_of_five():
    assert len(SWARMS) == 12
    for swarm in SWARMS:
        assert len(swarm.specialists) == 3
        assert swarm.coordinator.swarm_role == "coordinator"
        assert swarm.critic.swarm_role == "critic"
        assert all(s.swarm_role == "specialist" for s in swarm.specialists)


def test_there_are_forty_deep_agents_numbered_d01_to_d40():
    assert len(DEEP) == 40
    assert {a.agent_id for a in DEEP} == {f"D{n:02d}" for n in range(1, 41)}


def test_agent_ids_are_unique():
    ids = [a.agent_id for a in ALL_AGENTS]
    assert len(ids) == len(set(ids))


def test_model_tiers_follow_the_role_rule():
    for agent in ALL_AGENTS:
        expected = "reasoning" if agent.swarm_role in ("coordinator", "critic") \
            else "balanced"
        assert agent.model_tier == expected, agent.agent_id


def test_the_tier_counts_match_the_design_table():
    tiers = [a.model_tier for a in ALL_AGENTS]
    assert tiers.count("reasoning") == 24   # 12 coordinators + 12 critics
    assert tiers.count("balanced") == 76    # 36 specialists + 40 deep


def test_no_pattern_c_tier_exists():
    assert all(a.model_tier in ("reasoning", "balanced") for a in ALL_AGENTS)


def test_exactly_fourteen_agents_are_hitl():
    hitl = {a.agent_id for a in ALL_AGENTS if a.hitl_required}
    assert hitl == HITL_COORDINATORS | HITL_DEEP
    assert len(hitl) == 14


def test_specialists_and_critics_are_never_hitl():
    for agent in ALL_AGENTS:
        if agent.swarm_role in ("specialist", "critic"):
            assert agent.hitl_required is False, agent.agent_id


def test_every_agent_declares_at_least_one_source_table():
    """PRD success metric: 100 of 100 agents resolve to a real table.

    Bare truthiness would pass on [""] — a list that is structurally non-empty
    and semantically void, which is the exact shape of this project's known
    array-loss failure. Pin the count and the qualification of every entry.
    """
    for agent in ALL_AGENTS:
        assert len(agent.source_tables) >= 1, agent.agent_id
        for table in agent.source_tables:
            assert table.startswith("mining_data."), (agent.agent_id, table)
            assert len(table) > len("mining_data."), (agent.agent_id, table)


@pytest.mark.parametrize("agent_id,fragment", [
    ("D27", "Safety Stock"),
    ("D37", "Radio Sentiment"),
    ("S01-SP2", "Blast-Radius"),
    ("S12", "Shift Handover"),
])
def test_display_names_are_transcribed_from_the_prd(agent_id, fragment):
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    assert agent_id in by_id
    assert fragment in by_id[agent_id].display_name


def test_agents_reading_biometrics_declare_the_base_table():
    """D35 and D36 drive the DLP controls for biometric data.

    D40 (Operator Exposure Profile Analyst) does NOT declare
    biometric_fatigue_logs — least-privilege: it profiles operator exposure
    from incidents and assignments only, not from raw biometric readings.
    """
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    for agent_id in ("D35", "D36"):
        assert "mining_data.biometric_fatigue_logs" in by_id[agent_id].source_tables, \
            f"{agent_id} should declare biometric_fatigue_logs"
    # D40 must NOT have biometric access — it uses incident_involvements ×
    # operator_vehicle_assignments only.
    assert "mining_data.biometric_fatigue_logs" not in by_id["D40"].source_tables, \
        "D40 must not declare biometric_fatigue_logs (least-privilege)"


def test_agents_reading_free_text_declare_the_source_table():
    """Drives the untrusted-content notice in the instruction."""
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    assert "mining_data.radio_communications" in by_id["D37"].source_tables
    assert "mining_data.maintenance_logs" in by_id["D10"].source_tables


def test_bqml_predict_is_never_granted_without_a_model(live_models):
    """make_bqml_predict([]) would raise: a tool must declare tables_read."""
    granted = [a for a in ALL_AGENTS if "bqml_predict" in a.tools]
    assert granted, "no agent has bqml_predict — the loop below proves nothing"
    for agent in granted:
        assert len(agent.models) >= 1, agent.agent_id
        assert all(m in live_models for m in agent.models), agent.agent_id


def test_no_agent_declares_the_embedding_model():
    # text_embedding_model is a REMOTE model over Vertex text-embedding-005,
    # deployed to embed the PDF corpus for doc_search.  It lives in the same
    # dataset as the eight predictive models, so list_models() returns it and
    # live_models contains it — meaning test_bqml_predict_is_never_granted_
    # without_a_model would NOT catch an agent declaring it.  ML.PREDICT over a
    # remote embedding model is not a prediction; it returns a number that means
    # nothing.  Deployment is not permission, and this test is what enforces
    # that distinction.  This test requires no live call: the catalogue is
    # static data.
    for agent in ALL_AGENTS:
        assert "text_embedding_model" not in agent.models, (
            f"{agent.agent_id} declares text_embedding_model; "
            "ML.PREDICT over an embedding model is not a prediction"
        )


def test_graph_traverse_is_never_granted_without_a_traversal():
    granted = [a for a in ALL_AGENTS if "graph_traverse" in a.tools]
    assert granted, "no agent has graph_traverse — the loop below proves nothing"
    for agent in granted:
        assert len(agent.traversals) >= 1, agent.agent_id
        assert all(t in TRAVERSALS for t in agent.traversals), agent.agent_id


# ---------------------------------------------------------------------------
# Agent cards (value-framing design, §2). Cards live only on the nine
# coordinators that hold a method pack (five persona packs plus the two CFO
# proof-point + two persona-completion packs — S03/S09 for AGT-13/AGT-14, S04
# for P7, S12 for P8). Every other agent's `card` is None.
# ---------------------------------------------------------------------------

def test_exactly_the_nine_pack_holding_coordinators_declare_a_card():
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    with_card = {a.agent_id for a in ALL_AGENTS if a.card is not None}
    assert with_card == set(CARD_COORDINATORS)
    for agent_id in CARD_COORDINATORS:
        assert by_id[agent_id].swarm_role == "coordinator", agent_id


def test_every_other_agent_has_no_card():
    for agent in ALL_AGENTS:
        if agent.agent_id not in CARD_COORDINATORS:
            assert agent.card is None, agent.agent_id


def test_card_pack_matches_the_expected_pack_file_per_coordinator():
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    for agent_id, expected_pack in CARD_COORDINATORS.items():
        assert by_id[agent_id].card.pack == expected_pack, agent_id


def test_archetype_enumerates_the_prd_six_and_rejects_a_seventh():
    """A test that only checks 'archetype is a non-empty string' cannot fail
    on a typo. This test hardcodes the PRD's six archetype names — a typo in
    definitions.py's Literal (e.g. 'Sentinal') would desynchronise ARCHETYPES
    from this hardcoded set AND make every card using the correct spelling
    fail to import, so the mismatch cannot hide.
    """
    expected = {"Sentinel", "Diagnostician", "Optimiser", "Negotiator", "Assurer", "Curator"}
    assert set(ARCHETYPES) == expected
    assert len(ARCHETYPES) == 6

    # A seventh, invented archetype must be rejected at construction.
    kwargs = _minimal_card_kwargs()
    kwargs["archetype"] = "Strategist"  # not one of the six
    with pytest.raises(pydantic.ValidationError):
        AgentCard(**kwargs)


def test_evidence_class_is_a_b_or_c_and_rejects_a_fourth():
    assert set(EVIDENCE_CLASSES) == {"A", "B", "C"}
    with pytest.raises(pydantic.ValidationError):
        FinancialLine(line="x → y", evidence_class="D")


def test_every_card_financial_line_carries_a_valid_evidence_class():
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        for fl in agent.card.financial_lines:
            assert fl.evidence_class in EVIDENCE_CLASSES, agent.agent_id


def test_every_card_leak_is_in_the_prd_taxonomy():
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        for leak in agent.card.leaks:
            assert leak in LEAKS, agent.agent_id


@pytest.mark.parametrize("missing_field", [
    "decision", "leaks", "archetype", "authority", "financial_lines", "honest_limit",
])
def test_card_missing_a_required_field_raises_at_construction(missing_field):
    """A missing field must raise when the AgentCard is built (at module
    import time, since every card is constructed inline in definitions.py),
    not silently render blank on a screen later.
    """
    kwargs = _minimal_card_kwargs()
    del kwargs[missing_field]
    with pytest.raises(pydantic.ValidationError):
        AgentCard(**kwargs)


def test_card_leaks_must_be_non_empty():
    kwargs = _minimal_card_kwargs()
    kwargs["leaks"] = []
    with pytest.raises(pydantic.ValidationError):
        AgentCard(**kwargs)


def test_card_financial_lines_must_be_non_empty():
    kwargs = _minimal_card_kwargs()
    kwargs["financial_lines"] = []
    with pytest.raises(pydantic.ValidationError):
        AgentCard(**kwargs)


def test_agt11_agt13_agt14_cards_match_the_signed_off_decisions():
    """Locks in the specific field values the plan owner signed off on for
    S01 (AGT-11), S03 (AGT-13) and S09 (AGT-14), so a later edit that quietly
    drifts one of them off-spec is caught here rather than downstream.
    """
    by_id = {a.agent_id: a for a in ALL_AGENTS}

    s01 = by_id["S01"].card
    assert s01.archetype == "Diagnostician"
    assert set(s01.leaks) == {"Blind spot", "Latency"}
    assert s01.authority == "L1 — Recommend"
    assert len(s01.financial_lines) == 1
    assert s01.financial_lines[0].line == "unplanned repair cost → C1 cash cost"
    assert s01.financial_lines[0].evidence_class == "B"

    s03 = by_id["S03"].card
    assert s03.archetype == "Negotiator"
    # Revised after the cards were first authored, and deliberately. The
    # dispatch that specified these cards named only "Blind spot" for S03,
    # which was my error, not the implementer's: warranty and OEM claims
    # recovery sits in the source portfolio's Asset management row, and that
    # row's leaks are "Blind spot · Latency". Four cards were corrected the
    # same way, against the same table, and the reason to care is not
    # tidiness — with six of seven cards claiming "Blind spot" alone, the
    # value page's leak band showed Variance and Assurance at zero agents,
    # which reads as a broken taxonomy rather than an honest portfolio.
    assert set(s03.leaks) == {"Blind spot", "Latency"}
    assert s03.authority == "L1 — Recommend"
    assert s03.financial_lines[0].evidence_class == "A"
    assert "warranty and OEM claims recovery" in s03.financial_lines[0].line

    s09 = by_id["S09"].card
    assert s09.archetype == "Negotiator"
    assert set(s09.leaks) == {"Coordination"}
    assert s09.authority == "L1 — Recommend"
    assert s09.financial_lines[0].evidence_class == "A"
    assert "post-signature contract leakage recovered" in s09.financial_lines[0].line


def test_no_currency_figure_appears_in_any_card():
    """Binding constraint: money is expressed as a range, never a point
    figure, and no absolute currency amount belongs on a card at all.
    """
    currency_pattern = re.compile(r"[$£€]\s*\d")
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        text = " ".join([
            agent.card.decision,
            agent.card.honest_limit,
            *(fl.line for fl in agent.card.financial_lines),
            *(mi.metric for mi in agent.card.metric_impacts),
            *(mi.source for mi in agent.card.metric_impacts),
        ])
        assert not currency_pattern.search(text), agent.agent_id


def test_no_named_commodity_appears_in_any_card():
    """Binding constraint: commodity-neutral. Cards say 'contained metal',
    never a specific metal or mineral.
    """
    named_commodities = (
        "copper", "gold", "iron ore", "coal", "nickel", "zinc", "lithium",
        "bauxite", "silver", "cobalt", "uranium", "potash", "lead",
    )
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        text = " ".join([
            agent.card.decision,
            agent.card.honest_limit,
            *(fl.line for fl in agent.card.financial_lines),
            *(mi.metric for mi in agent.card.metric_impacts),
            *(mi.source for mi in agent.card.metric_impacts),
        ]).lower()
        for commodity in named_commodities:
            # \b word boundaries plus a "lead time" exclusion — "lead" is a
            # real commodity name AND an ordinary English word this codebase
            # legitimately uses ("lead time"); only the metal usage counts.
            pattern = rf"\b{commodity}\b" if commodity != "lead" else r"\blead\b(?!\s+time)"
            assert not re.search(pattern, text), (agent.agent_id, commodity)


# ---------------------------------------------------------------------------
# MetricImpact — the quantified, sourced benchmark ranges hung off a card
# (design: sales-ready workspace, Task A). These are INDUSTRY BENCHMARKS
# from published research, never a measurement on this site's data, and
# `source` is the field that makes that distinction legible — so it is
# validated, not merely required to be truthy.
# ---------------------------------------------------------------------------

#: Independently transcribed from the plan's researched benchmark table
#: (docs/plans/2026-08-18-sales-ready-workspace.md, "The
#: benchmark set", researched 2026-08-18) — the six rows usable as a
#: per-agent citation. The three portfolio-level rows (value pool, no
#: material value, at scale) are framing-page material, not per-agent
#: citations, and are excluded here on purpose. This is hardcoded
#: independently of BENCHMARK_SOURCES so a drift in either one is caught,
#: not assumed away by comparing the module to itself.
PLAN_BENCHMARK_SOURCES = {
    "BCG, mature AI sites in mining & metals",
    "McKinsey, metals & mining",
    "BCG",
    "McKinsey",
    "McKinsey / Deloitte, predictive maintenance",
    "industry contract-management research",
}

#: Firms actually named in the plan's benchmark table. "industry
#: contract-management research" is also a citation in that table (the
#: contract value recovered row), but it names a research category, not a
#: consultancy, so it is tracked separately rather than folded into this set.
PLAN_BENCHMARK_FIRMS = {"BCG", "McKinsey", "Deloitte"}

#: The exact metric_impacts expected on each of the seven carded agents,
#: transcribed by hand against the plan's benchmark table and each agent's
#: `decision` / `financial_lines`, independent of definitions.py, so an
#: accidental edit there is caught here rather than assumed correct.
CARD_METRIC_IMPACTS: dict[str, list[tuple]] = {
    "S01": [
        ("Unplanned downtime", "decrease", 30.0, 50.0,
         "McKinsey / Deloitte, predictive maintenance"),
    ],
    "S02": [
        ("Maintenance cost", "decrease", 18.0, 25.0, "McKinsey"),
    ],
    "S03": [],
    "S04": [],
    "S05": [],
    "S06": [
        ("Mineral recovery", "increase", 1.0, 3.0, "McKinsey"),
    ],
    "S07": [
        ("Throughput", "increase", 2.0, 5.0, "BCG, mature AI sites in mining & metals"),
        ("Throughput", "increase", 4.0, 8.0, "McKinsey, metals & mining"),
        ("Mineral recovery", "increase", 1.0, 3.0, "McKinsey"),
    ],
    "S09": [
        ("Contract value recovered", "increase", 3.0, 5.0, "industry contract-management research"),
    ],
    "S12": [],
}


def _minimal_impact_kwargs() -> dict:
    return dict(metric="Throughput", direction="increase", low_pct=2, high_pct=5,
                source="McKinsey")


def test_metric_impact_without_a_source_raises_at_construction():
    """The rule that matters most: an impact built without attribution must
    not be constructible at all. Covers both an empty string and the field
    omitted outright — 'no source' has two shapes and both must raise.
    """
    kwargs = _minimal_impact_kwargs()
    kwargs["source"] = ""
    with pytest.raises(pydantic.ValidationError):
        MetricImpact(**kwargs)

    kwargs = _minimal_impact_kwargs()
    del kwargs["source"]
    with pytest.raises(pydantic.ValidationError):
        MetricImpact(**kwargs)


def test_metric_impact_source_must_name_a_researched_benchmark_not_just_be_non_empty():
    """A test that only checked 'source is a non-empty string' would pass on
    source='x' or source='internal analysis' — exactly the unattributed
    filler the plan calls out as the thing that ends a CFO conversation.
    Both must be rejected at construction, not merely discouraged.
    """
    for bogus_source in ("internal analysis", "x", "site data", "TBD"):
        kwargs = _minimal_impact_kwargs()
        kwargs["source"] = bogus_source
        with pytest.raises(pydantic.ValidationError):
            MetricImpact(**kwargs)


def test_metric_impact_source_names_one_of_the_firms_actually_cited_in_the_plan():
    """Enumerate, don't guess. Every BENCHMARK_SOURCES entry that isn't the
    table's own contract-management citation must contain one of the firms
    the plan's benchmark table actually names (BCG, McKinsey, Deloitte).
    """
    assert set(BENCHMARK_SOURCES) == PLAN_BENCHMARK_SOURCES
    for source in BENCHMARK_SOURCES:
        if source == "industry contract-management research":
            continue  # the table's own citation for that row; not a firm
        assert any(firm in source for firm in PLAN_BENCHMARK_FIRMS), source


def test_metric_impact_rejects_low_pct_greater_than_high_pct():
    kwargs = _minimal_impact_kwargs()
    kwargs["low_pct"], kwargs["high_pct"] = 10, 5
    with pytest.raises(pydantic.ValidationError):
        MetricImpact(**kwargs)

    # Boundary: equal values are a valid (zero-width) range, not rejected —
    # the guard is strictly low > high, not low >= high.
    kwargs["low_pct"], kwargs["high_pct"] = 5, 5
    MetricImpact(**kwargs)


def test_metric_impact_rejects_a_bogus_direction():
    kwargs = _minimal_impact_kwargs()
    kwargs["direction"] = "sideways"
    with pytest.raises(pydantic.ValidationError):
        MetricImpact(**kwargs)


def test_card_metric_impacts_match_the_researched_benchmark_mapping():
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    for agent_id, expected in CARD_METRIC_IMPACTS.items():
        actual = [
            (mi.metric, mi.direction, mi.low_pct, mi.high_pct, mi.source)
            for mi in by_id[agent_id].card.metric_impacts
        ]
        assert actual == expected, agent_id


def test_s03_and_s05_carry_no_metric_impacts_by_design():
    """S03 (warranty/OEM claims recovery) and S05 (HSE, Class C
    risk-adjusted) have no defensible published benchmark in the plan's
    table for the specific claim their card makes. An empty list is the
    honest answer — not a maintenance or downtime figure borrowed from an
    adjacent agent to avoid an empty-looking card.
    """
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    assert by_id["S03"].card.metric_impacts == []
    assert by_id["S05"].card.metric_impacts == []


def test_s04_and_s12_carry_no_metric_impacts_by_design():
    """S04 (dispatch re-plan, Optimiser) and S12 (shift handover, Sentinel)
    have no row in the plan's benchmark table that prices their specific
    claim either — S04 would have to borrow S07's already-claimed
    "Throughput" citation for a mechanically different lever, and S12's
    Class C risk-adjusted briefing has no published benchmark at all. An
    empty list is the honest answer, same as S03 and S05.
    """
    by_id = {a.agent_id: a for a in ALL_AGENTS}
    assert by_id["S04"].card.metric_impacts == []
    assert by_id["S12"].card.metric_impacts == []


def test_no_metric_impact_reintroduces_the_disputed_leakage_figure():
    """S09's honest_limit already states the widely quoted '9.2% contract
    value leakage' figure is a misattribution. The 3-5% RECOVERY figure is a
    distinct, defensible claim — this guards against the disputed figure
    creeping back in via a metric_impacts entry instead of the line it was
    originally caught in.
    """
    for agent in ALL_AGENTS:
        if agent.card is None:
            continue
        for mi in agent.card.metric_impacts:
            assert "9.2" not in mi.metric, agent.agent_id
            assert "9.2" not in mi.source, agent.agent_id
