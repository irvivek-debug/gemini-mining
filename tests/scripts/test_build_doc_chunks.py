"""The authored site standards must reach the corpus.

The PDF corpus has no safety document, no maintenance policy and nothing on
reconciliation practice, so three guards would otherwise cite documents that do
not exist. These are authored as markdown in the repository rather than as PDFs
in the bucket, so that a reviewer can read them in a diff.
"""
from pathlib import Path

from scripts.build_doc_chunks import SOP_DIR, sop_rows

ROOT = Path(__file__).resolve().parents[2]


def test_every_authored_standard_is_picked_up():
    names = {r["file_name"] for r in sop_rows()}
    assert names == {
        "fatigue-management-standard.md",
        "work-order-prioritisation-standard.md",
        "grade-reconciliation-standard.md",
    }


def test_the_standards_are_filed_under_their_own_folder():
    # Not 'oem-equipment-manuals': a document this repository wrote must not be
    # indistinguishable from one the site supplied.
    assert {r["folder"] for r in sop_rows()} == {"site-standards"}


def test_each_standard_carries_a_retrievable_threshold():
    # A standard with no number in it cannot fence a recommendation.
    for row in sop_rows():
        assert any(ch.isdigit() for ch in row["chunk_text"]), row["file_name"]


def test_chunk_indexes_are_contiguous_per_file():
    """Verify that chunk indices are contiguous (0, 1, 2...) per file.

    The contiguity assertion guards against a future refactor that filters
    chunks without renumbering them — sop_rows() currently assigns indices
    via enumerate(), so contiguity is guaranteed by construction. The real
    value is as a regression guard: if a future refactor applies per-chunk
    filtering and forgets to renumber, this will catch it.

    The multi-chunk assertion prevents this test from passing vacuously. A
    single-chunk file makes the contiguity check bite on a list [0], which
    would pass even if future code broke renumbering on files with >1 chunk.
    """
    by_file: dict[str, list[int]] = {}
    for row in sop_rows():
        by_file.setdefault(row["file_name"], []).append(row["chunk_index"])

    # Contiguity guard against future filtering refactors that forget to renumber.
    for name, idx in by_file.items():
        assert sorted(idx) == list(range(len(idx))), name

    # Ensure the guard bites: at least one file must produce multiple chunks.
    max_chunks_per_file = max(len(idx) for idx in by_file.values())
    assert max_chunks_per_file > 1, (
        "all authored standards produced exactly one chunk; "
        "contiguity assertion cannot fail against a single-element list"
    )


def test_the_sop_directory_is_where_the_standards_live():
    assert SOP_DIR == ROOT / "method" / "sop"
