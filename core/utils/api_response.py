"""
Standardized API Error Handling and Response System
统一的API错误处理和响应系统

This module provides a comprehensive error handling system for Django REST API views,
eliminating repetitive error handling patterns and ensuring consistent API responses.
"""

import logging
import traceback
from functools import wraps
from typing import Any, Dict, Optional, Union, Callable

from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError, DatabaseError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import ValidationError as DRFValidationError

logger = logging.getLogger(__name__)


class StandardResponse:
    """
    Standardized response class for consistent API responses
    标准化响应类，确保API响应的一致性
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = status.HTTP_200_OK,
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create a successful response
        创建成功响应
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        response_data = {
            'success': True,
            'message': message
        }
        
        if data is not None:
            response_data['data'] = data
            
        if extra_fields:
            response_data.update(extra_fields)
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message: str = "操作失败",
        error_details: Optional[Union[str, Dict]] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create an error response
        创建错误响应
        
        Args:
            message: Error message
            error_details: Detailed error information
            status_code: HTTP status code
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        response_data = {
            'success': False,
            'message': message
        }
        
        if error_details is not None:
            if isinstance(error_details, dict):
                response_data['errors'] = error_details
            else:
                response_data['error'] = str(error_details)
                
        if extra_fields:
            response_data.update(extra_fields)
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def validation_error(
        message: str = "数据验证失败",
        errors: Optional[Dict] = None,
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create a validation error response
        创建验证错误响应
        
        Args:
            message: Error message
            errors: Validation errors
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        return StandardResponse.error(
            message=message,
            error_details=errors,
            status_code=status.HTTP_400_BAD_REQUEST,
            extra_fields=extra_fields
        )
    
    @staticmethod
    def permission_error(
        message: str = "权限不足",
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create a permission error response
        创建权限错误响应
        
        Args:
            message: Error message
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            extra_fields=extra_fields
        )
    
    @staticmethod
    def not_found_error(
        message: str = "资源不存在",
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create a not found error response
        创建未找到错误响应
        
        Args:
            message: Error message
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            extra_fields=extra_fields
        )
    
    @staticmethod
    def server_error(
        message: str = "服务器内部错误",
        extra_fields: Optional[Dict] = None
    ) -> Response:
        """
        Create a server error response
        创建服务器错误响应
        
        Args:
            message: Error message
            extra_fields: Additional fields to include in response
        
        Returns:
            Response: DRF Response object
        """
        return StandardResponse.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            extra_fields=extra_fields
        )


class ApiErrorHandler:
    """
    Comprehensive error handler for API views
    API视图的综合错误处理器
    """
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        operation_name: str = "未知操作",
        include_traceback: bool = False
    ) -> Response:
        """
        Handle different types of exceptions and return appropriate responses
        处理不同类型的异常并返回适当的响应
        
        Args:
            exception: The exception to handle
            operation_name: Name of the operation that failed
            include_traceback: Whether to include traceback in logs (for debugging)
        
        Returns:
            Response: Appropriate error response
        """
        error_message = f"{operation_name}失败"
        
        # Log the error with appropriate level
        if include_traceback:
            logger.error(
                f"{operation_name}失败: {str(exception)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
        else:
            logger.error(f"{operation_name}失败: {str(exception)}")
        
        # Handle specific exception types
        if isinstance(exception, DRFValidationError):
            # DRF serializer validation errors
            if hasattr(exception, 'detail'):
                return StandardResponse.validation_error(
                    message=f"{operation_name}失败，数据验证错误",
                    errors=exception.detail
                )
            return StandardResponse.validation_error(
                message=f"{operation_name}失败，数据验证错误",
                errors=str(exception)
            )
        
        elif isinstance(exception, ValidationError):
            # Django validation errors
            if hasattr(exception, 'message_dict'):
                return StandardResponse.validation_error(
                    message=f"{operation_name}失败，数据验证错误",
                    errors=exception.message_dict
                )
            return StandardResponse.validation_error(
                message=f"{operation_name}失败，数据验证错误",
                errors=exception.messages if hasattr(exception, 'messages') else str(exception)
            )
        
        elif isinstance(exception, PermissionDenied):
            # Permission errors
            return StandardResponse.permission_error(
                message=f"{operation_name}失败，权限不足"
            )
        
        elif isinstance(exception, (ObjectDoesNotExist, Http404)):
            # Object not found errors
            return StandardResponse.not_found_error(
                message=f"{operation_name}失败，资源不存在"
            )
        
        elif isinstance(exception, IntegrityError):
            # Database integrity errors (like unique constraint violations)
            logger.warning(f"数据库完整性错误在{operation_name}: {str(exception)}")
            return StandardResponse.validation_error(
                message=f"{operation_name}失败，数据约束冲突",
                errors="该操作违反了数据完整性约束"
            )
        
        elif isinstance(exception, DatabaseError):
            # Other database errors
            logger.error(f"数据库错误在{operation_name}: {str(exception)}")
            return StandardResponse.server_error(
                message=f"{operation_name}失败，数据库操作错误"
            )
        
        else:
            # Generic exceptions
            # Don't expose internal error details to client for security
            logger.error(f"未处理的异常在{operation_name}: {type(exception).__name__}: {str(exception)}")
            return StandardResponse.server_error(
                message=error_message
            )


def api_error_handler(operation_name: str, include_traceback: bool = False):
    """
    Decorator for API view methods to handle errors consistently
    API视图方法的装饰器，用于一致地处理错误
    
    Args:
        operation_name: Name of the operation (for logging and error messages)
        include_traceback: Whether to include full traceback in logs
    
    Returns:
        Decorated function that handles exceptions
    
    Usage:
        @api_error_handler("用户注册")
        def post(self, request, *args, **kwargs):
            # Method implementation
            return StandardResponse.success(data=result)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Execute the original function
                result = func(*args, **kwargs)
                
                # If the function returns a Response, return it as-is
                if isinstance(result, Response):
                    return result
                
                # If the function returns other data, wrap it in a success response
                return StandardResponse.success(data=result)
                
            except Exception as e:
                # Handle any exception that occurs
                return ApiErrorHandler.handle_exception(
                    exception=e,
                    operation_name=operation_name,
                    include_traceback=include_traceback
                )
        
        return wrapper
    return decorator


