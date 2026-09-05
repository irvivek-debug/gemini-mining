-- Work order count and cost grouped by asset criticality rating.
-- Disproportionate load on the most critical assets is visible when the
-- CRITICAL tier carries a share of cost substantially greater than its share
-- of assets. assets.criticality_rating is a categorical field; the query
-- returns one row per rating so that the agent can read the proportions
-- directly without further aggregation.
SELECT
  a.criticality_rating,
  COUNT(DISTINCT w.asset_id)   AS asset_count,
  COUNT(w.work_order_id)       AS wo_count,
  ROUND(SUM(w.repair_cost), 0) AS total_repair_cost,
  ROUND(AVG(w.repair_cost), 0) AS mean_repair_cost
FROM `mining_data.erp_work_orders` w
JOIN `mining_data.assets` a USING (asset_id)
GROUP BY a.criticality_rating
ORDER BY total_repair_cost DESC
