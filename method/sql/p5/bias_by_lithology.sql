-- Grade variance by geological domain. Each domain may carry a distinct
-- estimation error from the resource model; grouping by lithology reveals
-- whether the aggregate bias is uniform or concentrated in one or more domains.
-- The join radius is parameterised for the same reason as model_bias.sql:
-- the choice of search radius belongs to the site's reconciliation standard.
WITH sample AS (
  SELECT
    a.copper_grade_pct AS assayed,
    d.collar_easting  + (a.depth_start_meters + a.depth_end_meters) / 2
      * COS(ACOS(-1) * d.dip_degrees / 180)
      * SIN(ACOS(-1) * d.azimuth_degrees / 180) AS x,
    d.collar_northing + (a.depth_start_meters + a.depth_end_meters) / 2
      * COS(ACOS(-1) * d.dip_degrees / 180)
      * COS(ACOS(-1) * d.azimuth_degrees / 180) AS y,
    d.collar_elevation - (a.depth_start_meters + a.depth_end_meters) / 2
      * SIN(ACOS(-1) * ABS(d.dip_degrees) / 180) AS z
  FROM `mining_data.drill_assay_logs` a
  JOIN `mining_data.drill_holes` d USING (drill_hole_id)
)
SELECT
  b.lithology_type                                   AS domain,
  COUNT(*)                                           AS paired_samples,
  ROUND(AVG(b.copper_grade_pct_est), 4)              AS modelled_grade,
  ROUND(AVG(s.assayed), 4)                           AS assayed_grade,
  ROUND(AVG(s.assayed) - AVG(b.copper_grade_pct_est), 4) AS variance,
  ROUND(SAFE_DIVIDE(AVG(s.assayed) - AVG(b.copper_grade_pct_est),
                    AVG(b.copper_grade_pct_est)) * 100, 1) AS variance_pct
FROM sample s
JOIN `mining_data.geological_block_models` b
  ON ABS(b.centroid_x - s.x) <= @radius_m
 AND ABS(b.centroid_y - s.y) <= @radius_m
 AND ABS(b.centroid_z - s.z) <= @radius_m
GROUP BY b.lithology_type
ORDER BY variance_pct DESC
