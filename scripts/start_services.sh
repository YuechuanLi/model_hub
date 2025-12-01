#!/bin/bash
# Quick start script for Model Hub services

set -e

echo "🚀 Starting Model Hub Services"
echo "================================"

# Check if Redis is running
echo "📡 Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Starting with docker-compose..."
    docker-compose up -d redis
    sleep 2
else
    echo "✅ Redis is running"
fi

# Check if PostgreSQL is running
echo "🗄️  Checking PostgreSQL..."
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Starting with docker-compose..."
    docker-compose up -d postgres
    sleep 5
else
    echo "✅ PostgreSQL is running"
fi

# Run migrations
echo "🔄 Running database migrations..."
uv run alembic upgrade head

# Create model store directories
echo "📁 Creating model store directories..."
mkdir -p /data/model-store/blobs/sha256
mkdir -p /data/model-store/metadata
mkdir -p /data/model-store/temp
echo "✅ Directories created"

echo ""
echo "================================"
echo "✨ Services are ready!"
echo "================================"
echo ""
echo "To start the API server:"
echo "  uv run uvicorn src.hub_service.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "To start the worker (in a new terminal):"
echo "  uv run arq src.worker_service.main.WorkerSettings"
echo ""
echo "To test the API:"
echo "  uv run python tests/test_api_manual.py"
echo ""
