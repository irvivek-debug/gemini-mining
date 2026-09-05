-- Bands every biometric log into the two reporting periods this driver
-- compares, and reports both the log volume and the alert count for each so
-- a change in alert RATE cannot be mistaken for a change in monitoring
-- coverage.
SELECT
  CASE
    WHEN DATE(timestamp) BETWEEN DATE(@recent_start) AND DATE(@recent_end) THEN 'recent'
    WHEN DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@prior_end) THEN 'prior'
  END AS period,
  COUNT(*) AS log_count,
  SUM(CAST(fatigue_alert_triggered AS INT64)) AS alert_count,
  COUNT(DISTINCT operator_id) AS distinct_operators
FROM `mining_data.biometric_fatigue_logs`
WHERE DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@recent_end)
GROUP BY period
