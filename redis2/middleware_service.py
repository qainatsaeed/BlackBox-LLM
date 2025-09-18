"""
HRAsk Middleware Service - main entry point for the middleware
"""
import os
import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from pipeline import HRAskPipeline
from redis_client import RedisAsyncClient
from sql_executor import SQLExecutor
from haystack_wrapper import HaystackWrapper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('middleware.log')
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="HRAsk Middleware API")

# Global pipeline instance
pipeline = None
redis_client = None
sql_executor = None
haystack_wrapper = None

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global pipeline, redis_client, sql_executor, haystack_wrapper
    
    pipeline = HRAskPipeline()
    redis_client = RedisAsyncClient()
    sql_executor = SQLExecutor()
    haystack_wrapper = HaystackWrapper()
    
    # Initialize connections
    await redis_client.connect()
    await sql_executor.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global pipeline, redis_client, sql_executor
    
    if pipeline:
        await pipeline.shutdown()
    
    if redis_client:
        await redis_client.disconnect()
    
    if sql_executor:
        await sql_executor.disconnect()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    global redis_client, sql_executor, haystack_wrapper
    
    redis_healthy = await redis_client.is_healthy() if redis_client else False
    postgres_healthy = await sql_executor.is_healthy() if sql_executor else False
    docs_count = haystack_wrapper.get_document_count() if haystack_wrapper else 0
    
    return {
        "status": "healthy" if redis_healthy and postgres_healthy else "degraded",
        "redis": "connected" if redis_healthy else "disconnected",
        "postgres": "connected" if postgres_healthy else "disconnected",
        "document_store": f"{docs_count} documents"
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    global haystack_wrapper
    
    # Get pending queries count from Redis
    pending_count = 0
    try:
        if redis_client and await redis_client.is_healthy():
            # This is a simplification - would need LLEN command
            pass
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
    
    return {
        "documents_in_store": haystack_wrapper.get_document_count() if haystack_wrapper else 0,
        "pending_queries": pending_count
    }

@app.post("/query/direct")
async def direct_query(request: Request):
    """Process query directly (bypass Redis)"""
    global pipeline
    
    try:
        query_data = await request.json()
        
        if not pipeline:
            pipeline = HRAskPipeline()
            await pipeline.initialize()
        
        response = await pipeline.process_query(query_data)
        return response
    except Exception as e:
        logger.error(f"Error processing direct query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/postgres")
async def ingest_from_postgres(request: Request):
    """Ingest data from PostgreSQL to Haystack"""
    global sql_executor, haystack_wrapper
    
    try:
        data = await request.json()
        query = data.get("query")
        
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        # Execute query and convert to documents
        documents = await sql_executor.ingest_from_postgres_to_haystack(query)
        
        # Add documents to Haystack
        count = haystack_wrapper.add_documents(documents)
        
        return {
            "success": True,
            "documents_ingested": count
        }
    except Exception as e:
        logger.error(f"Error ingesting from PostgreSQL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_pipeline():
    """Run the main pipeline in the background"""
    global pipeline
    
    try:
        pipeline = HRAskPipeline()
        await pipeline.start_pipeline()
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")

async def main():
    """Main function to run both API server and pipeline"""
    # Start the pipeline in the background
    pipeline_task = asyncio.create_task(run_pipeline())
    
    # Start the API server
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8081,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Setup signal handling
    loop = asyncio.get_event_loop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(pipeline_task, server)))
    
    # Run the server
    try:
        await server.serve()
    finally:
        if not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass

async def shutdown(pipeline_task, server):
    """Graceful shutdown"""
    logger.info("Shutting down...")
    
    # Stop the server
    if server:
        server.should_exit = True
    
    # Cancel the pipeline task
    if pipeline_task and not pipeline_task.done():
        pipeline_task.cancel()
        try:
            await pipeline_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(main())