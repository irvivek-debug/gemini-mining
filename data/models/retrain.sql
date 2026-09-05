-- =============================================================================
-- Task 10 — retrain the seven BQML models against the regenerated data.
--
-- ARCHITECTURE IS UNCHANGED. Every statement below reproduces the model's
-- original CREATE OR REPLACE MODEL statement, recovered from
-- `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT (the models were all created
-- 2026-06-20). Same MODEL_TYPE, same OPTIONS, same feature list, same joins,
-- same filters. Only the underlying table contents differ, because Task 8
-- replaced the ten source tables.
--
-- ONE deviation from the recovered text, which was otherwise byte-faithful:
-- INFORMATION_SCHEMA returned every table and model fully qualified, with the
-- demo project as a third name part. Those are written here in the two-part
-- dataset.table form, matching infra/ddl/, so a fork can run this against its
-- own project without a sed pass. Supply the project on the command line:
--
--   bq query --use_legacy_sql=false --nouse_cache \
--     --project_id="${GOOGLE_CLOUD_PROJECT}" < data/models/retrain.sql
--
-- tests/test_infra_ddl.py enforces the two-part form across all checked-in SQL.
--
-- Model names: the plan and design docs call these "the four
-- `downtime_regression_model*` models". The deployed names are actually
-- `downtime_regression_model`, `inventory_impact_model_pump`,
-- `inventory_impact_model_mill`, `inventory_impact_model_crusher` — four
-- LINEAR_REG models whose label is `total_downtime_duration`. A fifth,
-- `inventory_impact_model`, is the one the plan names separately. Verified by
-- `bq ls --models`; do not trust the doc naming.
--
-- -----------------------------------------------------------------------------
-- !! PREFLIGHT — RUN SECTION 0 FIRST. DO NOT RUN SECTION B WHILE IT REPORTS 0 !!
-- -----------------------------------------------------------------------------
-- HISTORY. The first Task-10 attempt found the live
-- `maintenance_logs.parts_replaced` array EMPTY on all 152 rows, which left the
-- five Section B models with zero training rows (they reach `inventory_levels`
-- only through UNNEST(parts_replaced) -> part_number, and a BigQuery join that
-- matches nothing succeeds silently at zero rows). Root cause was a missing
-- `--parquet_enable_list_inference` on `bq load`: without it a 3-level parquet
-- LIST group is not mapped onto a BigQuery ARRAY.
--
-- That defect is FIXED. As of the Task-10b run the live table carries 186
-- element values across 126 of 152 rows and Section 0 reports non-zero for all
-- seven models, so Sections A and B have both been executed.
--
-- The preflight is kept, and Section B remains gated on it: it is cheap, and
-- the failure mode it guards (CREATE OR REPLACE MODEL destroying a deployed
-- model and replacing it with nothing) is not recoverable.
--
-- SECTION C adds ONE NEW MODEL, `telemetry_alarm_risk_model`. It is not one of
-- the seven and does not replace any of them. Architecture change was approved
-- for that model only; the seven above are a pure data refresh.
-- =============================================================================


-- =============================================================================
-- SECTION 0 — PREFLIGHT. Every count must be > 0 before the matching model in
-- Section A/B may be retrained. Zero means "do not run"; it does not mean
-- "the query is broken".
-- =============================================================================

WITH downtime_regression AS (
  SELECT AVG(i.lead_time_days) AS lead_time_days,
         AVG(i.stock_level) AS stock_level,
         SUM(m.actual_duration_hours) AS total_downtime_duration
  FROM `mining_data.inventory_levels` AS i
  JOIN `mining_data.maintenance_logs` AS m
    ON i.part_number = m.parts_replaced[SAFE_OFFSET(0)]
  GROUP BY m.asset_id
),
inventory_impact AS (
  SELECT m.asset_id
  FROM `mining_data.maintenance_logs` AS m
  CROSS JOIN UNNEST(m.parts_replaced) AS part_number
  INNER JOIN `mining_data.inventory_levels` AS i
    ON part_number = i.part_number
  INNER JOIN `mining_data.erp_work_orders` AS e
    ON m.work_order_id = e.work_order_id
  WHERE m.asset_id IN ('MILL-01', 'PUMP-104A', 'CRUSHER-03')
  GROUP BY m.asset_id
),
per_asset AS (
  SELECT t3.asset_id
  FROM `mining_data.maintenance_logs` AS t1
  CROSS JOIN UNNEST(t1.parts_replaced) AS part_name
  INNER JOIN `mining_data.inventory_levels` AS t2
    ON part_name = t2.part_number
  INNER JOIN `mining_data.assets` AS t3
    ON t1.asset_id = t3.asset_id
),
asset_clustering AS (
  SELECT t1.asset_id
  FROM `mining_data.erp_work_orders` AS t1
  JOIN `mining_data.maintenance_logs` AS t2
    ON t1.asset_id = t2.asset_id
  GROUP BY t1.asset_id
),
safety AS (
  SELECT s.severity_level
  FROM `mining_data.biometric_fatigue_logs` AS b
  INNER JOIN `mining_data.incident_involvements` AS i
    ON b.operator_id = i.operator_id
  INNER JOIN `mining_data.safety_incidents` AS s
    ON i.incident_id = s.incident_id
)
SELECT
  (SELECT COUNT(*) FROM safety)           AS safety_model_rows,            -- A1
  (SELECT COUNT(*) FROM asset_clustering) AS asset_clustering_model_rows,  -- A2
  (SELECT COUNT(*) FROM downtime_regression) AS downtime_regression_model_rows, -- B1
  (SELECT COUNT(*) FROM inventory_impact) AS inventory_impact_model_rows,  -- B2
  (SELECT COUNTIF(asset_id = 'PUMP-104A')  FROM per_asset) AS inventory_impact_model_pump_rows,    -- B3
  (SELECT COUNTIF(asset_id = 'MILL-01')    FROM per_asset) AS inventory_impact_model_mill_rows,    -- B4
  (SELECT COUNTIF(asset_id = 'CRUSHER-03') FROM per_asset) AS inventory_impact_model_crusher_rows, -- B5
  (SELECT SUM(ARRAY_LENGTH(parts_replaced))
     FROM `mining_data.maintenance_logs`) AS parts_replaced_values;


-- =============================================================================
-- SECTION A — EXECUTED. Training data intact; retrained on the regenerated
-- tables. Neither statement touches `parts_replaced`.
-- =============================================================================

-- A1. safety_model — retrained on the corrected fatigue physiology.
--     Source: biometric_fatigue_logs (regenerated) x incident_involvements x
--     safety_incidents (both static reference tables, not rewritten).
CREATE OR REPLACE MODEL `mining_data.safety_model`
OPTIONS(
  MODEL_TYPE='LOGISTIC_REG',
  INPUT_LABEL_COLS=['severity']
) AS
SELECT
  COALESCE(b.heart_rate_bpm, 0) AS heart_rate_bpm,
  COALESCE(b.microsleep_events_detected, 0) AS microsleep_events_detected,
  s.severity_level AS severity
FROM
  `mining_data.biometric_fatigue_logs` AS b
INNER JOIN
  `mining_data.incident_involvements` AS i
ON
  b.operator_id = i.operator_id
INNER JOIN
  `mining_data.safety_incidents` AS s
ON
  i.incident_id = s.incident_id;


-- A2. asset_clustering_model — retrained for consistency.
--     Source: erp_work_orders x maintenance_logs (both regenerated).
CREATE OR REPLACE MODEL `mining_data.asset_clustering_model`
OPTIONS(MODEL_TYPE='KMEANS', NUM_CLUSTERS=4)
AS
SELECT
  t1.asset_id,
  SUM(t1.repair_cost) AS total_repair_cost,
  SUM(t2.actual_duration_hours) AS total_downtime_duration,
  ANY_VALUE(t1.priority) AS asset_criticality
FROM
  `mining_data.erp_work_orders` AS t1
JOIN
  `mining_data.maintenance_logs` AS t2
ON
  t1.asset_id = t2.asset_id
GROUP BY
  t1.asset_id;


-- =============================================================================
-- SECTION B — EXECUTED (Task 10b), after the `parts_replaced` load defect was
-- fixed. Section 0 now reports 5 / 3 / 46 / 36 / 36 training rows for
-- B1..B5 respectively. DDL is byte-identical to what the first attempt left
-- here; only the underlying table contents changed.
-- =============================================================================

-- B1. downtime_regression_model
CREATE OR REPLACE MODEL `mining_data.downtime_regression_model`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['total_downtime_duration'])
AS
SELECT
  AVG(i.lead_time_days) AS lead_time_days,
  AVG(i.stock_level) AS stock_level,
  SUM(m.actual_duration_hours) AS total_downtime_duration
FROM
  `mining_data.inventory_levels` AS i
JOIN
  `mining_data.maintenance_logs` AS m
ON
  i.part_number = m.parts_replaced[SAFE_OFFSET(0)]
GROUP BY
  m.asset_id;


-- B2. inventory_impact_model
CREATE OR REPLACE MODEL `mining_data.inventory_impact_model`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['total_downtime_duration'])
AS
WITH aggregated_data AS (
  SELECT
    m.asset_id,
    AVG(i.unit_price_usd) AS unit_price_usd,
    AVG(i.stock_level) AS stock_level,
    AVG(i.lead_time_days) AS lead_time_days,
    SUM(m.actual_duration_hours) AS total_downtime_duration
  FROM
    `mining_data.maintenance_logs` AS m
  CROSS JOIN
    UNNEST(m.parts_replaced) AS part_number
  INNER JOIN
    `mining_data.inventory_levels` AS i ON part_number = i.part_number
  INNER JOIN
    `mining_data.erp_work_orders` AS e ON m.work_order_id = e.work_order_id
  WHERE
    m.asset_id IN ('MILL-01', 'PUMP-104A', 'CRUSHER-03')
  GROUP BY
    m.asset_id
)
SELECT
  unit_price_usd,
  stock_level,
  lead_time_days,
  total_downtime_duration
FROM
  aggregated_data;


-- B3. inventory_impact_model_pump   (PUMP-104A)
CREATE OR REPLACE MODEL `mining_data.inventory_impact_model_pump`
OPTIONS(MODEL_TYPE = 'LINEAR_REG', INPUT_LABEL_COLS = ['total_downtime_duration'], L2_REG = 0.1) AS
SELECT
  t1.actual_duration_hours AS total_downtime_duration,
  t2.stock_level,
  t2.lead_time_days
FROM `mining_data.maintenance_logs` AS t1
CROSS JOIN UNNEST(t1.parts_replaced) AS part_name
INNER JOIN `mining_data.inventory_levels` AS t2 ON part_name = t2.part_number
INNER JOIN `mining_data.assets` AS t3 ON t1.asset_id = t3.asset_id
WHERE t3.asset_type = 'PUMP' AND t3.asset_id IN ('PUMP-104A');


-- B4. inventory_impact_model_mill   (MILL-01)
CREATE OR REPLACE MODEL `mining_data.inventory_impact_model_mill`
OPTIONS(MODEL_TYPE = 'LINEAR_REG', INPUT_LABEL_COLS = ['total_downtime_duration'], L2_REG = 0.1) AS
SELECT
  t1.actual_duration_hours AS total_downtime_duration,
  t2.stock_level,
  t2.lead_time_days
FROM `mining_data.maintenance_logs` AS t1
CROSS JOIN UNNEST(t1.parts_replaced) AS part_name
INNER JOIN `mining_data.inventory_levels` AS t2 ON part_name = t2.part_number
INNER JOIN `mining_data.assets` AS t3 ON t1.asset_id = t3.asset_id
WHERE t3.asset_type = 'GRINDING_MILL' AND t3.asset_id = 'MILL-01';


-- B5. inventory_impact_model_crusher   (CRUSHER-03)
CREATE OR REPLACE MODEL `mining_data.inventory_impact_model_crusher`
OPTIONS(MODEL_TYPE = 'LINEAR_REG', INPUT_LABEL_COLS = ['total_downtime_duration'], L2_REG = 0.1) AS
SELECT
  t1.actual_duration_hours AS total_downtime_duration,
  t2.stock_level,
  t2.lead_time_days
FROM `mining_data.maintenance_logs` AS t1
CROSS JOIN UNNEST(t1.parts_replaced) AS part_name
INNER JOIN `mining_data.inventory_levels` AS t2 ON part_name = t2.part_number
INNER JOIN `mining_data.assets` AS t3 ON t1.asset_id = t3.asset_id
WHERE t3.asset_type = 'CRUSHER' AND t3.asset_id IN ('CRUSHER-03');


-- =============================================================================
-- SECTION C — NEW MODEL: `telemetry_alarm_risk_model`
--
-- This is the eighth model and the only one whose architecture is new. It is
-- additive: it replaces none of the seven above and none of them feed it.
--
-- WHY IT EXISTS
-- -------------
-- The Task 10 brief's headline acceptance test is "ML.PREDICT on PUMP-104A
-- returns a materially worse outcome inside the degradation ramp than outside
-- it". None of the seven can satisfy that: not one of them reads
-- `telemetry_stream`, none has a time-varying feature, and their label is
-- repair-hours. The ramp has no path into their input vector. This model gives
-- the shared `bqml_predict` tool something that has actually seen telemetry.
--
-- FORMULATION — why a hazard probability, not a time-to-failure regression
-- ----------------------------------------------------------------------
-- A time-to-failure (RUL) regression needs observed failure events to regress
-- against. This dataset contains exactly ONE degradation episode (PUMP-104A,
-- final 21 days) and no recorded failure. A TTF label would therefore be a
-- relabelling of "hours until the end of the table" fitted on a single episode,
-- which is not estimable and would not generalise.
--
-- What IS estimable from 13 series x 2004 samples is a discrete-time hazard:
--   P(this series breaches its alarm threshold at some point in the next 7 days)
-- Every series contributes both positives and negatives, and the quantity is
-- the one a maintenance planner actually acts on. Rising probability is the
-- "materially worse outcome" the brief asks for.
--
-- ALARM THRESHOLD
-- ---------------
-- Per (asset, metric): mu0 + 3*sd0, where mu0/sd0 are that series' own
-- commissioning baseline, computed over a FIXED reference period
-- 2026-01-01 .. 2026-03-01. The reference period is chosen to end well before
-- the ramp (2026-05-26 22:00) so that the ramp cannot inflate its own
-- threshold. A per-series 3-sigma band is the standard condition-monitoring
-- alarm; it is not tuned to any asset.
--
-- NO LABEL LEAKAGE — the six features are, deliberately:
--   z_now         current sample, in baseline sigma
--   z_mean_24h    trailing 24 h mean, in baseline sigma
--   z_mean_72h    trailing 72 h mean, in baseline sigma
--   z_trend_48h   trailing-24 h mean minus the preceding-24 h mean (slope)
--   z_vol_72h     trailing 72 h standard deviation, in baseline sigma
--   peer_z_24h    mean z_mean_24h of the SAME asset's OTHER metrics at time t
-- Every one is a backward-looking function of `telemetry_stream` alone, all
-- available at prediction time. There is deliberately NO asset_id, NO
-- metric_name, NO timestamp, NO ramp/window flag and NO failure flag among the
-- inputs. The model cannot key on "which asset" or "when"; it can only key on
-- what the sensors are doing. All window frames are RANGE-over-seconds rather
-- than ROWS so that the ~0.4 % telemetry dropouts do not shift a lookback.
-- The label window is strictly `1 FOLLOWING .. 604800 FOLLOWING` seconds, so no
-- future sample can reach a feature.
--
-- TRAINING WINDOW — the ramp is held out
-- --------------------------------------
-- Training rows are 2026-03-01 00:00 .. 2026-05-19 22:00. The upper bound is
-- ramp_start (2026-05-26 22:00) minus the 7-day label horizon, so neither a
-- feature nor a label of any training row can touch the ramp. The ramp is
-- therefore a genuine out-of-sample period: if the model separates ramp from
-- flat, it did so by generalising a degradation signature learned from ordinary
-- excursions on all five assets, not by memorising this episode.
-- Training set: 12,411 rows after NULL filtering, 630 positives (5.1 %).
-- =============================================================================

CREATE OR REPLACE MODEL `mining_data.telemetry_alarm_risk_model`
OPTIONS(
  MODEL_TYPE = 'LOGISTIC_REG',
  INPUT_LABEL_COLS = ['alarm_within_7d'],
  DATA_SPLIT_METHOD = 'AUTO_SPLIT',
  L2_REG = 0.1,
  MAX_ITERATIONS = 50
) AS
WITH t AS (
  SELECT asset_id, metric_name, timestamp, metric_value, UNIX_SECONDS(timestamp) AS ts
  FROM `mining_data.telemetry_stream`
),
base AS (
  SELECT asset_id, metric_name,
         AVG(metric_value) AS mu0,
         STDDEV_SAMP(metric_value) AS sd0
  FROM t
  WHERE timestamp < TIMESTAMP('2026-03-01 00:00:00')
  GROUP BY asset_id, metric_name
),
zs AS (
  SELECT t.asset_id, t.metric_name, t.timestamp, t.ts, t.metric_value,
         b.mu0, b.sd0, (t.metric_value - b.mu0) / b.sd0 AS z
  FROM t JOIN base b USING (asset_id, metric_name)
),
win AS (
  SELECT *,
    AVG(z)              OVER w24  AS z_mean_24h,
    AVG(z)              OVER w72  AS z_mean_72h,
    STDDEV_SAMP(z)      OVER w72  AS z_vol_72h,
    SUM(z)              OVER w24  AS s24,
    COUNT(z)            OVER w24  AS c24,
    SUM(z)              OVER w48  AS s48,
    COUNT(z)            OVER w48  AS c48,
    MAX(metric_value)   OVER wfut AS fut_max,
    COUNT(metric_value) OVER wfut AS c_fut
  FROM zs
  WINDOW
    w24  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN  86400 PRECEDING AND CURRENT ROW),
    w48  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 172800 PRECEDING AND CURRENT ROW),
    w72  AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 259200 PRECEDING AND CURRENT ROW),
    wfut AS (PARTITION BY asset_id, metric_name ORDER BY ts RANGE BETWEEN 1 FOLLOWING AND 604800 FOLLOWING)
),
feat AS (
  SELECT asset_id, metric_name, timestamp,
         z AS z_now,
         z_mean_24h,
         z_mean_72h,
         z_vol_72h,
         z_mean_24h - SAFE_DIVIDE(s48 - s24, c48 - c24) AS z_trend_48h,
         IF(c_fut = 0, NULL, fut_max > mu0 + 3 * sd0) AS alarm_within_7d
  FROM win
),
peer AS (
  SELECT *,
         SAFE_DIVIDE(SUM(z_mean_24h) OVER pa - z_mean_24h, COUNT(*) OVER pa - 1) AS peer_z_24h
  FROM feat
  WINDOW pa AS (PARTITION BY asset_id, timestamp)
)
SELECT
  z_now, z_mean_24h, z_mean_72h, z_trend_48h, z_vol_72h, peer_z_24h,
  alarm_within_7d
FROM peer
WHERE timestamp >= TIMESTAMP('2026-03-01 00:00:00')
  AND timestamp <= TIMESTAMP('2026-05-19 22:00:00')
  AND z_now IS NOT NULL AND z_mean_24h IS NOT NULL AND z_mean_72h IS NOT NULL
  AND z_trend_48h IS NOT NULL AND z_vol_72h IS NOT NULL AND peer_z_24h IS NOT NULL
  AND alarm_within_7d IS NOT NULL;
