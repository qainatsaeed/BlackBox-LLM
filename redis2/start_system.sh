#!/bin/bash

echo "🚀 Starting HR Assistant with Redis Queue System"

# Check if Ollama is running
echo "🔍 Checking Ollama connection..."
if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running and accessible"
else
    echo "❌ Ollama is not accessible at http://127.0.0.1:11434"
    echo "Please make sure Ollama is running with: ollama serve"
    echo "And that llama3.1:70b model is available with: ollama pull llama3.1:70b"
    exit 1
fi

# Start the Docker services
echo "🐳 Starting Docker services..."
docker-compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis is not responding"
fi

# Check Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null; then
    echo "✅ Elasticsearch is healthy"
else
    echo "❌ Elasticsearch is not responding"
fi

# Check API
if curl -s http://localhost:8080/health > /dev/null; then
    echo "✅ Ingestion API is healthy"
else
    echo "❌ Ingestion API is not responding"
fi

echo ""
echo "🎯 Services are starting up!"
echo ""
echo "📊 Access points:"
echo "   Streamlit UI:    http://localhost:8501"
echo "   Ingestion API:   http://localhost:8080"
echo "   Elasticsearch:   http://localhost:9200"
echo "   Redis:           localhost:6379"
echo ""
echo "📁 To ingest the CSV files, either:"
echo "   1. Use the Streamlit UI at http://localhost:8501"
echo "   2. Or run: curl -X POST http://localhost:8080/ingest/existing"
echo ""
echo "🔍 Example queries:"
echo "   - What were the sales on 5/15/2025?"
echo "   - Who worked as Line Cook on 6/1/2025?"
echo "   - Show me attendance vs scheduled hours for May 2025"
echo ""
echo "📋 To view logs:"
echo "   docker-compose logs -f hr_processor"
echo "   docker-compose logs -f ingestion_api"
echo "   docker-compose logs -f streamlit"
echo ""
echo "⏹️  To stop the system:"
echo "   docker-compose down"
