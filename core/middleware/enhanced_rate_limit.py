"""
增强的API限流中间件
支持分层限流、智能限流、用户类型区分等功能
基于建议的最佳实践实现
"""
import time
import logging
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from decouple import config

logger = logging.getLogger(__name__)

# 限流配置
DEFAULT_RATE_LIMITS = {
    'anonymous': {
        'requests_per_minute': config('ANON_RATE_LIMIT_MINUTE', default=20, cast=int),
        'requests_per_hour': config('ANON_RATE_LIMIT_HOUR', default=100, cast=int),
        'requests_per_day': config('ANON_RATE_LIMIT_DAY', default=1000, cast=int),
    },
    'authenticated': {
        'requests_per_minute': config('AUTH_RATE_LIMIT_MINUTE', default=60, cast=int),
        'requests_per_hour': config('AUTH_RATE_LIMIT_HOUR', default=1000, cast=int),
        'requests_per_day': config('AUTH_RATE_LIMIT_DAY', default=10000, cast=int),
    },
    'premium': {
        'requests_per_minute': config('PREMIUM_RATE_LIMIT_MINUTE', default=120, cast=int),
        'requests_per_hour': config('PREMIUM_RATE_LIMIT_HOUR', default=2000, cast=int),
        'requests_per_day': config('PREMIUM_RATE_LIMIT_DAY', default=50000, cast=int),
    },
    'admin': {
        'requests_per_minute': config('ADMIN_RATE_LIMIT_MINUTE', default=200, cast=int),
        'requests_per_hour': config('ADMIN_RATE_LIMIT_HOUR', default=5000, cast=int),
        'requests_per_day': config('ADMIN_RATE_LIMIT_DAY', default=100000, cast=int),
    }
}

# API特定限流
API_SPECIFIC_LIMITS = {
    '/api/ai/': {
        'requests_per_minute': config('AI_API_RATE_LIMIT_MINUTE', default=10, cast=int),
        'requests_per_hour': config('AI_API_RATE_LIMIT_HOUR', default=100, cast=int),
    },
    '/api/auth/login/': {
        'requests_per_minute': config('LOGIN_RATE_LIMIT_MINUTE', default=5, cast=int),
        'requests_per_hour': config('LOGIN_RATE_LIMIT_HOUR', default=20, cast=int),
    },
    '/api/auth/register/': {
        'requests_per_minute': config('REGISTER_RATE_LIMIT_MINUTE', default=3, cast=int),
        'requests_per_hour': config('REGISTER_RATE_LIMIT_HOUR', default=10, cast=int),
    },
}


