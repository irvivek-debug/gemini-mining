SELECT
  COUNTIF(bypass_valve_open) AS bypass_intervals,
  COUNT(*)                   AS intervals,
  COUNT(DISTINCT DATE(timestamp)) AS days
FROM `mining_data.crusher_states`
