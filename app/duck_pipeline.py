import os
import duckdb
import pandas as pd

SQL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sql'))


def get_stats(df: pd.DataFrame) -> dict:
    sql = open(os.path.join(SQL_DIR, 'stats.sql')).read()
    con = duckdb.connect()
    con.register('df', df)
    row = con.execute(sql).fetchone()
    con.close()
    return {
        'total_rows': int(row[0]),
        'avg_fare': float(row[1]),
        'avg_distance': float(row[2]),
        'avg_duration': float(row[3]),
        'date_range': [row[4], row[5]],
    }
