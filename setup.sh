#!/bin/bash
# Run this script before starting Claude Code to set up the project

set -e

cd "$(dirname "$0")"

echo "Creating directory structure..."
mkdir -p src/models src/schemas src/api/v1 src/services src/integrations
mkdir -p tests/unit/test_services tests/unit/test_integrations tests/integration/test_api tests/fixtures
mkdir -p data frontend alembic/versions

echo "Creating __init__.py files..."
touch src/__init__.py
touch src/models/__init__.py
touch src/schemas/__init__.py
touch src/api/__init__.py
touch src/api/v1/__init__.py
touch src/services/__init__.py
touch src/integrations/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/unit/test_services/__init__.py
touch tests/unit/test_integrations/__init__.py
touch tests/integration/__init__.py
touch tests/integration/test_api/__init__.py

echo "Generating SECRET_KEY if not exists..."
if [ ! -f .env ]; then
    echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env
    echo "DATABASE_URL=sqlite:///./data/homeoffice_assistant.db" >> .env
    echo "Created .env file"
else
    echo ".env already exists"
fi

echo "Creating Python virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "Created .venv"
else
    echo ".venv already exists"
fi

echo "Installing Python dependencies..."
source .venv/bin/activate
pip install -e ".[dev]"

echo ""
echo "Setup complete! Now run:"
echo "  cd $(pwd)"
echo "  claude"
echo ""
echo "Then paste the prompt from CLAUDE_CODE_PROMPT.md"
