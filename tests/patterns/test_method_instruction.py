"""Tests for the METHOD instruction block and the tool bindings that support it.

WHY THIS FILE EXISTS:
Before this task, build_instruction was a retrieval-governance layer: scope,
citation, tool failure, never-invent. The METHOD block is the change the whole
redesign turns on. Without it, the agent is a natural-language-to-SQL service.
With it, the agent is told to work a driver tree and return a diagnosis.

Every test here guards a clause that would silently disappear under a refactor
unless something names it explicitly.
"""
from mining_agents.catalog.definitions import ALL_AGENTS
from mining_agents.patterns.deep import bind_tools, build_instruction

BY_ID = {a.agent_id: a for a in ALL_AGENTS}


def test_an_agent_with_a_pack_is_told_to_work_the_tree():
    # Without this block the agent answers the user's question directly instead
    # of working the driver tree. That is the failure mode the whole redesign
    # exists to prevent.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "METHOD" in said
    assert "method_lookup" in said
    # The five steps that separate a diagnosis from a retrieval.
    for step in ("size", "attribute", "controllable", "why", "guard"):
        assert step in said.lower(), f"the {step!r} step is missing"


def test_an_agent_with_a_pack_is_told_to_use_run_diagnostic():
    # run_diagnostic is the mechanism by which the agent executes each driver's
    # fixed query. Without naming it in the instruction, the agent may fall back
    # to bq_query to implement its own version, defeating the pack entirely.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "run_diagnostic" in said


def test_the_agent_is_told_not_to_drop_a_driver():
    # A silently dropped driver reads as "no problem found". That is the single
    # most dangerous honesty failure in this system — the answer implies full
    # coverage when coverage is partial.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "unevidenced" in said.lower()


def test_the_agent_is_told_to_retrieve_the_constraint_before_recommending():
    # The guard fences the recommendation. Stating the guard after a
    # recommendation reverses the decision logic: the constraint becomes
    # optional context rather than a condition the recommendation must satisfy.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "doc_search" in said
    # The word "before" proves nothing about order — it is satisfied by a
    # clause that says "recommend, then retrieve the constraint before the
    # change is made", which is the reversal this test exists to catch. Both
    # the sentence and the positions are asserted: the literal pins the wording
    # a reader can check, and the index comparison survives a rewording that
    # keeps the order.
    assert "with doc_search BEFORE you recommend" in said
    # Ordering is compared INSIDE step 5, not across the whole instruction:
    # step 4 already says "a recommendation that cannot answer this", so a
    # whole-string comparison would be about that sentence instead of this one.
    step5 = next(line for line in said.split("\n") if "doc_search" in line)
    assert step5.index("doc_search") < step5.index("recommend"), (
        f"the guard step recommends before it retrieves the constraint, which "
        f"makes the constraint optional context: {step5}"
    )


def test_the_agent_is_told_to_read_the_guard_the_diagnostic_returns():
    # The step-5 clause names doc_search, which retrieves the SITE's documented
    # constraint. That is not the same thing as the 'guard' field run_diagnostic
    # returns, which is the METHOD's own caveat on the finding — and the two are
    # easy to conflate because both are called guards.
    #
    # This matters concretely. The P6 liberation guard says the torque figure is
    # a maximum over daily MEAN torque, so it bounds average duty and cannot
    # evidence headroom under an instantaneous alarm. If the instruction never
    # tells the agent to read the field, that caveat is dead text and the agent
    # will recommend a setting change on torque evidence that does not support
    # one. Without this assertion, the clause can be dropped in a refactor and
    # every other test here still passes.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "'guard' field" in said, "the guard field is never surfaced to the agent"
    assert "run_diagnostic result" in said


