# HR Assistant with Redis Queue System - Milestone 2

A comprehensive HR data analysis system that uses Redis for messaging, PostgreSQL for structured data, Haystack for RAG (Retrieval-Augmented Generation), and Ollama for local LLM processing.

## 🏗️ Architecture

- **Redis**: Message queue for async query processing (`hrask.ask.queue` → `hrask.response.queue`)
- **PostgreSQL**: Structured data store for employee records, shifts, and time punches
- **Elasticsearch**: Document store for unstructured HR data with full-text search
- **Haystack**: RAG framework for document retrieval and context building
- **Ollama**: Support for multiple local LLMs (llama3.1, qwen, mixtral)
- **FastAPI**: REST API for data ingestion and query submission
- **Streamlit**: Web UI for user interaction
- **Middleware**: Core Redis service for request processing and response handling

## 📋 Prerequisites

1. **Docker & Docker Compose** installed
2. **Ollama** running locally (or via Docker):
   ```bash
   # Install Ollama locally (if not using Docker)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama
   ollama serve
   
   # Pull the models
   ollama pull llama3.1:8b
   ollama pull qwen:14b         # Optional
   ollama pull mixtral:8x7b     # Optional
   ```

## 🆕 What's New in Milestone 2

- **Redis Pub/Sub Integration**: Asynchronous message processing with `redis.asyncio`
- **Role-based Access Control**: Data isolation based on user roles and permissions
- **PostgreSQL Integration**: Direct connection to structured data using `asyncpg`
- **Hybrid Retrieval Strategy**: Uses both Haystack for unstructured data and SQL for structured queries
- **Multi-LLM Support**: Configurable models via `models.yml` with ModelFactory pattern
- **Middleware Service**: Core service that processes messages from Redis queues

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
- **Middleware API**: http://localhost:8081
- **API Documentation**: http://localhost:8080/docs
- **Elasticsearch**: http://localhost:9201
- **PostgreSQL**: localhost:5432 (credentials: postgres/postgres)
- **Redis**: localhost:6380
- **Ollama**: http://localhost:11434

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

### Via Redis (New in Milestone 2):
```bash
# Push a test question to Redis
python tests/push_test_question.py --query "Who worked on 5/15/2025?" --role manager

# Listen for responses
python tests/listen_response.py
```

### Via Direct Middleware API:
```bash
curl -X POST http://localhost:8081/query/direct \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What were the sales on 5/15/2025?",
    "user_role": "manager",
    "user_id": "test_user",
    "account_id": "acct001",
    "location_ids": ["loc001", "loc002"],
    "model": "llama3.1:8b"
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

### PostgreSQL Data Structure (New in Milestone 2):
- **employees**: Employee records with role, account, location info
- **shifts**: Scheduled and attended shifts with position data
- **time_punches**: Clock in/out timestamps for employees
- **locations**: Store/location information
- **accounts**: Account/company information

## 🛠️ Development

### Project Structure (Updated for Milestone 2):
```
redis2/
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Python dependencies
├── hr_processor.py             # Redis queue processor (Milestone 1)
├── ingestion_api.py            # FastAPI ingestion service
├── middleware_service.py       # Core middleware service (New)
├── redis_client.py             # Async Redis client (New)
├── role_validator.py           # Role-based access control (New)
├── sql_executor.py             # PostgreSQL integration (New)
├── haystack_wrapper.py         # Haystack integration (New)
├── model_manager.py            # Multi-LLM flexibility (New)
├── pipeline.py                 # Request orchestration (New)
├── models.yml                  # LLM configuration (New)
├── redis2/
│   ├── query.py                # Original query functions
│   ├── dailySalesBreakdown.csv
│   ├── file1.csv
│   └── ui/
│       └── streamlit_app.py    # Enhanced Streamlit UI
├── tests/
│   ├── push_test_question.py   # Redis test client (New)
│   └── listen_response.py      # Redis response listener (New)
├── Dockerfile.api              # API service Dockerfile
├── Dockerfile.processor        # Processor service Dockerfile 
└── start_system.*              # Startup scripts
```

### Environment Variables (Updated for Milestone 2):
- `REDIS_HOST`: Redis hostname (default: redis)
- `REDIS_PORT`: Redis port (default: 6379)
- `POSTGRES_HOST`: PostgreSQL hostname (default: postgres)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_USER`: PostgreSQL username (default: postgres)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: postgres)
- `POSTGRES_DB`: PostgreSQL database (default: hrask)
- `ELASTICSEARCH_HOST`: Elasticsearch hostname (default: elasticsearch)
- `ELASTICSEARCH_PORT`: Elasticsearch port (default: 9200)
- `OLLAMA_HOST`: Ollama hostname (default: ollama)
- `OLLAMA_PORT`: Ollama port (default: 11434)

## 🔧 Troubleshooting

### Common Issues:

1. **Ollama not accessible**:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
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

5. **PostgreSQL connection issues**:
   ```bash
   # Check PostgreSQL
   docker-compose exec postgres psql -U postgres -d hrask -c "SELECT 1;"
   ```

6. **Middleware service not responding**:
   ```bash
   # Check middleware health
   curl http://localhost:8081/health
   
   # Check middleware logs
   docker-compose logs -f middleware
   ```

### Monitoring:

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f middleware
docker-compose logs -f ingestion_api
docker-compose logs -f streamlit

# Check service status
docker-compose ps

# Monitor Redis queues
docker-compose exec redis redis-cli llen hrask.ask.queue
docker-compose exec redis redis-cli llen hrask.response.queue

# Monitor PostgreSQL
docker-compose exec postgres psql -U postgres -d hrask -c "SELECT COUNT(*) FROM employees;"
```

## 📈 Performance Notes

- The system uses async/await for both Redis and PostgreSQL connections
- Hybrid retrieval strategy combines Haystack for unstructured data and SQL for structured queries
- Redis Pub/Sub enables scalable message processing
- Role-based middleware enforces data isolation based on user permissions
- Multiple LLM options with configurable settings via models.yml
- PostgreSQL provides fast structured data access for common HR queries

## ⏹️ Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears all data)
docker-compose down -v
```
