import os
import requests

ZONE_URL = 'https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv'
ZONE_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'taxi_zone_lookup.csv'))


def ensure_downloaded():
    if os.path.exists(ZONE_CSV):
        return
    os.makedirs(os.path.dirname(ZONE_CSV), exist_ok=True)
    r = requests.get(ZONE_URL, timeout=15)
    r.raise_for_status()
    with open(ZONE_CSV, 'wb') as f:
        f.write(r.content)
