-- Per-route mean payload against the fleet's own average rated capacity
-- (read from fleet_vehicles, not a hardcoded figure), so a fork whose fleet
-- mix changes gets a benchmark that moves with it.
WITH fleet_capacity AS (
  SELECT AVG(payload_capacity_tons) AS avg_capacity_tons
  FROM `mining_data.fleet_vehicles`
)
SELECT
  h.route_id,
  COUNT(*) AS halves,
  AVG(h.mean_payload_tons) AS mean_payload_tons,
  AVG(h.mean_payload_tons) / ANY_VALUE(fc.avg_capacity_tons) * 100 AS mean_utilization_pct
FROM `mining_data.haul_cycle_log` h
CROSS JOIN fleet_capacity fc
GROUP BY h.route_id
