import pathlib
import re
import subprocess

from mining_agents.config import settings

REQUIRED = ["agent_catalog", "agent_approvals", "agent_run_log", "v_fatigue_scored"]

# ---------------------------------------------------------------------------
# Offline: DDL portability check (no BigQuery needed)
# ---------------------------------------------------------------------------

# A three-part backtick reference (`project.dataset.table`) means a project ID
# has been hardcoded.  The allowed form in this repo is two-part: `dataset.table`.
# Each segment is matched as one-or-more identifier characters (word chars + hyphens),
# which covers GCP project IDs (which may contain hyphens) while preventing the
# pattern from spanning across separate backtick references or numeric literals.
_THREE_PART_RE = re.compile(r"`[\w-]+\.[\w-]+\.[\w-]+`")


def _bq_objects():
    s = settings()
    out = subprocess.run(
        [s.bq_binary, "ls", "--max_results=1000", f"{s.project_id}:{s.dataset}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return out


def test_all_additive_objects_exist():
    out = _bq_objects()
    missing = [name for name in REQUIRED if name not in out]
    assert missing == [], f"missing BigQuery objects: {missing}"


def test_no_hardcoded_project_id_in_any_checked_in_sql():
    """Every .sql file in the repo must use unqualified two-part table names.

    A three-part backtick reference (`project.dataset.table`) pins the SQL to a
    specific GCP project and makes the accelerator un-forkable without a sed pass.
    The allowed form is `dataset.table` — the project is resolved at runtime by
    BigQuery from the job's project context.

    The scan covers the whole repo rather than infra/ddl/ alone. It was scoped
    to that one directory, and the two files under data/models/ escaped it with
    ninety-odd hardcoded references between them: a rule that only inspects the
    place you first found the problem does not prevent the second instance.

    Guard: assert the file list is non-empty and has the expected size FIRST.
    An empty glob must not silently pass this test.
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    sql_files = sorted(
        path for path in root.rglob("*.sql")
        if ".git" not in path.parts and "generated" not in path.parts
    )

    # Population pin — must come before the offender scan.
    assert len(sql_files) >= 4, (
        f"expected at least 4 .sql files in the repo, found {len(sql_files)}: "
        f"{[str(p) for p in sql_files]}"
    )

    offenders = sorted(
        str(path.relative_to(root))
        for path in sql_files
        if _THREE_PART_RE.search(path.read_text())
    )

    assert offenders == [], (
        f"hardcoded project IDs found in checked-in SQL "
        f"(use `dataset.table` not `project.dataset.table`): {offenders}"
    )


def test_v_fatigue_scored_never_exposes_raw_heart_rate():
    s = settings()
    out = subprocess.run(
        [s.bq_binary, "query", "--use_legacy_sql=false", "--nouse_cache",
         "--format=csv", "--max_rows=5",
         f"SELECT * FROM `{s.project_id}.{s.dataset}.v_fatigue_scored` LIMIT 5"],
        capture_output=True, text=True, check=True,
    ).stdout
    header = out.splitlines()[0].lower()
    # DLP requirement: none of the sensitive numeric inputs may appear in the view
    assert "heart_rate_bpm" not in header
    assert "sleep_deficit_hours" not in header
    assert "microsleep_events_detected" not in header
    assert "fatigue_band" in header
