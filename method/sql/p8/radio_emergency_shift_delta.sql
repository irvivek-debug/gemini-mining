-- Bands every radio transmission into the two reporting periods this driver
-- compares. emergency_count is a count of transmissions the transcription
-- system flagged with the emergency_keyword_flag; mean_sentiment_score is
-- the mean of a continuous score derived from transcript text — a
-- statistical summary of recorded language, not a direct measurement of
-- operator state.
SELECT
  CASE
    WHEN DATE(timestamp) BETWEEN DATE(@recent_start) AND DATE(@recent_end) THEN 'recent'
    WHEN DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@prior_end) THEN 'prior'
  END AS period,
  COUNT(*) AS transmission_count,
  SUM(CAST(emergency_keyword_flag AS INT64)) AS emergency_count,
  AVG(sentiment_score) AS mean_sentiment_score
FROM `mining_data.radio_communications`
WHERE DATE(timestamp) BETWEEN DATE(@prior_start) AND DATE(@recent_end)
GROUP BY period
