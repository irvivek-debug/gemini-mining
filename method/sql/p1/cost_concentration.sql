-- Repair cost by asset, with each asset's share of total cost.
-- erp_work_orders carries one row per work order; assets carries one row per
-- asset. The join is asset_id. cost_share_pct is a proportion of the total,
-- so any dropped asset will inflate the remaining shares accordingly.
WITH totals AS (
  SELECT SUM(repair_cost) AS grand_total
  FROM `mining_data.erp_work_orders`
),
by_asset AS (
  SELECT
    w.asset_id,
    a.asset_name,
    COUNT(w.work_order_id)    AS wo_count,
    SUM(w.repair_cost)        AS total_repair_cost,
    AVG(w.repair_cost)        AS mean_repair_cost
  FROM `mining_data.erp_work_orders` w
  JOIN `mining_data.assets` a USING (asset_id)
  GROUP BY w.asset_id, a.asset_name
)
SELECT
  b.asset_id,
  b.asset_name,
  b.wo_count,
  ROUND(b.total_repair_cost, 0)                                   AS total_repair_cost,
  ROUND(b.mean_repair_cost, 0)                                    AS mean_repair_cost,
  ROUND(b.total_repair_cost / t.grand_total * 100, 1)             AS cost_share_pct
FROM by_asset b
CROSS JOIN totals t
ORDER BY b.total_repair_cost DESC
