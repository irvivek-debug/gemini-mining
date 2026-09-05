-- Bands each recorded half (route, AM/PM) by how far its realised congestion
-- ran above or below that ROUTE'S OWN baseline congestion_factor, then
-- compares cycle time and completed trips across the bands. Normalising to
-- each route's own baseline (rather than banding the raw congestion_index
-- pooled across routes) is what keeps a long, naturally slow route from
-- being counted as "congested" on the strength of its length alone.
WITH banded AS (
  SELECT
    h.route_id,
    h.trip_count,
    h.mean_cycle_time_mins / r.average_cycle_time_mins AS cycle_time_ratio,
    h.congestion_index / r.congestion_factor AS congestion_ratio
  FROM `mining_data.haul_cycle_log` h
  JOIN `mining_data.haulage_routes` r USING (route_id)
)
SELECT
  CASE
    WHEN congestion_ratio <= @tight_max THEN 'tight'
    WHEN congestion_ratio >= @wide_min THEN 'wide'
    ELSE 'mid'
  END AS band,
  COUNT(*) AS halves,
  AVG(cycle_time_ratio) AS mean_cycle_time_ratio,
  AVG(trip_count) AS mean_trip_count
FROM banded
GROUP BY band
