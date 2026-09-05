-- Grade variance by block-model elevation band. Topography, oxidation fronts
-- and structural controls can all produce grade patterns that correlate with
-- elevation rather than depth-below-collar. Grouping by elevation tests
-- whether the model bias is elevation-dependent and therefore possibly
-- attributable to a domain or weathering boundary. Cut points are parameterised
-- because the relevant geological boundaries are site-specific.
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
  CASE
    WHEN b.centroid_z <= @low_max  THEN 'low'
    WHEN b.centroid_z >= @high_min THEN 'high'
    ELSE 'mid'
  END AS elevation_band,
  COUNT(*)                                           AS paired_samples,
  ROUND(AVG(b.centroid_z), 0)                        AS mean_elevation_m,
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
GROUP BY elevation_band
ORDER BY mean_elevation_m
