"""Chunking is pure, so it is tested without GCS or BigQuery."""
from scripts.build_doc_chunks import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("a short manual page") == ["a short manual page"]


def test_long_text_splits_with_overlap():
    body = "x" * 2000
    chunks = chunk_text(body, size=800, overlap=100)
    assert len(chunks) == 3, chunks
    assert all(len(c) <= 800 for c in chunks)
    # Overlap exists so a sentence spanning a boundary is retrievable.
    assert chunks[0][-100:] == chunks[1][:100]


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_no_character_is_dropped_at_any_length():
    """The windowing loses nothing — the property the other tests only imply.

    A review of this file argued the range stop drops the tail just past one
    window, reading range(0, 701, 700) as [0]. It is [0, 700], so the tail is
    covered. The claim was wrong but the gap in the tests was real: nothing
    here exercised a length between one window and two. This does, and it
    checks the property directly rather than a chunk count.

    Chunks overlap by `overlap`, so concatenating the first chunk with each
    later chunk minus its leading overlap reconstructs the input exactly.
    """
    for length in list(range(1, 1700)) + [2000, 2400, 3500]:
        body = "x" * length
        chunks = chunk_text(body, size=800, overlap=100)
        rebuilt = chunks[0] + "".join(c[100:] for c in chunks[1:])
        assert len(rebuilt) == length, (
            f"length {length} lost {length - len(rebuilt)} characters"
        )
        assert all(len(c) <= 800 for c in chunks), length
