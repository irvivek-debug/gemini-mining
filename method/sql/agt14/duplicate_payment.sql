-- Self-joins invoices on vendor_name and amount for pairs whose payment_date
-- falls within @fuzzy_days of each other. exact_duplicate pairs also share
-- an identical invoice_number; fuzzy_duplicate pairs match on vendor,
-- amount and a close date but carry two different invoice_number values —
-- the shape a resubmitted invoice takes. day_gap is not selected in the
-- final aggregate; it is the join predicate, not the finding.
WITH pairs AS (
  SELECT
    a.invoice_id AS invoice_id_a,
    b.invoice_id AS invoice_id_b,
    a.vendor_name,
    a.amount,
    a.invoice_number AS invoice_number_a,
    b.invoice_number AS invoice_number_b
  FROM `mining_data.invoices` a
  JOIN `mining_data.invoices` b
    ON a.vendor_name = b.vendor_name
   AND a.amount = b.amount
   AND a.invoice_id < b.invoice_id
   AND ABS(DATE_DIFF(a.payment_date, b.payment_date, DAY)) <= @fuzzy_days
)
SELECT
  CASE
    WHEN invoice_number_a = invoice_number_b THEN 'exact_duplicate'
    ELSE 'fuzzy_duplicate'
  END AS match_type,
  COUNT(*) AS pair_count,
  ROUND(SUM(amount), 2) AS amount_at_risk_usd
FROM pairs
GROUP BY match_type
ORDER BY match_type
