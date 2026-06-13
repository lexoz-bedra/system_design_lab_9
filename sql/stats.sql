SELECT
    count(*) AS total_rows,
    round(avg(fare_amount), 2) AS avg_fare,
    round(avg(trip_distance), 2) AS avg_distance,
    round(avg(trip_duration_min), 2) AS avg_duration,
    min(pickup_at)::varchar AS date_from,
    max(pickup_at)::varchar AS date_to
FROM df
