#!/bin/bash
set -e

echo "============================================"
echo " NER-app: Starting All Services"
echo "============================================"
echo ""

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Checking virtual environment..."
if [ ! -f "$APP_DIR/venv/bin/activate" ]; then
    echo "ERROR: Virtual environment not found"
    echo "Run setup.sh first to create venv and install dependencies"
    exit 1
fi

echo "Starting ML Backend..."
"$APP_DIR/scripts/start_ml_backend.sh" &
ML_PID=$!

echo "Waiting 10 seconds for ML Backend to initialize..."
sleep 10

echo "Starting Label Studio..."
"$APP_DIR/scripts/start_label_studio.sh" &
LS_PID=$!

echo ""
echo "============================================"
echo " All services started!"
echo ""
echo " Label Studio:  http://localhost:8080"
echo " ML Backend:    http://localhost:9090"
echo ""
echo " Log files are in: $APP_DIR/logs/"
echo ""
echo " To stop services: press Ctrl+C or run:"
echo "   kill $ML_PID $LS_PID"
echo "============================================"
echo ""

# Wait for both processes
wait $ML_PID $LS_PID
