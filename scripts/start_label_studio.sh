#!/bin/bash
set -e

echo "============================================"
echo " Starting Label Studio"
echo "============================================"
echo ""

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$APP_DIR/venv"
ENV_FILE="$APP_DIR/config/label-studio.env"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Run setup.sh first"
    exit 1
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "Loading configuration from $ENV_FILE..."
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set defaults
export LABEL_STUDIO_PORT="${LABEL_STUDIO_PORT:-8080}"
export LABEL_STUDIO_HOST="${LABEL_STUDIO_HOST:-http://localhost:8080}"

echo ""
echo "Label Studio URL: $LABEL_STUDIO_HOST"
echo "Database: ${POSTGRE_HOST:-localhost}:${POSTGRE_PORT:-5432}/${POSTGRE_NAME:-label_studio}"
echo ""

mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/data"

# Check if PostgreSQL is available
if ! command -v psql &> /dev/null; then
    echo "WARNING: psql not found. Make sure PostgreSQL is installed and running."
fi

# Run Label Studio
cd "$APP_DIR"

# For SQLite fallback (development only), remove --database postgresql and related args
if [ -z "$POSTGRE_HOST" ] || [ "$POSTGRE_HOST" = "" ]; then
    echo "Running Label Studio with SQLite (development mode)..."
    exec label-studio start \
        --host 0.0.0.0 \
        --port "$LABEL_STUDIO_PORT" \
        --log-level INFO \
        2>&1 | tee "$APP_DIR/logs/label-studio.log"
else
    echo "Running Label Studio with PostgreSQL..."
    exec label-studio start \
        --host 0.0.0.0 \
        --port "$LABEL_STUDIO_PORT" \
        --database postgresql \
        --db-name "${POSTGRE_NAME:-label_studio}" \
        --db-user "${POSTGRE_USER:-label_studio_user}" \
        --db-password "${POSTGRE_PASSWORD:-}" \
        --db-host "${POSTGRE_HOST:-localhost}" \
        --db-port "${POSTGRE_PORT:-5432}" \
        --log-level INFO \
        2>&1 | tee "$APP_DIR/logs/label-studio.log"
fi
