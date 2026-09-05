"""Pytest configuration.

Production code *requires* the deployment variables and raises without them, so
that a missing configuration fails at import time rather than surfacing much
later as a confusing BigQuery 404 in whichever query happened to run first.

The test suite has no deployment, so it supplies deterministic stand-ins here
before any test imports the config. `setdefault` rather than assignment: a
developer running the suite against a real project keeps their own values.

These are placeholders, not a live project. Tests that need to exercise a
*specific* project spelling override the variable themselves.
"""

import os

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT_NUMBER", "000000000000")
os.environ.setdefault("VERTEX_STAGING_BUCKET", "gs://test-staging-bucket")
os.environ.setdefault("VIDEO_BUCKET", "test-video-bucket")
