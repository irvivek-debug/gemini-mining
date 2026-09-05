-- Compare daily delivered feed grade against the block-model mean. This
-- diagnostic bridges the geological and metallurgical records: the block model
-- predicts a grade before mining; the feed grade is measured at the plant after
-- ore has been mined, hauled, blended and crushed. A persistent gap between
-- them is consistent with a model bias, but cannot establish causation — it
-- may also reflect selective mining, blending of off-specification ore, or
-- measurement differences between the two protocols.
SELECT
  COUNT(*) AS day_count,
  ROUND(AVG(feed_grade_pct), 4)    AS daily_mean_feed_grade,
  ROUND(STDDEV(feed_grade_pct), 4) AS daily_stddev_feed_grade,
  ROUND(
    (SELECT AVG(copper_grade_pct_est) FROM `mining_data.geological_block_models`),
    4
  ) AS block_model_mean_grade,
  ROUND(
    AVG(feed_grade_pct) - (SELECT AVG(copper_grade_pct_est)
                            FROM `mining_data.geological_block_models`),
    4
  ) AS feed_vs_model_variance,
  ROUND(
    SAFE_DIVIDE(
      AVG(feed_grade_pct) - (SELECT AVG(copper_grade_pct_est)
                              FROM `mining_data.geological_block_models`),
      (SELECT AVG(copper_grade_pct_est) FROM `mining_data.geological_block_models`)
    ) * 100,
    1
  ) AS feed_vs_model_variance_pct
FROM `mining_data.metallurgical_recovery`
