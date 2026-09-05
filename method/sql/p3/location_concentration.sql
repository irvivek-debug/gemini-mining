-- safety_incidents is a flat event log with no sub-table of location details;
-- the location_description column is the only spatial grain available.
-- Returning one row per (location, severity_level) pair keeps the query free
-- of string-literal predicates and lets the caller assess the severity mix
-- within each location without a pivot that would widen the row if new severity
-- categories were introduced. incident_count is reported at both the location
-- level and the (location, severity) level so the caller can assess cell sizes
-- before drawing any cross-location or within-location severity conclusion.
SELECT
  location_description,
  severity_level,
  COUNT(*) AS incident_count
FROM `mining_data.safety_incidents`
GROUP BY location_description, severity_level
ORDER BY
  SUM(COUNT(*)) OVER (PARTITION BY location_description) DESC,
  location_description,
  incident_count DESC
