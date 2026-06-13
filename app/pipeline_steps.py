import os
import duckdb
import pandas as pd
from .zones import ZONE_CSV, ensure_downloaded

SQL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sql'))

STEPS = [
    {
        'id': 'raw',
        'name': 'Сырые данные',
        'file': '01_raw.sql',
        'desc': 'Данные из источника без изменений (за исключением поля processed_dttm)',
    },
    {
        'id': 'clean',
        'name': 'Очистка данных',
        'file': '02_clean.sql',
        'desc': 'Каст типов, удаление null, дедупликация',
    },
    {
        'id': 'features',
        'name': 'Подготовка',
        'file': '03_features.sql',
        'desc': 'Удаление выбросов и извлечение признаков для модели hour, day_of_week, trip_duration_min',
    },
]

SAMPLE_ROWS = 8


def _filepath_expr(filepath) -> str:
    if isinstance(filepath, list):
        escaped = ', '.join(f"'{p.replace(chr(39), chr(39)*2)}'" for p in filepath)
        return f'[{escaped}]'
    return f"'{filepath.replace(chr(39), chr(39)*2)}'"


def _read_sql(filename: str, filepath) -> str:
    path = os.path.join(SQL_DIR, filename)
    with open(path) as f:
        sql = f.read()
    return sql.replace('{filepath}', _filepath_expr(filepath))


def _df_to_sample(df: pd.DataFrame) -> dict:
    sample = df.head(SAMPLE_ROWS).copy()
    for col in sample.columns:
        if pd.api.types.is_datetime64_any_dtype(sample[col]):
            sample[col] = sample[col].astype(str)
        elif pd.api.types.is_float_dtype(sample[col]):
            sample[col] = sample[col].apply(lambda x: round(x, 4) if pd.notnull(x) else None)
        elif pd.api.types.is_integer_dtype(sample[col]):
            sample[col] = sample[col].apply(lambda x: int(x) if pd.notnull(x) else None)
        else:
            sample[col] = sample[col].where(pd.notnull(sample[col]), None)
    return {
        'columns': list(sample.columns),
        'rows': [list(row) for row in sample.itertuples(index=False, name=None)],
    }


def run_pipeline(filepath, on_step=None):
    ensure_downloaded()
    con = duckdb.connect()
    zones_sql_path = os.path.join(SQL_DIR, 'zones.sql')
    if os.path.exists(ZONE_CSV) and os.path.exists(zones_sql_path):
        sql = open(zones_sql_path).read().replace('{zone_csv}', ZONE_CSV)
        con.execute(sql)
    else:
        con.execute("CREATE TABLE zones (location_id INTEGER, zone_name VARCHAR, borough VARCHAR, service_zone VARCHAR)")
    results = []
    prev_count = None
    current_df = None

    for i, step in enumerate(STEPS):
        sql = _read_sql(step['file'], filepath)

        if i > 0 and current_df is not None:
            con.register('current_data', current_df)

        current_df = con.execute(sql).df()
        row_count = len(current_df)

        result = {
            'id': step['id'],
            'name': step['name'],
            'desc': step['desc'],
            'rows_before': prev_count,
            'rows_after': row_count,
            'removed': (prev_count - row_count) if prev_count is not None else None,
            'sample': _df_to_sample(current_df),
        }
        results.append(result)
        prev_count = row_count

        if on_step:
            on_step(result)

    con.close()
    return results, current_df
