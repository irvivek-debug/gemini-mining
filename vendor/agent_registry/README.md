# Vendored agent registry source

`catalog_definitions.py` and `agent_manifest.json` are copied verbatim from the
mining-agents vault:

    gs://your-gcp-project-id-mining-agents-vault/services/agent_registry_service/

They are vendored rather than referenced because the generators that read them
(`scripts/build_frontend_data.py`, `scripts/build_data_graph.py`) previously
pointed at a session scratchpad. When that scratchpad was cleaned up the
generators could no longer run, and a front end that cannot be regenerated from
its source is a snapshot pretending to be a build step.

To refresh after a vault change:

    gsutil cp gs://your-gcp-project-id-mining-agents-vault/services/agent_registry_service/catalog_definitions.py vendor/agent_registry/
    gsutil cp gs://your-gcp-project-id-mining-agents-vault/agent_manifest.json vendor/agent_registry/
    python scripts/build_frontend_data.py
