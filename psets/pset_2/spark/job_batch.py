"""Lee el mismo CSV limpio y compara el agregado Spark con Pandas y dbt."""
import hashlib
import os
from pathlib import Path

import duckdb
import pandas as pd
from pyspark.sql import SparkSession, functions as F
from scripts.common import report
from scripts.warehouse_local import paths


def main():
    clean,warehouse=paths()
    expected=pd.read_csv(clean)
    spark=(SparkSession.builder.master('local[2]').appName('pset2-rubrica-batch')
           .config('spark.sql.shuffle.partitions','2').getOrCreate())
    spark.sparkContext.setLogLevel('WARN')
    try:
        frame=spark.read.csv(str(clean),header=True,inferSchema=True)
        if frame.count()!=len(expected) or frame.select('READING_KEY').distinct().count()!=len(expected):
            raise ValueError('Spark no conserva el grano del archivo limpio')
        aggregate=(frame.groupBy('SOURCE_SHA256','TYPE').agg(F.count('*').alias('OBSERVATIONS'),
                    F.sum('MACHINE_FAILURE').alias('FAILURES'),F.avg('MACHINE_FAILURE').alias('FAILURE_RATE'),
                    F.avg('TORQUE_NM').alias('AVG_TORQUE_NM')))
        actual=aggregate.toPandas().sort_values(['SOURCE_SHA256','TYPE']).reset_index(drop=True)
        with duckdb.connect(str(warehouse),read_only=True) as db:
            dbt=db.execute('SELECT * FROM main.mart_fallas_por_tipo ORDER BY SOURCE_SHA256,TYPE').df()
        pandas=(expected.groupby(['SOURCE_SHA256','TYPE']).agg(OBSERVATIONS=('READING_KEY','size'),
                FAILURES=('MACHINE_FAILURE','sum'),FAILURE_RATE=('MACHINE_FAILURE','mean'),AVG_TORQUE_NM=('TORQUE_NM','mean')).reset_index())
        actual=actual[dbt.columns]
        pd.testing.assert_frame_equal(actual,dbt,check_dtype=False,rtol=1e-9,atol=1e-9)
        pd.testing.assert_frame_equal(actual,pandas[dbt.columns],check_dtype=False,rtol=1e-9,atol=1e-9)
        target=Path(os.environ.get('PSET2_DATA_DIR','data'))/'processed/mart_spark.csv'
        actual.to_csv(target,index=False)
        report('spark_local.json',{'clean_rows':len(expected),'spark_rows':len(expected),'mart_groups':len(actual),
            'matches_dbt':True,'matches_pandas':True,'clean_sha256':hashlib.sha256(clean.read_bytes()).hexdigest(),
            'question':'Proporcion de fallas observadas por tipo y version de fuente', 'mart':actual.to_dict('records')})
    finally:
        spark.stop()


if __name__=='__main__':
    main()
