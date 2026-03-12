#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "Starting TK-AI node..."
hostname

echo
echo "Running cluster doctor..."
python3 tools/cluster_doctor.py

echo
echo "Starting investigation daemon..."
PYTHONPATH=. exec python3 tools/tkai_investigation_daemon.py
