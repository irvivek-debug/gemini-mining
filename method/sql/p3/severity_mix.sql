-- The share column is each severity level's proportion of the total incident
-- count, expressed as a percentage rounded to one decimal place. It is a
-- share of recorded incidents, not a share of exposure or risk; a level with
-- a high share is a level that appears often in the log, and nothing more.
-- The incident_count column is reported alongside the share so the caller can
-- assess the cell size before drawing any comparison across levels.
SELECT
  severity_level,
  COUNT(*) AS incident_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS share_pct
FROM `mining_data.safety_incidents`
GROUP BY severity_level
ORDER BY incident_count DESC
