import redis
import psycopg2
import json
from haystack.document_stores import ElasticsearchDocumentStore
from haystack.pipelines import Pipeline

# Redis connection
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

# PostgreSQL connection
pg_conn = psycopg2.connect(
    host="postgres",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="hrask"
)

# Elasticsearch connection
document_store = ElasticsearchDocumentStore(host="elasticsearch", port=9200)

# Load Haystack pipeline
pipeline = Pipeline.load_from_yaml("pipeline.yml")

# Redis queues
ASK_QUEUE = "hrask.ask.queue"
RESPONSE_QUEUE = "hrask.response.queue"

# Role-based filters
def apply_filters(user_context, documents):
    filters = {
        "account_id": user_context.get("account_id"),
        "location_id": {"$in": user_context.get("accessible_locations", [])},
        "employee_id": {"$in": user_context.get("team_employees", [])},
    }
    return [doc for doc in documents if all(doc.meta.get(k) in v for k, v in filters.items() if v)]

# Middleware loop
def middleware_loop():
    while True:
        _, message = redis_client.blpop(ASK_QUEUE)
        query_data = json.loads(message)

        user_context = {
            "user_id": query_data.get("user_id"),
            "account_id": query_data.get("account_id"),
            "role": query_data.get("role"),
            "accessible_locations": query_data.get("accessible_locations", []),
            "team_employees": query_data.get("team_employees", []),
        }

        query = query_data.get("query")
        top_k = query_data.get("top_k", 5)

        # Query Haystack pipeline
        results = pipeline.run(query=query, params={"Retriever": {"top_k": top_k}})
        documents = results.get("documents", [])

        # Apply role-based filters
        filtered_docs = apply_filters(user_context, documents)

        # Publish response
        response = {
            "query_id": query_data.get("query_id"),
            "success": True,
            "response": "\n\n".join([doc.content for doc in filtered_docs[:top_k]]),
            "documents_found": len(filtered_docs),
        }
        redis_client.rpush(RESPONSE_QUEUE, json.dumps(response))

if __name__ == "__main__":
    middleware_loop()