class RateLimitExceeded(Exception):
    """限流异常"""
    def __init__(self, message: str, retry_after: int = 60):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class ClientIdentifier:
    """客户端识别器"""
    
    @staticmethod
    def get_client_id(request) -> str:
        """获取客户端唯一标识"""
        # 优先使用用户ID
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # 使用IP地址
        ip = ClientIdentifier.get_client_ip(request)
        return f"ip:{ip}"
    
    @staticmethod
    def get_client_ip(request) -> str:
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    @staticmethod
    def get_user_type(request) -> str:
        """获取用户类型"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return 'anonymous'
        
        user = request.user
        
        if user.is_superuser or user.is_staff:
            return 'admin'
        
        # 检查是否是高级用户（需要根据实际业务逻辑调整）
        if hasattr(user, 'profile') and getattr(user.profile, 'is_premium', False):
            return 'premium'
        
        return 'authenticated'


class SlidingWindowCounter:
    """滑动窗口计数器"""
    
    def __init__(self, window_size: int):
        self.window_size = window_size  # 窗口大小（秒）
    
    def is_allowed(self, key: str, limit: int) -> Tuple[bool, int]:
        """检查是否允许请求"""
        now = int(time.time())
        window_start = now - self.window_size
        
        # 获取当前窗口内的请求记录
        cache_key = f"rate_limit:{key}:{self.window_size}"
        requests = cache.get(cache_key, [])
        
        # 清理过期的请求记录
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # 检查是否超过限制
        if len(requests) >= limit:
            # 计算重试时间
            oldest_request = min(requests) if requests else now
            retry_after = oldest_request + self.window_size - now
            return False, max(retry_after, 1)
        
        # 添加当前请求
        requests.append(now)
        
        # 更新缓存
        cache.set(cache_key, requests, self.window_size + 60)  # 多缓存60秒
        
        return True, 0


class TokenBucketRateLimiter:
    """令牌桶限流器"""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity  # 桶容量
        self.refill_rate = refill_rate  # 每秒填充速率
    
    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """检查是否允许请求"""
        now = time.time()
        cache_key = f"token_bucket:{key}"
        
        # 获取当前状态
        bucket_data = cache.get(cache_key, {
            'tokens': self.capacity,
            'last_refill': now
        })
        
        # 计算需要添加的令牌数
        time_passed = now - bucket_data['last_refill']
        tokens_to_add = time_passed * self.refill_rate
        
        # 更新令牌数（不超过容量）
        bucket_data['tokens'] = min(self.capacity, bucket_data['tokens'] + tokens_to_add)
        bucket_data['last_refill'] = now
        
        # 检查是否有可用令牌
        if bucket_data['tokens'] >= 1:
            bucket_data['tokens'] -= 1
            cache.set(cache_key, bucket_data, 3600)  # 缓存1小时
            return True, 0
        else:
            # 计算重试时间
            retry_after = int((1 - bucket_data['tokens']) / self.refill_rate)
            cache.set(cache_key, bucket_data, 3600)
            return False, max(retry_after, 1)


class AdaptiveRateLimiter:
    """自适应限流器 - 根据系统负载动态调整"""
    
    def __init__(self):
        self.load_threshold = config('ADAPTIVE_LOAD_THRESHOLD', default=0.8, cast=float)
        self.load_factor = config('ADAPTIVE_LOAD_FACTOR', default=0.5, cast=float)
    
    def get_system_load(self) -> float:
        """获取系统负载"""
        try:
            # 检查数据库连接数
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                active_connections = cursor.fetchone()[0]
                
                cursor.execute("SELECT setting::int FROM pg_settings WHERE name = 'max_connections';")
                max_connections = cursor.fetchone()[0]
                
                db_load = active_connections / max_connections
            
            # 检查缓存命中率
            cache_stats_key = "cache_hit_rate"
            cache_stats = cache.get(cache_stats_key, {'hits': 0, 'misses': 0})
            total_requests = cache_stats['hits'] + cache_stats['misses']
            cache_hit_rate = cache_stats['hits'] / total_requests if total_requests > 0 else 1.0
            
            # 综合负载指标
            system_load = (db_load * 0.7) + ((1 - cache_hit_rate) * 0.3)
            
            return min(system_load, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to get system load: {e}")
            return 0.5  # 默认中等负载
    
    def adjust_limits(self, original_limits: Dict[str, int]) -> Dict[str, int]:
        """根据系统负载调整限流"""
        system_load = self.get_system_load()
        
        if system_load > self.load_threshold:
            # 系统负载高，降低限流
            adjustment_factor = 1 - (system_load - self.load_threshold) * self.load_factor
            adjustment_factor = max(adjustment_factor, 0.1)  # 最少保留10%
            
            adjusted_limits = {}
            for key, value in original_limits.items():
                adjusted_limits[key] = max(int(value * adjustment_factor), 1)
            
            logger.warning(f"High system load ({system_load:.2f}), adjusting rate limits by {adjustment_factor:.2f}")
            return adjusted_limits
        
        return original_limits


class EnhancedRateLimitMiddleware:
    """增强的限流中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 初始化限流器
        self.sliding_window_minute = SlidingWindowCounter(60)
        self.sliding_window_hour = SlidingWindowCounter(3600)
        self.sliding_window_day = SlidingWindowCounter(86400)
        
        self.token_bucket = TokenBucketRateLimiter(
            capacity=config('TOKEN_BUCKET_CAPACITY', default=10, cast=int),
            refill_rate=config('TOKEN_BUCKET_REFILL_RATE', default=0.1, cast=float)
        )
        
        self.adaptive_limiter = AdaptiveRateLimiter()
        
        # 统计数据
        self.stats = defaultdict(int)
    
    def __call__(self, request):
        try:
            # 检查是否跳过限流
            if self.should_skip_rate_limiting(request):
                return self.get_response(request)
            
            # 执行限流检查
            self.check_rate_limits(request)
            
            # 继续处理请求
            response = self.get_response(request)
            
            # 添加限流头
            self.add_rate_limit_headers(request, response)
            
            return response
            
        except RateLimitExceeded as e:
            return self.create_rate_limit_response(e)
    
    def should_skip_rate_limiting(self, request) -> bool:
        """检查是否应该跳过限流"""
        # 跳过健康检查等内部请求
        if request.path in ['/health/', '/metrics/', '/admin/']:
            return True
        
        # 跳过静态文件
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True
        
        # 检查白名单IP
        client_ip = ClientIdentifier.get_client_ip(request)
        whitelist_ips = config('RATE_LIMIT_WHITELIST_IPS', default='', cast=lambda v: v.split(',') if v else [])
        if client_ip in whitelist_ips:
            return True
        
        return False
    
    def check_rate_limits(self, request):
        """执行限流检查"""
        client_id = ClientIdentifier.get_client_id(request)
        user_type = ClientIdentifier.get_user_type(request)
        
        # 获取基础限流配置
        base_limits = DEFAULT_RATE_LIMITS.get(user_type, DEFAULT_RATE_LIMITS['anonymous'])
        
        # 自适应调整
        adjusted_limits = self.adaptive_limiter.adjust_limits(base_limits)
        
        # 检查分钟级限流
        minute_key = f"{client_id}:minute"
        allowed, retry_after = self.sliding_window_minute.is_allowed(
            minute_key, adjusted_limits['requests_per_minute']
        )
        if not allowed:
            self.stats['minute_exceeded'] += 1
            raise RateLimitExceeded(
                f"Rate limit exceeded: {adjusted_limits['requests_per_minute']} requests per minute",
                retry_after
            )
        
        # 检查小时级限流
        hour_key = f"{client_id}:hour"
        allowed, retry_after = self.sliding_window_hour.is_allowed(
            hour_key, adjusted_limits['requests_per_hour']
        )
        if not allowed:
            self.stats['hour_exceeded'] += 1
            raise RateLimitExceeded(
                f"Rate limit exceeded: {adjusted_limits['requests_per_hour']} requests per hour",
                retry_after
            )
        
        # 检查日级限流
        day_key = f"{client_id}:day"
        allowed, retry_after = self.sliding_window_day.is_allowed(
            day_key, adjusted_limits['requests_per_day']
        )
        if not allowed:
            self.stats['day_exceeded'] += 1
            raise RateLimitExceeded(
                f"Rate limit exceeded: {adjusted_limits['requests_per_day']} requests per day",
                retry_after
            )
        
        # 检查API特定限流
        self.check_api_specific_limits(request, client_id)
        
        # 令牌桶检查（突发请求控制）
        bucket_key = f"{client_id}:burst"
        allowed, retry_after = self.token_bucket.is_allowed(bucket_key)
        if not allowed:
            self.stats['burst_exceeded'] += 1
            raise RateLimitExceeded("Too many requests in short time", retry_after)
        
        # 更新统计
        self.stats['requests_allowed'] += 1
    
    def check_api_specific_limits(self, request, client_id: str):
        """检查API特定限流"""
        path = request.path
        
        for api_pattern, limits in API_SPECIFIC_LIMITS.items():
            if path.startswith(api_pattern):
                # 检查分钟级限流
                if 'requests_per_minute' in limits:
                    api_key = f"{client_id}:api:{api_pattern}:minute"
                    allowed, retry_after = self.sliding_window_minute.is_allowed(
                        api_key, limits['requests_per_minute']
                    )
                    if not allowed:
                        raise RateLimitExceeded(
                            f"API rate limit exceeded for {api_pattern}: {limits['requests_per_minute']} requests per minute",
                            retry_after
                        )
                
                # 检查小时级限流
                if 'requests_per_hour' in limits:
                    api_key = f"{client_id}:api:{api_pattern}:hour"
                    allowed, retry_after = self.sliding_window_hour.is_allowed(
                        api_key, limits['requests_per_hour']
                    )
                    if not allowed:
                        raise RateLimitExceeded(
                            f"API rate limit exceeded for {api_pattern}: {limits['requests_per_hour']} requests per hour",
                            retry_after
                        )
                break
    
    def add_rate_limit_headers(self, request, response):
        """添加限流相关头"""
        try:
            client_id = ClientIdentifier.get_client_id(request)
            user_type = ClientIdentifier.get_user_type(request)
            
            limits = DEFAULT_RATE_LIMITS.get(user_type, DEFAULT_RATE_LIMITS['anonymous'])
            
            # 添加限流信息头
            response['X-RateLimit-Limit-Minute'] = str(limits['requests_per_minute'])
            response['X-RateLimit-Limit-Hour'] = str(limits['requests_per_hour'])
            response['X-RateLimit-Limit-Day'] = str(limits['requests_per_day'])
            
            # 获取剩余请求数（简化实现）
            minute_key = f"rate_limit:{client_id}:60"
            minute_requests = len(cache.get(minute_key, []))
            response['X-RateLimit-Remaining-Minute'] = str(max(0, limits['requests_per_minute'] - minute_requests))
            
            # 添加重置时间
            response['X-RateLimit-Reset'] = str(int(time.time()) + 60)
            
        except Exception as e:
            logger.error(f"Failed to add rate limit headers: {e}")
    
    def create_rate_limit_response(self, error: RateLimitExceeded):
        """创建限流响应"""
        response_data = {
            'error': 'Rate limit exceeded',
            'message': error.message,
            'retry_after': error.retry_after,
            'timestamp': timezone.now().isoformat()
        }
        
        response = JsonResponse(response_data, status=status.HTTP_429_TOO_MANY_REQUESTS)
        response['Retry-After'] = str(error.retry_after)
        response['X-RateLimit-Exceeded'] = 'true'
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """获取限流统计信息"""
        return dict(self.stats)


