"""Cadena completa con Snowflake obligatorio y conciliacion local."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from scripts.common import report


def run(*args):
    subprocess.run(args,check=True)


def main():
    if os.environ.get('PIPELINE_TARGET','snowflake') != 'snowflake':
        raise ValueError('Snowflake es obligatorio')
    from scripts.common import key_der
    key_der()  # Credencial obligatoria antes de procesar datos.
    Path('output/cadena_completa.json').unlink(missing_ok=True)
    data=Path(os.environ.get('PSET2_DATA_DIR','/workspace/data')).resolve()
    data.mkdir(parents=True,exist_ok=True)
    os.environ['PSET2_DATA_DIR']=str(data)
    os.environ['PSET2_DUCKDB_PATH']=str(data/'warehouse/pset2.duckdb')
    Path('output').mkdir(exist_ok=True)
    # En Kestra el codigo vive en un workingDir efimero; el historico se monta aparte.
    run(sys.executable,'kestra/scripts/ingesta_historico.py')
    os.environ['SOURCE_CSV']=str(data/'raw/source.csv')
    import nbformat
    from nbclient import NotebookClient
    notebook=nbformat.read('kestra/calidad/diagnostico.ipynb',as_version=4)
    NotebookClient(notebook,timeout=300,kernel_name='python3',resources={'metadata':{'path':str(Path.cwd())}}).execute()
    nbformat.write(notebook,'output/diagnostico_ejecutado.ipynb')
    run(sys.executable,'kestra/calidad/limpiar.py')
    run(sys.executable,'kestra/scripts/warehouse_local.py')
    run('dbt','run','--project-dir','dbt','--profiles-dir','dbt')
    run('dbt','test','--project-dir','dbt','--profiles-dir','dbt')
    run(sys.executable,'spark/job_batch.py')
    run(sys.executable,'kestra/scripts/evaluar_negocio.py','--clean-csv',str(data/'processed/ai4i_clean.csv'))
    warehouse=json.loads(Path('output/warehouse_local.json').read_text())
    spark=json.loads(Path('output/spark_local.json').read_text())
    if warehouse['clean_sha256']!=spark['clean_sha256']:
        raise ValueError('Warehouse y Spark usaron archivos diferentes')
    report('cadena_local.json',{'target':'duckdb','clean_rows':warehouse['clean_rows'],
           'warehouse_rows':warehouse['warehouse_rows'],'spark_rows':spark['spark_rows'],
           'same_clean_sha256':warehouse['clean_sha256'],'dbt_run':'SUCCESS','dbt_test':'SUCCESS',
           'spark_matches_dbt':spark['matches_dbt'],'spark_matches_pandas':spark['matches_pandas']})
    for source,name in [(data/'raw/historico.csv','historico.csv'),(data/'processed/ai4i_clean.csv','ai4i_clean.csv')]:
        shutil.copy2(source,Path('output')/name)
    shutil.copy2('dbt/target/run_results.json','output/dbt_local_tests.json')
    from scripts.common import connect,database,key_der
    os.environ['DBT_ENV_SECRET_PRIVATE_KEY']=base64.b64encode(key_der()).decode()
    with connect() as conn:
        with conn.cursor() as cur:
            for schema in ('RAW','BRONZE','SILVER','GOLD','OBT'):
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS {database()}.{schema}')
    run(sys.executable,'kestra/ingesta_csv.py')
    run('dbt','build','--project-dir','dbt/snowflake','--profiles-dir','dbt/snowflake')
    run(sys.executable,'spark/construir_obt.py')
    run(sys.executable,'kestra/scripts/evaluar_negocio.py')
    report('cadena_completa.json',{'target':'snowflake','status':'SUCCESS',
           'local_reconciliation':'cadena_local.json','snowflake_layers':['RAW','BRONZE','SILVER','GOLD','OBT']})


if __name__=='__main__':
    main()
