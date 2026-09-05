-- radio_communications records one row per transmission. The query groups by
-- an operational shift bucket derived from the timestamp hour so the caller
-- can assess whether emergency traffic concentrates in a particular part of
-- the day. The shift bucket boundaries are parameterised (@day_start_hour,
-- @afternoon_start_hour, @night_start_hour) so that a site with a different
-- roster can supply its own boundaries before drawing any shift-pattern
-- conclusion. The defaults (6, 14, 22) reflect a standard three-shift roster.
-- mean_sentiment_score is the mean of the sentiment_score column for all
-- transmissions in each bucket; it is a mean over recorded transcripts, not
-- a human-assessed distress rating. transmission_count and emergency_count
-- are reported so the caller can assess the cell size in each bucket.
SELECT
  CASE
    WHEN EXTRACT(HOUR FROM timestamp) >= @day_start_hour
         AND EXTRACT(HOUR FROM timestamp) < @afternoon_start_hour THEN 'day'
    WHEN EXTRACT(HOUR FROM timestamp) >= @afternoon_start_hour
         AND EXTRACT(HOUR FROM timestamp) < @night_start_hour     THEN 'afternoon'
    ELSE                                                                'night'
  END AS shift_bucket,
  COUNT(*) AS transmission_count,
  COUNT(CASE WHEN emergency_keyword_flag = true THEN 1 END) AS emergency_count,
  ROUND(AVG(sentiment_score), 4) AS mean_sentiment_score
FROM `mining_data.radio_communications`
GROUP BY shift_bucket
ORDER BY shift_bucket
