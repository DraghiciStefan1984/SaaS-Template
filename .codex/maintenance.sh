#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r backend/requirements-dev.txt
npm install --prefix frontend
