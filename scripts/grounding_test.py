"""Prove an agent reads real data, rather than answering from memory.

THE PROBLEM THIS EXISTS FOR
All 100 registered agents were built as LlmAgent(name, model, instruction) with
no tools. They cannot reach BigQuery at all. They answered fluently -- citing
ISO 37001, FIDIC, IMSBC -- and every figure came from model knowledge. The UAT
scored 98/100 because it checked whether an answer looked right, never whether
it came from anywhere.

So this asks a different question: is the number the agent reports the number
that is actually in the warehouse RIGHT NOW?

THE THREE GATES
  1. NO HARDCODING     ground truth is computed from BigQuery at test time, not
                       stored in the test. If the data changes, the expected
                       answer changes with it, and an agent replaying a
                       memorised figure drifts out of tolerance.
  2. REAL SOURCE       the agent's answer must match that live value within
                       tolerance. A plausible number is a failure.
  3. GROUNDING + MATHS the agent must name the table it read, and any
                       arithmetic it shows is recomputed independently.

A probe is only usable if its answer CANNOT be guessed. "What is a typical
copper recovery?" is guessable -- a model will say 88-92% and hit by luck.
"What is the mean recovery_rate_pct in metallurgical_recovery?" has one right
answer to two decimals, and no prior gets there.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is unset. Copy .env.example to .env and fill it in "
            "(see docs/RECREATE.md)."
        )
    return value


PROJECT = _required("GOOGLE_CLOUD_PROJECT")
SPECS = ROOT / "data" / "grounding" / "probes.json"


@dataclass
class Probe:
    """One unfakeable question, and how to know the true answer."""
    agent_id: str
    question: str            # what to ask the agent
    truth_sql: str           # computes the answer from BigQuery, at test time
    truth_key: str           # column of truth_sql holding the value
    tolerance_pct: float = 1.0
    must_name: list[str] = field(default_factory=list)   # tables it must cite
    # Arithmetic the agent is expected to show, recomputed independently.
    # Each entry: (label, python expression over the truth row, tolerance_pct)
    derived: list[tuple] = field(default_factory=list)


def bq(sql: str) -> list[dict]:
    p = subprocess.run(["bq", f"--project_id={PROJECT}", "query", "--nouse_legacy_sql",
                        "--format=json", "--max_rows=100", sql],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"ground-truth query failed:\n{p.stderr.strip()[:300]}")
    return json.loads(p.stdout or "[]")


NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def numbers_in(text: str) -> list[float]:
    out = []
    for m in NUM.finditer(text or ""):
        try:
            out.append(float(m.group(0).replace(",", "")))
        except ValueError:
            pass
    return out


def within(value: float, target: float, tol_pct: float) -> bool:
    if target == 0:
        return abs(value) <= tol_pct / 100
    return abs(value - target) / abs(target) * 100 <= tol_pct


def evaluate(probe: Probe, reply: str) -> dict:
    """Score one reply against live ground truth."""
    row = bq(probe.truth_sql)
    if not row:
        return {"error": "ground-truth query returned no rows"}
    truth = float(row[0][probe.truth_key])

    found = numbers_in(reply)
    hit = next((n for n in found if within(n, truth, probe.tolerance_pct)), None)

    # GATE 1+2: the live value has to appear. Computed now, never stored.
    matches_source = hit is not None
    # GATE 3a: it has to say where it came from, and say it as a TABLE NAME.
    # Matching the bare word was worthless: "88 assets" satisfies a check for
    # the table `assets`, and "the contract" satisfies `vendor_contracts`. A
    # citation has to look like an identifier -- backticked, dotted, or
    # underscored -- not like ordinary prose about the subject.
    low = (reply or "").lower()
    named = []
    for t in probe.must_name:
        pats = [f"`{t}`", f"mining_data.{t}", t] if "_" in t else [f"`{t}`", f"mining_data.{t}"]
        if any(pat.lower() in low for pat in pats):
            named.append(t)
    cites_source = len(named) == len(probe.must_name)
    # GATE 3b: recompute anything derived.
    derived_ok, derived_detail = True, []
    for label, expr, tol in probe.derived:
        want = eval(expr, {"__builtins__": {}}, {k: float(v) for k, v in row[0].items()
                                                 if _is_num(v)})
        got = next((n for n in found if within(n, want, tol)), None)
        derived_detail.append({"label": label, "expected": round(want, 4),
                               "found": got, "ok": got is not None})
        derived_ok &= got is not None

    checks = {"matches_live_source": matches_source,
              "cites_its_source": cites_source,
              "derived_maths_correct": derived_ok}
    return {"truth": truth, "matched_number": hit, "tables_named": named,
            "derived": derived_detail, "checks": checks,
            "passed": all(checks.values())}


def _is_num(v) -> bool:
    try:
        float(v); return True
    except (TypeError, ValueError):
        return False


def load_probes() -> list[Probe]:
    raw = json.loads(SPECS.read_text()) if SPECS.exists() else []
    return [Probe(**{**p, "derived": [tuple(d) for d in p.get("derived", [])]}) for p in raw]


if __name__ == "__main__":
    probes = load_probes()
    print(f"{len(probes)} probes defined")
    for p in probes:
        row = bq(p.truth_sql)
        print(f"  {p.agent_id:<16} truth {p.truth_key}={row[0][p.truth_key] if row else 'NONE'}"
              f"   must name {p.must_name}")
