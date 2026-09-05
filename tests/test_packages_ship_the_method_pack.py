"""Gate: what the method pack needs at runtime actually reaches the container.

WHY THIS FILE EXISTS:
The whole redesign was deployed and verified live, and S07-SP3 answered by
improvising thirteen bq_query calls — exactly the natural-language-to-SQL
behaviour the redesign exists to end. Every unit test passed. The METHOD block
was correct, the pack was correct, the tools were correct. None of it was in
the container.

Three independent defects, each sufficient on its own, and none visible to any
test in this repo:

  1. `scripts.deploy.deploy` never regenerated `packages/`, so the container
     was built from a snapshot taken four days before this work existed.
  2. `method/` — the pack YAML and its SQL, both read at RUNTIME — was not in
     SHARED_TREES, so it would not have shipped even from a fresh snapshot.
  3. `pyyaml` was stripped from the container requirements on the stated
     reasoning that nothing under `mining_agents/` imports it. That reasoning
     became false the moment `mining_agents/method/pack.py` was written.

The shape of all three is the same: the deploy succeeds, the container builds,
the service answers, and the failure only appears as an agent quietly doing
the wrong thing. That is the most expensive kind of failure this repo can
have, because nothing reports it — so each one gets a test that fails loudly
in CI instead of silently in production.
"""
import ast
import subprocess
import sys
from pathlib import Path

from scripts.packages import SHARED_TREES, runtime_requirements, write_packages

REPO_ROOT = Path(__file__).resolve().parent.parent

#: import name -> distribution name, for the third-party packages
#: `mining_agents/` imports. Only the ones whose two names differ need an
#: entry; the check below falls back to the import name.
DIST_FOR_IMPORT = {
    "yaml": "pyyaml",
    "google": "google-adk",  # google.adk and google.cloud.* both live here
}

#: First-party repo trees, which are not installed from an index and so are not
#: container dependencies in the requirements sense. `infra` is imported by
#: `mining_agents/registry.py` and does NOT travel in SHARED_TREES — that is
#: safe only for as long as nothing the entrypoint imports reaches registry,
#: which `test_the_entrypoint_never_reaches_a_tree_that_does_not_travel` pins.
FIRST_PARTY = frozenset({"mining_agents", "infra", "scripts", "apps", "tests"})


def _third_party_imports_under(tree: Path) -> set[str]:
    """Top-level module names imported by every .py file under *tree*.

    Standard-library and first-party names are dropped, so what is left is
    exactly the set that must be installed in the container.
    """
    found: set[str] = set()
    for path in sorted(tree.rglob("*.py")):
        module = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return {
        name for name in found
        if name not in sys.stdlib_module_names
        and name not in FIRST_PARTY
        and not name.startswith("__")
    }


def test_the_container_requirements_cover_every_import_the_agent_tree_makes():
    """The bug this replaces a hand-maintained exclusion list to catch.

    `_TOOLING_ONLY` listed `pyyaml` with a comment explaining that nothing
    under `mining_agents/` imports it. That was true when written and false
    once the method pack landed — and a comment cannot notice when its own
    premise expires. Deriving the check from the imports themselves means the
    next runtime dependency cannot be silently stripped.
    """
    imports = _third_party_imports_under(REPO_ROOT / "mining_agents")
    assert imports, "no third-party imports found — this test would prove nothing"
    requirements = runtime_requirements()
    missing = sorted(
        name for name in imports
        if DIST_FOR_IMPORT.get(name, name) not in requirements
    )
    assert missing == [], (
        f"{missing} is imported under mining_agents/ but is not in the "
        "container requirements. The container will build, deploy and serve, "
        "and then die on the first call that reaches that import."
    )


def test_the_entrypoint_never_reaches_a_tree_that_does_not_travel():
    """`mining_agents/registry.py` imports `infra`, which is not in
    SHARED_TREES.

    The whole `mining_agents` tree is copied into every package, so that module
    ships — it simply cannot be imported in the container, because the tree it
    depends on is not there. Today nothing the entrypoint touches imports it,
    which is the only reason this is latent rather than fatal. That is a fact
    about the current import graph, not a property anyone maintains, so it is
    pinned here: an import added to `build`, `patterns` or `catalog` that
    reaches `registry` would otherwise turn a passing test suite into a
    container that dies on startup.
    """
    # A subprocess, not this interpreter: the test session has already imported
    # scripts/, tests/ and infra/ for its own reasons, so `sys.modules` here
    # answers a question about pytest rather than about the container.
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "import mining_agents.build\n"
        "roots = {m.split('.')[0] for m in sys.modules}\n"
        "print(' '.join(sorted(roots & %r)))\n"
        % (str(REPO_ROOT), set(FIRST_PARTY - {"mining_agents"}))
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    reached = result.stdout.split()
    assert reached == [], (
        f"the entrypoint now imports {reached}, whose tree is not copied into "
        "the package. The container will fail on import, before it serves "
        "anything."
    )


def test_the_method_pack_travels_with_every_package(tmp_path):
    """The YAML and the SQL are read at runtime, exactly like references/.

    `method_lookup` resolves PACK_DIR as parents[2] of its own module, which
    inside a package is `<pkg>/method`. If the tree does not travel, every
    diagnostic returns NO_METHOD_PACK and the agent falls back to improvising
    SQL — which looks like a working agent, not like a broken deploy.
    """
    assert "method" in SHARED_TREES, (
        "method/ is not copied into the packages, so the pack cannot be read "
        "in the container"
    )
    written = write_packages(tmp_path)
    assert written, "no packages written — the loop below would prove nothing"
    for pkg in written:
        assert (pkg / "method" / "p6-metallurgist.yaml").is_file(), pkg
        assert (pkg / "method" / "sql" / "p6" / "liberation.sql").is_file(), pkg


def test_method_lookup_resolves_its_pack_from_inside_a_generated_package(tmp_path):
    """Proves the path arithmetic, not just the file copy.

    A test that only checks the files exist would still pass if PACK_DIR
    resolved somewhere else in the container layout — which is the failure
    that actually costs a container build to discover. This one imports out of
    the generated tree, in a subprocess whose sys.path is the container's, and
    asserts the tool returns a real tree rather than NO_METHOD_PACK.
    """
    write_packages(tmp_path)
    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "sys.path.insert(0, %r)\n"
        "from mining_agents.tools.method_lookup import make_method_lookup\n"
        "result = make_method_lookup('P6')()\n"
        "print(result['success'], len(result['data']['drivers']))\n"
        % (str(tmp_path / "S07"), str(tmp_path))
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    ok, drivers = result.stdout.split()
    assert ok == "True", result.stdout
    assert int(drivers) > 0, "the pack loaded but carries no drivers"


def test_run_diagnostic_finds_its_sql_from_inside_a_generated_package(tmp_path):
    """The SQL files are a second tree under method/, and copytree is not the
    only way they could go missing — an ignore pattern that excluded *.sql
    would leave the YAML in place and every driver unrunnable."""
    write_packages(tmp_path)
    pack_dir = tmp_path / "S07" / "method"
    sql_files = sorted(p.name for p in (pack_dir / "sql" / "p6").glob("*.sql"))
    source = sorted(p.name for p in (REPO_ROOT / "method" / "sql" / "p6").glob("*.sql"))
    assert source, "no source SQL found — this test would prove nothing"
    assert sql_files == source
