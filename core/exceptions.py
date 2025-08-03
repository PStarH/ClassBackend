"""
统一异常处理器和响应格式
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError
import logging

logger = logging.getLogger('security')


def custom_exception_handler(exc, context):
    """
    统一API异常处理器
    """
    # 调用DRF默认异常处理器
    response = exception_handler(exc, context)
    
    # 标准化响应格式
    if response is not None:
        custom_response_data = {
            'status': 'error',
            'code': response.status_code,
            'message': get_error_message(exc, response),
            'data': None,
            'timestamp': timezone.now().isoformat(),
        }
        
        # 在开发环境添加详细错误信息
        if settings.DEBUG:
            custom_response_data['debug'] = {
                'exception_type': exc.__class__.__name__,
                'details': response.data if hasattr(response, 'data') else str(exc)
            }
        
        # 记录安全相关异常
        if response.status_code in [401, 403, 429]:
            logger.warning(
                f"Security exception: {exc.__class__.__name__} - "
                f"User: {getattr(context.get('request'), 'user', 'Anonymous')} - "
                f"IP: {get_client_ip(context.get('request'))} - "
                f"Path: {context.get('request').path if context.get('request') else 'N/A'}"
            )
        
        response.data = custom_response_data
    
    return response


def get_error_message(exc, response):
    """
    获取用户友好的错误消息
    """
    error_messages = {
        400: "请求参数错误",
        401: "身份验证失败",
        403: "权限不足",
        404: "资源不存在", 
        405: "请求方法不允许",
        406: "请求格式不被接受",
        429: "请求过于频繁，请稍后再试",
        500: "服务器内部错误",
        502: "网关错误",
        503: "服务暂时不可用",
    }
    
    status_code = response.status_code
    
    # 优先使用异常中的详细消息
    if hasattr(exc, 'detail') and exc.detail:
        if isinstance(exc.detail, dict):
            # 提取字段验证错误
            field_errors = []
            for field, errors in exc.detail.items():
                if isinstance(errors, list):
                    field_errors.append(f"{field}: {', '.join(str(e) for e in errors)}")
                else:
                    field_errors.append(f"{field}: {str(errors)}")
            return '; '.join(field_errors) if field_errors else error_messages.get(status_code, "未知错误")
        else:
            return str(exc.detail)
    
    # 使用预定义的错误消息
    return error_messages.get(status_code, "未知错误")


def get_client_ip(request):
    """
    获取客户端真实IP地址
    """
    if not request:
        return 'Unknown'
        
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class APIResponse:
    """
    标准化API响应类
    """
    
    @staticmethod
    def success(data=None, message="操作成功", code=200, pagination=None):
        """
        成功响应
        """
        response_data = {
            'status': 'success',
            'code': code,
            'message': message,
            'data': data,
            'timestamp': timezone.now().isoformat(),
        }
        
        if pagination:
            response_data['pagination'] = pagination
            
        return Response(response_data, status=code)
    
    @staticmethod
    def error(message="操作失败", code=400, data=None, errors=None):
        """
        错误响应
        """
        response_data = {
            'status': 'error',
            'code': code,
            'message': message,
            'data': data,
            'timestamp': timezone.now().isoformat(),
        }
        
        if errors:
            response_data['errors'] = errors
            
        return Response(response_data, status=code)
    
    @staticmethod
    def created(data=None, message="创建成功"):
        """
        创建成功响应
        """
        return APIResponse.success(data=data, message=message, code=201)
    
    @staticmethod
    def not_found(message="资源不存在"):
        """
        资源不存在响应
        """
        return APIResponse.error(message=message, code=404)
    
    @staticmethod
    def forbidden(message="权限不足"):
        """
        权限不足响应
        """
        return APIResponse.error(message=message, code=403)
    
    @staticmethod
    def unauthorized(message="身份验证失败"):
        """
        未授权响应
        """
        return APIResponse.error(message=message, code=401)


# 导入必要的模块
from django.utils import timezone
from django.conf import settings