"""Carga exclusivamente el archivo limpio en un DuckDB compartido con dbt."""
import hashlib
import os
from pathlib import Path

import duckdb
import pandas as pd
from scripts.common import report


def paths():
    data=Path(os.environ.get('PSET2_DATA_DIR','data')).resolve()
    return data/'processed/ai4i_clean.csv', data/'warehouse/pset2.duckdb'


def main():
    clean,warehouse=paths()
    warehouse.parent.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(clean)
    if df.empty or not df.READING_KEY.is_unique:
        raise ValueError('Archivo limpio vacio o con claves duplicadas')
    with duckdb.connect(str(warehouse)) as db:
        db.execute('CREATE SCHEMA IF NOT EXISTS raw')
        db.register('clean_input',df)
        db.execute('CREATE OR REPLACE TABLE raw.ai4i_clean AS SELECT * FROM clean_input')
        stored=db.execute('SELECT COUNT(*),COUNT(DISTINCT READING_KEY) FROM raw.ai4i_clean').fetchone()
    if stored!=(len(df),len(df)):
        raise ValueError('El warehouse no coincide con el archivo limpio')
    report('warehouse_local.json',{'clean_rows':len(df),'warehouse_rows':stored[0],
           'clean_sha256':hashlib.sha256(clean.read_bytes()).hexdigest(),'duckdb_path':str(warehouse)})


if __name__=='__main__':
    main()
