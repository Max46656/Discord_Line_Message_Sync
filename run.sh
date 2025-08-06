#!/bin/bash

# Change to the script's directory
cd "$(dirname "$0")"

# Check if the virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Starting setup..."

    # Check if uv is installed
    if command -v uv &> /dev/null; then
        echo "Found uv! Using uv for setup..."
        uv sync
        if [ $? -ne 0 ]; then
            echo "Failed to sync with uv"
            exit 1
        fi
    else
        echo "uv not found, falling back to traditional setup..."
        echo "Creating virtual environment..."
        python3 -m venv .venv
        if [ $? -ne 0 ]; then
            echo "Failed to create virtual environment"
            exit 1
        fi
        echo "Activating virtual environment..."
        source .venv/bin/activate
        if [ $? -ne 0 ]; then
            echo "Failed to activate virtual environment"
            exit 1
        fi
        echo "Installing requirements..."
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Failed to install requirements"
            exit 1
        fi
    fi
    echo "Setup completed successfully!"
fi

# Run the application
if command -v uv &> /dev/null; then
    echo "Running with uv..."
    uv run main.py
else
    echo "Running with traditional venv..."
    source .venv/bin/activate
    python3 main.py
fi