CREATE VIEW zones AS
SELECT
    LocationID::INTEGER AS location_id,
    Zone AS zone_name,
    Borough AS borough,
    service_zone
FROM read_csv_auto('{zone_csv}')
