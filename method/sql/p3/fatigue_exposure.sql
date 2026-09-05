-- biometric_fatigue_logs records one row per monitoring session per operator.
-- The query bands sessions by a parameterised sleep-deficit threshold
-- (@deficit_hours) so the caller can vary the threshold against the
-- OPS-FMS-001 clause 4.2 fitness-for-duty trigger (2 hours against the
-- 24-hour target). mean_sleep_deficit_hours and max_sleep_deficit_hours name
-- what the numbers are: aggregates over the deficit column, not instantaneous
-- readings. The microsleep column is a count of detected events per session;
-- microsleep_event_total is a sum across sessions in each band. distinct_operators
-- is the count of unique operator identifiers in that band and is included so
-- the caller can assess whether a band's finding rests on one or two individuals.
SELECT
  CASE
    WHEN sleep_deficit_hours >= @deficit_hours THEN 'above_threshold'
    ELSE 'below_threshold'
  END AS deficit_band,
  COUNT(*) AS log_count,
  COUNT(CASE WHEN fatigue_alert_triggered = true THEN 1 END) AS alert_count,
  ROUND(AVG(sleep_deficit_hours), 2) AS mean_sleep_deficit_hours,
  ROUND(MAX(sleep_deficit_hours), 2) AS max_sleep_deficit_hours,
  SUM(microsleep_events_detected) AS microsleep_event_total,
  COUNT(DISTINCT operator_id) AS distinct_operators
FROM `mining_data.biometric_fatigue_logs`
GROUP BY deficit_band
ORDER BY deficit_band
