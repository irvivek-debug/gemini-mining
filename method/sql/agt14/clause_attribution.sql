-- One row per contract clause that a settled transaction actually breaches.
--
-- Scope is deliberately narrow and is stated rather than implied: the only
-- breach `contract_transactions` can evidence is a unit price paid above the
-- one the contract agreed, so this attributes overpayments to the clause that
-- fixes the price -- the PRICE clause type, bound as @clause_type -- and to
-- no other clause. A rebate
-- that was never claimed, a duplicate payment and a late delivery each breach
-- a different clause, and each is measured by its own driver against its own
-- table; inventing rows for them here would attribute a number to a clause
-- this query never tested.
--
-- recoverable_usd sums only the positive gap, for the same reason
-- price_variance does: a transaction settled below the agreed price
-- contributes zero rather than a negative offset, so an underpayment on one
-- line cannot quietly cancel an overpayment on another within one contract.
--
-- The clause type is bound as @clause_type rather than written inline. It
-- reads like a constant, but a literal in a predicate is exactly what
-- assert_no_interpolation exists to catch, and the rule does not carve out
-- literals that happen to look safe today.
--
-- clause_id and source_uri travel with every row so a finding cites the clause
-- and the document it is written in, which is the whole point of the driver —
-- a bare price mismatch names no obligation, and an obligation nobody can read
-- is not evidence.
SELECT
  cl.clause_id,
  cl.clause_type,
  cl.recoverable_basis,
  t.contract_id,
  ANY_VALUE(t.vendor_name) AS vendor_name,
  ANY_VALUE(t.part_number) AS part_number,
  ANY_VALUE(c.agreed_unit_price) AS agreed_unit_price,
  COUNT(*) AS breaching_transaction_count,
  ROUND(SUM(t.paid_unit_price - c.agreed_unit_price), 2) AS recoverable_usd,
  ANY_VALUE(cl.source_uri) AS source_uri
FROM `mining_data.contract_transactions` t
JOIN `mining_data.contracts` c
  ON c.contract_id = t.contract_id
JOIN `mining_data.contract_clauses` cl
  ON cl.contract_id = t.contract_id
 AND cl.clause_type = @clause_type
WHERE t.paid_unit_price > c.agreed_unit_price
GROUP BY cl.clause_id, cl.clause_type, cl.recoverable_basis, t.contract_id
ORDER BY recoverable_usd DESC
