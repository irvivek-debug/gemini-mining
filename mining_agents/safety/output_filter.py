"""Biometric masking. Enforced by code, not by prompt instruction.

Agents may say "OP-014 is HIGH fatigue risk". Agents may not emit a raw
heart rate, sleep deficit, or microsleep count.

Two controls, because neither one is sufficient alone:

  mask_rows          on the way IN — redacts the three raw columns in every
                     BigQuery result before the rows reach a model. Exact on
                     column names, but blind to `SELECT heart_rate_bpm AS hr`,
                     which returns a column named `hr`.
  scrub / redact_model_response
                     on the way OUT — redacts raw values in the text a model
                     produces, whatever it chose to call them. Catches the
                     aliased case above, and anything the model restates from
                     memory, but it is pattern matching: a value spelled out
                     in words ("a pulse of one-eighteen") survives.

Neither is an access control. What stops an agent reading a biometric table
it has no business in is `assert_reads_only_declared_tables` in
mining_agents/tools/bq_query.py. These two limit what leaks from a table the agent
IS allowed to read — the 14 agents that legitimately analyse fatigue and are
required to report it as a band.

NOT enforceable at the IAM layer: all 100 agents share three service accounts,
so no binding can separate a biometric reader from a non-reader. See
infra/iam/service_accounts.py and its test_biometric_access_is_not_restricted_
at_the_iam_layer.
"""
from __future__ import annotations

import re
from typing import Any

REDACTION = "[REDACTED:BIOMETRIC]"

# Exactly three sensitive columns — if you add a fourth here you MUST also add
# a matching prose pattern below, or the test_prose_coverage_matches_biometric_fields
# test will fail loudly.
BIOMETRIC_FIELDS = (
    "heart_rate_bpm",
    "sleep_deficit_hours",
    "microsleep_events_detected",
)

_NUM = r"[-+]?\d+(?:\.\d+)?"

# Between a column name and its numeric value, JSON, Python repr, and prose all
# insert different punctuation.  The connector group accepts: optional
# whitespace, then an optional run of punctuation characters (quotes, brackets,
# braces, commas) and/or keyword connectors (of/=/:/is/was/to), then optional
# whitespace again.  This matches all of:
#   heart_rate_bpm 118          (bare)
#   heart_rate_bpm: 118         (colon connector)
#   "heart_rate_bpm": 118       (JSON)
#   'heart_rate_bpm': 118       (Python repr)
#   heart_rate_bpm = 118        (assignment)
#   heart_rate_bpm is 118       (natural language)
#   {"heart_rate_bpm": 118, …}  (JSON object)
_CONN = r"""[\s"'{\[,]*(?:of|=|:|is|was|to)?[\s"'\]},]*"""

_PATTERNS = (
    # column-name forms — connector allows JSON/repr punctuation between name and value
    *(re.compile(rf"(?i)\b{field}\b{_CONN}{_NUM}")
      for field in BIOMETRIC_FIELDS),
    # prose: heart rate / heart_rate — connector includes "elevated to", "increased to",
    # etc. where an adjective/verb precedes the "to".
    re.compile(rf"(?i)\bheart[ _]rate\b\s*(?:\w+\s+)?{_CONN}{_NUM}\s*(?:bpm)?"),
    # bpm abbreviation (e.g. "118 bpm", "pulse: 118 bpm")
    re.compile(rf"(?i){_NUM}\s*bpm\b"),
    # HR: 118 / pulse: 118 — short abbreviations commonly used in reports
    re.compile(rf"(?i)\b(?:HR|pulse)\s*[:\-=]\s*{_NUM}"),
    # beats per minute
    re.compile(rf"(?i){_NUM}\s*beats?\s+per\s+minute\b"),
    # sleep deficit / sleep debt
    re.compile(rf"(?i)\bsleep[ _](?:deficit|debt)\b{_CONN}{_NUM}"),
    # microsleep count / microsleep events
    re.compile(rf"(?i)\bmicrosleep(?:[ _](?:events?|count))?\b{_CONN}{_NUM}"),
)


class RawBiometricLeak(Exception):
    """A raw biometric value reached an agent output or log."""


def scrub(text: str) -> str:
    """Redact raw biometric values, preserving the operator pseudonym."""
    out = text
    for pattern in _PATTERNS:
        out = pattern.sub(REDACTION, out)
    return out


def assert_clean(text: str) -> None:
    """Raise if any raw biometric value is present.

    Not called on the agent execution path — redact_model_response redacts
    rather than raises there, because aborting a whole Workflow graph over a
    number that has already been replaced helps nobody. This is for callers
    that want the leak to be fatal: tests, and any future audit step.
    """
    if scrub(text) != text:
        raise RawBiometricLeak(
            "raw biometric value present in output; use the v_fatigue_scored band"
        )


_MASKABLE = frozenset(field.lower() for field in BIOMETRIC_FIELDS)


def mask_value(key: str, value: Any) -> Any:
    """Redact `value` if `key` names a raw biometric column, else recurse.

    Recursion matters: BigQuery returns STRUCT columns as nested dicts and
    ARRAY columns as lists, so a biometric field can arrive one level down
    from the row itself and a flat pass over the top-level keys would miss it.
    """
    if key.lower() in _MASKABLE:
        return REDACTION
    if isinstance(value, dict):
        return {k: mask_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_value(key, v) for v in value]
    return value


def mask_rows(rows: list[dict]) -> list[dict]:
    """Redact raw biometric columns in a BigQuery result set.

    The key is kept and its value replaced, rather than the column dropped.
    A column that vanishes without explanation reads to an agent as a failed
    query and invites a retry loop; `[REDACTED:BIOMETRIC]` in place says the
    mask was deliberate and tells the agent to go get the band instead.
    """
    return [{k: mask_value(k, v) for k, v in row.items()} for row in rows]


def redact_model_response(callback_context, llm_response):  # noqa: ANN001
    """ADK after_model_callback: redact raw biometric values from model text.

    Bound to all 100 agents rather than the 14 that read biometric tables.
    The other 86 cannot reach those tables at all now, so the pass is a no-op
    for them — and an unconditional rule is one fewer allowlist to keep in
    sync with the catalog.

    Returning None tells ADK to keep the original response, which is the right
    answer when nothing matched: it avoids claiming a modification we did not
    make. Parts carrying a function_call rather than text have text=None and
    are skipped.
    """
    content = getattr(llm_response, "content", None)
    if content is None or not content.parts:
        return None
    redacted = False
    for part in content.parts:
        if not part.text:
            continue
        cleaned = scrub(part.text)
        if cleaned != part.text:
            part.text = cleaned
            redacted = True
    return llm_response if redacted else None
