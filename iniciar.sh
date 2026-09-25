#!/usr/bin/env bash
# Inicia o servidor em Linux/macOS
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || ./instalar.sh
exec .venv/bin/python run.py "$@"
