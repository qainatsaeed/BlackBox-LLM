# HR Assistant with Redis Queue System

A comprehensive HR data analysis system that uses Redis for messaging, Haystack for RAG (Retrieval-Augmented Generation), and Ollama for local LLM processing.

## 🏗️ Architecture

- **Redis**: Message queue for async query processing (`hrask.ask.queue` → `hrask.response.queue`)
- **Elasticsearch**: Document store for HR data with full-text search
- **Haystack**: RAG framework for document retrieval and context building
- **Ollama**: Local LLM (llama3.1:70b) for generating responses
- **FastAPI**: REST API for data ingestion and query submission
- **Streamlit**: Web UI for user interaction

## 📋 Prerequisites

1. **Docker & Docker Compose** installed
2. **Ollama** running locally:
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama
   ollama serve
   
   # Pull the model
   ollama pull llama3.1:70b
   ```

## 🚀 Quick Start

### Windows:
```cmd
# Navigate to the project directory
cd "d:\Development\BlackBox LLM\redis2"

# Run the startup script
start_system.bat
```

### Linux/Mac:
```bash
# Navigate to the project directory
cd "/path/to/BlackBox LLM/redis2"

# Make the script executable
chmod +x start_system.sh

# Run the startup script
./start_system.sh
```

### Manual Start:
```bash
# Start all services
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 📊 Access Points

Once running, you can access:

- **Streamlit UI**: http://localhost:8501
- **Ingestion API**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **Elasticsearch**: http://localhost:9200
- **Redis**: localhost:6379

## 📁 Data Ingestion

### Automatic Ingestion (Existing Files)
The system will automatically detect and ingest these CSV files:
- `dailySalesBreakdown.csv` - Sales, costs, and variance data
- `file1.csv` - Employee schedules and attendance

### Via Streamlit UI:
1. Go to http://localhost:8501
2. Click "Ingest Existing CSV Files" button
3. Or upload new CSV files using the file uploader

### Via API:
```bash
# Ingest existing files
curl -X POST http://localhost:8080/ingest/existing

# Check system stats
curl http://localhost:8080/stats

# Health check
curl http://localhost:8080/health
```

## 🔍 Querying Data

### Via Streamlit UI:
1. Open http://localhost:8501
2. Select your role (employee, supervisor, manager, admin)
3. Enter your user ID
4. Ask questions in natural language

### Via API:
```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were the sales on 5/15/2025?",
    "user_role": "manager",
    "user_id": "test_user"
  }'
```

## 🎯 Example Queries

### Sales & Financial:
- "What were the total sales for RT2 - South Austin in May 2025?"
- "What was the cost variance on 6/15/2025?"
- "Show me the scheduled vs attendance costs for June 2025"

### Employee & Schedules:
- "Who worked as a Line Cook on 5/10/2025?"
- "What positions did Allison Milam work in May?"
- "Show me attendance vs scheduled hours for Brian Villarreal"

### Time & Attendance:
- "What was the total hour difference for all employees on 6/1/2025?"
- "Who had the most overtime in May 2025?"
- "Which employees frequently came in early or stayed late?"

## 🔐 Role-Based Access Control

The system implements hierarchical access control:

- **Employee**: Only sees their own data + general sales metrics
- **Supervisor**: Sees team-level data for supervised employees
- **Manager**: Sees location-level performance and team data
- **Admin**: Has access to all data

## 🗂️ Data Structure

### Sales Data (`dailySalesBreakdown.csv`):
- Date, Sales figures, Scheduled/Attendance costs, Variances
- Processed with location context (RT2 - South Austin)

### Employee Data (`file1.csv`):
- Employee schedules, positions, departments
- Attendance tracking, hour differences
- Both BOH (Back of House) and FOH (Front of House) positions

## 🛠️ Development

### Project Structure:
```
redis2/
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Python dependencies
├── hr_processor.py            # Redis queue processor
├── ingestion_api.py           # FastAPI ingestion service
├── redis2/
│   ├── query.py               # Original query functions
│   ├── dailySalesBreakdown.csv
│   ├── file1.csv
│   └── ui/
│       └── streamlit_app.py   # Enhanced Streamlit UI
├── Dockerfile.api             # API service Dockerfile
├── Dockerfile.processor       # Processor service Dockerfile
├── Dockerfile.streamlit       # Streamlit service Dockerfile
└── start_system.*             # Startup scripts
```

### Environment Variables:
- `REDIS_HOST`: Redis hostname (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `ELASTICSEARCH_HOST`: Elasticsearch hostname (default: localhost)
- `ELASTICSEARCH_PORT`: Elasticsearch port (default: 9200)
- `OLLAMA_HOST`: Ollama hostname (default: host.docker.internal)
- `OLLAMA_PORT`: Ollama port (default: 11434)

## 🔧 Troubleshooting

### Common Issues:

1. **Ollama not accessible**:
   ```bash
   # Check if Ollama is running
   curl http://127.0.0.1:11434/api/tags
   
   # Start Ollama if needed
   ollama serve
   ```

2. **Services not starting**:
   ```bash
   # Check Docker logs
   docker-compose logs
   
   # Restart services
   docker-compose down && docker-compose up --build -d
   ```

3. **No documents found**:
   ```bash
   # Check if data was ingested
   curl http://localhost:8080/stats
   
   # Re-ingest data
   curl -X POST http://localhost:8080/ingest/existing
   ```

4. **Redis connection issues**:
   ```bash
   # Check Redis
   docker-compose exec redis redis-cli ping
   ```

### Monitoring:

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f hr_processor
docker-compose logs -f ingestion_api
docker-compose logs -f streamlit

# Check service status
docker-compose ps

# Monitor Redis queues
docker-compose exec redis redis-cli llen hrask.ask.queue
docker-compose exec redis redis-cli llen hrask.response.queue
```

## 📈 Performance Notes

- The system processes queries asynchronously via Redis queues
- Elasticsearch provides fast full-text search across HR documents
- Haystack retrieves relevant context before sending to the LLM
- Role-based filtering ensures users only see authorized data
- The llama3.1:70b model provides high-quality analysis of HR data

## ⏹️ Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears all data)
docker-compose down -v
```
