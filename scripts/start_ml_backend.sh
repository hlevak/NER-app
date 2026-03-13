#!/bin/bash
set -e

echo "============================================"
echo " Starting NER ML Backend"
echo "============================================"
echo ""

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$APP_DIR/venv"
ENV_FILE="$APP_DIR/config/ml-backend.env"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Run setup.sh first"
    exit 1
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Loading configuration..."
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

export ML_BACKEND_HOST="${ML_BACKEND_HOST:-0.0.0.0}"
export ML_BACKEND_PORT="${ML_BACKEND_PORT:-9090}"

mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/models/fine_tuned"

echo ""
echo "ML Backend starting on http://$ML_BACKEND_HOST:$ML_BACKEND_PORT"
echo "spaCy model: ${SPACY_MODEL:-ru_core_news_sm}"
echo "Logs dir: ${LOGS_DIR:-$APP_DIR/logs}"
echo ""

cd "$APP_DIR"

# Run with logging to file
exec python -m ml_backend.wsgi 2>&1 | tee "$APP_DIR/logs/ml-backend.log"
