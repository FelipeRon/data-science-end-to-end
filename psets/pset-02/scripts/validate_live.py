"""Ejecución integrada con credenciales existentes montadas en /credentials."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_connection import load_legacy_env
from scripts.common import connect, database


def main():
    load_legacy_env('/credentials')
    for key, value in {
        'SNOWFLAKE_ACCOUNT': 'MRIWLBX-HH95628', 'SNOWFLAKE_USER': 'PSET2_KESTRA',
        'SNOWFLAKE_ROLE': 'PSET2_INGEST', 'SNOWFLAKE_WAREHOUSE': 'PSET2_WH',
        'SNOWFLAKE_DATABASE': 'PSET2_MANTENIMIENTO',
    }.items():
        os.environ.setdefault(key, value)
    with connect() as conn:
        with conn.cursor() as cur:
            for schema in ('RAW', 'BRONZE', 'SILVER', 'GOLD', 'OBT'):
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS {database()}.{schema}')
    from scripts.run_pipeline import main as pipeline
    pipeline()


if __name__ == '__main__':
    main()
