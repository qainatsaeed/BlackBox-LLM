import streamlit as st
import tempfile
import os
import json
import uuid
import time
import redis
import requests
from query import ask_llm, ingest_csv

# Redis connection
@st.cache_resource
def get_redis_client():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )

def submit_query_via_api(query: str, user_role: str = "employee", user_id: str = ""):
    """Submit query via API /query endpoint"""
    api_url = os.getenv('INGESTION_API_URL', 'http://ingestion_api:8080')
    
    query_data = {
        "query": query,
        "user_role": user_role,
        "user_id": user_id,
        "top_k": 5
    }
    
    try:
        response = requests.post(f"{api_url}/query", json=query_data, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def submit_query_via_direct_api(query: str, user_role: str = "employee", user_id: str = ""):
    """Submit query via API /query/direct endpoint (bypass Redis)"""
    api_url = os.getenv('INGESTION_API_URL', 'http://ingestion_api:8080')
    
    query_data = {
        "query": query,
        "user_role": user_role,
        "user_id": user_id,
        "top_k": 5
    }
    
    try:
        response = requests.post(f"{api_url}/query/direct", json=query_data, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

st.set_page_config(page_title="HR Assistant with API", layout="wide")

st.title("🏢 HR Assistant - API Integration")
st.markdown("Upload CSV files and ask questions about employee data via API endpoints.")

# Sidebar for system status
with st.sidebar:
    st.header("System Status")
    
    # Check API health
    try:
        api_url = os.getenv('INGESTION_API_URL', 'http://ingestion_api:8080')
        api_response = requests.get(f"{api_url}/health", timeout=5)
        if api_response.status_code == 200:
            health_data = api_response.json()
            st.success(f"✅ API: {health_data['status']}")
            st.info(f"Redis: {health_data.get('redis', 'unknown')}")
            st.info(f"Document Store: {health_data.get('document_store', 'unknown')}")
        else:
            st.error("❌ API not responding")
    except:
        st.warning("⚠️ Cannot reach API")
    
    # Get stats
    try:
        stats_response = requests.get(f"{api_url}/stats", timeout=5)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            st.metric("Documents in Store", stats.get('documents_in_store', 0))
            st.metric("Pending Queries", stats.get('pending_queries', 0))
    except:
        pass

# Main interface
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📁 Data Ingestion")
    
    # Option 1: Ingest existing files
    if st.button("📤 Ingest Existing CSV Files"):
        with st.spinner("Ingesting existing CSV files..."):
            try:
                api_url = os.getenv('INGESTION_API_URL', 'http://ingestion_api:8080')
                api_response = requests.post(f"{api_url}/ingest/existing", timeout=30)
                if api_response.status_code == 200:
                    result = api_response.json()
                    st.success(f"✅ Ingested {result['total_documents_ingested']} documents")
                    
                    for file_result in result['results']:
                        if file_result['success']:
                            st.success(f"✅ {file_result['filename']}: {file_result['documents_ingested']} docs")
                        else:
                            st.error(f"❌ {file_result['filename']}: {file_result['error']}")
                else:
                    st.error(f"API Error: {api_response.status_code}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Option 2: Upload new files
    st.subheader("Upload New CSV Files")
    uploaded_files = st.file_uploader("Choose CSV files", type="csv", accept_multiple_files=True)
    
    if uploaded_files and st.button("📤 Upload and Ingest"):
        with st.spinner("Uploading and ingesting files..."):
            try:
                api_url = os.getenv('INGESTION_API_URL', 'http://ingestion_api:8080')
                files_data = []
                for uploaded_file in uploaded_files:
                    files_data.append(("files", (uploaded_file.name, uploaded_file.getvalue(), "text/csv")))
                
                api_response = requests.post(f"{api_url}/upload/csv", files=files_data, timeout=60)
                
                if api_response.status_code == 200:
                    result = api_response.json()
                    
                    for file_result in result['results']:
                        if file_result['success']:
                            st.success(f"✅ {file_result['filename']}: {file_result['documents_ingested']} docs")
                        else:
                            st.error(f"❌ {file_result['filename']}: {file_result['error']}")
                else:
                    st.error(f"Upload failed: {api_response.status_code}")
            except Exception as e:
                st.error(f"Upload error: {str(e)}")

with col2:
    st.header("💬 Ask Questions")
    
    # User role selection
    user_role = st.selectbox(
        "Select your role:",
        ["employee", "supervisor", "manager", "admin"],
        help="Different roles have access to different data levels"
    )
    
    user_id = st.text_input(
        "User ID (for role-based access):",
        value="test_user",
        help="Enter your employee ID for personalized results"
    )
    
    query = st.text_area(
        "Enter your question about the data:",
        height=100,
        placeholder="Examples:\n- What were the sales on 5/15/2025?\n- Who worked on 6/1/2025?\n- What was the labor cost variance in May?"
    )
    
    col2a, col2b = st.columns([1, 1])
    
    with col2a:
        use_redis = st.checkbox("Use Redis Queue", value=True, help="Use Redis messaging system via API")
    
    with col2b:
        use_direct = st.checkbox("Use Direct Query", value=False, help="Use direct document store query")
    
    if st.button("🔍 Ask Question"):
        if query.strip():
            with st.spinner("Processing your question..."):
                response = None
                
                if use_redis:
                    # Use Redis queue via API
                    response = submit_query_via_api(query, user_role, user_id)
                    
                    if response.get("success"):
                        st.success("✅ Answer from Redis Queue API:")
                        st.write(response["response"])
                        if response.get("documents_found"):
                            st.info(f"📄 Found {response['documents_found']} relevant documents")
                    else:
                        st.error(f"❌ Redis API Error: {response.get('error', 'Unknown error')}")
                        
                        # Fallback to direct API if Redis fails
                        if use_direct:
                            st.warning("Trying direct API method...")
                            response = submit_query_via_direct_api(query, user_role, user_id)
                
                if use_direct and (not use_redis or not response or not response.get("success")):
                    # Use direct API query method
                    response = submit_query_via_direct_api(query, user_role, user_id)
                    
                    if response.get("success"):
                        st.success("✅ Direct API Answer:")
                        st.write(response["response"])
                        if response.get("documents_found"):
                            st.info(f"📄 Found {response['documents_found']} relevant documents")
                    else:
                        st.error(f"❌ Direct API Error: {response.get('error', 'Unknown error')}")
                        
                        # Final fallback to local query
                        st.warning("Trying local fallback method...")
                        try:
                            fallback_response = ask_llm(query)
                            st.success("✅ Local Fallback Answer:")
                            st.write(fallback_response)
                        except Exception as e:
                            st.error(f"❌ All methods failed: {str(e)}")
                
                if not use_redis and not use_direct:
                    st.warning("Please select at least one query method")
        else:
            st.warning("Please enter a question")

# Example queries section
with st.expander("📋 Example Queries"):
    st.markdown("""
    **Sales & Financial Questions:**
    - What were the total sales for RT2 - South Austin in May 2025?
    - What was the cost variance on 6/15/2025?
    - Show me the scheduled vs attendance costs for June 2025
    
    **Employee & Schedule Questions:**
    - Who worked as a Line Cook on 5/10/2025?
    - What positions did Allison Milam work in May?
    - Show me attendance vs scheduled hours for Brian Villarreal
    
    **Time & Attendance Questions:**
    - What was the total hour difference for all employees on 6/1/2025?
    - Who had the most overtime in May 2025?
    - Which employees frequently came in early or stayed late?
    
    **Department Questions:**
    - How many people worked in BOH vs FOH on 5/20/2025?
    - What's the average scheduled hours for prep positions?
    - Show me all shift leads and their schedules
    """)

# Footer
st.markdown("---")
st.markdown("💡 **Tip:** Use Redis Queue for full processing pipeline or Direct Query for immediate results. Different user roles show different data levels.")
