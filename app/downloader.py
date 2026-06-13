import os
import requests

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
BASE_URL = 'https://d37ci6vzurychx.cloudfront.net/trip-data'

AVAILABLE_YEARS = list(range(2022, 2025))
QUARTERS = {
    1: [1, 2, 3],
    2: [4, 5, 6],
    3: [7, 8, 9],
    4: [10, 11, 12],
}


def get_url(year: int, month: int) -> str:
    return f'{BASE_URL}/yellow_tripdata_{year}-{month:02d}.parquet'


def get_local_path(year: int, month: int) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, f'yellow_tripdata_{year}-{month:02d}.parquet')


def download_month(year: int, month: int, progress_callback=None) -> str:
    local_path = get_local_path(year, month)
    if os.path.exists(local_path):
        if progress_callback:
            progress_callback(1, 1)
        return local_path

    response = requests.get(get_url(year, month), stream=True, timeout=120)
    response.raise_for_status()

    total = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=256 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)

    return local_path


def download_quarter(year: int, quarter: int, on_progress=None) -> list[str]:
    """
    Download 3 monthly parquet files for the given quarter.
    on_progress(month_idx, month_done_bytes, month_total_bytes)
    Returns list of local filepaths.
    """
    months = QUARTERS[quarter]
    paths = []
    for i, month in enumerate(months):
        def cb(done, total, idx=i):
            if on_progress:
                on_progress(idx, done, total)
        paths.append(download_month(year, month, progress_callback=cb))
    return paths
