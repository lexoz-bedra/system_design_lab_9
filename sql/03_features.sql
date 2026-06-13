SELECT
    cd.pickup_at,
    cd.trip_distance,
    cd.fare_amount,
    cd.passenger_count,
    cd.pickup_zone_id,
    cd.dropoff_zone_id,
    COALESCE(pu.zone_name || ', ' || pu.borough, CAST(cd.pickup_zone_id AS VARCHAR)) AS pickup_zone,
    COALESCE(do_.zone_name || ', ' || do_.borough, CAST(cd.dropoff_zone_id AS VARCHAR)) AS dropoff_zone,
    cd.processed_at,
    hour(cd.pickup_at) AS hour,
    dayofweek(cd.pickup_at) AS day_of_week,
    epoch(cd.dropoff_at - cd.pickup_at) / 60.0 AS trip_duration_min
FROM current_data cd
LEFT JOIN zones pu ON cd.pickup_zone_id = pu.location_id
LEFT JOIN zones do_ ON cd.dropoff_zone_id = do_.location_id
WHERE
    cd.fare_amount BETWEEN 1 AND 500
    AND cd.trip_distance BETWEEN 0.1 AND 100
    AND cd.passenger_count BETWEEN 1 AND 6
    AND epoch(cd.dropoff_at - cd.pickup_at) / 60.0 BETWEEN 1 AND 180
