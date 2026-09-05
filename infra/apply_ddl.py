"""Apply the additive-table DDL idempotently and verify the objects exist."""
from __future__ import annotations

import pathlib
import subprocess
import sys

from mining_agents.config import settings

DDL_FILES = ("agent_tables.sql", "v_fatigue_scored.sql")
REQUIRED = ("agent_catalog", "agent_approvals", "agent_run_log", "v_fatigue_scored")


def _run_statement(bq_binary: str, project_id: str, statement: str) -> None:
    """Run a single SQL statement via bq query, passing SQL on stdin."""
    subprocess.run(
        [bq_binary, "query", "--use_legacy_sql=false", "--nouse_cache",
         f"--project_id={project_id}"],
        input=statement,
        text=True,
        check=True,
    )


def apply_ddl() -> None:
    s = settings()
    ddl_dir = pathlib.Path(__file__).resolve().parent / "ddl"
    for name in DDL_FILES:
        sql = (ddl_dir / name).read_text()
        print(f"applying {name} ...")
        # Split on semicolons to run one statement at a time.
        # bq query supports only a single statement per invocation.
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        for stmt in statements:
            _run_statement(s.bq_binary, s.project_id, stmt)

    listing = subprocess.run(
        [s.bq_binary, "ls", "--max_results=1000", f"{s.project_id}:{s.dataset}"],
        capture_output=True, text=True, check=True,
    ).stdout
    missing = [obj for obj in REQUIRED if obj not in listing]
    if missing:
        sys.exit(f"DDL applied but objects missing: {missing}")
    print(f"verified: {', '.join(REQUIRED)}")


if __name__ == "__main__":
    apply_ddl()
