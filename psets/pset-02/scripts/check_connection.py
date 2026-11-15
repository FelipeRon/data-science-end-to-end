"""Diagnóstico de solo lectura; reutiliza secretos locales sin imprimirlos."""
import base64
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.common import connect, report


def load_legacy_env(folder):
    values = {}
    for line in (Path(folder) / ".env.kestra").read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    for source, target in (("SECRET_SNOWFLAKE_PRIVATE_KEY", "SNOWFLAKE_PRIVATE_KEY"),
                           ("SECRET_SNOWFLAKE_KEY_PASSWORD", "SNOWFLAKE_PRIVATE_KEY_PASSWORD")):
        if values.get(source):
            os.environ[target] = base64.b64decode(values[source]).decode()


def main():
    if Path("/credentials/.env.kestra").exists():
        load_legacy_env("/credentials")
    os.environ.setdefault("SNOWFLAKE_ACCOUNT", "MRIWLBX-HH95628")
    os.environ.setdefault("SNOWFLAKE_USER", "PSET2_KESTRA")
    os.environ.setdefault("SNOWFLAKE_ROLE", "PSET2_INGEST")
    os.environ.setdefault("SNOWFLAKE_DATABASE", "PSET2_MANTENIMIENTO")
    os.environ.setdefault("SNOWFLAKE_WAREHOUSE", "PSET2_WH")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()")
            context = cur.fetchone()
            cur.execute("SHOW WAREHOUSES")
            names = [col[0].lower() for col in cur.description]
            warehouses = [{k: row[names.index(k)] for k in ("name", "state", "size")}
                          for row in cur.fetchall()]
            cur.execute("SHOW SCHEMAS IN DATABASE PSET2_MANTENIMIENTO")
            names = [col[0].lower() for col in cur.description]
            schemas = [row[names.index("name")] for row in cur.fetchall()]
    report("conexion.json", {"context": context, "warehouses": warehouses, "schemas": schemas})


if __name__ == "__main__":
    main()

