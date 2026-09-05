-- One row per filed rebate claim. amount_entitled and amount_claimed are
-- both recorded on the claim itself — this query does not re-derive the
-- entitled figure from contracts.rebate_schedule and contract_transactions
-- volume, so it reports the gap between what the claim states was owed and
-- what was actually invoiced, not an independent recomputation of the tier
-- the site's purchase volume crossed.
SELECT
  rc.claim_id,
  rc.contract_id,
  c.vendor_name,
  rc.period,
  rc.amount_entitled,
  rc.amount_claimed,
  ROUND(rc.amount_entitled - rc.amount_claimed, 2) AS unclaimed_rebate_usd
FROM `mining_data.rebate_claims` rc
JOIN `mining_data.contracts` c ON c.contract_id = rc.contract_id
ORDER BY unclaimed_rebate_usd DESC
