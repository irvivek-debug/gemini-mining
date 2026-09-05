-- Per asset and metric, the count of readings beyond @sigma standard
-- deviations from that series' own mean, and the rate per 1,000 readings.
-- Each series is normalised to its own statistics so that metrics with
-- different engineering units are comparable.
-- @sigma controls sensitivity. A tighter threshold raises the rate for every
-- series; the relative ranking across assets is what the agent reads, not the
-- absolute count at a particular threshold.
WITH stats AS (
  SELECT
    asset_id,
    metric_name,
    AVG(metric_value)    AS series_mean,
    STDDEV(metric_value) AS series_sd
  FROM `mining_data.telemetry_stream`
  GROUP BY asset_id, metric_name
)
SELECT
  t.asset_id,
  t.metric_name,
  COUNT(*)                                                             AS reading_count,
  ROUND(s.series_mean, 3)                                             AS series_mean,
  ROUND(s.series_sd, 3)                                               AS series_sd,
  COUNTIF(ABS(t.metric_value - s.series_mean) > @sigma * s.series_sd) AS excursion_count,
  ROUND(
    COUNTIF(ABS(t.metric_value - s.series_mean) > @sigma * s.series_sd) * 1000.0 / COUNT(*),
    2
  )                                                                    AS excursion_rate_per_1000
FROM `mining_data.telemetry_stream` t
JOIN stats s USING (asset_id, metric_name)
GROUP BY t.asset_id, t.metric_name, s.series_mean, s.series_sd
ORDER BY t.asset_id, t.metric_name
