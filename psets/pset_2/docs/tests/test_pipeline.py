import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('ingest', ROOT / 'kestra/ingesta_csv.py')
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def test_backfill_covers_source_once():
    source = pd.DataFrame({'UDI': range(10000)})
    batches = [ingest.select_batch(source, i, 1300) for i in range(8)]
    combined = pd.concat(batches)
    assert len(combined) == 10000
    assert combined.UDI.is_unique
    assert combined.UDI.tolist() == source.UDI.tolist()


@pytest.mark.parametrize('batch,size', [(-2, 1000), (10, 1000), (0, 0), (0, -1)])
def test_invalid_batches_fail(batch, size):
    with pytest.raises(ValueError):
        ingest.select_batch(pd.DataFrame({'UDI': range(10000)}), batch, size)


@pytest.fixture(scope='module')
def spark():
    from pyspark.sql import SparkSession
    session = (SparkSession.builder.master('local[2]').appName('test-pset2')
               .config('spark.sql.shuffle.partitions', '2').getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    yield session
    session.stop()


def sample_frames(spark):
    facts = spark.createDataFrame([
        ('r1', 'p1', 's1', 300.0, 310.0, 1500, 40.0, 100, 0),
        ('r2', 'p1', 's1', 302.0, 312.0, 1400, 35.0, 200, 1)],
        ['READING_KEY', 'PRODUCT_KEY', 'SOURCE_KEY', 'AIR_TEMPERATURE_K',
         'PROCESS_TEMPERATURE_K', 'ROTATIONAL_SPEED_RPM', 'TORQUE_NM', 'TOOL_WEAR_MIN', 'MACHINE_FAILURE'])
    products = spark.createDataFrame([('p1', 'L123', 'L')],
                                     ['PRODUCT_KEY', 'PRODUCT_ID', 'PRODUCT_TYPE'])
    sources = spark.createDataFrame([('s1', 'uci')], ['SOURCE_KEY', 'SOURCE_NAME'])
    return facts, products, sources


def test_spark_preserves_grain_and_calculates_features(spark):
    from spark.construir_obt import build_obt
    result, metrics = build_obt(*sample_frames(spark))
    assert metrics['obt_rows'] == 2
    rows = result.orderBy('READING_KEY').collect()
    assert rows[0].TEMPERATURE_DELTA_K == 10
    assert rows[0].MECHANICAL_POWER_W == pytest.approx(6283.1853, rel=1e-6)
    assert rows[0].BASELINE_RULE_VERSION == 'UCI_PHYSICS_WEAR200_v1'
    from scripts.decision_policy import rule_alert
    assert [r.BASELINE_ALERT for r in rows] == [rule_alert(r.asDict()) for r in rows] == [0, 1]


def test_spark_rejects_join_multiplication(spark):
    from spark.construir_obt import build_obt
    facts, products, sources = sample_frames(spark)
    with pytest.raises(ValueError, match='duplicada'):
        build_obt(facts, products.union(products), sources)


def test_spark_rejects_orphan_facts(spark):
    from spark.construir_obt import build_obt
    facts, products, sources = sample_frames(spark)
    with pytest.raises(ValueError, match='sin dimensión'):
        build_obt(facts, products.filter("PRODUCT_KEY = 'missing'"), sources)

