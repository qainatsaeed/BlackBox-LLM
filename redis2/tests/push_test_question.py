"""
Test script to push a sample question to Redis queue
"""
import os
import sys
import json
import uuid
import redis
import argparse
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Push a test question to Redis queue')
    parser.add_argument('--query', '-q', type=str, required=True, 
                       help='Question to ask')
    parser.add_argument('--role', '-r', type=str, default='employee',
                       choices=['employee', 'supervisor', 'manager', 'admin'],
                       help='User role')
    parser.add_argument('--user-id', '-u', type=str, default='test_user',
                       help='User ID')
    parser.add_argument('--account-id', '-a', type=str, default='acct001',
                       help='Account ID')
    parser.add_argument('--location-ids', '-l', type=str, default='loc001',
                       help='Location IDs (comma-separated)')
    parser.add_argument('--model', '-m', type=str, default=None,
                       help='Model name (default: use system default)')
    parser.add_argument('--top-k', '-k', type=int, default=5,
                       help='Number of documents to retrieve')
    parser.add_argument('--host', type=str, default='localhost',
                       help='Redis host')
    parser.add_argument('--port', type=int, default=6379,
                       help='Redis port')
    
    return parser.parse_args()

def main():
    """Push a test question to Redis queue"""
    args = parse_args()
    
    # Connect to Redis
    r = redis.Redis(
        host=args.host,
        port=args.port,
        decode_responses=True
    )
    
    # Check Redis connection
    try:
        r.ping()
        print(f"Connected to Redis at {args.host}:{args.port}")
    except redis.ConnectionError:
        print(f"Failed to connect to Redis at {args.host}:{args.port}")
        return 1
    
    # Split location IDs
    location_ids = [loc.strip() for loc in args.location_ids.split(',') if loc.strip()]
    
    # Create query data
    query_data = {
        "query_id": str(uuid.uuid4()),
        "query": args.query,
        "user_role": args.role,
        "user_id": args.user_id,
        "account_id": args.account_id,
        "location_ids": location_ids,
        "model": args.model,
        "top_k": args.top_k,
        "timestamp": datetime.now().isoformat()
    }
    
    # Push to Redis queue
    queue_name = "hrask.ask.queue"
    try:
        r.rpush(queue_name, json.dumps(query_data))
        print(f"Query pushed to {queue_name}")
        print(f"Query ID: {query_data['query_id']}")
        print(f"Use this ID with listen_response.py to get the response")
    except Exception as e:
        print(f"Error pushing query to Redis: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())