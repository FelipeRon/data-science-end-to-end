#!/bin/sh
set -eu
# Ejecutar dentro de la imagen: docker compose run --rm pipeline sh scripts/dbt.sh build
export DBT_ENV_SECRET_PRIVATE_KEY="$(python -c 'import base64; from scripts.common import key_der; print(base64.b64encode(key_der()).decode())')"
exec dbt "$@" --project-dir dbt --profiles-dir dbt

