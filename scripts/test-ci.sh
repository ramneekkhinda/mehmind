#!/bin/bash

# Test script to verify CI setup locally
set -e

echo "🧪 Testing MeshMind CI Setup"
echo "=============================="

# Check Python version
echo "📋 Python Version:"
python --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -e .
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Run tests
echo "🧪 Running tests..."
python -m pytest --cov=meshmind --cov-report=term-missing --disable-warnings

# Run unit tests
echo "🔬 Running unit tests..."
python -m pytest -m unit --disable-warnings

# Run integration tests
echo "🔗 Running integration tests..."
python -m pytest -m integration --disable-warnings

# Check test count
echo "📊 Test Summary:"
python -m pytest --collect-only -q | grep "test session starts" -A 1

echo "✅ All tests passed! CI setup is ready."
