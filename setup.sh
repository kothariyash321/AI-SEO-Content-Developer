#!/bin/bash
# Setup script for SEO Content Generation Platform

echo "Setting up SEO Content Generation Platform..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite+aiosqlite:///./seo_content.db

# OpenAI API (REQUIRED - add your key here)
OPENAI_API_KEY=your_openai_api_key_here

# SERP API (optional - will use mock if not provided)
SERP_API_KEY=
SERP_API_PROVIDER=serpapi

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# LLM Settings
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4096
EOF
    echo ".env file created. Please edit it and add your OPENAI_API_KEY"
else
    echo ".env file already exists"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Run: source venv/bin/activate"
echo "3. Run: uvicorn app.main:app --reload"
echo ""
echo "API will be available at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
