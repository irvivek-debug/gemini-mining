-- One row per plan_version_id. Every plan version in this build carries
-- exactly two plan_scenarios rows (an upside and a downside case against
-- the same assumption), so scenario_count is not itself a finding — it is
-- the fixed shape of the table. min/max/mean_reversal_cost_usd span both
-- cases; reversal_cost is the cost recorded on the scenario of reversing
-- the capital or operating decision that plan version's case supports, not
-- a probability-weighted or realised figure.
SELECT
  s.plan_version_id,
  v.published_date,
  v.next_review_date,
  COUNT(*) AS scenario_count,
  ROUND(MIN(s.reversal_cost), 2) AS min_reversal_cost_usd,
  ROUND(MAX(s.reversal_cost), 2) AS max_reversal_cost_usd,
  ROUND(AVG(s.reversal_cost), 2) AS mean_reversal_cost_usd
FROM `mining_data.plan_scenarios` s
JOIN `mining_data.plan_versions` v ON v.plan_version_id = s.plan_version_id
GROUP BY s.plan_version_id, v.published_date, v.next_review_date
ORDER BY v.published_date
