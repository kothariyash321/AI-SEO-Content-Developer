#!/bin/bash
# Run script for SEO Content Generation Platform

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
    exit 0
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please run ./setup.sh first"
    exit 1
fi

# Check if OPENAI_API_KEY is set
if grep -q "your_openai_api_key_here" .env || ! grep -q "OPENAI_API_KEY=" .env; then
    echo "Warning: OPENAI_API_KEY not set in .env file"
    echo "Please edit .env and add your OpenAI API key"
    exit 1
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting FastAPI server..."
echo "API will be available at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
