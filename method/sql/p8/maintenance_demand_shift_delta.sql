-- Bands every work order by its created_at into the two reporting periods
-- this driver compares. priority is the ERP system's own field, applied at
-- work-order creation; it is not re-derived here.
SELECT
  CASE
    WHEN DATE(created_at) BETWEEN DATE(@recent_start) AND DATE(@recent_end) THEN 'recent'
    WHEN DATE(created_at) BETWEEN DATE(@prior_start) AND DATE(@prior_end) THEN 'prior'
  END AS period,
  COUNT(*) AS work_order_count,
  SUM(CASE WHEN priority IN UNNEST(@high_priority_values) THEN 1 ELSE 0 END)
    AS high_priority_count,
  SUM(repair_cost) AS total_repair_cost_usd
FROM `mining_data.erp_work_orders`
WHERE DATE(created_at) BETWEEN DATE(@prior_start) AND DATE(@recent_end)
GROUP BY period
