-- Reuses the work-order-grain coverage join documented in
-- entitlement_coverage.sql (see that file for why the aggregation matters)
-- and keeps only repairs whose entitlement's coverage_end has already
-- passed as of @as_of_date. A returned row is repair cost that sat inside a
-- window which has now closed with no warranty_claims row ever filed
-- against it: value this build can no longer recover through the
-- entitlement, as distinct from own_cost_repairs.sql, which reports the
-- same shape of gap for windows that have not yet closed.
WITH covered AS (
  SELECT
    m.work_order_id,
    ANY_VALUE(m.asset_id) AS asset_id,
    ANY_VALUE(w.coverage_end) AS coverage_end,
    ANY_VALUE(wo.repair_cost) AS repair_cost_usd,
    LOGICAL_OR(wc.work_order_id IS NOT NULL) AS has_claim
  FROM `mining_data.maintenance_logs` m
  JOIN `mining_data.erp_work_orders` wo ON wo.work_order_id = m.work_order_id
  JOIN `mining_data.warranty_entitlements` w
    ON m.asset_id = w.asset_id
   AND DATE(wo.created_at) BETWEEN w.coverage_start AND w.coverage_end
  LEFT JOIN `mining_data.warranty_claims` wc ON wc.work_order_id = m.work_order_id
  GROUP BY m.work_order_id
)
SELECT
  work_order_id,
  asset_id,
  coverage_end,
  repair_cost_usd,
  has_claim
FROM covered
WHERE coverage_end < DATE(@as_of_date)
ORDER BY coverage_end, work_order_id
