#!/usr/bin/env bash
# Se puede invocar desde cualquier carpeta. No requiere PowerShell.
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
command_name="${1:-help}"
if [ "$#" -gt 0 ]; then shift; fi
case "$command_name" in
  prepare)
    python3 scripts/prepare_codespaces.py "$@"
    ;;
  start)
    python3 scripts/prepare_codespaces.py
    docker info >/dev/null
    docker compose version
    docker compose build pipeline
    docker compose up -d --force-recreate kestra
    python3 scripts/kestra_cli.py wait-ready --timeout 180
    python3 scripts/kestra_cli.py upload
    echo 'Kestra listo. Abre el puerto 8080 en Ports (mantener Private).'
    echo 'Ejecutar todo: bash scripts/codespaces.sh run'
    ;;
  run)
    python3 scripts/kestra_cli.py upload
    python3 scripts/kestra_cli.py execute --wait "$@"
    ;;
  backfill)
    python3 scripts/kestra_cli.py upload
    python3 scripts/kestra_cli.py backfill "$@"
    ;;
  test)
    # Pruebas locales sin Snowflake ni secretos. La imagen también tiene Java/Spark.
    docker build -t pset2-pipeline:local .
    docker run --rm pset2-pipeline:local pytest -q
    ;;
  status)
    docker compose ps
    ;;
  stop)
    docker compose stop
    ;;
  *)
    echo 'Uso: bash scripts/codespaces.sh {prepare|start|run|backfill|test|status|stop}'
    echo 'run --batch-id 0 --batch-size 1000 ejecuta un lote. start no ejecuta cargas Snowflake.'
    ;;
esac
