#!/bin/bash
# Setup virtual environment (if needed) and run the game
set -e

VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt
else
    source "$VENV_DIR/bin/activate"
fi

python3 -m src.main "$@"
