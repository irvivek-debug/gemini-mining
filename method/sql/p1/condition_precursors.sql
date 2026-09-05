-- Per asset-day, whether any telemetry metric on that asset exceeded @sigma
-- standard deviations from its series mean (excursion band vs normal band),
-- against the work order rate in the following @window_days.
-- Returns one row per band so that the separation between bands is legible.
-- A flat result — equal rates across bands — is a finding about this dataset
-- and must be reported as such. The query does not distinguish which metric
-- caused an excursion; the excursion_rate diagnostic carries that detail.
WITH stats AS (
  SELECT
    asset_id,
    metric_name,
    AVG(metric_value)    AS series_mean,
    STDDEV(metric_value) AS series_sd
  FROM `mining_data.telemetry_stream`
  GROUP BY asset_id, metric_name
),
daily_excursions AS (
  SELECT
    t.asset_id,
    DATE(t.timestamp)                                                    AS obs_date,
    LOGICAL_OR(ABS(t.metric_value - s.series_mean) > @sigma * s.series_sd) AS had_excursion
  FROM `mining_data.telemetry_stream` t
  JOIN stats s USING (asset_id, metric_name)
  GROUP BY t.asset_id, DATE(t.timestamp)
),
wo_daily AS (
  SELECT asset_id, DATE(created_at) AS wo_date, COUNT(*) AS wo_count
  FROM `mining_data.erp_work_orders`
  GROUP BY asset_id, DATE(created_at)
),
joined AS (
  SELECT
    d.asset_id,
    d.obs_date,
    d.had_excursion,
    COALESCE(
      SUM(w.wo_count), 0
    )                                                                    AS wo_in_window
  FROM daily_excursions d
  LEFT JOIN wo_daily w
    ON  d.asset_id = w.asset_id
    AND w.wo_date BETWEEN d.obs_date
                      AND DATE_ADD(d.obs_date, INTERVAL @window_days DAY)
  GROUP BY d.asset_id, d.obs_date, d.had_excursion
)
SELECT
  IF(had_excursion, 'excursion', 'normal')                               AS band,
  COUNT(*)                                                                AS asset_days,
  ROUND(AVG(wo_in_window), 4)                                            AS mean_wo_in_window_per_asset_day
FROM joined
GROUP BY had_excursion
ORDER BY had_excursion DESC
