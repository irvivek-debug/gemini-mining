"""One command: regenerate all ten tables and load them into BigQuery.

    python data/generator/run_all.py --dry-run   # staging only, nothing live touched
    python data/generator/run_all.py --apply     # overwrite the ten live tables

Both modes regenerate first, so a dry run exercises the whole pipeline rather
than whatever happened to be left in ``data/generated/`` from an earlier run.
Regeneration takes ~30s; the loads dominate after that.

Generation order
----------------
``GENERATORS`` is a fixed list, ordered by what reads whose output:

    telemetry     -> telemetry_stream                     (no dependencies)
    metallurgy    -> crusher_states, metallurgical_recovery
                     reads data/generated/telemetry_stream.parquet
    maintenance   -> erp_work_orders, maintenance_logs
    fatigue       -> biometric_fatigue_logs, fatigue_logs_node
    geology       -> drill_assay_logs, geological_block_models
    supply_chain  -> inventory_levels
                     reads telemetry_stream, erp_work_orders, maintenance_logs

Every generator's entry point is recorded by name because they are not uniform:
``telemetry`` exposes ``generate()``, the rest ``write_parquet()``, and
``maintenance.generate_maintenance_logs()`` takes no seed argument at all.  None
of them is called with a seed here — each defaults to ``config.SEED``.

Every generator calibrates against the frozen ``*_original_20260810`` backups,
never against a live rewritten table.  Nothing in this file changes that: it
calls the generators exactly as they are, then hands ``data/generated/*.parquet``
to :mod:`load`.

Determinism
-----------
The generator list and ``load.LOAD_ORDER`` are literal lists.  Nothing here is
seeded, nothing iterates a set or a dict whose order could vary, and no value is
derived from Python's salted ``hash()`` — so two runs in two processes issue the
same operations in the same order.

Rollback
--------
    python data/generator/load.py --rollback

restores all ten live tables from their frozen backups.  ``--dry-run`` executes
that same code path against a throwaway staging table on every run, so the
rollback is proven rather than merely documented.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
# Both roots: the generators are inconsistent about how they import each other.
# telemetry.py uses absolute `data.generator.*` imports (needs the repo root on
# the path), the rest use flat `import config` (needs this directory).
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..")))
sys.path.insert(0, _HERE)

import load as loader  # noqa: E402
from config import REWRITE_TABLES  # noqa: E402

#: (module, entry point, tables produced) in dependency order.
GENERATORS: list[tuple[str, str, list[str]]] = [
    ("telemetry", "generate", ["telemetry_stream"]),
    ("metallurgy", "write_parquet", ["crusher_states", "metallurgical_recovery"]),
    ("maintenance", "write_parquet", ["erp_work_orders", "maintenance_logs"]),
    ("fatigue", "write_parquet", ["biometric_fatigue_logs", "fatigue_logs_node"]),
    ("geology", "write_parquet", ["drill_assay_logs", "geological_block_models"]),
    ("supply_chain", "write_parquet", ["inventory_levels"]),
    # Task 2b — new tables for AGT-14/AGT-13/AGT-19, not REWRITE_TABLES (they
    # have no pre-existing profiled state to back up or roll back to; see
    # data/generator/contracts.py's module docstring). Registered here so a
    # full `regenerate()` produces their parquet alongside the other ten, but
    # loader.dry_run()/apply() do not load them — that is a one-off call to
    # load.load_table() per table, documented in the Task 2b report.
    ("contracts", "write_parquet",
     ["contracts", "contract_transactions", "rebate_claims", "invoices"]),
    ("warranty", "write_parquet", ["warranty_entitlements", "warranty_claims"]),
    ("capital", "write_parquet",
     ["plan_versions", "plan_assumptions", "plan_scenarios", "capital_options",
      "contained_metal_price_deck"]),
]


def generated_tables() -> list[str]:
    """Every table GENERATORS claims to produce, in generation order."""
    return [table for _, _, tables in GENERATORS for table in tables]


def regenerate() -> None:
    """Run every generator in dependency order and check the parquet landed."""
    missing = sorted(set(REWRITE_TABLES) - set(generated_tables()))
    if missing:
        raise RuntimeError(f"no generator produces {missing}")

    for module_name, entry_point, tables in GENERATORS:
        module = importlib.import_module(module_name)
        started = time.time()
        getattr(module, entry_point)()
        elapsed = time.time() - started
        for table in tables:
            path = loader.parquet_path(table)
            if not path.exists():
                raise RuntimeError(
                    f"{module_name}.{entry_point}() did not write {path}"
                )
        print(
            f"[GEN  ] {module_name:<14} {elapsed:5.1f}s  "
            + ", ".join(f"{t} ({loader.parquet_row_count(t)} rows)" for t in tables)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate the ten mining tables and load them to BigQuery."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="load into *_staging_ copies, verify, prove rollback, clean up",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="overwrite the ten live tables",
    )
    args = parser.parse_args(argv)

    print("=== Regenerating ===")
    regenerate()

    if args.dry_run:
        print("\n=== Dry run: staging only ===")
        loader.dry_run()
        print("\nDry run clean. Nothing live was touched.")
    else:
        print("\n=== Apply: overwriting live tables ===")
        loader.apply()
        print(
            "\nApply complete. Roll back with:\n"
            "  python data/generator/load.py --rollback"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
