import pytest
from mining_agents.safety.output_filter import (
    BIOMETRIC_FIELDS,
    REDACTION,
    RawBiometricLeak,
    assert_clean,
    mask_rows,
    redact_model_response,
    scrub,
)


# ---------------------------------------------------------------------------
# Existing baseline tests
# ---------------------------------------------------------------------------

def test_a_banded_statement_is_left_alone():
    text = "OP-014 is HIGH fatigue risk and should be stood down."
    assert scrub(text) == text
    assert_clean(text)


def test_a_raw_heart_rate_is_redacted():
    out = scrub("OP-014 shows heart_rate_bpm of 118 during shift 3.")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_prose_phrasing_is_caught_too():
    out = scrub("Her heart rate was 118 bpm at 04:00.")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out  # pinned: must replace, not just strip


def test_sleep_deficit_and_microsleep_counts_are_redacted():
    out = scrub("sleep_deficit_hours = 3.4 and microsleep_events_detected = 5")
    assert "3.4" not in out
    assert "5" not in out
    assert out.count("[REDACTED:BIOMETRIC]") == 2  # pinned: exactly two redactions


def test_the_operator_pseudonym_is_retained():
    """Banding OP-014 would make S10's stand-down action unactionable."""
    out = scrub("OP-014 heart_rate_bpm 118")
    assert "OP-014" in out


def test_assert_clean_raises_on_a_leak():
    with pytest.raises(RawBiometricLeak):
        assert_clean("heart_rate_bpm 118")


# ---------------------------------------------------------------------------
# C-1 / C-2: JSON and Python repr shapes must be caught
# ---------------------------------------------------------------------------

def test_json_dict_payload_is_fully_redacted():
    """C-1/C-2: bq_query returns rows as Python dicts; their JSON repr must be caught."""
    payload = (
        '{"heart_rate_bpm": 118, "sleep_deficit_hours": 3.4, '
        '"microsleep_events_detected": 5}'
    )
    out = scrub(payload)
    assert "118" not in out
    assert "3.4" not in out
    assert "5" not in out
    assert out.count("[REDACTED:BIOMETRIC]") == 3

def test_python_repr_payload_is_fully_redacted():
    """C-1/C-2: Python repr uses single-quotes — must also be caught."""
    payload = "{'heart_rate_bpm': 118, 'sleep_deficit_hours': 3.4, 'microsleep_events_detected': 5}"
    out = scrub(payload)
    assert "118" not in out
    assert "3.4" not in out
    assert "5" not in out
    assert out.count("[REDACTED:BIOMETRIC]") == 3


def test_pretty_printed_json_payload_is_fully_redacted():
    """C-1/C-2: multi-line pretty-printed JSON (as logged by some BigQuery clients)."""
    payload = (
        "{\n"
        '  "heart_rate_bpm": 118,\n'
        '  "sleep_deficit_hours": 3.4,\n'
        '  "microsleep_events_detected": 5\n'
        "}"
    )
    out = scrub(payload)
    assert "118" not in out
    assert "3.4" not in out
    assert "5" not in out
    assert out.count("[REDACTED:BIOMETRIC]") == 3


# ---------------------------------------------------------------------------
# I-1: alternate prose phrasings must be caught
# ---------------------------------------------------------------------------

def test_beats_per_minute_phrasing_is_caught():
    """I-1: '118 beats per minute' — only bpm abbreviation was previously covered."""
    out = scrub("Operator recorded 118 beats per minute during exertion.")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_heart_rate_elevated_to_connector_is_caught():
    """I-1: connector 'to' was missing from the alternation."""
    out = scrub("heart rate elevated to 118")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_sleep_debt_synonym_is_caught():
    """I-1: 'sleep debt' used interchangeably with 'sleep deficit' in reports."""
    out = scrub("sleep debt: 3.4 hours logged for this shift.")
    assert "3.4" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_microsleep_count_phrasing_is_caught():
    """I-1: 'microsleep count' phrasing not previously covered."""
    out = scrub("microsleep count: 5 detected in the last two hours.")
    assert "5" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_pulse_abbreviation_is_caught():
    """I-1: 'pulse: 118' commonly used in incident reports."""
    out = scrub("Medic recorded pulse: 118 on arrival.")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out


