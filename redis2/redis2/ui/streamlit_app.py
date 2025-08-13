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
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )

def submit_query_via_redis(query: str, user_role: str = "employee", user_id: str = ""):
    """Submit query via Redis queue and wait for response"""
    redis_client = get_redis_client()
    query_id = str(uuid.uuid4())
    
    query_data = {
        "query_id": query_id,
        "query": query,
        "user_role": user_role,
        "user_id": user_id,
        "top_k": 5
    }
    
    try:
        # Send to Redis queue
        redis_client.rpush("hrask.ask.queue", json.dumps(query_data))
        
        # Wait for response
        for _ in range(30):  # 30 second timeout
            response_data = redis_client.blpop("hrask.response.queue", timeout=1)
            if response_data:
                _, response_json = response_data
                response = json.loads(response_json)
                if response.get("query_id") == query_id:
                    return response
        
        return {"success": False, "error": "Query timeout"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

st.set_page_config(page_title="HR Assistant with Redis", layout="wide")

st.title("🏢 HR Assistant - Redis Queue System")
st.markdown("Upload CSV files and ask questions about employee data via Redis messaging.")

# Sidebar for system status
with st.sidebar:
    st.header("System Status")
    
    # Check API health
    try:
        api_response = requests.get("http://ingestion_api:8080/health", timeout=5)
        if api_response.status_code == 200:
            health_data = api_response.json()
            st.success(f"✅ API: {health_data['status']}")
            st.info(f"Redis: {health_data.get('redis', 'unknown')}")
            st.info(f"Elasticsearch: {health_data.get('elasticsearch', 'unknown')}")
        else:
            st.error("❌ API not responding")
    except:
        st.warning("⚠️ Cannot reach API")
    
    # Get stats
    try:
        stats_response = requests.get("http://ingestion_api:8080/stats", timeout=5)
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
                api_response = requests.post("http://ingestion_api:8080/ingest/existing", timeout=30)
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
                files_data = []
                for uploaded_file in uploaded_files:
                    files_data.append(("files", (uploaded_file.name, uploaded_file.getvalue(), "text/csv")))
                
                api_response = requests.post("http://ingestion_api:8080/upload/csv", files=files_data, timeout=60)
                
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
        use_redis = st.checkbox("Use Redis Queue", value=True, help="Use Redis messaging system")
    
    with col2b:
        use_fallback = st.checkbox("Use Fallback (Direct)", value=False, help="Use direct query if Redis fails")
    
    if st.button("🔍 Ask Question"):
        if query.strip():
            with st.spinner("Processing your question..."):
                if use_redis:
                    # Use Redis queue system
                    response = submit_query_via_redis(query, user_role, user_id)
                    
                    if response.get("success"):
                        st.success("✅ Answer from Redis Queue:")
                        st.write(response["response"])
                        if response.get("documents_found"):
                            st.info(f"📄 Found {response['documents_found']} relevant documents")
                    else:
                        st.error(f"❌ Error: {response.get('error', 'Unknown error')}")
                        
                        # Fallback to direct query if enabled
                        if use_fallback:
                            st.warning("Trying fallback method...")
                            try:
                                fallback_response = ask_llm(query)
                                st.success("✅ Fallback Answer:")
                                st.write(fallback_response)
                            except Exception as e:
                                st.error(f"❌ Fallback also failed: {str(e)}")
                
                elif use_fallback:
                    # Use direct query method
                    try:
                        response = ask_llm(query)
                        st.success("✅ Direct Answer:")
                        st.write(response)
                    except Exception as e:
                        st.error(f"❌ Direct query failed: {str(e)}")
                
                else:
                    st.warning("Please select either Redis Queue or Fallback method")
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
st.markdown("💡 **Tip:** Different user roles (employee, supervisor, manager, admin) will see different levels of data based on access permissions.")
