# Redis-based Multi-Level Caching System
"""
Advanced caching implementation with Redis backend
Provides intelligent cache invalidation, compression, and monitoring
"""

import redis
import json
import pickle
import zlib
import hashlib
import time
from datetime import timedelta, datetime
from typing import Any, Optional, Dict, List, Union
from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
import logging

logger = logging.getLogger('performance')

class AdvancedCacheManager:
    """Advanced Redis cache manager with compression and intelligent invalidation"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=False,  # Handle binary data
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Cache configuration
        self.default_timeout = 300  # 5 minutes
        self.compression_threshold = 1024  # Compress data > 1KB
        self.max_cache_size = 10 * 1024 * 1024  # 10MB per key
        
        # Cache levels configuration
        self.cache_levels = {
            'L1': {'timeout': 60, 'prefix': 'l1'},      # Fast access - 1 minute
            'L2': {'timeout': 300, 'prefix': 'l2'},     # Medium access - 5 minutes  
            'L3': {'timeout': 3600, 'prefix': 'l3'},    # Slow access - 1 hour
            'L4': {'timeout': 86400, 'prefix': 'l4'},   # Very slow - 24 hours
        }
        
        # Performance tracking
        self.performance_stats = {
            'hits': 0,
            'misses': 0,
            'compressions': 0,
            'errors': 0
        }
    
    def _generate_key(self, key: str, level: str = 'L2') -> str:
        """Generate cache key with level prefix"""
        prefix = self.cache_levels[level]['prefix']
        # Hash long keys to avoid Redis key length limits
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            key = f"{key[:100]}_{key_hash}"
        return f"{prefix}:{key}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data with optional compression"""
        try:
            # Use pickle for complex Python objects, JSON for simple ones
            if isinstance(data, (dict, list, str, int, float, bool)):
                serialized = json.dumps(data, cls=DjangoJSONEncoder).encode('utf-8')
            else:
                serialized = pickle.dumps(data)
            
            # Apply compression if data is large enough
            if len(serialized) > self.compression_threshold:
                compressed = zlib.compress(serialized, level=6)
                self.performance_stats['compressions'] += 1
                return b'COMP:' + compressed
            
            return b'RAW:' + serialized
            
        except Exception as e:
            logger.error(f"Cache serialization error: {e}")
            self.performance_stats['errors'] += 1
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data with decompression support"""
        try:
            if data.startswith(b'COMP:'):
                # Decompress data
                compressed_data = data[5:]
                decompressed = zlib.decompress(compressed_data)
                
                # Check if it's JSON or pickle
                try:
                    return json.loads(decompressed.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return pickle.loads(decompressed)
            
            elif data.startswith(b'RAW:'):
                raw_data = data[4:]
                
                # Try JSON first, then pickle
                try:
                    return json.loads(raw_data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return pickle.loads(raw_data)
            
            else:
                # Legacy data without prefix
                try:
                    return json.loads(data.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return pickle.loads(data)
                    
        except Exception as e:
            logger.error(f"Cache deserialization error: {e}")
            self.performance_stats['errors'] += 1
            raise
    
    def get(self, key: str, level: str = 'L2', default: Any = None) -> Any:
        """Get value from cache with fallback levels"""
        start_time = time.time()
        
        try:
            # Try to get from specified level first
            cache_key = self._generate_key(key, level)
            data = self.redis_client.get(cache_key)
            
            if data is not None:
                self.performance_stats['hits'] += 1
                result = self._deserialize_data(data)
                
                # Record hit time
                hit_time = (time.time() - start_time) * 1000
                if hit_time > 10:  # Log slow cache operations
                    logger.warning(f"Slow cache GET: {key} took {hit_time:.2f}ms")
                
                return result
            
            # Try fallback levels (L3, L4) if current level missed
            if level in ['L1', 'L2']:
                for fallback_level in ['L3', 'L4']:
                    fallback_key = self._generate_key(key, fallback_level)
                    data = self.redis_client.get(fallback_key)
                    
                    if data is not None:
                        result = self._deserialize_data(data)
                        # Repopulate higher-level cache
                        self.set(key, result, level=level)
                        self.performance_stats['hits'] += 1
                        return result
            
            self.performance_stats['misses'] += 1
            return default
            
        except Exception as e:
            logger.error(f"Cache GET error for key {key}: {e}")
            self.performance_stats['errors'] += 1
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None, level: str = 'L2') -> bool:
        """Set value in cache with automatic compression"""
        try:
            cache_key = self._generate_key(key, level)
            
            if timeout is None:
                timeout = self.cache_levels[level]['timeout']
            
            # Check data size
            serialized_data = self._serialize_data(value)
            
            if len(serialized_data) > self.max_cache_size:
                logger.warning(f"Cache data too large for key {key}: {len(serialized_data)} bytes")
                return False
            
            # Set with expiration
            result = self.redis_client.setex(cache_key, timeout, serialized_data)
            
            # Set metadata for monitoring
            metadata_key = f"{cache_key}:meta"
            metadata = {
                'created_at': timezone.now().isoformat(),
                'size': len(serialized_data),
                'compressed': serialized_data.startswith(b'COMP:'),
                'level': level
            }
            self.redis_client.setex(metadata_key, timeout, json.dumps(metadata))
            
            return result
            
        except Exception as e:
            logger.error(f"Cache SET error for key {key}: {e}")
            self.performance_stats['errors'] += 1
            return False
    
    def delete(self, key: str, all_levels: bool = True) -> bool:
        """Delete key from cache, optionally from all levels"""
        try:
            deleted_count = 0
            
            if all_levels:
                # Delete from all cache levels
                for level in self.cache_levels.keys():
                    cache_key = self._generate_key(key, level)
                    metadata_key = f"{cache_key}:meta"
                    
                    deleted_count += self.redis_client.delete(cache_key)
                    self.redis_client.delete(metadata_key)
            else:
                # Delete from L2 (default level) only
                cache_key = self._generate_key(key, 'L2')
                metadata_key = f"{cache_key}:meta"
                
                deleted_count = self.redis_client.delete(cache_key)
                self.redis_client.delete(metadata_key)
            
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Cache DELETE error for key {key}: {e}")
            self.performance_stats['errors'] += 1
            return False
    
    def invalidate_pattern(self, pattern: str, level: Optional[str] = None) -> int:
        """Invalidate all keys matching pattern"""
        try:
            deleted_count = 0
            
            if level:
                # Invalidate specific level
                prefix = self.cache_levels[level]['prefix']
                search_pattern = f"{prefix}:*{pattern}*"
                keys = self.redis_client.keys(search_pattern)
                
                if keys:
                    deleted_count = self.redis_client.delete(*keys)
                    # Also delete metadata
                    meta_keys = [k + b':meta' for k in keys]
                    self.redis_client.delete(*meta_keys)
            else:
                # Invalidate all levels
                for level_name in self.cache_levels.keys():
                    prefix = self.cache_levels[level_name]['prefix']
                    search_pattern = f"{prefix}:*{pattern}*"
                    keys = self.redis_client.keys(search_pattern)
                    
                    if keys:
                        deleted_count += self.redis_client.delete(*keys)
                        meta_keys = [k + b':meta' for k in keys]
                        self.redis_client.delete(*meta_keys)
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache pattern invalidation error for {pattern}: {e}")
            self.performance_stats['errors'] += 1
            return 0
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache statistics and health information"""
        try:
            redis_info = self.redis_client.info()
            
            # Get cache size by level
            level_stats = {}
            for level, config in self.cache_levels.items():
                prefix = config['prefix']
                keys = self.redis_client.keys(f"{prefix}:*")
                level_stats[level] = {
                    'key_count': len([k for k in keys if not k.endswith(b':meta')]),
                    'prefix': prefix,
                    'timeout': config['timeout']
                }
            
            return {
                'redis_info': {
                    'used_memory': redis_info.get('used_memory_human'),
                    'connected_clients': redis_info.get('connected_clients'),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                    'uptime_in_seconds': redis_info.get('uptime_in_seconds')
                },
                'level_stats': level_stats,
                'performance_stats': self.performance_stats.copy(),
                'health_status': 'healthy' if self.redis_client.ping() else 'unhealthy'
            }
            
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            return {'error': str(e), 'health_status': 'unhealthy'}

