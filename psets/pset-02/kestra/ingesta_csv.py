"""Descarga AI4I o lee el CSV recibido de Kestra y carga RAW idempotente."""
import hashlib
import io
import math
import os
from pathlib import Path
import sys
from urllib.request import urlopen
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.common import connect, database, report

URL = "https://archive.ics.uci.edu/static/public/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bdataset.zip"
HEADERS = ["UDI", "Product ID", "Type", "Air temperature [K]", "Process temperature [K]",
           "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", "Machine failure",
           "TWF", "HDF", "PWF", "OSF", "RNF"]
COLUMNS = ["UDI", "PRODUCT_ID", "TYPE", "AIR_TEMPERATURE_K", "PROCESS_TEMPERATURE_K",
           "ROTATIONAL_SPEED_RPM", "TORQUE_NM", "TOOL_WEAR_MIN", "MACHINE_FAILURE",
           "TWF", "HDF", "PWF", "OSF", "RNF"]


def select_batch(df, batch_id, batch_size):
    if batch_size <= 0:
        raise ValueError("BATCH_SIZE debe ser positivo")
    if batch_id == -1:
        return df.copy()
    if not 0 <= batch_id < math.ceil(len(df) / batch_size):
        raise ValueError("BATCH_ID fuera de rango; usar -1 para la fuente completa")
    return df.iloc[batch_id * batch_size:(batch_id + 1) * batch_size].copy()


def read_source():
    path = Path(os.environ.get("SOURCE_CSV", "ai4i2020.csv"))
    if path.exists():
        return path.read_bytes()
    with urlopen(URL, timeout=120) as response:
        archive = response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        return zf.read("ai4i2020.csv")


def main():
    import pandas as pd
    from snowflake.connector.pandas_tools import write_pandas
    raw = read_source()
    digest = hashlib.sha256(raw).hexdigest()
    # Todo se conserva como texto en RAW, sin imputación ni transformación de negocio.
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    if list(df.columns) != HEADERS or len(df) != 10000:
        raise ValueError("El contrato de AI4I cambió: se esperaban 10.000 filas y 14 columnas conocidas")
    df.columns = COLUMNS
    if not df.UDI.str.fullmatch(r"[0-9]+").all() or not df.UDI.is_unique:
        raise ValueError("UDI vacío, no entero o repetido: se detiene la ingesta")
    df = df.iloc[df.UDI.astype(int).argsort()].reset_index(drop=True)
    batch_id = int(os.environ.get("BATCH_ID", "-1"))
    batch_size = int(os.environ.get("BATCH_SIZE", "1000"))
    batch = select_batch(df, batch_id, batch_size)
    batch["SOURCE_SHA256"] = digest
    batch["SOURCE_URL"] = URL
    batch["BATCH_ID"] = str(batch_id)
    db = database()
    columns = COLUMNS + ["SOURCE_SHA256", "SOURCE_URL", "BATCH_ID"]
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE TABLE IF NOT EXISTS {db}.RAW.AI4I_OBSERVATIONS ("
                        + ", ".join(f'"{c}" VARCHAR' for c in columns)
                        + ", LOADED_AT TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP())")
            # Falla claramente si AI4I existía con una estructura diferente.
            cur.execute(f"CREATE TEMPORARY TABLE {db}.RAW.AI4I_OBSERVATIONS_LOAD LIKE {db}.RAW.AI4I_OBSERVATIONS")
        ok, _, count, _ = write_pandas(conn, batch, "AI4I_OBSERVATIONS_LOAD", database=db,
                                       schema="RAW", auto_create_table=False)
        if not ok or count != len(batch):
            raise RuntimeError("Carga incompleta al staging temporal")
        with conn.cursor() as cur:
            cur.execute(f"""MERGE INTO {db}.RAW.AI4I_OBSERVATIONS t USING {db}.RAW.AI4I_OBSERVATIONS_LOAD s
                ON t.SOURCE_SHA256 = s.SOURCE_SHA256 AND t.UDI = s.UDI
                WHEN NOT MATCHED THEN INSERT ({','.join(columns)})
                VALUES ({','.join('s.' + c for c in columns)})""")
            inserted = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*), COUNT(DISTINCT UDI) FROM {db}.RAW.AI4I_OBSERVATIONS WHERE SOURCE_SHA256=%s", (digest,))
            total, unique = cur.fetchone()
            if total != unique:
                raise RuntimeError("Duplicados en RAW para la misma versión de la fuente")
    report("ingesta.json", {"source_sha256": digest, "source_rows": len(df),
           "selected_rows": len(batch), "inserted_rows": inserted, "stored_rows": total,
           "batch_id": batch_id, "batch_size": batch_size})


if __name__ == "__main__":
    main()

