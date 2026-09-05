WITH cs AS (
  SELECT DATE(timestamp) AS d, AVG(gap_size_setting_mm) AS gap
  FROM `mining_data.crusher_states` GROUP BY d
),
m AS (
  SELECT DATE(timestamp) AS d, AVG(recovery_rate_pct) AS rec,
         AVG(feed_grade_pct) AS feed
  FROM `mining_data.metallurgical_recovery` GROUP BY d
),
j AS (
  -- The tiebreaker is not cosmetic: feed is rounded to 2 dp, so ties straddle
  -- a tercile boundary and an unordered NTILE assigns them arbitrarily,
  -- making the strata differ run to run.
  SELECT m.d, m.rec, m.feed, cs.gap,
         NTILE(3) OVER (ORDER BY m.feed, m.d) AS feed_tercile
  FROM m JOIN cs USING (d)
)
SELECT
  feed_tercile,
  ROUND(MIN(feed), 3) AS feed_lo,
  ROUND(MAX(feed), 3) AS feed_hi,
  COUNTIF(gap <= @tight_max) AS tight_days,
  ROUND(AVG(IF(gap <= @tight_max, rec, NULL)), 2) AS recovery_tight,
  -- The residual feed means are what make this query auditable. Controlling
  -- for feed is its entire job, so it must show how much feed imbalance is
  -- left inside each stratum rather than asking to be taken on trust.
  ROUND(AVG(IF(gap <= @tight_max, feed, NULL)), 3) AS feed_tight,
  COUNTIF(gap >= @wide_min) AS wide_days,
  ROUND(AVG(IF(gap >= @wide_min, rec, NULL)), 2) AS recovery_wide,
  ROUND(AVG(IF(gap >= @wide_min, feed, NULL)), 3) AS feed_wide
FROM j
GROUP BY feed_tercile
ORDER BY feed_tercile
