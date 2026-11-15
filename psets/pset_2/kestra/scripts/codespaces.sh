#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
command_name="${1:-help}"
if [ "$#" -gt 0 ]; then shift; fi
case "$command_name" in
  prepare) python3 kestra/scripts/prepare_codespaces.py "$@" ;;
  start)
    python3 kestra/scripts/prepare_codespaces.py
    docker info >/dev/null
    docker compose build pipeline
    docker compose up -d --force-recreate kestra
    python3 kestra/scripts/kestra_cli.py wait-ready --timeout 180
    python3 kestra/scripts/kestra_cli.py upload
    echo 'Abre 8080 en Ports (Private). Ejecuta: bash kestra/scripts/codespaces.sh run'
    ;;
  run)
    python3 kestra/scripts/kestra_cli.py upload
    python3 kestra/scripts/kestra_cli.py execute --wait "$@"
    ;;
  backfill)
    python3 kestra/scripts/kestra_cli.py upload
    python3 kestra/scripts/kestra_cli.py backfill "$@"
    ;;
  test)
    docker build -f kestra/runtime/Dockerfile -t pset2-pipeline:local .
    docker run --rm pset2-pipeline:local pytest -q docs/tests
    ;;
  status) docker compose ps ;;
  credentials)
    python3 -c "import sys; sys.path.insert(0,'kestra/scripts'); from prepare_codespaces import ROOT,read_env; v=read_env(ROOT/'.env'); print('Usuario:',v['KESTRA_USER']); print('Password:',v['KESTRA_PASSWORD'])"
    ;;
  stop) docker compose stop ;;
  *) echo 'Uso: bash kestra/scripts/codespaces.sh {prepare|start|run|backfill|test|status|stop}' ;;
esac
