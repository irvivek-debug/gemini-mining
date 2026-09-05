-- Self-joins each route-day's AM half to its own PM half and asks whether an
-- elevated AM congestion ratio (against the route's own baseline) precedes an
-- elevated PM cycle-time ratio on the SAME route, SAME day. This is the
-- leading-indicator question: a queue observed in the morning is a candidate
-- signal for the afternoon only if it is answerable from paired same-day
-- halves, which is exactly the grain this table carries.
WITH by_half AS (
  SELECT
    h.route_id,
    DATE(h.timestamp) AS day,
    EXTRACT(HOUR FROM h.timestamp) AS hour_of_day,
    h.congestion_index / r.congestion_factor AS congestion_ratio,
    h.mean_cycle_time_mins / r.average_cycle_time_mins AS cycle_time_ratio,
    h.mean_queue_wait_mins
  FROM `mining_data.haul_cycle_log` h
  JOIN `mining_data.haulage_routes` r USING (route_id)
),
am AS (
  SELECT route_id, day, congestion_ratio AS am_congestion_ratio
  FROM by_half WHERE hour_of_day = @am_hour
),
pm AS (
  SELECT
    route_id, day,
    cycle_time_ratio AS pm_cycle_time_ratio,
    mean_queue_wait_mins AS pm_queue_wait_mins
  FROM by_half WHERE hour_of_day = @pm_hour
)
SELECT
  CASE
    WHEN am.am_congestion_ratio >= @am_congestion_ratio_high_min THEN 'am_high'
    ELSE 'am_normal'
  END AS am_band,
  COUNT(*) AS route_days,
  AVG(pm.pm_cycle_time_ratio) AS mean_pm_cycle_time_ratio,
  AVG(pm.pm_queue_wait_mins) AS mean_pm_queue_wait_mins
FROM am
JOIN pm USING (route_id, day)
GROUP BY am_band
