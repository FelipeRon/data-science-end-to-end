"""Conexión compartida; nunca imprime credenciales."""
import base64
import json
import os
import re
from pathlib import Path


def identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Identificador SQL inválido: {value!r}")
    return value.upper()


def database():
    return identifier(os.environ.get("SNOWFLAKE_DATABASE", "PSET2_MANTENIMIENTO"))


def key_der():
    from cryptography.hazmat.primitives import serialization
    text = os.environ.get("SNOWFLAKE_PRIVATE_KEY", "")
    if text:
        data = text.encode()
    else:
        data = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_FILE"]).read_bytes()
    password_text = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSWORD", "")
    if not password_text and os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64"):
        password_text = base64.b64decode(os.environ["SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64"]).decode()
    password = password_text.encode() or None
    # Kestra secret() ya decodifica su envoltura Base64. Aceptar PEM o DER Base64.
    if b"-----BEGIN" in data:
        key = serialization.load_pem_private_key(data, password=password)
    else:
        key = serialization.load_der_private_key(base64.b64decode(data), password=password)
    return key.private_bytes(serialization.Encoding.DER,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def connect():
    import snowflake.connector
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=database(), schema="RAW", private_key=key_der(),
        login_timeout=45, network_timeout=120,
        session_parameters={"QUERY_TAG": "pset2-ai4i"})


def report(name, data):
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / name).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(json.dumps(data, default=str))

