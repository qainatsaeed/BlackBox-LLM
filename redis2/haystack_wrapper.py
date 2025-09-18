"""
Haystack wrapper module for HRAsk system - integration with Haystack
"""
import os
import logging
from typing import Dict, Any, List, Optional, Union
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack import Document
import pandas as pd
import asyncio

logger = logging.getLogger(__name__)

class HaystackWrapper:
    def __init__(self):
        """Initialize Haystack document store and retriever"""
        self.document_store = InMemoryDocumentStore()
        self.retriever = InMemoryBM25Retriever(document_store=self.document_store)
        logger.info("Haystack components initialized")
    
    async def retrieve_documents(self, query: str, filters: Dict[str, Any] = None, 
                                top_k: int = 5) -> List[Document]:
        """
        Retrieve documents from Haystack using the query
        """
        try:
            # Retriever.run() is synchronous, so we run it in an executor to avoid blocking
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.retriever.run(query=query, filters=filters, top_k=top_k)
            )
            documents = result["documents"]
            logger.info(f"Retrieved {len(documents)} documents for query: {query[:50]}...")
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []
    
    def add_documents(self, documents: List[Document]) -> int:
        """
        Add documents to Haystack document store
        """
        try:
            self.document_store.write_documents(documents)
            logger.info(f"Added {len(documents)} documents to document store")
            return len(documents)
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return 0
    
    async def ingest_csv(self, file_path: str) -> int:
        """
        Ingest CSV file into Haystack document store
        This is a wrapper around the existing functionality to make it async-compatible
        """
        try:
            # Reading CSV is I/O bound, so we run it in an executor
            loop = asyncio.get_running_loop()
            df = await loop.run_in_executor(None, pd.read_csv, file_path)
            
            docs = []
            for idx, row in df.iterrows():
                # Create content from CSV row
                content_parts = []
                meta_data = {"source": "csv", "row_id": idx}
                
                for col, val in row.items():
                    if pd.notna(val):
                        content_parts.append(f"{col}: {val}")
                        meta_data[col] = str(val)
                
                content = "\n".join(content_parts)
                
                # Create document
                doc = Document(content=content, meta=meta_data)
                docs.append(doc)
            
            # Adding to document store
            added = self.add_documents(docs)
            
            return added
            
        except Exception as e:
            logger.error(f"Error ingesting CSV: {str(e)}")
            return 0
    
    def get_document_count(self) -> int:
        """Get the number of documents in the document store"""
        try:
            return len(self.document_store.filter_documents())
        except Exception as e:
            logger.error(f"Error getting document count: {str(e)}")
            return 0
    
    def clear_documents(self) -> bool:
        """Clear all documents from the document store"""
        try:
            self.document_store.delete_documents()
            logger.info("Document store cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing documents: {str(e)}")
            return False