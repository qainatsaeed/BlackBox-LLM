"""
HR Ask Service - Processes questions from Redis queue using Haystack v2 and Ollama
"""
import json
import logging
import os
import time
from typing import Dict, Any, Optional
import redis
import requests
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HRProcessor:
    def __init__(self):
        # Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Document store - using InMemory for simplicity (can switch to Elasticsearch later)
        self.document_store = InMemoryDocumentStore()
        self.retriever = InMemoryBM25Retriever(document_store=self.document_store)
        
        # Ollama connection
        self.ollama_host = os.getenv('OLLAMA_HOST', 'localhost')
        self.ollama_port = os.getenv('OLLAMA_PORT', '11434')
        self.ollama_base_url = f"http://{self.ollama_host}:{self.ollama_port}"
        
        # Queue names
        self.ask_queue = "hrask.ask.queue"
        self.response_queue = "hrask.response.queue"
        
        logger.info("HR Processor initialized")

    def ingest_csv_files(self):
        """Ingest CSV files from the data directory"""
        data_dir = "/app/data"
        csv_files = ["dailySalesBreakdown.csv", "file1.csv"]
        
        all_docs = []
        
        for csv_file in csv_files:
            file_path = os.path.join(data_dir, csv_file)
            if os.path.exists(file_path):
                logger.info(f"Ingesting {csv_file}")
                docs = self._process_csv_file(file_path, csv_file)
                all_docs.extend(docs)
            else:
                logger.warning(f"File not found: {file_path}")
        
        if all_docs:
            self.document_store.write_documents(all_docs)
            logger.info(f"Ingested {len(all_docs)} documents")
        
        return len(all_docs)

    def _process_csv_file(self, file_path: str, source_file: str) -> list:
        """Process a CSV file and convert to Haystack documents"""
        df = pd.read_csv(file_path)
        docs = []
        
        # Determine file type and process accordingly
        if "dailySalesBreakdown" in source_file:
            docs = self._process_sales_data(df, source_file)
        elif "file1" in source_file:
            docs = self._process_employee_data(df, source_file)
        else:
            # Generic processing
            docs = self._process_generic_csv(df, source_file)
        
        return docs

    def _process_sales_data(self, df: pd.DataFrame, source_file: str) -> list:
        """Process daily sales breakdown data"""
        docs = []
        
        for idx, row in df.iterrows():
            if pd.isna(row.get('Date', pd.NaT)) or 'Totals' in str(row.get('Date', '')):
                continue
                
            # Create structured content for sales data
            content_parts = []
            
            if not pd.isna(row.get('Date')):
                content_parts.append(f"Date: {row['Date']}")
            
            # Sales data
            sales_cols = ['Sales-Projected NET SALES', 'Threshold Ratio']
            for col in sales_cols:
                if col in row and not pd.isna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            # Cost data
            cost_cols = ['Scheduled Cost ', 'Scheduled Threshold', 'Attendance Cost ', 'Attendance Threshold']
            for col in cost_cols:
                if col in row and not pd.isna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            # Variance data
            variance_cols = ['Cost   Variance', 'Threshold  Variance']
            for col in variance_cols:
                if col in row and not pd.isna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
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

    def _process_employee_data(self, df: pd.DataFrame, source_file: str) -> list:
        """Process employee schedule and attendance data"""
        docs = []
        
        for idx, row in df.iterrows():
            if pd.isna(row.get('Employee')):
                continue
                
            content_parts = []
            
            # Employee info
            content_parts.append(f"Employee: {row['Employee']}")
            content_parts.append(f"Date: {row['Date']}")
            
            # Scheduled info
            sched_cols = ['Sched Position', 'Sched Department', 'Sched Start', 'Sched End', 'Sched Total hrs']
            for col in sched_cols:
                if col in row and not pd.isna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            # Attendance info
            att_cols = ['Att Position', 'Att Department', 'Att Start', 'Att End', 'Att Total hrs']
            for col in att_cols:
                if col in row and not pd.isna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            
            # Hour difference
            if 'Hour Difference' in row and not pd.isna(row['Hour Difference']):
                content_parts.append(f"Hour Difference: {row['Hour Difference']}")
            
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
                    "attendance_position": str(row.get('Att Position', '')),
                    "attendance_department": str(row.get('Att Department', '')),
                    "row_id": idx,
                    **{col: str(val) for col, val in row.items() if not pd.isna(val)}
                }
            )
            docs.append(doc)
        
        return docs

    def _process_generic_csv(self, df: pd.DataFrame, source_file: str) -> list:
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

    def query_llm(self, query: str, context: str, user_role: str = "employee", user_id: str = None) -> str:
        """Query the Ollama LLM with context"""
        
        # Role-based prompt engineering
        role_context = self._get_role_context(user_role, user_id)
        
        prompt = f"""You are an HR assistant with access to employee data. {role_context}

Context from database:
{context}

Question: {query}

Instructions:
- Only use information from the provided context
- If the context doesn't contain relevant information, say so
- Be precise with numbers, dates, and employee names
- For financial data, include currency symbols and proper formatting
- For time data, use clear time formats

Answer:"""

        payload = {
            "model": "llama3.1:8b",  # Much faster than 70b
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 150,  # Shorter responses
                "stop": ["Human:", "Question:", "\n\n"]
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=30  # Reduced timeout for 8b model
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response generated")
        except Exception as e:
            logger.error(f"Error querying Ollama: {str(e)}")
            return f"Error querying LLM: {str(e)}"

    def _get_role_context(self, user_role: str, user_id: str) -> str:
        """Get role-specific context for prompts"""
        role_contexts = {
            "employee": f"You're answering for an employee (ID: {user_id}). Only provide information relevant to this specific employee.",
            "supervisor": f"You're answering for a supervisor (ID: {user_id}). Provide team-level information for their supervised employees.",
            "manager": f"You're answering for a manager (ID: {user_id}). Provide location-level performance and team data.",
            "admin": "You're answering for an administrator. Provide comprehensive information as requested."
        }
        return role_contexts.get(user_role, role_contexts["employee"])

    def process_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a query from the Redis queue"""
        try:
            query_text = query_data.get('query', '')
            user_role = query_data.get('user_role', 'employee')
            user_id = query_data.get('user_id', '')
            top_k = query_data.get('top_k', 5)
            
            # Retrieve relevant documents
            docs = self.retriever.run(query=query_text, top_k=top_k)["documents"]
            
            # Apply role-based filtering
            filtered_docs = self._filter_docs_by_role(docs, user_role, user_id)
            
            # Create context from documents
            context = "\n\n".join([doc.content for doc in filtered_docs])
            
            if not context.strip():
                response_text = "I don't have access to information relevant to your query."
            else:
                # Query the LLM
                response_text = self.query_llm(query_text, context, user_role, user_id)
            
            return {
                "success": True,
                "response": response_text,
                "query_id": query_data.get('query_id', ''),
                "documents_found": len(filtered_docs)
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query_id": query_data.get('query_id', '')
            }

    def _filter_docs_by_role(self, docs: list, user_role: str, user_id: str) -> list:
        """Filter documents based on user role and access permissions"""
        if user_role == "admin":
            return docs  # Admins see everything
        
        filtered_docs = []
        for doc in docs:
            # Role-based filtering logic
            if user_role == "employee":
                # Employees only see their own data
                if doc.meta.get('employee', '').lower() == user_id.lower():
                    filtered_docs.append(doc)
                # Or general sales data (no personal info)
                elif doc.meta.get('data_type') == 'sales_breakdown':
                    filtered_docs.append(doc)
            
            elif user_role == "supervisor":
                # Supervisors see team data (implement team mapping logic)
                filtered_docs.append(doc)  # For now, show all
            
            elif user_role == "manager":
                # Managers see location-level data
                filtered_docs.append(doc)  # For now, show all
        
        return filtered_docs

    def run(self):
        """Main processing loop"""
        logger.info("Starting HR Processor...")
        
        # Initial ingestion
        try:
            self.ingest_csv_files()
        except Exception as e:
            logger.error(f"Error during initial ingestion: {str(e)}")
        
        # Start processing loop
        while True:
            try:
                # Check for messages in the ask queue
                message = self.redis_client.blpop(self.ask_queue, timeout=5)
                
                if message:
                    queue_name, message_data = message
                    query_data = json.loads(message_data)
                    
                    logger.info(f"Processing query: {query_data.get('query', '')[:50]}...")
                    
                    # Process the query
                    response = self.process_query(query_data)
                    
                    # Send response to response queue
                    self.redis_client.rpush(self.response_queue, json.dumps(response))
                    
                    logger.info(f"Response sent for query ID: {response.get('query_id', 'unknown')}")
                
                time.sleep(0.1)  # Short sleep to prevent busy waiting
                
            except KeyboardInterrupt:
                logger.info("Shutting down HR Processor...")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {str(e)}")
                time.sleep(1)  # Wait before retrying

if __name__ == "__main__":
    processor = HRProcessor()
    processor.run()
