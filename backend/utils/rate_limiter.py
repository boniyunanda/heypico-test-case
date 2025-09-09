"""
Rate limiting utilities
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter with sliding window"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.limits = {
            "default": {"requests": 60, "window": 60},  # 60 requests per minute
            "maps": {"requests": 30, "window": 60},     # 30 maps requests per minute
            "directions": {"requests": 20, "window": 60}, # 20 directions per minute
            "websocket": {"requests": 100, "window": 60}  # 100 websocket messages per minute
        }
    
    async def check_limit(
        self, 
        user_id: str, 
        endpoint: str = "default"
    ) -> bool:
        """
        Check if user is within rate limits
        """
        try:
            limit_config = self.limits.get(endpoint, self.limits["default"])
            max_requests = limit_config["requests"]
            window_seconds = limit_config["window"]
            
            # Redis key for this user and endpoint
            key = f"rate_limit:{endpoint}:{user_id}"
            
            # Current timestamp
            now = datetime.now().timestamp()
            window_start = now - window_seconds
            
            # Remove old entries and count current requests
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, window_seconds + 1)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            # Check if under limit
            if current_requests >= max_requests:
                logger.warning(f"Rate limit exceeded for user {user_id} on endpoint {endpoint}")
                return False
            
            # Add current request
            await self.redis.zadd(key, {str(now): now})
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Allow request if rate limiting fails
    
    async def get_remaining_requests(
        self, 
        user_id: str, 
        endpoint: str = "default"
    ) -> int:
        """Get remaining requests for user"""
        try:
            limit_config = self.limits.get(endpoint, self.limits["default"])
            max_requests = limit_config["requests"]
            window_seconds = limit_config["window"]
            
            key = f"rate_limit:{endpoint}:{user_id}"
            
            # Count current requests in window
            now = datetime.now().timestamp()
            window_start = now - window_seconds
            
            current_requests = await self.redis.zcount(key, window_start, now)
            
            return max(0, max_requests - current_requests)
            
        except Exception as e:
            logger.error(f"Get remaining requests error: {e}")
            return 0
    
    async def reset_user_limits(self, user_id: str) -> bool:
        """Reset all rate limits for a user"""
        try:
            pattern = f"rate_limit:*:{user_id}"
            keys = await self.redis.keys(pattern)
            
            if keys:
                await self.redis.delete(*keys)
            
            return True
            
        except Exception as e:
            logger.error(f"Reset user limits error: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, int]:
        """Get rate limiting statistics"""
        try:
            stats = {}
            
            for endpoint in self.limits.keys():
                pattern = f"rate_limit:{endpoint}:*"
                keys = await self.redis.keys(pattern)
                stats[f"{endpoint}_active_users"] = len(keys)
                
                # Count total requests in current window
                total_requests = 0
                for key in keys:
                    count = await self.redis.zcard(key)
                    total_requests += count
                
                stats[f"{endpoint}_total_requests"] = total_requests
            
            return stats
            
        except Exception as e:
            logger.error(f"Rate limit stats error: {e}")
            return {}

