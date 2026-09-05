-- Open backlog aged against the dataset's own maximum date.
-- Age is computed relative to MAX(created_at) in the table so that the query
-- produces the same answer on any fork, regardless of when it is run.
-- Only OPEN and IN_PROGRESS work orders are in scope. COMPLETED and CANCELLED
-- orders carry no open remediation path; the exclusion uses an array parameter
-- with NOT IN UNNEST so that no string literal appears in a comparison predicate.
-- Rows are banded by @stale_days: orders at or older than that threshold are
-- "stale", others are "fresh". The >= boundary aligns with MAINT-WOP-002
-- clause 3.1, which specifies that a work order reaching the review-trigger
-- age must be reviewed — a work order at exactly @stale_days days has reached
-- the trigger. The threshold is a parameter rather than a constant so the
-- site's own standard (MAINT-WOP-002 clause 3) governs the boundary.
WITH max_date AS (
  SELECT MAX(created_at) AS ds
  FROM `mining_data.erp_work_orders`
),
aged AS (
  SELECT
    wo.work_order_id,
    wo.status,
    wo.priority,
    wo.repair_cost,
    DATE_DIFF(DATE(md.ds), DATE(wo.created_at), DAY) AS age_days
  FROM `mining_data.erp_work_orders` wo
  CROSS JOIN max_date md
  WHERE wo.status NOT IN UNNEST(@exclude_statuses)
)
SELECT
  CASE WHEN age_days >= @stale_days THEN 'stale' ELSE 'fresh' END AS age_band,
  status,
  COUNT(work_order_id)               AS wo_count,
  ROUND(AVG(age_days), 1)            AS mean_age_days,
  ROUND(AVG(repair_cost), 2)         AS mean_repair_cost_usd
FROM aged
GROUP BY age_band, status
ORDER BY age_band DESC, status
