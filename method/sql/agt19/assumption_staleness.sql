-- One row per metric_name (7 rows). plan_version_count is always the full
-- 6; superseded_count is how many of those 6 versions carry a
-- superseded_date, i.e. were replaced by a later value before the next
-- plan_versions.next_review_date arrived. days_stale_before_review is the
-- calendar gap between an assumption being superseded and the next
-- scheduled review that would re-test the plan against it — a large gap
-- means the group plan kept running on a superseded number for that much
-- longer before the review cadence, not the calendar, caught it.
--
-- @price_metric_name is the one metric_name this build can independently
-- verify against an observed series (contained_metal_price_deck); every
-- other metric_name carries no independent series, so its four
-- price_lag1_* / price_min_* / price_max_* columns are NULL by construction,
-- not because that metric held steady. price_lag1_autocorr is the Pearson
-- correlation between the deck's month-over-month observations and their
-- own prior month, over every consecutive pair in the deck — a property of
-- the observed series as a whole, not of any one plan version.
WITH staleness AS (
  SELECT
    a.metric_name,
    COUNT(*) AS plan_version_count,
    COUNTIF(a.superseded_date IS NOT NULL) AS superseded_count,
    ROUND(AVG(DATE_DIFF(v.next_review_date, a.superseded_date, DAY)), 1)
      AS mean_days_stale_before_review,
    MIN(DATE_DIFF(v.next_review_date, a.superseded_date, DAY))
      AS min_days_stale_before_review,
    MAX(DATE_DIFF(v.next_review_date, a.superseded_date, DAY))
      AS max_days_stale_before_review
  FROM `mining_data.plan_assumptions` a
  JOIN `mining_data.plan_versions` v ON v.plan_version_id = a.plan_version_id
  GROUP BY a.metric_name
),
deck_stats AS (
  SELECT
    ROUND(CORR(price, prev_price), 4) AS price_lag1_autocorr,
    COUNT(prev_price) AS price_lag1_pairs,
    MIN(price) AS price_min_usd_per_tonne,
    MAX(price) AS price_max_usd_per_tonne
  FROM (
    SELECT
      contained_metal_price_usd_per_tonne AS price,
      LAG(contained_metal_price_usd_per_tonne) OVER (ORDER BY price_date) AS prev_price
    FROM `mining_data.contained_metal_price_deck`
  )
)
SELECT
  s.metric_name,
  s.plan_version_count,
  s.superseded_count,
  s.mean_days_stale_before_review,
  s.min_days_stale_before_review,
  s.max_days_stale_before_review,
  CASE WHEN s.metric_name = @price_metric_name THEN d.price_lag1_autocorr END AS price_lag1_autocorr,
  CASE WHEN s.metric_name = @price_metric_name THEN d.price_lag1_pairs END AS price_lag1_pairs,
  CASE WHEN s.metric_name = @price_metric_name THEN d.price_min_usd_per_tonne END AS price_min_usd_per_tonne,
  CASE WHEN s.metric_name = @price_metric_name THEN d.price_max_usd_per_tonne END AS price_max_usd_per_tonne
FROM staleness s
CROSS JOIN deck_stats d
ORDER BY s.metric_name
