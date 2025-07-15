"""
性能监控中间件
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.core.cache import cache
from .performance import performance_monitor, PerformanceMetric

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """性能监控中间件"""
    
    def process_request(self, request):
        """处理请求开始"""
        request._performance_start_time = time.time()
        request._performance_initial_queries = len(connection.queries)
        
    def process_response(self, request, response):
        """处理响应结束"""
        if not hasattr(request, '_performance_start_time'):
            return response
        
        # 计算总时间
        total_time = time.time() - request._performance_start_time
        duration_ms = total_time * 1000
        
        # 计算数据库查询数
        db_queries = len(connection.queries) - request._performance_initial_queries
        
        # 记录API性能指标
        metric = PerformanceMetric(
            timestamp=time.time(),
            metric_type='api',
            operation=f"{request.method} {request.path}",
            duration_ms=duration_ms,
            success=200 <= response.status_code < 400,
            metadata={
                'status_code': response.status_code,
                'method': request.method,
                'path': request.path,
                'db_queries': db_queries,
                'user_id': str(request.user.uuid) if hasattr(request, 'user') and request.user.is_authenticated else None,
                'content_length': len(response.content) if hasattr(response, 'content') else 0
            }
        )
        
        performance_monitor.collector.record_metric(metric)
        
        # 如果请求太慢，记录警告
        if duration_ms > 2000:  # 超过2秒
            logger.warning(
                f"Slow API request: {request.method} {request.path} "
                f"took {duration_ms:.2f}ms with {db_queries} DB queries"
            )
        
        # 添加性能头部
        response['X-Response-Time'] = f"{duration_ms:.2f}ms"
        response['X-DB-Queries'] = str(db_queries)
        
        return response


class DatabaseQueryMonitoringMiddleware(MiddlewareMixin):
    """数据库查询监控中间件"""
    
    def process_request(self, request):
        """监控数据库查询"""
        # 注入查询监控
        original_execute = connection.cursor().execute
        
        def monitored_execute(sql, params=None):
            start_time = time.time()
            try:
                result = original_execute(sql, params)
                success = True
                return result
            except Exception as e:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # 只记录慢查询
                if duration_ms > 100:  # 超过100ms
                    metric = PerformanceMetric(
                        timestamp=time.time(),
                        metric_type='database',
                        operation='slow_query',
                        duration_ms=duration_ms,
                        success=success,
                        metadata={
                            'sql_preview': sql[:200] + '...' if len(sql) > 200 else sql,
                            'params_count': len(params) if params else 0
                        }
                    )
                    performance_monitor.collector.record_metric(metric)
        
        # 替换执行方法
        connection.cursor().execute = monitored_execute
        
        return None


class CacheMonitoringMixin:
    """缓存监控混入"""
    
    @staticmethod
    def monitor_cache_get(original_get):
        """监控缓存获取"""
        def wrapper(key, default=None, version=None, **kwargs):
            start_time = time.time()
            
            try:
                # Check if original_get accepts 'using' parameter
                import inspect
                sig = inspect.signature(original_get)
                if 'using' in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
                    # Pass all arguments including 'using' if supported
                    result = original_get(key, default, version, **kwargs)
                else:
                    # Don't pass kwargs if not supported
                    result = original_get(key, default, version)
                success = True
                is_hit = result is not default
                return result
            except Exception as e:
                success = False
                is_hit = False
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                metric = PerformanceMetric(
                    timestamp=time.time(),
                    metric_type='cache',
                    operation='get',
                    duration_ms=duration_ms,
                    success=success,
                    metadata={
                        'key_hash': hash(str(key)) % 10000,
                        'is_hit': is_hit
                    }
                )
                performance_monitor.collector.record_metric(metric)
        
        return wrapper
    
    @staticmethod
    def monitor_cache_set(original_set):
        """监控缓存设置"""
        def wrapper(key, value, timeout=None, version=None, **kwargs):
            start_time = time.time()
            
            try:
                # Check if original_set accepts 'using' parameter
                import inspect
                sig = inspect.signature(original_set)
                if 'using' in sig.parameters or any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values()):
                    # Pass all arguments including 'using' if supported
                    result = original_set(key, value, timeout, version, **kwargs)
                else:
                    # Don't pass kwargs if not supported
                    result = original_set(key, value, timeout, version)
                success = True
                return result
            except Exception as e:
                success = False
                logger.error(f"Cache set operation failed: {e}")
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                metric = PerformanceMetric(
                    timestamp=time.time(),
                    metric_type='cache',
                    operation='set',
                    duration_ms=duration_ms,
                    success=success,
                    metadata={
                        'key_hash': hash(str(key)) % 10000,
                        'timeout': timeout,
                        'value_size': len(str(value)) if value else 0
                    }
                )
                performance_monitor.collector.record_metric(metric)
        
        return wrapper


# 初始化缓存监控
def init_cache_monitoring():
    """初始化缓存监控"""
    try:
        from django.core.cache import cache
        
        # 监控默认缓存
        if hasattr(cache, 'get'):
            original_get = cache.get
            cache.get = CacheMonitoringMixin.monitor_cache_get(original_get)
        
        if hasattr(cache, 'set'):
            original_set = cache.set
            cache.set = CacheMonitoringMixin.monitor_cache_set(original_set)
            
        logger.info("Cache monitoring initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize cache monitoring: {e}")


# 应用启动时初始化监控
init_cache_monitoring()