# Convenience decorators for common operations
def user_operation_handler(operation_name: str):
    """Decorator specifically for user-related operations"""
    return api_error_handler(f"用户{operation_name}")


def course_operation_handler(operation_name: str):
    """Decorator specifically for course-related operations"""
    return api_error_handler(f"课程{operation_name}")


def settings_operation_handler(operation_name: str):
    """Decorator specifically for settings-related operations"""
    return api_error_handler(f"设置{operation_name}")


# Example usage patterns for different scenarios
class ApiResponsePatterns:
    """
    Common response patterns for API operations
    API操作的常见响应模式
    """
    
    @staticmethod
    def created_response(data: Any, resource_name: str = "资源") -> Response:
        """Response for successful resource creation"""
        return StandardResponse.success(
            data=data,
            message=f"{resource_name}创建成功",
            status_code=status.HTTP_201_CREATED
        )
    
    @staticmethod
    def updated_response(data: Any, resource_name: str = "资源") -> Response:
        """Response for successful resource update"""
        return StandardResponse.success(
            data=data,
            message=f"{resource_name}更新成功"
        )
    
    @staticmethod
    def deleted_response(resource_name: str = "资源") -> Response:
        """Response for successful resource deletion"""
        return StandardResponse.success(
            message=f"{resource_name}删除成功"
        )
    
    @staticmethod
    def list_response(data: Any, count: Optional[int] = None, resource_name: str = "资源") -> Response:
        """Response for successful resource listing"""
        extra_fields = {'count': count} if count is not None else None
        return StandardResponse.success(
            data=data,
            message=f"{resource_name}列表获取成功",
            extra_fields=extra_fields
        )