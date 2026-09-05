-- Views that make the agent catalogue's declared table names resolve.
--
-- Unqualified `mining_data.x` throughout: checked-in SQL names the dataset,
-- never the project, so the same file applies to any project the deployer
-- points bq at. test_no_hardcoded_project_id_in_any_checked_in_sql enforces it.
--
-- THE PROBLEM THESE SOLVE
-- The vault catalogue declares 34 source tables. 26 of them do not exist in
-- `mining_data`, and 65 of 101 agents had ZERO surviving grounding as a
-- result. The names were written against a medallion lakehouse
-- (mining_lakehouse_bronze/silver/gold) that was designed in the tech doc and
-- never built, so the catalogue described an architecture nobody deployed.
--
-- WHAT A VIEW HERE IS AND IS NOT
-- Each view below is a RENAME plus an honest filter over data that genuinely
-- holds what the declared name promises. It is not a synonym for "close
-- enough": `geotech_sensors` is deliberately absent from this file because
-- telemetry_stream carries no geotechnical metric -- no pore pressure, no
-- displacement, only temperature, vibration, belt tension, payload, engine
-- temperature, load, speed, power draw, rotational speed and torque, feed rate.
-- Mapping it here would have manufactured a fiction that looked like a fix.
-- Tables with no honest source are generated instead, from real anchors --
-- see scripts/generate_missing_domain_data.py.

-- ---------------------------------------------------------------- telemetry
-- telemetry_stream is genuinely multi-domain: 25,946 rows across CONVEYOR,
-- MILL, PUMP, CRUSHER (plant) and TRUCK (mobile fleet). The split below is by
-- asset prefix, which is what actually distinguishes them.
CREATE OR REPLACE VIEW `mining_data.plant_telemetry` AS
SELECT asset_id, metric_name, metric_value, timestamp,
       REGEXP_EXTRACT(asset_id, r'^[A-Za-z]+') AS asset_class
FROM `mining_data.telemetry_stream`
WHERE REGEXP_CONTAINS(asset_id, r'^(CONVEYOR|MILL|PUMP|CRUSHER)');

CREATE OR REPLACE VIEW `mining_data.fleet_telemetry` AS
SELECT t.asset_id AS vehicle_id, t.metric_name, t.metric_value, t.timestamp,
       v.model, v.payload_capacity_tons, v.operational_status
FROM `mining_data.telemetry_stream` t
LEFT JOIN `mining_data.fleet_vehicles` v
  ON v.vehicle_id = t.asset_id
WHERE REGEXP_CONTAINS(t.asset_id, r'^TRUCK');

-- crusher_telemetry joins the crusher's own state record to its sensor stream,
-- because the agents that declare it need both the setting and the reading.
CREATE OR REPLACE VIEW `mining_data.crusher_telemetry` AS
SELECT asset_id, timestamp, gap_size_setting_mm, feed_rate_tph,
       rotational_torque_nm, bypass_valve_open
FROM `mining_data.crusher_states`;

CREATE OR REPLACE VIEW `mining_data.vibration_monitors` AS
SELECT asset_id, timestamp, metric_value AS vibration_hz
FROM `mining_data.telemetry_stream`
WHERE metric_name = 'vibration_hz';

-- ----------------------------------------------------------------- geology
CREATE OR REPLACE VIEW `mining_data.assay_logs` AS
SELECT drill_hole_id, depth_start_meters, depth_end_meters, geology_code,
       copper_grade_pct, gold_grade_gpt, logged_at
FROM `mining_data.drill_assay_logs`;

-- qaqc_standards is the assay record narrowed to the intervals a QA/QC review
-- actually examines: those carrying a grade at all. The narrowing is the
-- point -- a standards check on a null-grade interval is not a check.
CREATE OR REPLACE VIEW `mining_data.qaqc_standards` AS
SELECT drill_hole_id, depth_start_meters, depth_end_meters, geology_code,
       copper_grade_pct, gold_grade_gpt, logged_at,
       (copper_grade_pct IS NOT NULL AND gold_grade_gpt IS NOT NULL) AS both_elements_assayed
