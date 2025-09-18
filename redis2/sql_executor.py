"""
SQL Executor module for HRAsk system - PostgreSQL integration with asyncpg
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union
import asyncpg
import pandas as pd
from haystack import Document

logger = logging.getLogger(__name__)

class SQLExecutor:
    def __init__(self):
        """Initialize PostgreSQL executor with connection details from env vars"""
        self.host = os.getenv('POSTGRES_HOST', 'postgres')
        self.port = int(os.getenv('POSTGRES_PORT', 5432))
        self.user = os.getenv('POSTGRES_USER', 'postgres')
        self.password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        self.database = os.getenv('POSTGRES_DB', 'hrask')
        self._pool = None
        
        # Map query intents to SQL templates
        self.query_templates = {
            "employee_shifts": """
                SELECT e.name, s.date, s.position, s.department, s.start_time, s.end_time, s.hours 
                FROM shifts s 
                JOIN employees e ON s.employee_id = e.id 
                WHERE date = $1 
                ORDER BY e.name
            """,
            "employee_by_id": """
                SELECT * FROM employees WHERE id = $1
            """,
            "employees_by_position": """
                SELECT e.name, s.date, s.position, s.department, s.start_time, s.end_time, s.hours
                FROM shifts s
                JOIN employees e ON s.employee_id = e.id
                WHERE s.position = $1 AND s.date = $2
                ORDER BY e.name
            """,
            "labor_cost": """
                SELECT date, sum(hours * rate) as labor_cost 
                FROM shifts s 
                JOIN employees e ON s.employee_id = e.id 
                WHERE date BETWEEN $1 AND $2
                GROUP BY date 
                ORDER BY date
            """
        }
    
    async def connect(self) -> None:
        """Connect to PostgreSQL database"""
        if self._pool:
            return
            
        try:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                min_size=1,
                max_size=10
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL database"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Disconnected from PostgreSQL")
    
    async def execute_query(self, query: str, params: List = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dictionaries"""
        if not self._pool:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetch(query, *(params or []))
                return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            return []
    
    async def process_structured_query(self, query_intent: str, params: List) -> List[Dict[str, Any]]:
        """Process structured query using predefined templates"""
        if query_intent not in self.query_templates:
            logger.error(f"Unknown query intent: {query_intent}")
            return []
        
        query = self.query_templates[query_intent]
        return await self.execute_query(query, params)
    
    async def is_healthy(self) -> bool:
        """Check if PostgreSQL connection is healthy"""
        if not self._pool:
            try:
                await self.connect()
            except Exception:
                return False
        
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception:
            return False
    
    async def ingest_from_postgres_to_haystack(self, query: str, user_role: str = None) -> List[Document]:
        """
        Query PostgreSQL and convert results to Haystack documents
        """
        if not self._pool:
            await self.connect()
        
        try:
            # Execute query and get results
            async with self._pool.acquire() as conn:
                result = await conn.fetch(query)
                rows = [dict(row) for row in result]
                
            # Convert to Haystack documents
            documents = []
            
            for idx, row in enumerate(rows):
                # Create structured content from row data
                content_parts = []
                meta_data = {"source": "postgres", "row_id": idx}
                
                for key, value in row.items():
                    if value is not None:
                        content_parts.append(f"{key}: {value}")
                        meta_data[key] = str(value)
                
                content = "\n".join(content_parts)
                
                # Set data type based on keys in the row
                if "employee_id" in row or "name" in row:
                    meta_data["data_type"] = "employee"
                elif "date" in row and "position" in row:
                    meta_data["data_type"] = "shift"
                elif "date" in row and "labor_cost" in row:
                    meta_data["data_type"] = "labor_cost"
                else:
                    meta_data["data_type"] = "generic_sql"
                
                # Add document
                doc = Document(content=content, meta=meta_data)
                documents.append(doc)
                
            logger.info(f"Generated {len(documents)} Haystack documents from SQL query")
            return documents
            
        except Exception as e:
            logger.error(f"Error ingesting from PostgreSQL: {str(e)}")
            return []
    
    async def ingest_from_file(self, file_path: str, table_name: str) -> int:
        """
        Ingest data from JSON or Parquet file into PostgreSQL
        """
        if not self._pool:
            await self.connect()
        
        try:
            # Read data from file based on extension
            ext = file_path.split('.')[-1].lower()
            if ext == 'json':
                df = pd.read_json(file_path)
            elif ext in ('parquet', 'pq'):
                df = pd.read_parquet(file_path)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return 0
                
            # Convert dataframe to records
            records = df.to_dict(orient='records')
            
            # Get column names and types
            columns = list(records[0].keys()) if records else []
            
            if not columns:
                logger.error("No columns found in file")
                return 0
            
            # Create table if not exists (simple approach)
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("
            create_table_sql += ", ".join([f"{col} TEXT" for col in columns])
            create_table_sql += ")"
            
            # Generate insert SQL
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['$' + str(i+1) for i in range(len(columns))])})"
            
            # Execute SQL
            count = 0
            async with self._pool.acquire() as conn:
                await conn.execute(create_table_sql)
                
                # Insert records
                for record in records:
                    values = [record.get(col) for col in columns]
                    await conn.execute(insert_sql, *values)
                    count += 1
            
            logger.info(f"Ingested {count} records into {table_name}")
            return count
            
        except Exception as e:
            logger.error(f"Error ingesting from file: {str(e)}")
            return 0