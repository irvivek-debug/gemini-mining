-- Approval audit trail. Backs SC-4 — required by the HITL design.
CREATE TABLE IF NOT EXISTS `mining_data.agent_approvals` (
  approval_id              STRING  NOT NULL,
  agent_id                 STRING  NOT NULL,
  action_type              STRING  NOT NULL,   -- STAND_DOWN | SETPOINT_CHANGE | PO_RAISE | ...
  target_entity            STRING,
  decision                 STRING  NOT NULL,   -- APPROVED | CANCELLED | EXPIRED
  approver_principal       STRING  NOT NULL,
  decided_at               TIMESTAMP NOT NULL,
  hold_duration_ms         INT64,
  agent_reasoning_snapshot STRING  NOT NULL,   -- stored, never re-derived
  unverified_flags         ARRAY<STRING>,
  source_tables            ARRAY<STRING>
) PARTITION BY DATE(decided_at) CLUSTER BY agent_id, action_type;

-- Every agent invocation, for the accelerator metrics in the PRD.
CREATE TABLE IF NOT EXISTS `mining_data.agent_run_log` (
  run_id        STRING NOT NULL,
  agent_id      STRING NOT NULL,
  parent_run_id STRING,                        -- set on swarm specialists → A2A lineage
  pattern       STRING NOT NULL,               -- A | B
  status        STRING NOT NULL,               -- DONE | BLOCKED | ERROR
  blocked_reason STRING,
  started_at    TIMESTAMP NOT NULL,
  ended_at      TIMESTAMP,
  tables_read   ARRAY<STRING>,
  rows_scanned  INT64
) PARTITION BY DATE(started_at) CLUSTER BY agent_id, status;

-- Registry of the 100 agents. Single source of truth — replaces agent_manifest.json.
CREATE TABLE IF NOT EXISTS `mining_data.agent_catalog` (
  agent_id      STRING NOT NULL,
  display_name  STRING NOT NULL,
  pattern       STRING NOT NULL,               -- A | B
  swarm_id      STRING,                        -- null for Pattern B
  swarm_role    STRING,                        -- COORDINATOR | SPECIALIST | CRITIC
  apqc_code     STRING NOT NULL,
  persona       STRING NOT NULL,               -- P1..P8
  value_branch  STRING NOT NULL,               -- B1..B6
  model_tier    STRING NOT NULL,               -- reasoning | balanced
  hitl_required BOOL   NOT NULL,
  -- REQUIRED: must contain at least one table name. BigQuery cannot enforce ARRAY non-emptiness
  -- (NOT NULL is rejected on ARRAY, and an omitted value lands as [] not NULL), so this is
  -- enforced by the catalog loader.
  source_tables ARRAY<STRING>
);

ALTER TABLE `mining_data.agent_approvals`
  SET OPTIONS (partition_expiration_days = 90);
ALTER TABLE `mining_data.agent_run_log`
  SET OPTIONS (partition_expiration_days = 90);