def test_hr_abbreviation_is_caught():
    """I-1: 'HR: 118' used in wearable-device exports."""
    out = scrub("HR: 118 at 03:45 UTC")
    assert "118" not in out
    assert "[REDACTED:BIOMETRIC]" in out


# ---------------------------------------------------------------------------
# I-1 negative / anti-false-positive tests
# ---------------------------------------------------------------------------

def test_inventory_percentage_is_not_redacted():
    """I-1 guard: capacity percentage must survive untouched."""
    text = "inventory at 85% capacity"
    assert scrub(text) == text


def test_distance_in_km_is_not_redacted():
    """I-1 guard: a bare number with a unit unrelated to biometrics must survive."""
    text = "truck ran 118 km on the eastern haul road"
    assert scrub(text) == text


def test_shift_time_is_not_redacted():
    """I-1 guard: shift start times (colon-separated) must survive untouched."""
    text = "shift 3 started at 06:00"
    assert scrub(text) == text


# ---------------------------------------------------------------------------
# M-3: prose coverage must stay in sync with BIOMETRIC_FIELDS
# ---------------------------------------------------------------------------

def test_prose_coverage_matches_biometric_fields():
    """M-3: if BIOMETRIC_FIELDS gains a member, this test fails loudly.

    Each field in BIOMETRIC_FIELDS must be detectable in a bare column-name
    form (field_name: <number>).  The column-name patterns are generated from
    BIOMETRIC_FIELDS, so this test actually validates the generator loop rather
    than hand-written prose, but it will also catch a case where someone removes
    a field from BIOMETRIC_FIELDS without a corresponding change elsewhere.
    """
    for field in BIOMETRIC_FIELDS:
        payload = f"{field}: 99"
        out = scrub(payload)
        assert "99" not in out, (
            f"Field '{field}' in BIOMETRIC_FIELDS has no working pattern — "
            f"add a column-name pattern for it in _PATTERNS"
        )
        assert "[REDACTED:BIOMETRIC]" in out, (
            f"Field '{field}' in BIOMETRIC_FIELDS produced no redaction token"
        )


# ---------------------------------------------------------------------------
# mask_rows — the inbound control. Redacts raw columns before rows reach a
# model, so the value never enters the context window in the common case.
# ---------------------------------------------------------------------------

def test_every_biometric_field_is_redacted_in_a_row():
    """Driven off BIOMETRIC_FIELDS, so adding a fourth field fails here if
    mask_rows stops covering it."""
    row = {field: 42 for field in BIOMETRIC_FIELDS}
    row["operator_id"] = "OP-014"

    masked = mask_rows([row])[0]

    assert len(BIOMETRIC_FIELDS) == 3
    for field in BIOMETRIC_FIELDS:
        assert masked[field] == REDACTION, f"{field} was not redacted"
    assert masked["operator_id"] == "OP-014", "the pseudonym must be preserved"


def test_masking_keeps_the_column_rather_than_dropping_it():
    """A column that vanishes reads as a failed query and invites a retry."""
    masked = mask_rows([{"heart_rate_bpm": 118}])[0]
    assert "heart_rate_bpm" in masked
    assert masked["heart_rate_bpm"] == REDACTION


def test_masking_preserves_row_count_and_row_order():
    rows = [{"operator_id": f"OP-{n:03d}", "heart_rate_bpm": n} for n in range(5)]
    masked = mask_rows(rows)
    assert len(masked) == 5
    assert [r["operator_id"] for r in masked] == [f"OP-{n:03d}" for n in range(5)]


def test_masking_does_not_mutate_the_rows_it_was_given():
    original = [{"heart_rate_bpm": 118}]
    mask_rows(original)
    assert original[0]["heart_rate_bpm"] == 118


