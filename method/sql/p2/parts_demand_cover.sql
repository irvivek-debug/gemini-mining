-- Demanded parts per work order, joined to on-hand stock and lead time.
-- work_order_parts_edge names one row per (work_order, part) pair. The join
-- to inventory_levels is on part_number. demand_count is the number of work
-- orders that name the part, not a quantity column; the edge table carries no
-- quantity, so demand_count is the best available demand signal.
-- stock_on_hand is named for what it is: the current level recorded in the
-- inventory system, not a confirmed available quantity. lead_time_days is the
-- procurement lead time as recorded; it does not account for any purchase
-- order already in flight.
-- The join covers only the 5 distinct parts named in the edge table, which is
-- a subset of the 105 SKUs in the catalogue. A LEFT JOIN is used so that any
-- edge row without a matching inventory record surfaces as NULL rather than
-- being silently dropped.
-- ASSUMPTION: inventory_levels holds exactly one row per part_number.
-- MAX() is written to survive an accidental duplicate but it does NOT surface
-- multi-location schemas as extra rows — the join predicate forces
-- il.part_number = wope.part_number, so any GROUP BY on il.part_number
-- produces the same groups as GROUP BY on wope.part_number alone.
-- A fork whose inventory_levels carries one row per warehouse location must
-- confirm that these four columns represent site-wide totals before drawing
-- any cover conclusion. Verify by checking part_number uniqueness in
-- inventory_levels before running this diagnostic.
SELECT
  wope.part_number,
  COUNT(wope.work_order_id)          AS demand_count,
  MAX(il.stock_level)                AS stock_on_hand,
  MAX(il.reorder_point_limit)        AS reorder_point_limit,
  MAX(il.lead_time_days)             AS lead_time_days,
  MAX(il.unit_price_usd)             AS unit_price_usd
FROM `mining_data.work_order_parts_edge` wope
LEFT JOIN `mining_data.inventory_levels` il
  ON wope.part_number = il.part_number
GROUP BY wope.part_number
ORDER BY demand_count DESC
