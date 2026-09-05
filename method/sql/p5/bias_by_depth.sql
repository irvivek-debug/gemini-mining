-- Grade variance by depth band. Systematic model bias can concentrate at
-- depth because interpolation uncertainty grows with drill spacing, and because
-- deeper material may have been sampled under different QA/QC regimes. The
-- band cut points are parameterised because they are a planning decision that
-- belongs to the site, not a statistical optimisation we impose.
WITH sample AS (
  SELECT
    a.copper_grade_pct AS assayed,
    (a.depth_start_meters + a.depth_end_meters) / 2 AS mid_depth_m,
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
    WHEN s.mid_depth_m <= @shallow_max THEN 'shallow'
    WHEN s.mid_depth_m >= @deep_min    THEN 'deep'
    ELSE 'mid'
  END AS depth_band,
  COUNT(*)                                           AS paired_samples,
  ROUND(AVG(s.mid_depth_m), 0)                       AS mean_depth_m,
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
GROUP BY depth_band
ORDER BY mean_depth_m