def test_the_instruction_distinguishes_run_diagnostic_from_bq_query():
    # bq_query stays on S07-SP3 to size the prize and cover questions the tree
    # does not address. The risk: the agent uses bq_query to re-derive a driver
    # that run_diagnostic already computes, producing an inconsistent or silently
    # different result. This clause is load-bearing: without it, bq_query leaks
    # into diagnostic work and the pack's fixed queries are never run.
    said = build_instruction(BY_ID["S07-SP3"])
    # The instruction must tell the agent that run_diagnostic is the path for
    # any driver in the tree, and bq_query is for sizing and non-tree questions.
    assert "run_diagnostic" in said
    # The clause must positively distinguish the two uses.
    assert "bq_query" in said
    # And it must forbid using bq_query as a substitute for the pack's
    # diagnostics. Searching for the bare word "never" cannot show that: every
    # agent in the catalogue is told "NEVER supply a value a tool did not
    # return", and every agent with bq_query is told "Never interpolate a value
    # into SQL", so the assertion passed for agents that have no pack at all
    # and would keep passing with this entire clause deleted. The prohibition
    # is one sentence; assert that sentence.
    assert "It must never substitute for run_diagnostic on any driver in the tree." in said
    assert "Never use bq_query to re-derive or check a driver that the pack " \
        "already computes" in said.replace("\n", " ")


def test_the_agent_is_told_a_not_instrumented_result_is_a_success_not_a_failure():
    # run_diagnostic used to return a failure envelope for a driver with no
    # diagnostic behind it. That was wrong: nothing failed, the tool correctly
    # reported the pack has no query for this driver. The fix makes that call
    # succeed (success: true, data.status == "not_instrumented"), but the
    # earlier TOOL FAILURE clause in this same instruction says "a result with
    # success=false carries NO data ... say which call failed ... and stop" —
    # a model that has internalised that clause and nothing more would still
    # be primed to read ANY run_diagnostic result defensively unless it is
    # told explicitly that this particular shape is not that case. Without
    # this clause an agent could reasonably ignore the empty `rows` list on a
    # not_instrumented result as if the call had failed, silently reproducing
    # the exact bug the fix closes.
    said = build_instruction(BY_ID["S07-SP3"])
    assert "not_instrumented" in said
    assert "success: true" in said
    # It must positively distinguish this from the TOOL FAILURE clause above,
    # not merely mention both words somewhere in the instruction.
    assert "NOT the TOOL FAILURE case" in said
    # And it must tell the agent what to do with the result: read the
    # driver's question/note and report the gap, never call it a failure.
    assert "data.question" in said
    assert "data.note" in said
    assert "Never describe that call as failed" in said


def test_an_agent_without_the_tool_gets_no_method_block():
    # Naming a tool an agent does not hold invites a call that cannot resolve.
    # D22 is a P6 agent that does not carry method_lookup; it must not receive
    # instructions that reference it.
    said = build_instruction(BY_ID["D22"])
    assert "METHOD" not in said


def test_every_bound_tool_is_the_tool_that_was_asked_for():
    # This was a length comparison, which cannot fail: bind_tools appends one
    # entry per name and raises on a name it does not know, so the two lengths
    # are equal by construction. What can fail is a builder wired to the wrong
    # callable — "doc_search": lambda: ontology_lookup binds four tools for four
    # names and gives the agent one it was never granted. Comparing the bound
    # names to the declared ones, in order, is the assertion that catches it.
    agent = BY_ID["S07-SP3"]
    bound = bind_tools(agent)
    assert [t.__name__ for t in bound] == list(agent.tools)


def test_all_three_new_tool_names_resolve():
    # The corrections to the brief add run_diagnostic alongside method_lookup
    # and doc_search. Each must resolve separately: one missing builder silently
    # shrinks the tool list rather than raising in some call paths.
    agent = BY_ID["S07-SP3"]
    assert "method_lookup" in agent.tools
    assert "run_diagnostic" in agent.tools
    assert "doc_search" in agent.tools
    bound = bind_tools(agent)
    tool_names = {t.__name__ for t in bound}
    assert "method_lookup" in tool_names
    assert "run_diagnostic" in tool_names
    assert "doc_search" in tool_names