# Smart caching decorators
def smart_cache(timeout=300, level='L2', key_prefix='', vary_on=None, invalidate_on=None):
    """Smart caching decorator with automatic invalidation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__module__, func.__name__]
            
            # Add variation parameters
            if vary_on:
                for param in vary_on:
                    if param in kwargs:
                        key_parts.append(f"{param}:{kwargs[param]}")
                    elif args and len(args) > vary_on.index(param):
                        key_parts.append(f"arg{vary_on.index(param)}:{args[vary_on.index(param)]}")
            
            cache_key = ':'.join(str(part) for part in key_parts if part)
            
            # Try to get from cache
            cache_manager = AdvancedCacheManager()
            cached_result = cache_manager.get(cache_key, level=level)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Adjust timeout based on execution time (longer execution = longer cache)
            dynamic_timeout = min(timeout * (1 + execution_time), timeout * 3)
            cache_manager.set(cache_key, result, int(dynamic_timeout), level=level)
            
            # Set up invalidation triggers
            if invalidate_on:
                for trigger in invalidate_on:
                    invalidation_key = f"invalidate:{trigger}:{cache_key}"
                    cache_manager.set(invalidation_key, cache_key, dynamic_timeout, level='L1')
            
            return result
        
        wrapper.cache_key_func = lambda *args, **kwargs: ':'.join([
            key_prefix, func.__module__, func.__name__,
            *[f"{param}:{kwargs.get(param, 'None')}" for param in (vary_on or [])]
        ])
        
        return wrapper
    return decorator

def cache_user_data(timeout=900):  # 15 minutes
    """Cache decorator specifically for user data"""
    return smart_cache(timeout=timeout, level='L2', key_prefix='user_data', vary_on=['user_id'])

def cache_course_data(timeout=1800):  # 30 minutes
    """Cache decorator for course-related data"""
    return smart_cache(timeout=timeout, level='L3', key_prefix='course_data', vary_on=['course_id'])

def cache_analytics(timeout=600):  # 10 minutes
    """Cache decorator for analytics data"""
    return smart_cache(timeout=timeout, level='L2', key_prefix='analytics', vary_on=['user_id', 'date_range'])

# Cache warming utility
class CacheWarmer:
    """Utility to pre-warm cache with frequently accessed data"""
    
    def __init__(self):
        self.cache_manager = AdvancedCacheManager()
    
    def warm_user_data(self, user_ids: List[int]):
        """Pre-warm cache with user data"""
        from apps.learning_plans.models import StudySession
        from apps.courses.models import CourseProgress
        
        for user_id in user_ids:
            try:
                # Warm session analytics
                session_analytics = StudySession.objects.filter(user_id=user_id).aggregate(
                    total_sessions=models.Count('id'),
                    avg_duration=models.Avg('duration_minutes'),
                    total_duration=models.Sum('duration_minutes')
                )
                self.cache_manager.set(f"session_analytics_{user_id}", session_analytics, level='L2')
                
                # Warm course progress
                progress_data = CourseProgress.objects.filter(user_uuid_id=user_id).values(
                    'subject_name', 'proficiency_level', 'learning_hour_total'
                )
                self.cache_manager.set(f"course_progress_{user_id}", list(progress_data), level='L2')
                
            except Exception as e:
                logger.error(f"Cache warming error for user {user_id}: {e}")
    
    def warm_popular_content(self):
        """Pre-warm cache with popular content"""
        try:
            from apps.courses.models import CourseProgress
            
            # Get most popular subjects
            popular_subjects = CourseProgress.objects.values('subject_name').annotate(
                student_count=models.Count('user_uuid_id', distinct=True)
            ).order_by('-student_count')[:20]
            
            self.cache_manager.set('popular_subjects', list(popular_subjects), level='L3')
            
        except Exception as e:
            logger.error(f"Popular content cache warming error: {e}")

# Initialize global cache manager
cache_manager = AdvancedCacheManager()

# Export main components
__all__ = [
    'AdvancedCacheManager',
    'cache_manager',
    'smart_cache',
    'cache_user_data',
    'cache_course_data',
    'cache_analytics',
    'CacheWarmer'
]