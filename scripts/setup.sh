#!/bin/bash
set -e

echo "============================================"
echo " NER-app: Setup Script"
echo "============================================"
echo ""

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$APP_DIR/venv"

echo "App directory: $APP_DIR"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "ERROR: Python 3.10+ is required, found $PYTHON_VERSION"
    exit 1
fi

echo "Python version: $PYTHON_VERSION ✓"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

echo ""
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

echo ""
echo "Installing dependencies..."
pip install -r "$APP_DIR/requirements.txt"

echo ""
echo "Creating necessary directories..."
mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/data"
mkdir -p "$APP_DIR/models/fine_tuned"
mkdir -p "$APP_DIR/wheels"

echo ""
echo "Setting up permissions..."
chmod +x "$APP_DIR/scripts/"*.sh 2>/dev/null || true

echo ""
echo "============================================"
echo " Setup complete!"
echo ""
echo " Next steps:"
echo " 1. Configure database in config/label-studio.env"
echo " 2. Configure ML backend in config/ml-backend.env"
echo " 3. Run: ./scripts/start_all.sh"
echo ""
echo " Or start services separately:"
echo "  - ./scripts/start_ml_backend.sh"
echo "  - ./scripts/start_label_studio.sh"
echo "============================================"
