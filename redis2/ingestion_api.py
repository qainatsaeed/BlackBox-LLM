"""
Ingestion API - REST API for uploading and ingesting data files
"""
import json
import os
import tempfile
from typing import List, Optional
import pandas as pd
import redis
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack import Document

app = FastAPI(title="HR Data Ingestion API", version="1.0.0")

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)

# Document store (using InMemory for simplicity and compatibility)
document_store = InMemoryDocumentStore()

class QueryRequest(BaseModel):
    query: str
    user_role: str = "employee"
    user_id: str = ""
    top_k: int = 5

class QueryResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    query_id: str
    documents_found: Optional[int] = None

@app.post("/upload/csv")
async def upload_csv(files: List[UploadFile] = File(...)):
    """Upload and ingest CSV files"""
    results = []
    
    for file in files:
        if not file.filename.endswith('.csv'):
            results.append({
                "filename": file.filename,
                "success": False,
                "error": "File must be a CSV"
            })
            continue
        
        try:
            # Save temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            # Process the CSV
            docs_count = ingest_csv_file(tmp_file_path, file.filename)
            
            # Clean up
            os.unlink(tmp_file_path)
            
            results.append({
                "filename": file.filename,
                "success": True,
                "documents_ingested": docs_count
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results}

@app.post("/ingest/existing")
async def ingest_existing_files():
    """Ingest existing CSV files from the data directory"""
    data_dir = "/app/data"
    csv_files = ["dailySalesBreakdown.csv", "file1.csv"]
    
    results = []
    total_docs = 0
    
    for csv_file in csv_files:
        file_path = os.path.join(data_dir, csv_file)
        if os.path.exists(file_path):
            try:
                docs_count = ingest_csv_file(file_path, csv_file)
                results.append({
                    "filename": csv_file,
                    "success": True,
                    "documents_ingested": docs_count
                })
                total_docs += docs_count
            except Exception as e:
                results.append({
                    "filename": csv_file,
                    "success": False,
                    "error": str(e)
                })
        else:
            results.append({
                "filename": csv_file,
                "success": False,
                "error": "File not found"
            })
    
    return {
        "results": results,
        "total_documents_ingested": total_docs
    }

@app.post("/query", response_model=QueryResponse)
async def submit_query(request: QueryRequest):
    """Submit a query via Redis queue"""
    import uuid
    
    query_id = str(uuid.uuid4())
    
    query_data = {
        "query_id": query_id,
        "query": request.query,
        "user_role": request.user_role,
        "user_id": request.user_id,
        "top_k": request.top_k
    }
    
    try:
        # Send to Redis queue
        redis_client.rpush("hrask.ask.queue", json.dumps(query_data))
        
        # Wait for response (with timeout)
        response = None
        for _ in range(30):  # 30 second timeout
            response_data = redis_client.blpop("hrask.response.queue", timeout=1)
            if response_data:
                _, response_json = response_data
                response = json.loads(response_json)
                if response.get("query_id") == query_id:
                    break
        
        if not response:
            raise HTTPException(status_code=408, detail="Query timeout")
        
        if response.get("success"):
            return QueryResponse(
                success=True,
                response=response["response"],
                query_id=query_id,
                documents_found=response.get("documents_found", 0)
            )
        else:
            return QueryResponse(
                success=False,
                error=response.get("error", "Unknown error"),
                query_id=query_id
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        
        # Test Elasticsearch connection
        document_store.get_document_count()
        
        return {"status": "healthy", "redis": "connected", "elasticsearch": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        doc_count = document_store.get_document_count()
        queue_size = redis_client.llen("hrask.ask.queue")
        
        return {
            "documents_in_store": doc_count,
            "pending_queries": queue_size,
            "available_indices": ["hr-data"]
        }
    except Exception as e:
        return {"error": str(e)}

def ingest_csv_file(file_path: str, source_file: str) -> int:
    """Process and ingest a CSV file"""
    df = pd.read_csv(file_path)
    docs = []
    
    # Determine file type and process accordingly
    if "dailySalesBreakdown" in source_file.lower() or "sales" in source_file.lower():
        docs = process_sales_data(df, source_file)
    elif "file1" in source_file.lower() or "employee" in source_file.lower() or "schedule" in source_file.lower():
        docs = process_employee_data(df, source_file)
    else:
        docs = process_generic_csv(df, source_file)
    
    if docs:
        document_store.write_documents(docs)
    
    return len(docs)

def process_sales_data(df: pd.DataFrame, source_file: str) -> List[Document]:
    """Process daily sales breakdown data"""
    docs = []
    
    for idx, row in df.iterrows():
        if pd.isna(row.get('Date', pd.NaT)) or 'Totals' in str(row.get('Date', '')):
            continue
            
        content_parts = []
        
        if not pd.isna(row.get('Date')):
            content_parts.append(f"Date: {row['Date']}")
        
        # Add all non-null columns to content
        for col, val in row.items():
            if not pd.isna(val) and col != 'Date':
                content_parts.append(f"{col}: {val}")
        
        if content_parts:
            content = "\n".join(content_parts)
            
            doc = Document(
                content=content,
                meta={
                    "source": source_file,
                    "data_type": "sales_breakdown",
                    "date": str(row.get('Date', '')),
                    "location": "RT2 - South Austin",
                    "row_id": idx,
                    **{col: str(val) for col, val in row.items() if not pd.isna(val)}
                }
            )
            docs.append(doc)
    
    return docs

def process_employee_data(df: pd.DataFrame, source_file: str) -> List[Document]:
    """Process employee schedule and attendance data"""
    docs = []
    
    for idx, row in df.iterrows():
        if pd.isna(row.get('Employee')):
            continue
            
        content_parts = []
        
        # Add all non-null columns to content
        for col, val in row.items():
            if not pd.isna(val):
                content_parts.append(f"{col}: {val}")
        
        content = "\n".join(content_parts)
        
        doc = Document(
            content=content,
            meta={
                "source": source_file,
                "data_type": "employee_schedule",
                "employee": str(row.get('Employee', '')),
                "date": str(row.get('Date', '')),
                "scheduled_position": str(row.get('Sched Position', '')),
                "scheduled_department": str(row.get('Sched Department', '')),
                "row_id": idx,
                **{col: str(val) for col, val in row.items() if not pd.isna(val)}
            }
        )
        docs.append(doc)
    
    return docs

def process_generic_csv(df: pd.DataFrame, source_file: str) -> List[Document]:
    """Generic CSV processing"""
    docs = []
    
    for idx, row in df.iterrows():
        content = "\n".join([f"{col}: {val}" for col, val in row.items() if not pd.isna(val)])
        
        if content.strip():
            doc = Document(
                content=content,
                meta={
                    "source": source_file,
                    "data_type": "generic",
                    "row_id": idx,
                    **{col: str(val) for col, val in row.items() if not pd.isna(val)}
                }
            )
            docs.append(doc)
    
    return docs

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
