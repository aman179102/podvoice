#!/usr/bin/env bash
set -e

REQUIRED_PYTHON="3.10"

echo "🔍 Checking Python version..."

if command -v python3.10 >/dev/null 2>&1; then
  PYTHON=python3.10
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "❌ Python not found. Please install Python 3.10."
  exit 1
fi

VERSION=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

if [[ "$VERSION" != "$REQUIRED_PYTHON" ]]; then
  echo "❌ Python $REQUIRED_PYTHON required. Found Python $VERSION."
  echo "👉 Please install Python 3.10 and re-run this script."
  exit 1
fi

echo "✅ Python $VERSION detected"

echo "📦 Creating virtual environment..."
$PYTHON -m venv .venv

echo "⚙️ Activating virtual environment..."
source .venv/bin/activate

echo "⬇️ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.lock

echo "🔧 Installing podvoice..."
pip install -e .

echo ""
echo "🎉 Podvoice is ready!"
echo "👉 Run: source .venv/bin/activate"
echo "👉 Then: podvoice --help"