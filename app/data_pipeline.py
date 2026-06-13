import os
import pandas as pd
import numpy as np

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

REQUIRED_COLUMNS = {
    'tpep_pickup_datetime', 'tpep_dropoff_datetime',
    'trip_distance', 'fare_amount', 'passenger_count',
    'PULocationID', 'DOLocationID',
}

CHUNK_SIZE = 100_000


def load_file(filepath: str) -> pd.DataFrame:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.parquet':
        df = pd.read_parquet(filepath)
    elif ext == '.csv':
        chunks = []
        for chunk in pd.read_csv(filepath, chunksize=CHUNK_SIZE, low_memory=False):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
    else:
        raise ValueError(f'Unsupported file format: {ext}')
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f'Missing columns: {missing}')

    df = df[list(REQUIRED_COLUMNS)].copy()

    df['tpep_pickup_datetime'] = pd.to_datetime(df['tpep_pickup_datetime'], errors='coerce')
    df['tpep_dropoff_datetime'] = pd.to_datetime(df['tpep_dropoff_datetime'], errors='coerce')

    df['hour'] = df['tpep_pickup_datetime'].dt.hour
    df['day_of_week'] = df['tpep_pickup_datetime'].dt.dayofweek
    df['trip_duration_min'] = (
        (df['tpep_dropoff_datetime'] - df['tpep_pickup_datetime'])
        .dt.total_seconds() / 60
    )

    df = df.dropna()
    df = df[df['fare_amount'].between(1, 500)]
    df = df[df['trip_distance'].between(0.1, 100)]
    df = df[df['trip_duration_min'].between(1, 180)]
    df = df[df['passenger_count'].between(1, 6)]
    df['PULocationID'] = df['PULocationID'].astype(int)
    df['DOLocationID'] = df['DOLocationID'].astype(int)

    return df.reset_index(drop=True)


def get_stats(df: pd.DataFrame) -> dict:
    return {
        'total_rows': len(df),
        'avg_fare': round(float(df['fare_amount'].mean()), 2),
        'avg_distance': round(float(df['trip_distance'].mean()), 2),
        'avg_duration': round(float(df['trip_duration_min'].mean()), 2),
        'date_range': [
            str(df['tpep_pickup_datetime'].min()),
            str(df['tpep_pickup_datetime'].max()),
        ],
    }