def test_a_biometric_field_nested_in_a_struct_is_redacted():
    """BigQuery returns a STRUCT as a nested dict. A flat pass over top-level
    keys would miss this, and the value would reach the model intact."""
    masked = mask_rows([{
        "operator_id": "OP-014",
        "vitals": {"heart_rate_bpm": 118, "shift": "night"},
    }])[0]
    assert masked["vitals"]["heart_rate_bpm"] == REDACTION
    assert masked["vitals"]["shift"] == "night"


def test_a_biometric_field_inside_an_array_of_structs_is_redacted():
    masked = mask_rows([{
        "readings": [{"heart_rate_bpm": 118}, {"heart_rate_bpm": 121}],
    }])[0]
    assert [r["heart_rate_bpm"] for r in masked["readings"]] == [REDACTION] * 2


def test_a_repeated_biometric_column_is_replaced_whole_not_element_by_element():
    """The key is checked before the value is walked, so an ARRAY of readings
    collapses to a single token. Redacting element-wise would preserve the
    array's length, which leaks how many readings the operator has."""
    masked = mask_rows([{"heart_rate_bpm": [118, 121]}])[0]
    assert masked["heart_rate_bpm"] == REDACTION


def test_column_matching_is_case_insensitive():
    masked = mask_rows([{"Heart_Rate_BPM": 118}])[0]
    assert masked["Heart_Rate_BPM"] == REDACTION


def test_an_alias_defeats_row_masking_which_is_why_the_output_scrub_exists():
    """Pin the known hole rather than imply mask_rows is complete.

    `SELECT heart_rate_bpm AS hr` returns a column named `hr`, and nothing
    about the returned row says where it came from. This is the case
    redact_model_response is there to catch on the way out.
    """
    masked = mask_rows([{"hr": 118}])[0]
    assert masked["hr"] == 118  # NOT redacted — by design, documented above


def test_masking_an_empty_result_set_is_not_an_error():
    assert mask_rows([]) == []


# ---------------------------------------------------------------------------
# redact_model_response — the outbound control, wired as an ADK
# after_model_callback on all 100 agents.
# ---------------------------------------------------------------------------

class _Part:
    """Stands in for google.genai.types.Part: text is optional and mutable."""

    def __init__(self, text=None, function_call=None):
        self.text = text
        self.function_call = function_call


class _Content:
    def __init__(self, parts):
        self.parts = parts


class _Response:
    def __init__(self, parts):
        self.content = _Content(parts) if parts is not None else None


def test_a_raw_value_in_a_model_response_is_redacted_in_place():
    response = _Response([_Part(text="OP-014 heart rate was 118 bpm.")])

    returned = redact_model_response(None, response)

    assert returned is response, "a modified response must be returned to ADK"
    assert "118" not in response.content.parts[0].text
    assert REDACTION in response.content.parts[0].text
    assert "OP-014" in response.content.parts[0].text


def test_a_clean_response_returns_none_so_adk_keeps_the_original():
    """Returning the response unchanged would claim a modification we did not
    make. None is ADK's signal to keep what the model produced."""
    response = _Response([_Part(text="OP-014 is HIGH fatigue risk.")])
    assert redact_model_response(None, response) is None
    assert response.content.parts[0].text == "OP-014 is HIGH fatigue risk."


def test_a_function_call_part_carrying_no_text_is_skipped():
    """Tool-call turns produce parts with text=None. Scrubbing must not crash
    on them, and must not report a redaction it did not perform."""
    response = _Response([_Part(function_call={"name": "bq_query"})])
    assert redact_model_response(None, response) is None


def test_only_the_offending_part_of_a_multi_part_response_changes():
    clean, dirty = _Part(text="Fatigue band: HIGH."), _Part(text="heart_rate_bpm 118")
    response = _Response([clean, dirty])

    assert redact_model_response(None, response) is response
    assert clean.text == "Fatigue band: HIGH."
    assert REDACTION in dirty.text


def test_a_response_with_no_content_is_handled():
    assert redact_model_response(None, _Response(None)) is None


def test_a_response_with_an_empty_parts_list_is_handled():
    assert redact_model_response(None, _Response([])) is None
