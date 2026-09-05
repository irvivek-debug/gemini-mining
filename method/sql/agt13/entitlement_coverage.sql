-- Each asset in warranty_entitlements carries one entitlement row per
-- covered component. In this build ten entitlement rows span five assets —
-- two component-level rows per asset, and both of an asset's rows usually
-- share the same coverage_start/coverage_end. A join from a repair to
-- warranty_entitlements on asset_id alone therefore matches every component
-- entitlement on that asset, so a single repair inside a shared window is
-- counted once per matching entitlement rather than once. This query
-- aggregates to work_order_id so a repair is counted once regardless of how
-- many component entitlements on its asset it falls inside, and it reports
-- matching_entitlement_count explicitly rather than folding the multiplicity
-- away.
SELECT
  m.work_order_id,
  ANY_VALUE(m.asset_id) AS asset_id,
  COUNT(DISTINCT w.entitlement_id) AS matching_entitlement_count,
  ANY_VALUE(wo.repair_cost) AS repair_cost_usd,
  ANY_VALUE(DATE(wo.created_at)) AS repair_date,
  LOGICAL_OR(wc.work_order_id IS NOT NULL) AS has_claim
FROM `mining_data.maintenance_logs` m
JOIN `mining_data.erp_work_orders` wo ON wo.work_order_id = m.work_order_id
JOIN `mining_data.warranty_entitlements` w
  ON m.asset_id = w.asset_id
 AND DATE(wo.created_at) BETWEEN w.coverage_start AND w.coverage_end
LEFT JOIN `mining_data.warranty_claims` wc ON wc.work_order_id = m.work_order_id
GROUP BY m.work_order_id
ORDER BY m.work_order_id
