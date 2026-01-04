#!/bin/bash
# Quick start script for Watch Number Generator

# Detect OS and set environment accordingly
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS: Set pkg-config path for Homebrew GTK
    export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

cd "$(dirname "$0")/src"
python3 main.py
