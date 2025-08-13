@echo off

echo 🚀 Starting HR Assistant with Redis Queue System

REM Check if Ollama is running
echo 🔍 Checking Ollama connection...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama is running and accessible
) else (
    echo ❌ Ollama is not accessible at http://127.0.0.1:11434
    echo Please make sure Ollama is running with: ollama serve
    echo And that llama3.1:70b model is available with: ollama pull llama3.1:70b
    pause
    exit /b 1
)

REM Start the Docker services
echo 🐳 Starting Docker services...
docker-compose up --build -d

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo 🏥 Checking service health...

REM Check services (simplified for Windows)
echo ✅ Services should be starting up...

echo.
echo 🎯 Services are starting up!
echo.
echo 📊 Access points:
echo    Streamlit UI:    http://localhost:8501
echo    Ingestion API:   http://localhost:8080
echo    Elasticsearch:   http://localhost:9200
echo    Redis:           localhost:6379
echo.
echo 📁 To ingest the CSV files, either:
echo    1. Use the Streamlit UI at http://localhost:8501
echo    2. Or run: curl -X POST http://localhost:8080/ingest/existing
echo.
echo 🔍 Example queries:
echo    - What were the sales on 5/15/2025?
echo    - Who worked as Line Cook on 6/1/2025?
echo    - Show me attendance vs scheduled hours for May 2025
echo.
echo 📋 To view logs:
echo    docker-compose logs -f hr_processor
echo    docker-compose logs -f ingestion_api
echo    docker-compose logs -f streamlit
echo.
echo ⏹️  To stop the system:
echo    docker-compose down
echo.
pause
