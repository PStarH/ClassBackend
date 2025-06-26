"""
缓存工具类
提供各种缓存操作的便捷方法
"""
import json
import logging
from functools import wraps
from typing import Any, Optional, Union, Dict
from django.core.cache import cache, caches
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    缓存服务类
    """
    
    def __init__(self, cache_alias: str = 'default'):
        self.cache = caches[cache_alias]
        self.cache_alias = cache_alias
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        try:
            return self.cache.get(key, default)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            return self.cache.set(key, value, timeout)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return self.cache.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False
    
    def get_or_set(self, key: str, default_func, timeout: Optional[int] = None) -> Any:
        """获取缓存，如果不存在则设置默认值"""
        try:
            value = self.cache.get(key)
            if value is None:
                value = default_func() if callable(default_func) else default_func
                self.cache.set(key, value, timeout)
            return value
        except Exception as e:
            logger.error(f"Cache get_or_set error for key {key}: {str(e)}")
            return default_func() if callable(default_func) else default_func
    
    def increment(self, key: str, delta: int = 1) -> int:
        """增加计数器"""
        try:
            return self.cache.incr(key, delta)
        except ValueError:
            # 键不存在，先设置为0
            self.cache.set(key, 0, timeout=86400)  # 24小时
            return self.cache.incr(key, delta)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {str(e)}")
            return 0
    
    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有键"""
        try:
            if hasattr(self.cache, 'delete_pattern'):
                return self.cache.delete_pattern(pattern)
            else:
                # 如果不支持模式删除，记录警告
                logger.warning(f"Cache backend doesn't support pattern deletion: {pattern}")
                return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {str(e)}")
            return 0


# 全局缓存服务实例 - 延迟初始化
def get_default_cache():
    """获取默认缓存服务"""
    return CacheService('default')

def get_api_cache():
    """获取 API 缓存服务"""
    try:
        return CacheService('api_cache')
    except Exception:
        # 如果 api_cache 不存在，使用默认缓存
        return CacheService('default')

def get_session_cache():
    """获取会话缓存服务"""
    try:
        return CacheService('sessions')
    except Exception:
        # 如果 sessions 缓存不存在，使用默认缓存
        return CacheService('default')

# 为了向后兼容，提供属性访问
class CacheProxy:
    @property
    def default_cache(self):
        return get_default_cache()
    
    @property
    def api_cache(self):
        return get_api_cache()
    
    @property
    def session_cache(self):
        return get_session_cache()

_cache_proxy = CacheProxy()
default_cache = _cache_proxy.default_cache
api_cache = _cache_proxy.api_cache
session_cache = _cache_proxy.session_cache


def cache_result(timeout: int = 300, cache_alias: str = 'default', key_prefix: str = ''):
    """
    缓存装饰器
    用于缓存函数或方法的返回值
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试获取缓存
            cache_service = CacheService(cache_alias)
            cached_result = cache_service.get(cache_key)
            
            if cached_result is not None:
                logger.debug(f"Cache hit for function {func.__name__}")
                return cached_result
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache_service.set(cache_key, result, timeout)
            logger.debug(f"Cached result for function {func.__name__}")
            
            return result
        return wrapper
    return decorator


def cache_user_data(user_id: int, key: str, timeout: int = 1800):
    """
    用户数据缓存装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"user:{user_id}:{key}"
            cached_data = default_cache.get(cache_key)
            
            if cached_data is not None:
                return cached_data
            
            result = func(*args, **kwargs)
            default_cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


class UserCacheManager:
    """
    用户相关缓存管理器
    """
    
    @staticmethod
    def get_user_cache_key(user_id: int, key: str) -> str:
        """生成用户缓存键"""
        return f"user:{user_id}:{key}"
    
    @staticmethod
    def set_user_cache(user_id: int, key: str, data: Any, timeout: int = 1800) -> bool:
        """设置用户缓存"""
        cache_key = UserCacheManager.get_user_cache_key(user_id, key)
        return get_default_cache().set(cache_key, data, timeout)
    
    @staticmethod
    def get_user_cache(user_id: int, key: str, default: Any = None) -> Any:
        """获取用户缓存"""
        cache_key = UserCacheManager.get_user_cache_key(user_id, key)
        return get_default_cache().get(cache_key, default)
    
    @staticmethod
    def delete_user_cache(user_id: int, key: str = None) -> bool:
        """删除用户缓存"""
        if key:
            cache_key = UserCacheManager.get_user_cache_key(user_id, key)
            return get_default_cache().delete(cache_key)
        else:
            # 删除用户所有缓存
            pattern = f"user:{user_id}:*"
            return get_default_cache().clear_pattern(pattern)
    
    @staticmethod
    def refresh_user_cache(user_id: int, key: str, data_func, timeout: int = 1800) -> Any:
        """刷新用户缓存"""
        data = data_func() if callable(data_func) else data_func
        UserCacheManager.set_user_cache(user_id, key, data, timeout)
        return data


class APICacheManager:
    """
    API 缓存管理器
    """
    
    @staticmethod
    def get_api_cache_key(endpoint: str, params: Dict = None, user_id: int = None) -> str:
        """生成 API 缓存键"""
        key_parts = ['api', endpoint]
        
        if user_id:
            key_parts.append(f'user:{user_id}')
        
        if params:
            # 对参数排序确保缓存键一致性
            sorted_params = sorted(params.items())
            params_str = ':'.join([f"{k}={v}" for k, v in sorted_params])
            key_parts.append(params_str)
        
        return ':'.join(key_parts)
    
    @staticmethod
    def cache_api_response(endpoint: str, data: Any, timeout: int = 600, 
                          params: Dict = None, user_id: int = None) -> bool:
        """缓存 API 响应"""
        cache_key = APICacheManager.get_api_cache_key(endpoint, params, user_id)
        return get_api_cache().set(cache_key, data, timeout)
    
    @staticmethod
    def get_cached_api_response(endpoint: str, params: Dict = None, 
                               user_id: int = None, default: Any = None) -> Any:
        """获取缓存的 API 响应"""
        cache_key = APICacheManager.get_api_cache_key(endpoint, params, user_id)
        return get_api_cache().get(cache_key, default)
    
    @staticmethod
    def invalidate_api_cache(endpoint: str, params: Dict = None, user_id: int = None) -> bool:
        """使 API 缓存失效"""
        if params is None and user_id is None:
            # 清除整个端点的所有缓存
            pattern = f"api:{endpoint}:*"
            return get_api_cache().clear_pattern(pattern)
        else:
            cache_key = APICacheManager.get_api_cache_key(endpoint, params, user_id)
            return get_api_cache().delete(cache_key)


# 便捷函数
def get_cache(key: str, default: Any = None, cache_alias: str = 'default') -> Any:
    """获取缓存的便捷函数"""
    return CacheService(cache_alias).get(key, default)


def set_cache(key: str, value: Any, timeout: Optional[int] = None, 
              cache_alias: str = 'default') -> bool:
    """设置缓存的便捷函数"""
    return CacheService(cache_alias).set(key, value, timeout)


def delete_cache(key: str, cache_alias: str = 'default') -> bool:
    """删除缓存的便捷函数"""
    return CacheService(cache_alias).delete(key)
