#!/bin/bash
# Setup script for gptimage

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up gptimage..."

# Pick a Python 3.11+ interpreter
PY=""
for cand in python3.12 python3.11 python3; do
    if command -v "$cand" &> /dev/null; then
        PY="$cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "Error: Python 3.11+ is required but not found."
    echo "Install it with: brew install python@3.12"
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with $PY..."
    "$PY" -m venv .venv
fi

# Activate and install
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env file. Please edit it and add your OPENAI_API_KEY."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Add your OpenAI API key to .env, then run commands via run.sh, e.g.:"
echo "  ./run.sh generate \"a cat astronaut\" -a 16:9 -r 1K"
