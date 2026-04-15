#!/usr/bin/env bash
set -euo pipefail

# Simple local demo launcher for independent bridge testing.
# It opens 4 terminals for:
# 1) Mock UFS API
# 2) UFS Kafka Bridge
# 3) Output reader
# 4) Input publisher (manual trigger)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$PROJECT_DIR/.venv/bin/activate"

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "[ERROR] Virtual environment not found at .venv/"
  echo "Run:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker is not installed or not in PATH."
  exit 1
fi

if ! command -v gnome-terminal >/dev/null 2>&1; then
  echo "[ERROR] gnome-terminal not found."
  echo "Run the commands manually from README.md (Independent local testing section)."
  exit 1
fi

echo "[INFO] Starting local Kafka..."
docker compose up -d

echo "[INFO] Creating local test topics..."
source "$VENV_ACTIVATE"
python "$PROJECT_DIR/local_test_create_topics.py"

echo "[INFO] Launching demo terminals..."

gnome-terminal -- bash -lc "cd '$PROJECT_DIR'; source '$VENV_ACTIVATE'; python local_mock_ufs_api.py; exec bash"
gnome-terminal -- bash -lc "cd '$PROJECT_DIR'; source '$VENV_ACTIVATE'; export UFS_FORECAST_ENDPOINT='http://localhost:8080/forecast'; python ufs_kafka_bridge.py; exec bash"
gnome-terminal -- bash -lc "cd '$PROJECT_DIR'; source '$VENV_ACTIVATE'; python local_test_read_output.py; exec bash"
gnome-terminal -- bash -lc "cd '$PROJECT_DIR'; source '$VENV_ACTIVATE'; echo 'Run when ready: python local_test_publish_input.py'; exec bash"

echo "[DONE] Demo terminals opened."
echo "In the publisher terminal, run:"
echo "  python local_test_publish_input.py"
