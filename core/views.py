"""
核心视图
"""
import time
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .cache import (
    get_default_cache, get_api_cache, 
    APICacheManager, cache_result,
    CacheService
)


class BaseAPIView(APIView):
    """基础API视图类"""
    
    def handle_exception(self, exc):
        """统一异常处理"""
        response = super().handle_exception(exc)
        
        # 自定义错误响应格式
        if hasattr(response, 'data'):
            custom_response_data = {
                'success': False,
                'error': {
                    'message': str(exc),
                    'type': exc.__class__.__name__
                },
                'data': None
            }
            response.data = custom_response_data
        
        return response


class CachedAPIView(BaseAPIView):
    """支持缓存的API视图基类"""
    
    cache_timeout = 300  # 默认5分钟缓存
    cache_key_prefix = 'api'
    
    def get_cache_key(self, request, *args, **kwargs):
        """生成缓存键"""
        endpoint = self.__class__.__name__.lower()
        user_id = getattr(request.user, 'id', 'anonymous')
        params = dict(request.GET.items())
        return APICacheManager.get_api_cache_key(endpoint, params, user_id)
    
    def get_cached_response(self, request, *args, **kwargs):
        """获取缓存的响应"""
        if request.method != 'GET':
            return None
            
        cache_key = self.get_cache_key(request, *args, **kwargs)
        cached_data = get_api_cache().get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        return None
    
    def cache_response(self, request, response, *args, **kwargs):
        """缓存响应"""
        if request.method == 'GET' and response.status_code == 200:
            cache_key = self.get_cache_key(request, *args, **kwargs)
            get_api_cache().set(cache_key, response.data, self.cache_timeout)
    
    def dispatch(self, request, *args, **kwargs):
        """重写dispatch方法以支持缓存"""
        # 尝试获取缓存响应
        cached_response = self.get_cached_response(request, *args, **kwargs)
        if cached_response:
            cached_response['X-Cache'] = 'HIT'
            return cached_response
        
        # 正常处理请求
        response = super().dispatch(request, *args, **kwargs)
        
        # 缓存响应
        if hasattr(response, 'data'):
            self.cache_response(request, response, *args, **kwargs)
            response['X-Cache'] = 'MISS'
        
        return response


def custom_404(request, exception):
    """自定义 404 页面"""
    return JsonResponse({
        'error': 'Not Found',
        'message': 'The requested resource was not found.',
        'status_code': 404
    }, status=404)


def custom_500(request):
    """自定义 500 页面"""
    return JsonResponse({
        'error': 'Internal Server Error',
        'message': 'An internal server error occurred.',
        'status_code': 500
    }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    健康检查端点
    检查 Redis 连接和应用状态
    """
    try:
        # 检查 Redis 连接
        default_cache_service = get_default_cache()
        test_key = 'health_check_test'
        default_cache_service.set(test_key, 'ok', 10)
        redis_status = default_cache_service.get(test_key) == 'ok'
        default_cache_service.delete(test_key)
        
        # 检查 API 缓存
        api_cache_status = True
        try:
            api_cache_service = get_api_cache()
            api_cache_service.set('api_health_test', 'ok', 10)
            api_cache_status = api_cache_service.get('api_health_test') == 'ok'
            api_cache_service.delete('api_health_test')
        except:
            api_cache_status = False
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': time.time(),
            'services': {
                'redis_default': redis_status,
                'redis_api_cache': api_cache_status,
                'django': True
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }, status=503)


@api_view(['GET'])
@permission_classes([AllowAny])
def cache_stats(request):
    """
    缓存统计信息
    """
    try:
        stats = {
            'timestamp': time.time(),
            'cache_backends': {
                'default': 'Available',
                'api_cache': 'Available',
                'sessions': 'Available'
            }
        }
        
        # 尝试获取 Redis 统计信息
        try:
            # 检查 Redis 连接
            default_cache_service = get_default_cache()
            test_key = 'stats_test'
            default_cache_service.set(test_key, 'test', 10)
            cache_working = default_cache_service.get(test_key) == 'test'
            default_cache_service.delete(test_key)
            
            stats['redis_status'] = 'connected' if cache_working else 'disconnected'
        except Exception as e:
            stats['redis_status'] = f'error: {str(e)}'
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'timestamp': time.time()
        }, status=500)
