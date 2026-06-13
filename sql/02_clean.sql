SELECT
    tpep_pickup_datetime::TIMESTAMP AS pickup_at,
    tpep_dropoff_datetime::TIMESTAMP AS dropoff_at,
    trip_distance::DOUBLE AS trip_distance,
    fare_amount::DOUBLE AS fare_amount,
    passenger_count::INTEGER AS passenger_count,
    PULocationID::INTEGER AS pickup_zone_id,
    DOLocationID::INTEGER AS dropoff_zone_id,
    processed_at
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                tpep_pickup_datetime,
                tpep_dropoff_datetime,
                trip_distance,
                fare_amount,
                passenger_count,
                PULocationID,
                DOLocationID
            ORDER BY processed_at
        ) AS rn
    FROM current_data
    WHERE
        tpep_pickup_datetime IS NOT NULL
        AND tpep_dropoff_datetime IS NOT NULL
        AND trip_distance IS NOT NULL
        AND fare_amount IS NOT NULL
        AND passenger_count IS NOT NULL
        AND PULocationID IS NOT NULL
        AND DOLocationID IS NOT NULL
)
WHERE rn = 1