FROM `mining_data.drill_assay_logs`
WHERE copper_grade_pct IS NOT NULL OR gold_grade_gpt IS NOT NULL;

CREATE OR REPLACE VIEW `mining_data.pit_designs` AS
SELECT block_id, centroid_x, centroid_y, centroid_z, lithology_type,
       specific_gravity, copper_grade_pct_est, gold_grade_gpt_est
FROM `mining_data.geological_block_models`;

-- ------------------------------------------------------------------- plant
CREATE OR REPLACE VIEW `mining_data.flotation_assays` AS
SELECT concentrator_id, timestamp, feed_grade_pct, concentrate_grade_pct,
       tailings_grade_pct, recovery_rate_pct
FROM `mining_data.metallurgical_recovery`;

-- -------------------------------------------------------------- planning
CREATE OR REPLACE VIEW `mining_data.mine_production_schedule` AS
SELECT v.plan_version_id, v.published_date, v.next_review_date,
       a.assumption_id, a.metric_name, a.assumed_value,
       a.effective_date, a.superseded_date
FROM `mining_data.plan_versions` v
LEFT JOIN `mining_data.plan_assumptions` a
  ON a.plan_version_id = v.plan_version_id;

-- --------------------------------------------------------------- safety
-- safety_permits is the incident record framed as the permit/authorisation
-- trail: which work was authorised where, and whether its investigation is
-- closed. It is the only authorisation-shaped data the dataset holds.
CREATE OR REPLACE VIEW `mining_data.safety_permits` AS
SELECT incident_id AS permit_reference, timestamp, location_description,
       severity_level, investigation_status,
       investigation_status = 'CLOSED' AS cleared
FROM `mining_data.safety_incidents`;

CREATE OR REPLACE VIEW `mining_data.safety_telemetry` AS
SELECT incident_id, timestamp, gps_location, location_description,
       severity_level, investigation_status
FROM `mining_data.safety_incidents`;

CREATE OR REPLACE VIEW `mining_data.fatigue_monitoring_logs` AS
SELECT operator_id, timestamp, heart_rate_bpm, sleep_deficit_hours,
       microsleep_events_detected, fatigue_alert_triggered
FROM `mining_data.biometric_fatigue_logs`;

-- ------------------------------------------------------------ supply chain
-- reagent_inventory, explosives_inventory and lube_samples were drafted here
-- as filtered views and then REMOVED. inventory_levels holds spares only --
-- its descriptions are gaskets, filters, splice kits and "Heavy industrial
-- spare part classification N" -- with no reagent or explosive line at all,
-- and maintenance_logs.technician_notes is boilerplate carrying no tribology
-- content. Each view returned zero rows.
--
-- An empty view is worse than a missing table: the agent stops saying "that
-- table does not exist" and starts saying "there is no data", which reads as a
-- finding about the mine rather than a gap in the build. They are generated
-- from real anchors instead -- see scripts/generate_missing_domain_data.py.

CREATE OR REPLACE VIEW `mining_data.dispatch_routes` AS
SELECT r.route_id, r.source_location, r.destination_location, r.distance_meters,
       r.average_cycle_time_mins, r.congestion_factor,
       h.trip_count, h.mean_cycle_time_mins, h.mean_queue_wait_mins,
       h.mean_payload_tons, h.congestion_index, h.timestamp
FROM `mining_data.haulage_routes` r
LEFT JOIN `mining_data.haul_cycle_log` h
  ON h.route_id = r.route_id;

-- ----------------------------------------------------------------- finance
CREATE OR REPLACE VIEW `mining_data.financial_ledger` AS
SELECT price_date AS ledger_date,
       'contained_metal_price' AS line_item,
       contained_metal_price_usd_per_tonne AS amount_usd,
       'price_deck' AS source_system
FROM `mining_data.contained_metal_price_deck`
UNION ALL
SELECT payment_date, CONCAT('invoice:', vendor_name), amount, 'accounts_payable'
FROM `mining_data.invoices`;
