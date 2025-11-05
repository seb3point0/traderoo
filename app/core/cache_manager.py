"""
Cache manager for AI analysis using Redis
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class CacheManager:
    """
    Redis-based cache manager for AI analysis
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or getattr(settings, 'redis_url', 'redis://redis:6379')
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 14400  # 4 hours in seconds
        self.connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            log.warning("Redis library not available, caching disabled")
            return
        
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.connected = True
            log.info("Connected to Redis cache")
            
        except Exception as e:
            log.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.connected = False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            log.info("Redis connection closed")
    
    async def get_cached_analysis(self, key: str) -> Optional[Dict]:
        """
        Get cached AI analysis
        
        Args:
            key: Cache key (e.g., 'ai_analysis:BTC/USDT:1h')
        
        Returns:
            Cached data or None if not found/expired
        """
        if not self.connected or not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(key)
            
            if cached:
                data = json.loads(cached)
                
                # Check if stale (additional validation)
                if self._is_stale(data):
                    await self.redis_client.delete(key)
                    return None
                
                log.info(f"Cache HIT: {key}")
                return data
            
            log.info(f"Cache MISS: {key}")
            return None
            
        except Exception as e:
            log.error(f"Error getting cached analysis: {e}")
            return None
    
    async def set_cached_analysis(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache AI analysis
        
        Args:
            key: Cache key
            data: Analysis data to cache
            ttl: Time to live in seconds (default: 4 hours)
        
        Returns:
            True if successful
        """
        if not self.connected or not self.redis_client:
            return False
        
        try:
            # Add timestamp to cached data
            data['cached_at'] = datetime.utcnow().isoformat()
            
            ttl = ttl or self.default_ttl
            
            await self.redis_client.setex(
                key,
                ttl,
                json.dumps(data)
            )
            
            log.info(f"Cached analysis: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            log.error(f"Error caching analysis: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str):
        """
        Invalidate cache by pattern
        
        Args:
            pattern: Key pattern (e.g., 'ai_analysis:BTC/*')
        """
        if not self.connected or not self.redis_client:
            return
        
        try:
            # Scan and delete matching keys
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    await self.redis_client.delete(*keys)
                    deleted_count += len(keys)
                
                if cursor == 0:
                    break
            
            log.info(f"Invalidated {deleted_count} cache entries matching: {pattern}")
            
        except Exception as e:
            log.error(f"Error invalidating cache: {e}")
    
    async def invalidate_symbol(self, symbol: str):
        """Invalidate all cache entries for a symbol"""
        await self.invalidate_cache(f"ai_analysis:{symbol}:*")
    
    def _is_stale(self, data: Dict, max_age_seconds: int = 14400) -> bool:
        """
        Check if cached data is stale
        
        Args:
            data: Cached data with 'cached_at' timestamp
            max_age_seconds: Maximum age in seconds
        
        Returns:
            True if data is stale
        """
        if 'cached_at' not in data:
            return True
        
        try:
            cached_at = datetime.fromisoformat(data['cached_at'])
            age_seconds = (datetime.utcnow() - cached_at).total_seconds()
            return age_seconds > max_age_seconds
            
        except Exception:
            return True
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.connected or not self.redis_client:
            return {
                'connected': False,
                'total_keys': 0
            }
        
        try:
            info = await self.redis_client.info('stats')
            
            # Count ai_analysis keys
            cursor = 0
            ai_keys_count = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match="ai_analysis:*",
                    count=100
                )
                ai_keys_count += len(keys)
                
                if cursor == 0:
                    break
            
            return {
                'connected': True,
                'total_keys': ai_keys_count,
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
            
        except Exception as e:
            log.error(f"Error getting cache stats: {e}")
            return {
                'connected': True,
                'error': str(e)
            }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        if total == 0:
            return 0.0
        return (hits / total) * 100
    
    def get_cache_key(
        self,
        prefix: str,
        symbol: str,
        timeframe: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> str:
        """
        Generate standardized cache key
        
        Args:
            prefix: Key prefix (e.g., 'ai_analysis')
            symbol: Trading symbol
            timeframe: Optional timeframe
            strategy: Optional strategy name
        
        Returns:
            Formatted cache key
        """
        parts = [prefix, symbol]
        
        if timeframe:
            parts.append(timeframe)
        
        if strategy:
            parts.append(strategy)
        
        return ":".join(parts)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.connect()
    
    return _cache_manager

