import redis
import json
import logging
import hashlib
from typing import Any, Dict, Optional, Union, List
from datetime import datetime, timedelta
from functools import wraps

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """
    Redis cache manager for analytics data
    """
    
    def __init__(self, host="localhost", port=6379, db=0, password=None):
        """
        Initialize Redis connection
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database
            password: Redis password
        """
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False
            )
            self.connected = True
            logger.info(f"Connected to Redis at {host}:{port}")
        except Exception as e:
            self.connected = False
            logger.warning(f"Failed to connect to Redis: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.connected:
            return None
        
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 900) -> bool:
        """
        Set a value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 15 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            serialized = json.dumps(value, default=self._json_serial)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    def clear_pattern(self, pattern: str) -> bool:
        """
        Delete all keys matching a pattern
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            cursor = 0
            while True:
                cursor, keys = self.redis.scan(cursor, pattern, 100)
                if keys:
                    self.redis.delete(*keys)
                if cursor == 0:
                    break
            return True
        except Exception as e:
            logger.error(f"Error clearing cache pattern: {str(e)}")
            return False
    
    def hash_key(self, prefix: str, obj: Any) -> str:
        """
        Create a hash key from an object
        
        Args:
            prefix: Key prefix
            obj: Object to hash
            
        Returns:
            Hashed key string
        """
        if isinstance(obj, dict):
            serialized = json.dumps(obj, sort_keys=True, default=self._json_serial)
        else:
            serialized = str(obj)
        
        hash_value = hashlib.md5(serialized.encode()).hexdigest()
        return f"{prefix}:{hash_value}"
    
    def _json_serial(self, obj: Any) -> Any:
        """
        JSON serializer for objects not serializable by default json code
        
        Args:
            obj: Object to serialize
            
        Returns:
            Serialized object
        """
        if isinstance(obj, (datetime, datetime.date)):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

# Create a singleton instance
cache_manager = CacheManager()

def cached(prefix: str, ttl: int = 900):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (default: 15 minutes)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique key based on function arguments
            key_parts = {
                'func': func.__name__,
                'args': args,
                'kwargs': kwargs
            }
            
            cache_key = cache_manager.hash_key(prefix, key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix: str):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        prefix: Cache key prefix to invalidate
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Clear all cache with the given prefix
            cache_manager.clear_pattern(f"{prefix}:*")
            
            return result
        return wrapper
    return decorator