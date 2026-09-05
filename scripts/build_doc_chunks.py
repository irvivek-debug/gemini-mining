"""Extract the GCS PDF corpus into mining_data.doc_chunks.

The corpus is read from GCS directly. mining_data.unstructured_docs_metadata
is NOT used: every file_path it carries resolves to nothing, and its
chunk_count sums to 3,392 against the 48 chunks this script actually extracts
from the 40 objects in the bucket.
"""
from __future__ import annotations

import io
from pathlib import Path

from google.cloud import bigquery, storage
from pypdf import PdfReader

from mining_agents.config import settings

BUCKET = "mining-knowledge-base"
TABLE = "mining_data.doc_chunks"
SOP_DIR = Path(__file__).resolve().parents[1] / "method" / "sop"
SOP_FOLDER = "site-standards"
SCHEMA = [
    bigquery.SchemaField("doc_id", "STRING"),
    bigquery.SchemaField("folder", "STRING"),
    bigquery.SchemaField("file_name", "STRING"),
    bigquery.SchemaField("chunk_index", "INT64"),
    bigquery.SchemaField("chunk_text", "STRING"),
]


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping windows. Overlap keeps a sentence that
    spans a boundary retrievable from either side."""
    body = text.strip()
    if not body:
        return []
    if len(body) <= size:
        return [body]
    step = size - overlap
    return [body[i:i + size] for i in range(0, len(body) - overlap, step)]


def extract(blob) -> str:
    reader = PdfReader(io.BytesIO(blob.download_as_bytes()))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def sop_rows() -> list[dict]:
    """Chunk the standards this repository authored.

    They are markdown in the repository rather than PDFs in the bucket so that
    a reviewer can read them in a diff, and they are filed under their own
    folder so that a document we wrote is never mistaken for one the site
    supplied.
    """
    out: list[dict] = []
    for path in sorted(SOP_DIR.glob("*.md")):
        for index, chunk in enumerate(chunk_text(path.read_text())):
            out.append({
                "doc_id": f"repo://method/sop/{path.name}",
                "folder": SOP_FOLDER,
                "file_name": path.name,
                "chunk_index": index,
                "chunk_text": chunk,
            })
    return out


def rows() -> list[dict]:
    client = storage.Client()
    out = []
    for blob in client.list_blobs(BUCKET):
        if not blob.name.lower().endswith(".pdf"):
            continue
        folder, _, file_name = blob.name.rpartition("/")
        for index, chunk in enumerate(chunk_text(extract(blob))):
            out.append({
                "doc_id": blob.name,
                "folder": folder,
                "file_name": file_name,
                "chunk_index": index,
                "chunk_text": chunk,
            })
    return out


def main() -> None:
    data = rows() + sop_rows()
    if not data:
        raise SystemExit("no chunks extracted; refusing to write an empty table")
    # Pinned rather than inferred. An ambient default project would write this
    # table somewhere else and say nothing, which is the whole failure mode
    # unstructured_docs_metadata already demonstrates.
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    job = client.load_table_from_json(
        data,
        TABLE,
        job_config=bigquery.LoadJobConfig(
            schema=SCHEMA, write_disposition="WRITE_TRUNCATE"
        ),
    )
    job.result()
    print(f"loaded {len(data)} chunks from {len({r['doc_id'] for r in data})} documents")


if __name__ == "__main__":
    main()
