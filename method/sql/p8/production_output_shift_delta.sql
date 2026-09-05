-- Bands the two daily production readings (concentrator recovery, crusher
-- feed rate) into the two reporting periods this driver compares. The two
-- series are unioned under a metric_name column rather than joined, because
-- they come from different tables at the same daily grain and neither is a
-- key for the other.
WITH readings AS (
  SELECT 'recovery_rate_pct' AS metric_name, DATE(timestamp) AS day,
         recovery_rate_pct AS value
  FROM `mining_data.metallurgical_recovery`
  UNION ALL
  SELECT 'feed_rate_tph' AS metric_name, DATE(timestamp) AS day,
         feed_rate_tph AS value
  FROM `mining_data.crusher_states`
)
SELECT
  metric_name,
  CASE
    WHEN day BETWEEN DATE(@recent_start) AND DATE(@recent_end) THEN 'recent'
    WHEN day BETWEEN DATE(@prior_start) AND DATE(@prior_end) THEN 'prior'
  END AS period,
  COUNT(*) AS reading_count,
  AVG(value) AS mean_value
FROM readings
WHERE day BETWEEN DATE(@prior_start) AND DATE(@recent_end)
GROUP BY metric_name, period
