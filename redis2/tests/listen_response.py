"""
Test script to listen for responses from Redis queue
"""
import os
import sys
import json
import time
import redis
import argparse
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Listen for responses from Redis queue')
    parser.add_argument('--query-id', '-q', type=str, default=None,
                       help='Query ID to filter (if omitted, listen for all responses)')
    parser.add_argument('--timeout', '-t', type=int, default=60,
                       help='Timeout in seconds (0 for indefinite)')
    parser.add_argument('--host', type=str, default='localhost',
                       help='Redis host')
    parser.add_argument('--port', type=int, default=6379,
                       help='Redis port')
    
    return parser.parse_args()

def main():
    """Listen for responses from Redis queue"""
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
    
    # Listen for responses
    queue_name = "hrask.response.queue"
    print(f"Listening for responses on {queue_name}...")
    if args.query_id:
        print(f"Filtering for query ID: {args.query_id}")
    
    start_time = time.time()
    while args.timeout == 0 or time.time() - start_time < args.timeout:
        try:
            # Check for messages with timeout
            message = r.blpop(queue_name, timeout=1)
            
            if message:
                queue_name, message_data = message
                response = json.loads(message_data)
                
                # Filter by query ID if specified
                if args.query_id and response.get('query_id') != args.query_id:
                    # Put the message back in the queue
                    r.rpush(queue_name, message_data)
                    continue
                
                # Print the response
                print("\n" + "="*50)
                print(f"Received response for query ID: {response.get('query_id')}")
                print(f"Success: {response.get('success', False)}")
                print(f"Documents found: {response.get('documents_found', 0)}")
                print("-"*50)
                print("Response:")
                print(response.get('response', 'No response'))
                
                # Print debug info if available
                if 'debug' in response:
                    print("-"*50)
                    print("Debug info:")
                    for key, value in response['debug'].items():
                        print(f"  {key}: {value}")
                
                print("="*50 + "\n")
                
                # If we found the specific query ID, we're done
                if args.query_id:
                    return 0
                    
        except KeyboardInterrupt:
            print("\nListening stopped by user")
            return 0
        except Exception as e:
            print(f"Error: {str(e)}")
            continue
    
    if args.timeout > 0:
        print(f"\nTimeout reached after {args.timeout} seconds")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())