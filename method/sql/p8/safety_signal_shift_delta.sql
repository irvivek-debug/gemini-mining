-- Bands every recorded incident into the two reporting periods this driver
-- compares. Incident volume at this operation's scale is bounded even at a
-- 60-incident-total corpus, so both counts must be read alongside the
-- severity_level breakdown, not the period total alone.
SELECT
  CASE
    WHEN DATE(timestamp) BETWEEN DATE(@recent_start) AND DATE(@recent_end) THEN 'recent'
    WHEN DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@prior_end) THEN 'prior'
  END AS period,
  severity_level,
  COUNT(*) AS incident_count
FROM `mining_data.safety_incidents`
WHERE DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@recent_end)
GROUP BY period, severity_level
