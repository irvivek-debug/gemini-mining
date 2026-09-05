import pytest
from mining_agents.catalog.definitions import DEEP
from mining_agents.patterns.deep import bind_tools, build_deep_agent, build_instruction


def _by_id(agent_id):
    return next(a for a in DEEP if a.agent_id == agent_id)


def test_every_deep_agent_builds():
    built = [build_deep_agent(a) for a in DEEP]
    assert len(built) == 40


def test_tools_are_bound_to_the_names_the_catalog_declares():
    agent = _by_id("D01")
    tools = bind_tools(agent)
    assert len(tools) == len(agent.tools)
    assert all(callable(t) for t in tools)


def test_only_hitl_agents_get_request_approval():
    for agent in DEEP:
        has_approval = "request_approval" in agent.tools
        assert has_approval == agent.hitl_required, agent.agent_id


def test_every_bound_tool_declares_tables_read():
    for agent in DEEP:
        for tool in bind_tools(agent):
            tables_read = getattr(tool, "tables_read", None)
            # Bare truthiness passes on [""] — a structurally non-empty but
            # semantically void list.  Pin that every entry is a non-empty string.
            assert tables_read is not None, (
                f"{agent.agent_id}: tool {tool.__name__!r} has no tables_read"
            )
            assert len(tables_read) >= 1, (
                f"{agent.agent_id}: tool {tool.__name__!r} tables_read is empty"
            )
            for entry in tables_read:
                assert isinstance(entry, str) and entry.strip(), (
                    f"{agent.agent_id}: tool {tool.__name__!r} tables_read "
                    f"contains empty or non-string entry: {entry!r}"
                )


def test_an_unknown_tool_name_is_rejected_loudly():
    agent = _by_id("D01").model_copy(update={"tools": ["teleport"]})
    with pytest.raises(ValueError, match="teleport"):
        bind_tools(agent)


def test_the_instruction_carries_the_citation_mandate():
    text = build_instruction(_by_id("D01"))
    assert "mining_data.telemetry_stream" in text
    assert "cite" in text.lower()


def test_every_agent_is_told_not_to_invent_data_when_a_tool_fails():
    """The clause exists because an agent did exactly this in production.

    D01's first live run had every bq_query call refused. It answered with a
    fabricated asset id and a fabricated vibration reading, presented as
    queried fact, while its own envelope reported rows_scanned 0. For a
    showcase that is the worst available failure mode: a reader cannot
    distinguish the invention from a real result.

    Checked across all 40 rather than a sample, because the clause is
    unconditional and a per-agent branch that skipped it would be invisible.
    """
    assert len(DEEP) == 40
    missing = [a.agent_id for a in DEEP if "TOOL FAILURE" not in build_instruction(a)]
    assert missing == []
    for agent in DEEP:
        text = build_instruction(agent)
        assert "success=false" in text, agent.agent_id
        assert "rows_scanned" in text, agent.agent_id
        assert "NEVER supply a value a tool did not return" in text, agent.agent_id


def test_the_instruction_warns_about_untrusted_field_content():
    text = build_instruction(_by_id("D37"))   # reads radio_communications
    assert "UNTRUSTED" in text
    assert "never instructions" in text


def test_biometric_agents_are_told_to_use_bands_not_raw_values():
    text = build_instruction(_by_id("D35"))   # Fatigue Risk Scorer
    assert "band" in text.lower()
    assert "heart_rate_bpm" in text


def test_the_agent_resolves_its_model_from_the_tier_not_a_literal():
    import inspect
    import mining_agents.patterns.deep as module
    source = inspect.getsource(module)
    assert "gemini" not in source
    assert "llm_for_tier" in source


def test_the_instruction_never_names_a_tool_the_agent_does_not_hold():
    """Naming an unbound tool invites a call that cannot resolve."""
    for agent in DEEP:
        text = build_instruction(agent)
        for tool_name in ("operational_math", "request_approval"):
            if tool_name not in agent.tools:
                assert tool_name not in text, (agent.agent_id, tool_name)


def test_agents_that_hold_operational_math_are_told_to_use_it():
    holders = [a for a in DEEP if "operational_math" in a.tools]
    assert len(holders) >= 1, "no deep agent holds operational_math"
    for agent in holders:
        assert "operational_math" in build_instruction(agent), agent.agent_id


def test_bq_query_holders_are_told_not_to_introspect_the_schema():
    """On the live P6 run, every agent holding bq_query reflexively opened
    with a query against mining_data.INFORMATION_SCHEMA.COLUMNS — a table no
    agent declares, so assert_reads_only_declared_tables refused it, and the
    refusal littered the activity log on every run. Nothing ever asked for
    that lookup; it is just what models do before writing SQL.

    Checked both ways — present for a bq_query holder, absent for one that
    doesn't hold the tool — the same shape as
    test_the_instruction_never_names_a_tool_the_agent_does_not_hold above,
    so a wrong gate (e.g. always-on, or gated on the wrong tool name) fails
    in whichever direction it drifts.
    """
    holders = [a for a in DEEP if "bq_query" in a.tools]
    non_holders = [a for a in DEEP if "bq_query" not in a.tools]
    assert holders, "no deep agent holds bq_query"
    assert non_holders, "no deep agent lacks bq_query — the negative branch is untestable"
    for agent in holders:
        text = build_instruction(agent)
        assert "DO NOT QUERY THE SCHEMA" in text, agent.agent_id
        assert "INFORMATION_SCHEMA" in text, agent.agent_id
    for agent in non_holders:
        text = build_instruction(agent)
        assert "DO NOT QUERY THE SCHEMA" not in text, agent.agent_id
        assert "INFORMATION_SCHEMA" not in text, agent.agent_id


def test_the_tool_failure_clause_asks_for_error_values_not_field_names():
    """The cosmetic half of the P6 defect: the coordinator's answer read
    'failed with error.code and error.message .' twice — the literal field
    NAMES, empty, printed at the reader — because the old wording ("quote
    error.code and error.message") named the fields without saying it meant
    their values. The reworded clause must say so explicitly, and the old,
    ambiguous phrasing must be gone so it cannot be misread the same way
    again."""
    for agent in DEEP:
        text = build_instruction(agent)
        assert "write out the VALUES" in text, agent.agent_id
        assert "quote error.code and" not in text, agent.agent_id
