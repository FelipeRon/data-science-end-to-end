"""Kestra y Docker usan el mismo entrypoint reproducible."""
import os
from pathlib import Path
import subprocess
import sys

from scripts.common import key_der


def run(*args):
    subprocess.run(args, check=True)


def main():
    # dbt recibe una clave DER Base64 efímera y no un archivo secreto versionado.
    import base64
    os.environ["DBT_ENV_SECRET_PRIVATE_KEY"] = base64.b64encode(key_der()).decode()
    # En instalaciones nuevas el rol debe tener CREATE SCHEMA (ver permisos_pendientes.sql).
    from scripts.common import connect, database
    with connect() as conn:
        with conn.cursor() as cur:
            for schema in ("RAW", "BRONZE", "SILVER", "GOLD", "OBT"):
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {database()}.{schema}")
    run(sys.executable, "kestra/ingesta_csv.py")
    run("dbt", "debug", "--project-dir", "dbt", "--profiles-dir", "dbt")
    run("dbt", "build", "--project-dir", "dbt", "--profiles-dir", "dbt")
    run(sys.executable, "spark/construir_obt.py")
    run(sys.executable, "scripts/evaluar_negocio.py")
    # Copiar artefactos útiles, sin perfiles ni secretos.
    import shutil
    Path("output").mkdir(exist_ok=True)
    for name in ("manifest.json", "run_results.json"):
        source = Path("dbt/target") / name
        if source.exists():
            shutil.copy2(source, Path("output") / name)


if __name__ == "__main__":
    main()

