"""
Redis client module for HRAsk system - async pub/sub
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
import redis.asyncio as redis_async

logger = logging.getLogger(__name__)

class RedisAsyncClient:
    def __init__(self):
        """Initialize Redis async client with connection from env vars"""
        self.host = os.getenv('REDIS_HOST', 'redis')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self._redis_client = None
        self.ask_queue = "hrask.ask.queue"
        self.response_queue = "hrask.response.queue"
    
    async def connect(self) -> None:
        """Connect to Redis server"""
        self._redis_client = await redis_async.Redis(
            host=self.host,
            port=self.port,
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {self.host}:{self.port}")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis server"""
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def publish_response(self, response_data: Dict[str, Any]) -> None:
        """Publish structured response to the response queue"""
        if not self._redis_client:
            await self.connect()
        
        try:
            response_json = json.dumps(response_data)
            await self._redis_client.rpush(self.response_queue, response_json)
            logger.info(f"Published response for query ID: {response_data.get('query_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Error publishing response: {str(e)}")
    
    async def subscribe_to_questions(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Subscribe to incoming questions and process with callback
        
        Args:
            callback: Async function that processes the question
        """
        if not self._redis_client:
            await self.connect()
        
        logger.info(f"Subscribing to queue: {self.ask_queue}")
        
        try:
            while True:
                # Use blocking list pop with timeout
                message = await self._redis_client.blpop(self.ask_queue, timeout=1)
                
                if message:
                    _, message_data = message
                    try:
                        query_data = json.loads(message_data)
                        logger.info(f"Received question: {query_data.get('query', '')[:50]}...")
                        await callback(query_data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON message: {message_data}")
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
        except Exception as e:
            logger.error(f"Subscription error: {str(e)}")
            raise
    
    async def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        if not self._redis_client:
            try:
                await self.connect()
            except Exception:
                return False
        
        try:
            return await self._redis_client.ping()
        except Exception:
            return False