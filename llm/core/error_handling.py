"""
LLM服务错误处理和重试机制
"""
import time
import asyncio
import logging
from typing import Any, Callable, Optional
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True


class LLMRateLimitError(Exception):
    """API限制异常"""
    pass


class LLMTimeoutError(Exception):
    """超时异常"""
    pass


class LLMQuotaExceededError(Exception):
    """配额超出异常"""
    pass


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试"""
        # 这些异常类型应该重试
        retryable_exceptions = (
            LLMRateLimitError,
            LLMTimeoutError,
            ConnectionError,
            TimeoutError,
        )
        
        # 这些异常类型不应该重试
        non_retryable_exceptions = (
            LLMQuotaExceededError,
            ValueError,
            TypeError,
        )
        
        if isinstance(exception, non_retryable_exceptions):
            return False
        
        if isinstance(exception, retryable_exceptions):
            return True
        
        # 检查异常消息中的特定关键词
        error_msg = str(exception).lower()
        if any(keyword in error_msg for keyword in ['timeout', 'rate limit', 'connection']):
            return True
        
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        delay = min(
            self.config.base_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 添加50%的抖动
        
        return delay


def retry_llm_request(config: RetryConfig = None):
    """LLM请求重试装饰器"""
    retry_handler = RetryHandler(config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_handler.config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not retry_handler.should_retry(e):
                        logger.error(f"不可重试的错误: {e}")
                        raise
                    
                    if attempt < retry_handler.config.max_attempts - 1:
                        delay = retry_handler.calculate_delay(attempt)
                        logger.warning(
                            f"第{attempt + 1}次尝试失败: {e}，"
                            f"{delay:.2f}秒后重试"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"所有{retry_handler.config.max_attempts}次尝试都失败")
            
            raise last_exception
        
        return wrapper
    return decorator


def async_retry_llm_request(config: RetryConfig = None):
    """异步LLM请求重试装饰器"""
    retry_handler = RetryHandler(config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(retry_handler.config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not retry_handler.should_retry(e):
                        logger.error(f"不可重试的错误: {e}")
                        raise
                    
                    if attempt < retry_handler.config.max_attempts - 1:
                        delay = retry_handler.calculate_delay(attempt)
                        logger.warning(
                            f"第{attempt + 1}次尝试失败: {e}，"
                            f"{delay:.2f}秒后重试"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"所有{retry_handler.config.max_attempts}次尝试都失败")
            
            raise last_exception
        
        return wrapper
    return decorator


class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.reset_timeout
        )
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"熔断器打开，失败次数: {self.failure_count}")


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_requests: int = 60, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            self._cleanup_old_requests()
            
            if len(self.requests) >= self.max_requests:
                wait_time = self.time_window - (time.time() - self.requests[0])
                if wait_time > 0:
                    logger.warning(f"速率限制：等待{wait_time:.2f}秒")
                    time.sleep(wait_time)
                    self._cleanup_old_requests()
            
            self.requests.append(time.time())
            return func(*args, **kwargs)
        
        return wrapper
    
    def _cleanup_old_requests(self):
        """清理过期的请求记录"""
        current_time = time.time()
        self.requests = [
            req_time for req_time in self.requests
            if current_time - req_time < self.time_window
        ]


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, check_interval: float = 30.0):
        self.check_interval = check_interval
        self.last_check = 0
        self.is_healthy = True
        self.health_score = 1.0
    
    def check_health(self, service) -> bool:
        """检查服务健康状态"""
        current_time = time.time()
        
        if current_time - self.last_check < self.check_interval:
            return self.is_healthy
        
        try:
            # 执行健康检查
            test_response = service.simple_completion(
                "Hello", use_cache=False
            )
            
            if test_response and len(test_response.strip()) > 0:
                self.is_healthy = True
                self.health_score = min(1.0, self.health_score + 0.1)
            else:
                self.is_healthy = False
                self.health_score = max(0.0, self.health_score - 0.2)
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            self.is_healthy = False
            self.health_score = max(0.0, self.health_score - 0.3)
        
        self.last_check = current_time
        return self.is_healthy
    
    def get_health_score(self) -> float:
        """获取健康分数 (0.0-1.0)"""
        return self.health_score


# 预配置的重试策略
AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    backoff_factor=2.0
)

CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=10.0,
    backoff_factor=1.5
)

STANDARD_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=20.0,
    backoff_factor=2.0
)
