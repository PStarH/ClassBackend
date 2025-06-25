"""
核心视图
"""
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response


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


def health_check(request):
    """健康检查端点"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'Education Platform API is running.',
        'version': '1.0.0'
    })
