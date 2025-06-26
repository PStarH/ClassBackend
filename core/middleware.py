"""
核心中间件
"""
import time
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """
    API 速率限制中间件
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limit = getattr(settings, 'API_RATE_LIMIT', 100)  # 每分钟请求数
        self.rate_limit_period = getattr(settings, 'API_RATE_LIMIT_PERIOD', 60)  # 时间窗口（秒）
    
    def process_request(self, request):
        # 只对 API 路径应用速率限制
        if not request.path.startswith('/api/'):
            return None
            
        # 获取客户端 IP
        client_ip = self.get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}"
        
        try:
            # 获取当前请求计数
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= self.rate_limit:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Limit: {self.rate_limit} per {self.rate_limit_period} seconds'
                }, status=429)
            
            # 增加请求计数
            cache.set(cache_key, current_requests + 1, self.rate_limit_period)
            
        except Exception as e:
            # Redis 异常时不影响正常请求
            logger.error(f"Rate limit middleware error: {str(e)}")
            
        return None
    
    def get_client_ip(self, request):
        """获取客户端真实 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CacheResponseMiddleware(MiddlewareMixin):
    """
    响应缓存中间件
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.cache_timeout = getattr(settings, 'API_CACHE_TIMEOUT', 300)  # 5分钟
    
    def process_request(self, request):
        # 只缓存 GET 请求的 API 响应
        if request.method != 'GET' or not request.path.startswith('/api/'):
            return None
            
        # 构建缓存键
        cache_key = self.get_cache_key(request)
        
        try:
            cached_response = cache.get(cache_key, using='api_cache')
            if cached_response:
                logger.debug(f"Cache hit for: {cache_key}")
                response = JsonResponse(cached_response['data'])
                response.status_code = cached_response['status_code']
                response['X-Cache'] = 'HIT'
                return response
        except Exception as e:
            logger.error(f"Cache middleware error: {str(e)}")
            
        return None
    
    def process_response(self, request, response):
        # 只缓存成功的 GET 请求响应
        if (request.method == 'GET' and 
            request.path.startswith('/api/') and 
            response.status_code == 200 and 
            hasattr(response, 'content')):
            
            cache_key = self.get_cache_key(request)
            
            try:
                # 尝试解析 JSON 响应
                import json
                data = json.loads(response.content.decode('utf-8'))
                
                cached_data = {
                    'data': data,
                    'status_code': response.status_code
                }
                
                cache.set(cache_key, cached_data, self.cache_timeout, using='api_cache')
                response['X-Cache'] = 'MISS'
                logger.debug(f"Cached response for: {cache_key}")
                
            except Exception as e:
                logger.error(f"Failed to cache response: {str(e)}")
        
        return response
    
    def get_cache_key(self, request):
        """生成缓存键"""
        path = request.path
        query_params = request.GET.urlencode()
        user_id = getattr(request.user, 'id', 'anonymous')
        return f"api_response:{user_id}:{path}:{query_params}"


class HealthCheckMiddleware(MiddlewareMixin):
    """
    健康检查中间件
    监控 Redis 连接状态
    """
    
    def process_request(self, request):
        if request.path == '/health/':
            try:
                # 检查 Redis 连接
                cache.set('health_check', 'ok', 10)
                redis_status = cache.get('health_check') == 'ok'
                
                if redis_status:
                    return JsonResponse({
                        'status': 'healthy',
                        'redis': 'connected',
                        'timestamp': time.time()
                    })
                else:
                    return JsonResponse({
                        'status': 'unhealthy',
                        'redis': 'disconnected',
                        'timestamp': time.time()
                    }, status=503)
                    
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                return JsonResponse({
                    'status': 'unhealthy',
                    'redis': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }, status=503)
        
        return None
