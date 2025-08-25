#!/bin/bash

# Activate Python virtual environment
source /app/venv/bin/activate

# Check if dist directory exists
if [ ! -d "dist" ]; then
    echo "Error: dist directory not found!"
    exit 1
fi

# Start the server
python3 proxy_server.py