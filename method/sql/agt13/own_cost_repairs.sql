-- Reuses the work-order-grain coverage join documented in
-- entitlement_coverage.sql. Keeps only repairs whose entitlement's
-- coverage_end has NOT yet passed as of @as_of_date and which carry no
-- warranty_claims row: repair cost currently being absorbed by the site's
-- own maintenance budget while the entitlement that would recover it is
-- still open, as distinct from expired_unclaimed.sql, which reports the
-- same shape of gap for windows that have already closed.
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
  repair_cost_usd
FROM covered
WHERE coverage_end >= DATE(@as_of_date)
  AND NOT has_claim
ORDER BY repair_cost_usd DESC
