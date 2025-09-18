"""
Pipeline module for HRAsk system - orchestrates flow from Redis to LLM
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union

from redis_client import RedisAsyncClient
from role_validator import RoleValidator, User
from sql_executor import SQLExecutor
from haystack_wrapper import HaystackWrapper
from model_manager import ModelManager

logger = logging.getLogger(__name__)

class HRAskPipeline:
    def __init__(self):
        """Initialize pipeline components"""
        self.redis_client = RedisAsyncClient()
        self.role_validator = RoleValidator()
        self.sql_executor = SQLExecutor()
        self.haystack_wrapper = HaystackWrapper()
        self.model_manager = ModelManager()
        
        # Query classification patterns for routing
        self.sql_patterns = {
            "who is working": "employee_shifts",
            "who worked on": "employee_shifts",
            "employees working": "employee_shifts",
            "labor cost": "labor_cost",
            "employee id": "employee_by_id",
            "position": "employees_by_position"
        }
    
    async def initialize(self) -> None:
        """Initialize all components"""
        await self.redis_client.connect()
        await self.sql_executor.connect()
    
    async def shutdown(self) -> None:
        """Shutdown all components"""
        await self.redis_client.disconnect()
        await self.sql_executor.disconnect()
    
    async def process_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a query through the pipeline
        
        Args:
            query_data: Dictionary containing query text and metadata
        
        Returns:
            Response dictionary with answer
        """
        try:
            query_id = query_data.get('query_id', 'unknown')
            query_text = query_data.get('query', '')
            model_name = query_data.get('model', None)
            top_k = int(query_data.get('top_k', 5))
            
            logger.info(f"Processing query ID {query_id}: {query_text[:50]}...")
            
            # Validate user role and get filters
            user = self.role_validator.validate_role(query_data)
            filters = self.role_validator.create_filters(user)
            
            # Determine query type and route appropriately
            query_type = self._classify_query(query_text)
            
            documents = []
            sql_results = []
            
            # For structured queries, use SQL executor
            if query_type.startswith('sql:'):
                sql_intent = query_type.split(':')[1]
                sql_params = self._extract_sql_params(query_text, sql_intent)
                
                if sql_params:
                    sql_results = await self.sql_executor.process_structured_query(sql_intent, sql_params)
                    
                    # Convert SQL results to documents for context
                    for idx, result in enumerate(sql_results):
                        content = "\n".join([f"{k}: {v}" for k, v in result.items()])
                        documents.append({
                            "content": content,
                            "meta": {**result, "source": "sql", "idx": idx}
                        })
            
            # Always retrieve from document store as well (hybrid approach)
            haystack_docs = await self.haystack_wrapper.retrieve_documents(
                query=query_text,
                filters=filters,
                top_k=top_k
            )
            
            # Combine documents from both sources
            all_docs = haystack_docs + documents
            
            # Filter documents by role permissions
            filtered_docs = self.role_validator.apply_document_filters(all_docs, user)
            
            # Create context from documents
            context = self._create_context(filtered_docs)
            
            if not context.strip():
                response_text = "I don't have access to information relevant to your query."
            else:
                # Query the LLM with the context
                response_text = await self.model_manager.query_model(
                    model_name=model_name,
                    query=query_text,
                    context=context,
                    user_role=user.role
                )
            
            # Prepare response
            response = {
                "success": True,
                "response": response_text,
                "query_id": query_id,
                "documents_found": len(filtered_docs)
            }
            
            # Add debug info for non-employees
            if user.role != 'employee':
                response["debug"] = {
                    "filters_applied": filters,
                    "documents_retrieved": len(all_docs),
                    "documents_after_filtering": len(filtered_docs),
                    "query_type": query_type,
                    "model_used": model_name or self.model_manager.default_model
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query_id": query_data.get('query_id', 'unknown')
            }
    
    def _classify_query(self, query: str) -> str:
        """
        Classify query type for routing
        
        Returns:
            'sql:<intent>' for structured queries, 'haystack' for others
        """
        query_lower = query.lower()
        
        for pattern, sql_type in self.sql_patterns.items():
            if pattern in query_lower:
                return f"sql:{sql_type}"
        
        return "haystack"
    
    def _extract_sql_params(self, query: str, intent: str) -> List:
        """
        Extract parameters for SQL query based on intent
        
        This is a simplistic implementation - in production would use NER
        """
        # Simple parameter extraction for demo purposes
        import re
        from datetime import datetime
        
        query_lower = query.lower()
        
        if intent == "employee_shifts":
            # Extract date
            date_match = re.search(r'on (\d{1,2}/\d{1,2}/\d{4})', query_lower)
            if date_match:
                return [date_match.group(1)]
            
            # Try more date formats
            date_match = re.search(r'on (january|february|march|april|may|june|july|august|september|october|november|december) (\d{1,2}),? (\d{4})', query_lower)
            if date_match:
                month_dict = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                month = month_dict[date_match.group(1)]
                day = int(date_match.group(2))
                year = int(date_match.group(3))
                return [f"{month}/{day}/{year}"]
            
            # Today as fallback
            return [datetime.now().strftime("%m/%d/%Y")]
            
        elif intent == "employee_by_id":
            # Extract employee ID
            id_match = re.search(r'employee (\w+)', query_lower)
            if id_match:
                return [id_match.group(1)]
            return None
            
        elif intent == "employees_by_position":
            # Extract position and date
            position_match = re.search(r'position (\w+)', query_lower)
            date_match = re.search(r'on (\d{1,2}/\d{1,2}/\d{4})', query_lower)
            
            if position_match and date_match:
                return [position_match.group(1), date_match.group(1)]
            elif position_match:
                return [position_match.group(1), datetime.now().strftime("%m/%d/%Y")]
            
            return None
            
        elif intent == "labor_cost":
            # Extract date range
            start_date_match = re.search(r'from (\d{1,2}/\d{1,2}/\d{4})', query_lower)
            end_date_match = re.search(r'to (\d{1,2}/\d{1,2}/\d{4})', query_lower)
            
            if start_date_match and end_date_match:
                return [start_date_match.group(1), end_date_match.group(1)]
            
            # If only looking at a month
            month_match = re.search(r'in (january|february|march|april|may|june|july|august|september|october|november|december)', query_lower)
            if month_match:
                month_dict = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }
                month = month_dict[month_match.group(1)]
                year = datetime.now().year
                return [f"{month}/1/{year}", f"{month}/28/{year}"]
            
            # Default to current month
            now = datetime.now()
            return [f"{now.month}/1/{now.year}", f"{now.month}/{now.day}/{now.year}"]
            
        return None
    
    def _create_context(self, documents: List) -> str:
        """
        Create context string from documents
        """
        context_parts = []
        
        for i, doc in enumerate(documents):
            if hasattr(doc, 'content'):
                # Haystack Document
                context_parts.append(f"--- Document {i+1} ---\n{doc.content}")
            elif isinstance(doc, dict) and 'content' in doc:
                # Dictionary with content field
                context_parts.append(f"--- Document {i+1} ---\n{doc['content']}")
        
        return "\n\n".join(context_parts)
    
    async def start_pipeline(self) -> None:
        """Start the pipeline to process questions from Redis"""
        await self.initialize()
        
        async def process_callback(query_data: Dict[str, Any]) -> None:
            """Callback function for processing queries"""
            response = await self.process_query(query_data)
            await self.redis_client.publish_response(response)
        
        try:
            logger.info("Starting pipeline...")
            await self.redis_client.subscribe_to_questions(process_callback)
        except asyncio.CancelledError:
            logger.info("Pipeline shutdown requested")
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
        finally:
            await self.shutdown()