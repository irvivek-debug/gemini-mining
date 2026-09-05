-- crusher_states is itself a daily roll-up of the 2-hourly telemetry, so the
-- torque column below is a maximum over DAILY MEAN torque, not an
-- instantaneous peak. It is named for what it is; headroom against an
-- instantaneous alarm cannot be established from this table.
WITH cs AS (
  SELECT DATE(timestamp) AS d, AVG(gap_size_setting_mm) AS gap,
         AVG(feed_rate_tph) AS tph, MAX(rotational_torque_nm) AS torque_max
  FROM `mining_data.crusher_states` GROUP BY d
),
m AS (
  SELECT DATE(timestamp) AS d, AVG(recovery_rate_pct) AS rec,
         AVG(tailings_grade_pct) AS tails, AVG(feed_grade_pct) AS feed
  FROM `mining_data.metallurgical_recovery` GROUP BY d
)
SELECT
  CASE WHEN gap <= @tight_max THEN 'tight'
       WHEN gap >= @wide_min  THEN 'wide'
       ELSE 'mid' END AS band,
  COUNT(*) AS days,
  ROUND(AVG(gap), 1)    AS gap_mm,
  ROUND(AVG(rec), 2)    AS recovery_pct,
  ROUND(AVG(tails), 4)  AS tailings_pct,
  ROUND(AVG(feed), 3)   AS feed_pct,
  ROUND(AVG(tph), 0)    AS throughput_tph,
  ROUND(MAX(torque_max), 0) AS daily_mean_torque_max_nm
FROM m JOIN cs USING (d)
GROUP BY band
ORDER BY gap_mm
