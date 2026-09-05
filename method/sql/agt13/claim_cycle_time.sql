-- One row per filed claim. days_repair_to_filing is the gap between the
-- repair's own work order being created and the claim being filed;
-- pct_window_consumed_at_filing is how much of the entitlement's own
-- coverage_start..coverage_end span had elapsed by the filing date. The
-- second figure can exceed 100: a claim filed after coverage_end has
-- already lapsed still shows here, with a value over 100, rather than being
-- silently excluded.
SELECT
  wc.claim_id,
  wc.entitlement_id,
  wc.work_order_id,
  DATE(wo.created_at) AS repair_date,
  wc.filed_date,
  w.coverage_start,
  w.coverage_end,
  DATE_DIFF(wc.filed_date, DATE(wo.created_at), DAY) AS days_repair_to_filing,
  ROUND(
    SAFE_DIVIDE(
      DATE_DIFF(wc.filed_date, w.coverage_start, DAY),
      DATE_DIFF(w.coverage_end, w.coverage_start, DAY)
    ) * 100, 1
  ) AS pct_window_consumed_at_filing
FROM `mining_data.warranty_claims` wc
JOIN `mining_data.erp_work_orders` wo ON wo.work_order_id = wc.work_order_id
JOIN `mining_data.warranty_entitlements` w ON w.entitlement_id = wc.entitlement_id
ORDER BY wc.filed_date
