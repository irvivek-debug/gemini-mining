"""Create the remote embedding model and embed mining_data.doc_chunks."""
from __future__ import annotations

import os

from google.cloud import bigquery

from mining_agents.config import settings

CONNECTION = (
    f"projects/{settings().project_id}/locations/us/connections/"
    f"{os.environ.get('BQ_CONNECTION_ID', 'gemini-connection')}"
)

MODEL_DDL = f"""
CREATE OR REPLACE MODEL `mining_data.text_embedding_model`
REMOTE WITH CONNECTION `{CONNECTION}`
OPTIONS (ENDPOINT = 'text-embedding-005')
"""

EMBED_DDL = """
CREATE OR REPLACE TABLE `mining_data.doc_chunks_embedded` AS
SELECT * EXCEPT (content), content AS chunk_text
FROM ML.GENERATE_EMBEDDING(
  MODEL `mining_data.text_embedding_model`,
  (SELECT doc_id, folder, file_name, chunk_index, chunk_text AS content
     FROM `mining_data.doc_chunks`),
  STRUCT(TRUE AS flatten_json_output, 'RETRIEVAL_DOCUMENT' AS task_type)
)
"""


def main() -> None:
    s = settings()
    client = bigquery.Client(project=s.project_id, location=s.location)
    client.query(MODEL_DDL).result()
    client.query(EMBED_DDL).result()
    row = next(iter(client.query(
        "SELECT COUNT(*) AS n FROM `mining_data.doc_chunks_embedded`"
    ).result()))
    print(f"embedded {row['n']} chunks")


if __name__ == "__main__":
    main()
