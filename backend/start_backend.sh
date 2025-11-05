#!/bin/bash

# Portfolio Manager Backend Startup Script

echo "Starting Portfolio Manager Backend Server..."
echo "==========================================="

# Check if we're in the backend directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the backend directory."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements if needed
if [ -f "requirements.txt" ]; then
    echo "Installing/updating requirements..."
    pip install -r requirements.txt
fi

# Initialize database if it doesn't exist
if [ ! -f "portfolio_manager.db" ]; then
    echo "Database not found. Initializing database..."
    python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database created successfully!')"
fi

# Start the server
echo ""
echo "Starting Flask server on http://localhost:5000..."
echo "Press Ctrl+C to stop the server"
echo ""
python3 app.py