class RateLimitMonitor:
    """限流监控器"""
    
    @staticmethod
    def log_rate_limit_violation(client_id: str, limit_type: str, request_path: str):
        """记录限流违规"""
        violation_data = {
            'client_id': client_id,
            'limit_type': limit_type,
            'request_path': request_path,
            'timestamp': timezone.now().isoformat()
        }
        
        # 记录到日志
        logger.warning(f"Rate limit violation: {violation_data}")
        
        # 记录到缓存（用于分析）
        violations_key = f"rate_limit_violations:{timezone.now().strftime('%Y%m%d')}"
        violations = cache.get(violations_key, [])
        violations.append(violation_data)
        cache.set(violations_key, violations, 86400)  # 24小时
    
    @staticmethod
    def get_top_violators(days: int = 1) -> list:
        """获取主要违规者"""
        violators = defaultdict(int)
        
        for day_offset in range(days):
            date = (timezone.now() - timedelta(days=day_offset)).strftime('%Y%m%d')
            violations_key = f"rate_limit_violations:{date}"
            violations = cache.get(violations_key, [])
            
            for violation in violations:
                client_id = violation.get('client_id', 'unknown')
                violators[client_id] += 1
        
        # 排序并返回前10名
        return sorted(violators.items(), key=lambda x: x[1], reverse=True)[:10]


# 导出主要组件
__all__ = [
    'EnhancedRateLimitMiddleware',
    'RateLimitMonitor',
    'ClientIdentifier',
    'SlidingWindowCounter',
    'TokenBucketRateLimiter',
    'AdaptiveRateLimiter',
    'RateLimitExceeded',
]