-- Buckets every contract_transactions row by whether it can be tied to a
-- live, signed contract. no_contract is a NULL contract_id on the
-- transaction itself; unknown_contract is a non-NULL contract_id that
-- matches no row in contracts (a dangling reference, not a missing one);
-- outside_window is a transaction whose own date falls before
-- effective_from or after effective_to of the contract it cites.
SELECT
  CASE
    WHEN t.contract_id IS NULL THEN 'no_contract'
    WHEN c.contract_id IS NULL THEN 'unknown_contract'
    WHEN t.transaction_date BETWEEN c.effective_from AND c.effective_to THEN 'valid_window'
    ELSE 'outside_window'
  END AS coverage_state,
  COUNT(*) AS transaction_count
FROM `mining_data.contract_transactions` t
LEFT JOIN `mining_data.contracts` c ON c.contract_id = t.contract_id
GROUP BY coverage_state
ORDER BY coverage_state
