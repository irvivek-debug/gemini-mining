-- Mean, median and maximum actual_duration_hours by asset from maintenance
-- logs, with the log count. Duration is the total elapsed time from work order
-- open to close; it is an elapsed-time figure, not a wrench-time figure.
-- Elapsed time includes waiting for parts and access windows; the agent must
-- not present it as labour content without checking the notes.
SELECT
  a.asset_id,
  a.asset_name,
  COUNT(m.log_entry_id)                                                     AS log_count,
  ROUND(AVG(m.actual_duration_hours), 2)                                    AS mean_duration_hours,
  -- approx_median: APPROX_QUANTILES is probabilistic, not exact; the qualifier
  -- prevents an agent from citing this as a precise percentile boundary.
  ROUND(APPROX_QUANTILES(m.actual_duration_hours, 2)[OFFSET(1)], 1)         AS approx_median_duration_hours,
  ROUND(MAX(m.actual_duration_hours), 1)                                    AS max_duration_hours
FROM `mining_data.maintenance_logs` m
JOIN `mining_data.assets` a USING (asset_id)
GROUP BY a.asset_id, a.asset_name
ORDER BY mean_duration_hours DESC
