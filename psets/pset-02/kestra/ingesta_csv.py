import os
from datetime import date
from math import ceil

from kestra import Kestra
from ucimlrepo import fetch_ucirepo

BATCH_SIZE = int(os.environ["BATCH_SIZE"])
START_DATE = date.fromisoformat(os.environ["START_DATE"])
RUN_DATE = date.fromisoformat(os.environ["RUN_DATE"])

COLUMNS = ["udi", "product_id", "type", "air_temperature_k",
           "process_temperature_k", "rotational_speed_rpm", "torque_nm",
           "tool_wear_min", "machine_failure", "twf", "hdf", "pwf",
           "osf", "rnf"]

# 1. Descargar el dataset completo desde UCI
df = fetch_ucirepo(id=601).data.original.copy()

# 2. Validar la fuente antes de usarla
assert df.shape == (10000, 14), f"Forma inesperada: {df.shape}"
df.columns = COLUMNS
assert df["udi"].is_unique, "udi duplicado en la fuente"
print(f"Fuente: {len(df)} filas, tasa de falla {df['machine_failure'].mean():.2%}")

# 3. Seleccionar el lote que corresponde a la fecha de ejecución
n_batches = ceil(len(df) / BATCH_SIZE)
batch_no = (RUN_DATE - START_DATE).days
if batch_no < 0:
    raise ValueError(f"{RUN_DATE} es anterior a start_date {START_DATE}")

    df = df.sort_values("udi")
    batch = df.iloc[batch_no * BATCH_SIZE:(batch_no + 1) * BATCH_SIZE]
    print(f"Lote {batch_no + 1} de {n_batches}: {len(batch)} filas")

    batch.to_csv("ai4i_batch.csv", index=False)
    Kestra.outputs({"rows": len(batch), "batch_id": RUN_DATE.isoformat(),
                      "batch_no": batch_no, "n_batches": n_batches})