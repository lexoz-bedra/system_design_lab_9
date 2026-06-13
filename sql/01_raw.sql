SELECT
    *,
    current_timestamp AS processed_at
FROM read_parquet({filepath})
