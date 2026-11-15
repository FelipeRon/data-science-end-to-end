"""Joins en Spark; Snowflake Connector mueve solo los datos de entrada/salida.

Adecuado al AI4I de 10k filas; para volúmenes grandes usar el conector Spark-Snowflake
distribuido en lugar de fetch_pandas_all/toPandas.
"""
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.common import connect, database, report
from scripts.decision_policy import assumptions, spark_rule_expression


def build_obt(facts, products, sources):
    from pyspark.sql import functions as F
    for name, frame, key in (("facts", facts, "READING_KEY"),
                              ("products", products, "PRODUCT_KEY"),
                              ("sources", sources, "SOURCE_KEY")):
        if frame.filter(F.col(key).isNull()).limit(1).count():
            raise ValueError(f"Clave nula en {name}")
        if frame.count() != frame.select(key).distinct().count():
            raise ValueError(f"Clave duplicada en {name}")
    expected = facts.count()
    if expected == 0:
        raise ValueError("Gold vacío")
    if facts.join(products, "PRODUCT_KEY", "left_anti").limit(1).count():
        raise ValueError("Hechos sin dimensión de producto")
    if facts.join(sources, "SOURCE_KEY", "left_anti").limit(1).count():
        raise ValueError("Hechos sin dimensión de fuente")
    obt = (facts.join(products, "PRODUCT_KEY", "inner")
           .join(sources, "SOURCE_KEY", "inner")
           .withColumn("TEMPERATURE_DELTA_K",
                       F.col("PROCESS_TEMPERATURE_K") - F.col("AIR_TEMPERATURE_K"))
           .withColumn("MECHANICAL_POWER_W", F.col("TORQUE_NM")
                       * F.col("ROTATIONAL_SPEED_RPM") * F.lit(2 * 3.141592653589793 / 60)))
    obt = (obt.withColumn("BASELINE_ALERT", spark_rule_expression())
           .withColumn("BASELINE_RULE_VERSION", F.lit(assumptions()['rule']['version'])))
    # Tipos de fallo y discrepancias revelan el target. No son features de predicción.
    obt = obt.drop("TWF", "HDF", "PWF", "OSF", "RNF", "FAILURE_FLAG_MISMATCH")
    actual = obt.count()
    if actual != expected or obt.select("READING_KEY").distinct().count() != expected:
        raise ValueError("Los joins cambiaron el grano o el número de observaciones")
    return obt, {"gold_rows": expected, "obt_rows": actual, "duplicate_reading_keys": 0}


def main():
    import pandas as pd
    from pyspark.sql import SparkSession
    from snowflake.connector.pandas_tools import write_pandas
    spark = (SparkSession.builder.master("local[2]").appName("pset2-ai4i-obt")
             .config("spark.sql.shuffle.partitions", "2").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    db = database()
    try:
        with connect() as conn:
            frames = []
            with conn.cursor() as cur:
                for table in ("FACT_READING", "DIM_PRODUCT", "DIM_SOURCE"):
                    # Timestamps convertidos a texto para evitar dependencias de timezone.
                    select = "* EXCLUDE LOADED_AT, TO_VARCHAR(LOADED_AT) AS LOADED_AT" if table == "FACT_READING" else "*"
                    cur.execute(f"SELECT {select} FROM {db}.GOLD.{table}")
                    pdf = cur.fetch_pandas_all()
                    if pdf.empty:
                        raise ValueError(f"{table} vacío")
                    frames.append(spark.createDataFrame(pdf))
            obt, metrics = build_obt(*frames)
            pdf = obt.toPandas()
            # Publicación atómica: validar una tabla nueva y publicar mediante CLONE.
            temp = "AI4I_OBT_BUILD_" + uuid.uuid4().hex.upper()
            ok, _, nrows, _ = write_pandas(conn, pdf, temp, database=db, schema="OBT",
                                           auto_create_table=True, overwrite=False)
            try:
                if not ok or nrows != metrics["obt_rows"]:
                    raise RuntimeError("Escritura OBT incompleta")
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT READING_KEY) FROM {db}.OBT.{temp}")
                    stored, unique = cur.fetchone()
                    if stored != nrows or unique != nrows:
                        raise RuntimeError("Validación OBT en Snowflake falló")
                    cur.execute(f"CREATE OR REPLACE TABLE {db}.OBT.AI4I_OBT CLONE {db}.OBT.{temp} COPY GRANTS")
                    cur.execute(f"SELECT * FROM {db}.SILVER.QUALITY_REPORT")
                    quality = cur.fetch_pandas_all().to_dict(orient="records")
                report("calidad.json", quality)
                report("obt.json", {**metrics, "stored_rows": stored,
                                    "grain": "source_sha256 + udi",
                                    "target": "MACHINE_FAILURE",
                                    "horizon": "current_observation_only",
                                    "baseline_rule": assumptions()['rule']['version'],
                                    "excluded_features": ["UDI", "PRODUCT_ID", "READING_KEY", "LOADED_AT",
                                                          "SOURCE_KEY", "SOURCE_URL", "SOURCE_NAME", "PRODUCT_KEY",
                                                          "BASELINE_ALERT", "BASELINE_RULE_VERSION"]})
            finally:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {db}.OBT.{temp}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
