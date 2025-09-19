import redis
import json

# Redis connection
redis_client = redis.Redis(host="localhost", port=6380, decode_responses=True)

print("Connected to Redis at localhost:6380")
print("Listening for responses on hrask.response.queue...")

while True:
    _, message = redis_client.blpop("hrask.response.queue")
    response = json.loads(message)

    print("\nResponse received:")
    print(json.dumps(response, indent=4))

    if response.get("success"):
        print("\nQuery processed successfully!")
        print(f"Response: {response['response']}")
    else:
        print("\nQuery failed!")
        print(f"Error: {response['error']}")