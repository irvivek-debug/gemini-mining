-- One row per contract that has at least one settled transaction.
-- above_agreed_count is transactions paid at more than the contract's own
-- agreed_unit_price; leakage_usd sums only the positive gap (a transaction
-- paid below the agreed price contributes zero, not a negative offset, so a
-- large underpayment cannot mask a separate overpayment elsewhere in the
-- same contract).
SELECT
  t.contract_id,
  ANY_VALUE(t.vendor_name) AS vendor_name,
  ANY_VALUE(t.part_number) AS part_number,
  ANY_VALUE(c.agreed_unit_price) AS agreed_unit_price,
  COUNT(*) AS transaction_count,
  COUNTIF(t.paid_unit_price > c.agreed_unit_price) AS above_agreed_count,
  ROUND(AVG(t.paid_unit_price - c.agreed_unit_price), 2) AS mean_variance_usd,
  ROUND(SUM(GREATEST(t.paid_unit_price - c.agreed_unit_price, 0)), 2) AS leakage_usd
FROM `mining_data.contract_transactions` t
JOIN `mining_data.contracts` c ON c.contract_id = t.contract_id
GROUP BY t.contract_id
ORDER BY leakage_usd DESC
