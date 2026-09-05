-- Repair cost grouped by priority level, ordered LOW → CRITICAL.
-- erp_work_orders carries one row per work order across all statuses.
-- mean_repair_cost_usd and total_repair_cost_usd are named for what they are:
-- the recorded cost at the time the work order was written, not a settled
-- invoice. The scope covers all statuses so that open and in-progress work
-- orders are included; the metric this diagnostic supports is cost per
-- completed work order, not cost of completed work orders only.
SELECT
  priority,
  COUNT(work_order_id)               AS wo_count,
  ROUND(AVG(repair_cost), 2)         AS mean_repair_cost_usd,
  ROUND(SUM(repair_cost), 2)         AS total_repair_cost_usd
FROM `mining_data.erp_work_orders`
GROUP BY priority
ORDER BY
  CASE priority
    WHEN 'LOW'      THEN 1
    WHEN 'MEDIUM'   THEN 2
    WHEN 'HIGH'     THEN 3
    WHEN 'CRITICAL' THEN 4
    ELSE 5
  END
