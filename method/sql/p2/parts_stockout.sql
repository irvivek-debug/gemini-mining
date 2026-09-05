-- Parts at or below their reorder_point_limit.
-- In continuous-review inventory policy a replenishment order is triggered
-- when inventory position falls TO OR BELOW the reorder point. A part sitting
-- exactly at its reorder point is the trigger event — one more unit of
-- consumption puts it below threshold with no purchase order in flight. The
-- operator is <= so that the most time-sensitive case is included.
-- The site's standard (MAINT-WOP-002 clause 4) specifies the procurement
-- action required when a lead time exceeds 14 days or 45 days respectively.
-- Columns are named for what each number actually is.
SELECT
  part_number,
  part_description,
  stock_level,
  reorder_point_limit,
  lead_time_days,
  unit_price_usd
FROM `mining_data.inventory_levels`
WHERE stock_level <= reorder_point_limit
ORDER BY stock_level ASC, lead_time_days DESC
