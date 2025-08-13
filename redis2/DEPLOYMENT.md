# Remote Server Deployment Checklist

## Files Ready for Git Upload ✅

The following files are ready to be committed and pushed to your repository:

### Core System Files:
- ✅ `docker-compose.yml` - Updated for remote server deployment
- ✅ `Dockerfile` - Main application container
- ✅ `requirements.txt` - All Python dependencies included
- ✅ `hr_processor.py` - Redis queue processor with Ollama integration
- ✅ `ingestion_api.py` - FastAPI service for data ingestion
- ✅ `ingest_data.py` - Manual data ingestion script
- ✅ `start_system.sh` - Ubuntu server startup script
- ✅ `README.md` - Complete documentation

### Data Files:
- ✅ `dailySalesBreakdown.csv` - Sales and cost data
- ✅ `file1.csv` - Employee schedules and attendance
- ✅ `redis2/ui/streamlit_app.py` - Enhanced UI with Redis support
- ✅ `redis2/query.py` - Original query functions

### Startup Scripts:
- ✅ `start_system.sh` - Linux/Ubuntu deployment script

## Commands to Run on Remote Ubuntu Server

### 1. First Time Setup:
```bash
# Clone the repository
git clone <your-git-repo-url>
cd <repo-directory>

# Install Ollama if not already installed
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama in background
nohup ollama serve > ollama.log 2>&1 &

# Pull the model
ollama pull llama3.1:70b

# Test Ollama is working
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:70b", 
  "prompt": "Hello, how are you?"
}'
```

### 2. Deploy the System:
```bash
# Make startup script executable
chmod +x start_system.sh

# Run the startup script
./start_system.sh
```

### 3. Alternative Manual Startup:
```bash
# Create directories
mkdir -p data logs ui

# Copy CSV files
cp dailySalesBreakdown.csv data/
cp file1.csv data/

# Start Docker services
docker-compose up --build -d

# Wait for services to start
sleep 30

# Ingest data
python3 ingest_data.py
```

### 4. Verify System is Running:
```bash
# Check all services
docker-compose ps

# Test API health
curl http://localhost:8080/health

# Test data ingestion
curl -X POST http://localhost:8080/ingest/existing

# Check stats
curl http://localhost:8080/stats
```

### 5. Access Points:
- **Streamlit UI**: http://YOUR_SERVER_IP:8501
- **API**: http://YOUR_SERVER_IP:8080
- **Elasticsearch**: http://YOUR_SERVER_IP:9200

### 6. Test Queries:
```bash
# Via API
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many employees worked in May 2025?",
    "user_role": "manager",
    "user_id": "test_user"
  }'

# Via Streamlit UI
# Open http://YOUR_SERVER_IP:8501 in browser
```

## Troubleshooting on Remote Server:

### If Ollama is not responding:
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
pkill ollama
nohup ollama serve > ollama.log 2>&1 &

# Check Ollama logs
tail -f ollama.log
```

### If Docker services fail:
```bash
# Check Docker status
docker-compose ps

# View logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up --build -d
```

### If data ingestion fails:
```bash
# Check if CSV files exist
ls -la data/

# Manual ingestion
python3 ingest_data.py

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health
```

## Summary for Git Push:

1. ✅ All files are configured for remote deployment
2. ✅ Docker Compose uses `network_mode: host` for localhost Ollama access
3. ✅ Environment variables are set for localhost connections
4. ✅ Startup script handles all dependencies
5. ✅ Complete documentation provided

**Ready to push to Git and deploy!** 🚀
