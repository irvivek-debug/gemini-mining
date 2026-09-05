CREATE OR REPLACE VIEW `mining_data.v_fatigue_scored` AS
SELECT
  operator_id,
  DATE(timestamp) AS log_date,
  CASE
    WHEN sleep_deficit_hours >= 3.0 OR microsleep_events_detected >= 3 THEN 'HIGH'
    WHEN sleep_deficit_hours >= 1.5 OR microsleep_events_detected >= 1 THEN 'ELEVATED'
    ELSE 'LOW'
  END AS fatigue_band
FROM `mining_data.biometric_fatigue_logs`;
