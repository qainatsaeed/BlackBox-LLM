from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack import Document
import pandas as pd
import requests
import json

INDEX_NAME = "employee-shifts"

# Init document store & retriever
document_store = InMemoryDocumentStore()
retriever = InMemoryBM25Retriever(document_store=document_store)

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def ingest_csv(file_path: str):
    """Ingest CSV file into Elasticsearch document store"""
    df = pd.read_csv(file_path)
    docs = []
    for idx, row in df.iterrows():
        # Create more structured content from CSV row
        content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
        doc = Document(
            content=content, 
            meta={
                "source": "csv",
                "row_id": idx,
                **{col: str(val) for col, val in row.items() if pd.notna(val)}
            }
        )
        docs.append(doc)
    
    document_store.write_documents(docs)
    return len(docs)

def ask_llm_ollama(query: str, top_k: int = 5) -> str:
    """Query LLM using Ollama instead of OpenAI"""
    docs = retriever.run(query=query, top_k=top_k)["documents"]
    context = "\n\n".join([doc.content for doc in docs])
    
    prompt = f"""You're an HR assistant answering questions based on employee shifts. Only use the provided context.

Context:
{context}

Question: {query}

Answer:"""

    payload = {
        "model": "llama3.1:8b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 150
        }
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=100  # Reduced timeout for 8b model
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response generated")
    except Exception as e:
        return f"Error querying Ollama: {str(e)}"

# Keep the old function name for backward compatibility
def ask_llm(query: str, top_k: int = 5) -> str:
    return ask_llm_ollama(query, top_k)
