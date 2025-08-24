#!/bin/bash

# MeshMind Local Development Setup Script
# This script sets up MeshMind for local development

set -e

echo "🚀 Setting up MeshMind for local development..."

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.9+ first."
    exit 1
fi

echo "✅ Prerequisites check passed!"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    python3 -m pip install -e .
elif command -v python &> /dev/null; then
    python -m pip install -e .
else
    echo "❌ Python not found"
    exit 1
fi

echo "✅ Python dependencies installed!"

# Start Docker services
echo "🐳 Starting Docker services..."
docker compose up -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
if ! docker compose ps | grep -q "Up"; then
    echo "❌ Services failed to start. Check logs with: docker compose logs"
    exit 1
fi

echo "✅ Services are running!"

# Test referee health
echo "🏥 Testing referee health..."
if command -v curl &> /dev/null; then
    if curl -s http://localhost:8080/healthz | grep -q "healthy"; then
        echo "✅ Referee service is healthy!"
    else
        echo "❌ Referee service is not responding. Check logs with: docker compose logs referee"
        exit 1
    fi
else
    echo "⚠️  curl not available, skipping health check"
fi

echo ""
echo "🎉 MeshMind setup complete!"
echo ""
echo "📊 Available services:"
echo "   • Referee API: http://localhost:8080"
echo "   • Jaeger UI: http://localhost:16686"
echo "   • PostgreSQL: localhost:5432"
echo "   • Redis: localhost:6379"
echo ""
echo "🧪 Run the demo:"
echo "   python examples/yc_demo/demo.py"
echo ""
echo "📖 View logs:"
echo "   docker compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker compose down"
echo ""
echo "Happy developing! 🚀"
