#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}/api"

if [[ ! -d ".venv" ]]; then
  python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
