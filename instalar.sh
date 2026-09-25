#!/usr/bin/env bash
# Instalação em Linux/macOS
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
command -v "$PY" >/dev/null || { echo "Python 3.10+ não encontrado."; exit 1; }

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

[ -f .env ] || cp .env.example .env
[ -f config/motoboys.json ] || cp config/motoboys.example.json config/motoboys.json
.venv/bin/python scripts/seed_demo.py

echo "Instalação concluída. Execute ./iniciar.sh"
