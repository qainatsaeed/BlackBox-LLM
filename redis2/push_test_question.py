import redis
import json
import uuid
import argparse

# Redis connection
redis_client = redis.Redis(host="localhost", port=6380, decode_responses=True)

# Parse arguments
parser = argparse.ArgumentParser(description="Push a test question to Redis.")
parser.add_argument("--query", required=True, help="The question to push to Redis.")
parser.add_argument("--role", required=True, help="The role of the user (e.g., manager, employee).")
parser.add_argument("--user_id", default="test_user", help="The user ID.")
args = parser.parse_args()

# Generate a unique query ID
query_id = str(uuid.uuid4())

# Create the query payload
query_data = {
    "query_id": query_id,
    "query": args.query,
    "user_role": args.role,
    "user_id": args.user_id,
    "top_k": 5
}

# Push the question to Redis
redis_client.rpush("hrask.ask.queue", json.dumps(query_data))
print(f"Query pushed to hrask.ask.queue")
print(f"Query ID: {query_id}")
print("Use this ID with listen_response.py to get the response")