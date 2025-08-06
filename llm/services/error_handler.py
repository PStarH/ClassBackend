"""
Error Handler - Centralized error handling patterns for AI services
"""
import logging
from typing import Any, Callable, Dict, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass


class PlanCreationError(AIServiceError):
    """Error in plan creation"""
    pass


class ConversationError(AIServiceError):
    """Error in conversation handling"""
    pass


class PersonalizationError(AIServiceError):
    """Error in personalization"""
    pass


def handle_ai_service_errors(
    fallback_result: Any = None,
    error_key: str = 'error',
    log_error: bool = True
):
    """
    Decorator for handling AI service errors with consistent patterns
    
    Args:
        fallback_result: Result to return on error
        error_key: Key to use for error information in result dict
        log_error: Whether to log the error
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                if fallback_result is not None:
                    if isinstance(fallback_result, dict):
                        result = fallback_result.copy()
                        result[error_key] = str(e)
                        return result
                    elif isinstance(fallback_result, list) and len(fallback_result) > 0:
                        if isinstance(fallback_result[0], dict):
                            for item in fallback_result:
                                item[error_key] = str(e)
                        return fallback_result
                    else:
                        return fallback_result
                else:
                    raise
        return wrapper
    return decorator


def handle_async_ai_service_errors(
    fallback_result: Any = None,
    error_key: str = 'error',
    log_error: bool = True
):
    """
    Async version of the AI service error handler decorator
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                
                if fallback_result is not None:
                    if isinstance(fallback_result, dict):
                        result = fallback_result.copy()
                        result[error_key] = str(e)
                        return result
                    elif isinstance(fallback_result, list) and len(fallback_result) > 0:
                        if isinstance(fallback_result[0], dict):
                            for item in fallback_result:
                                item[error_key] = str(e)
                        return fallback_result
                    else:
                        return fallback_result
                else:
                    raise
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for consistent error handling across AI services"""
    
    def __init__(
        self, 
        operation_name: str, 
        fallback_result: Any = None,
        raise_on_error: bool = False
    ):
        self.operation_name = operation_name
        self.fallback_result = fallback_result
        self.raise_on_error = raise_on_error
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error = exc_val
            logger.error(f"Error in {self.operation_name}: {str(exc_val)}", exc_info=True)
            
            if not self.raise_on_error:
                # Suppress the exception
                return True
        return False
    
    def get_result(self, success_result: Any = None):
        """Get the result, with fallback if there was an error"""
        if self.error and self.fallback_result is not None:
            return self.fallback_result
        return success_result