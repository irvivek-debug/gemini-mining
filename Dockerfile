# The workspace container: both applications, plus the proxy that lets
# application 2 reach the 52 agent services.
#
# This is the only container this repository defines. The 52 agents are built
# by ADK's own `deploy cloud_run` verb, which generates its Dockerfile into a
# temp directory at deploy time — see scripts/deploy.py. So there is no
# ambiguity about which image this file produces, despite sitting at the root:
# it is the one thing here that ADK does not build for us.
#
# The build context is the repository root rather than apps/workspace/, because
# server.py derives its agent list from mining_agents.registry — the same
# function scripts/deploy.py used to create the services. That import is the
# whole guarantee that the proxy addresses services that exist, so the package
# has to be in the image.

FROM python:3.12-slim

# Unbuffered so Cloud Run's log tail shows a traceback as it happens rather
# than when the process dies. PYTHONDONTWRITEBYTECODE because the filesystem is
# ephemeral and .pyc files only add image layers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies before source, so that editing a screen does not invalidate the
# pip layer. apps/workspace/requirements.txt is the container's list and is
# deliberately not the repository's — see the comment at the top of that file.
COPY apps/workspace/requirements.txt /app/apps/workspace/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/workspace/requirements.txt

# Only what the process imports or serves. `references/` carries
# model-policy.md, which mining_agents.config reads to resolve a model tier —
# the workspace never asks for one, but the module is shared with code that
# does, and a 4 KB file is not worth a divergent import path.
COPY apps/ /app/apps/
COPY mining_agents/ /app/mining_agents/
COPY infra/ /app/infra/
COPY scripts/ /app/scripts/
COPY references/ /app/references/

# Cloud Run sends traffic to $PORT and rejects a container that binds anything
# else. The shell form is required: exec form would pass the literal string
# "$PORT" to uvicorn.
#
# One worker on purpose. The proxy is I/O-bound and async, so a second worker
# buys no throughput here, and Cloud Run's own concurrency setting is the knob
# that actually applies.
CMD exec uvicorn apps.workspace.server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
