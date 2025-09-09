#!/bin/bash

# Local LLM with Google Maps - Startup Script
# This script sets up and starts the entire application stack

set -e

echo "🚀 Starting Local LLM with Google Maps Integration"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    cp env.example .env
    echo "📝 Please edit .env file with your Google Maps API key and other settings"
    echo "   Required: GOOGLE_MAPS_API_KEY"
    echo "   Optional: WEBUI_SECRET_KEY, ENCRYPTION_KEY"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$GOOGLE_MAPS_API_KEY" ] || [ "$GOOGLE_MAPS_API_KEY" = "your-google-maps-api-key-here" ]; then
    echo "❌ GOOGLE_MAPS_API_KEY is not set in .env file"
    echo "   Please get an API key from: https://console.cloud.google.com/"
    exit 1
fi

echo "✅ Environment validation passed"

# Check if NVIDIA GPU is available
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 NVIDIA GPU detected - enabling GPU support"
    export COMPOSE_FILE="docker-compose.yml:docker-compose.gpu.yml"
else
    echo "💻 No GPU detected - using CPU mode"
fi

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker-compose pull

# Start services
echo "🔄 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check Open WebUI
if curl -f http://localhost:3000/health > /dev/null 2>&1; then
    echo "✅ Open WebUI is running"
else
    echo "⚠️  Open WebUI may still be starting..."
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis is not responding"
fi

# Download and setup Ollama models
echo "🤖 Setting up LLM models..."
docker-compose exec -T open-webui ollama pull llama3 || echo "⚠️  Failed to pull llama3 model"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📱 Access points:"
echo "   • Open WebUI: http://localhost:3000"
echo "   • Grafana: http://localhost:3001 (admin/admin)"
echo "   • Prometheus: http://localhost:9090"
echo ""
echo "📋 Next steps:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Create an account or sign in"
echo "   3. Try asking: 'Find coffee shops near Times Square'"
echo ""
echo "🔧 Useful commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop services: docker-compose down"
echo "   • Restart: docker-compose restart"
echo ""
echo "📚 For more information, see README.md"
