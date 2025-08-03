# High-Performance API Middleware
"""
Optimized middleware stack for maximum API performance
Includes response compression, caching, rate limiting, and monitoring
"""

import time
import json
import gzip
import hashlib
from typing import Optional, Dict, Any
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import logging

logger = logging.getLogger('performance')

class ResponseCompressionMiddleware(MiddlewareMixin):
    """High-performance response compression middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.min_length = getattr(settings, 'COMPRESSION_MIN_LENGTH', 1000)
        self.compressible_types = {
            'application/json',
            'text/html', 
            'text/css',
            'text/javascript',
            'application/javascript',
            'text/plain',
            'application/xml',
            'text/xml'
        }
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only compress if client accepts gzip
        if 'gzip' not in request.META.get('HTTP_ACCEPT_ENCODING', ''):
            return response
        
        # Check if response should be compressed
        if (hasattr(response, 'content') and 
            len(response.content) >= self.min_length and
            self._should_compress(response)):
            
            # Compress response content
            compressed_content = gzip.compress(response.content)
            
            # Only use compression if it actually reduces size
            if len(compressed_content) < len(response.content):
                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = len(compressed_content)
                response['Vary'] = response.get('Vary', '') + ', Accept-Encoding'
        
        return response
    
    def _should_compress(self, response):
        """Check if response should be compressed"""
        content_type = response.get('Content-Type', '').split(';')[0].lower()
        return (content_type in self.compressible_types and
                not response.get('Content-Encoding') and
                response.status_code == 200)

class SmartCacheMiddleware(MiddlewareMixin):
    """Intelligent response caching middleware"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = getattr(settings, 'API_CACHE_TIMEOUT', 300)
        self.cacheable_methods = {'GET', 'HEAD', 'OPTIONS'}
        self.cache_headers = {
            'Cache-Control': 'public, max-age=300',
            'Vary': 'Accept, Accept-Encoding, Authorization'
        }
    
    def __call__(self, request):
        # Only cache safe methods
        if request.method not in self.cacheable_methods:
            return self.get_response(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get cached response
        cached_response = cache.get(cache_key)
        if cached_response:
            # Add cache hit header for monitoring
            cached_response['X-Cache-Status'] = 'HIT'
            return cached_response
        
        # Get fresh response
        response = self.get_response(request)
        
        # Cache successful responses
        if self._should_cache(request, response):
            # Clone response for caching
            cached_response = HttpResponse(
                content=response.content,
                status=response.status_code,
                content_type=response.get('Content-Type')
            )
            
            # Copy important headers
            for header in ['Content-Type', 'Content-Encoding']:
                if header in response:
                    cached_response[header] = response[header]
            
            # Add cache headers
            for header, value in self.cache_headers.items():
                cached_response[header] = value
            
            # Cache the response
            cache.set(cache_key, cached_response, self.cache_timeout)
            response['X-Cache-Status'] = 'MISS'
        else:
            response['X-Cache-Status'] = 'SKIP'
        
        return response
    
    def _generate_cache_key(self, request):
        """Generate cache key for request"""
        key_parts = [
            request.method,
            request.get_full_path(),
            request.META.get('HTTP_ACCEPT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        ]
        
        # Include user ID for personalized content
        if hasattr(request, 'user') and request.user.is_authenticated:
            key_parts.append(str(request.user.pk))
        
        key_string = '|'.join(key_parts)
        return f"api_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    def _should_cache(self, request, response):
        """Determine if response should be cached"""
        # Only cache successful responses
        if response.status_code != 200:
            return False
        
        # Don't cache responses with cache-control: no-cache
        cache_control = response.get('Cache-Control', '')
        if 'no-cache' in cache_control or 'private' in cache_control:
            return False
        
        # Don't cache API endpoints that modify data
        if request.path.startswith('/api/') and request.method != 'GET':
            return False
        
        # Don't cache responses with authentication errors
        if 'WWW-Authenticate' in response:
            return False
        
        return True

class AdvancedRateLimitMiddleware(MiddlewareMixin):
    """Advanced rate limiting with burst protection and user tiers"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rate limit tiers
        self.rate_limits = {
            'anonymous': {'requests': 100, 'window': 3600, 'burst': 20},    # 100/hour, 20/minute
            'authenticated': {'requests': 1000, 'window': 3600, 'burst': 50}, # 1000/hour, 50/minute  
            'premium': {'requests': 5000, 'window': 3600, 'burst': 100},    # 5000/hour, 100/minute
            'admin': {'requests': 10000, 'window': 3600, 'burst': 200},     # 10000/hour, 200/minute
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/ai/': {'requests': 50, 'window': 3600},   # AI endpoints are expensive
            '/api/auth/login/': {'requests': 10, 'window': 900}, # Login attempts
            '/api/upload/': {'requests': 20, 'window': 3600},    # File uploads
        }
    
    def __call__(self, request):
        # Check rate limits before processing request
        if not self._check_rate_limit(request):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': 60
            }, status=429)
        
        # Process request
        start_time = time.time()
        response = self.get_response(request)
        processing_time = time.time() - start_time
        
        # Add rate limit headers
        self._add_rate_limit_headers(request, response)
        
        # Log slow requests
        if processing_time > 1.0:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {processing_time:.3f}s from {self._get_client_ip(request)}"
            )
        
        return response
    
    def _check_rate_limit(self, request):
        """Check if request exceeds rate limits"""
        client_ip = self._get_client_ip(request)
        user_tier = self._get_user_tier(request)
        
        # Check general rate limit
        if not self._check_limit(client_ip, user_tier, 'general'):
            return False
        
        # Check burst rate limit (per minute)
        if not self._check_limit(client_ip, user_tier, 'burst', window=60):
            return False
        
        # Check endpoint-specific limits
        for endpoint, limits in self.endpoint_limits.items():
            if request.path.startswith(endpoint):
                if not self._check_limit(client_ip, f"endpoint:{endpoint}", 'custom', 
                                       requests=limits['requests'], window=limits['window']):
                    return False
        
        return True
    
    def _check_limit(self, client_id, tier, limit_type, requests=None, window=None):
        """Check specific rate limit"""
        if limit_type == 'custom':
            max_requests = requests
            time_window = window
        else:
            tier_config = self.rate_limits.get(tier, self.rate_limits['anonymous'])
            if limit_type == 'burst':
                max_requests = tier_config['burst']
                time_window = 60  # 1 minute
            else:
                max_requests = tier_config['requests']
                time_window = tier_config['window']
        
        # Redis-based sliding window counter
        cache_key = f"rate_limit:{client_id}:{tier}:{limit_type}"
        
        try:
            current_count = cache.get(cache_key, 0)
            
            if current_count >= max_requests:
                return False
            
            # Increment counter
            cache.set(cache_key, current_count + 1, time_window)
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Fail open
    
    def _get_user_tier(self, request):
        """Determine user's rate limit tier"""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return 'anonymous'
        
        if request.user.is_superuser:
            return 'admin'
        
        # Check for premium subscription (implement based on your user model)
        if hasattr(request.user, 'subscription') and request.user.subscription.is_premium:
            return 'premium'
        
        return 'authenticated'
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _add_rate_limit_headers(self, request, response):
        """Add rate limit headers to response"""
        user_tier = self._get_user_tier(request)
        tier_config = self.rate_limits.get(user_tier, self.rate_limits['anonymous'])
        
        response['X-RateLimit-Limit'] = str(tier_config['requests'])
        response['X-RateLimit-Window'] = str(tier_config['window'])
        
        # Add remaining requests (simplified)
        client_ip = self._get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}:{user_tier}:general"
        current_count = cache.get(cache_key, 0)
        remaining = max(0, tier_config['requests'] - current_count)
        
        response['X-RateLimit-Remaining'] = str(remaining)

class APIPerformanceMiddleware(MiddlewareMixin):
    """Monitor and optimize API performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_request_threshold = 1.0  # 1 second
        self.performance_cache = {}
    
    def __call__(self, request):
        start_time = time.time()
        
        # Add request start time for downstream middleware
        request._start_time = start_time
        
        response = self.get_response(request)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Add performance headers
        response['X-Response-Time'] = f"{processing_time:.3f}s"
        response['X-Timestamp'] = timezone.now().isoformat()
        
        # Log performance metrics
        self._log_performance(request, response, processing_time)
        
        # Store performance data for monitoring
        self._store_performance_data(request, processing_time)
        
        return response
    
    def _log_performance(self, request, response, processing_time):
        """Log performance metrics"""
        if processing_time > self.slow_request_threshold:
            logger.warning(
                f"Slow API request: {request.method} {request.path} "
                f"took {processing_time:.3f}s, status: {response.status_code}"
            )
        
        # Log to performance cache for analytics
        endpoint = self._normalize_endpoint(request.path)
        if endpoint not in self.performance_cache:
            self.performance_cache[endpoint] = []
        
        self.performance_cache[endpoint].append({
            'timestamp': timezone.now().isoformat(),
            'processing_time': processing_time,
            'status_code': response.status_code,
            'method': request.method
        })
        
        # Keep only last 1000 entries per endpoint
        if len(self.performance_cache[endpoint]) > 1000:
            self.performance_cache[endpoint] = self.performance_cache[endpoint][-1000:]
    
    def _store_performance_data(self, request, processing_time):
        """Store performance data in cache for monitoring dashboard"""
        endpoint = self._normalize_endpoint(request.path)
        cache_key = f"api_performance:{endpoint}"
        
        # Get existing data
        perf_data = cache.get(cache_key, {
            'total_requests': 0,
            'total_time': 0,
            'avg_time': 0,
            'max_time': 0,
            'min_time': float('inf'),
            'slow_requests': 0
        })
        
        # Update metrics
        perf_data['total_requests'] += 1
        perf_data['total_time'] += processing_time
        perf_data['avg_time'] = perf_data['total_time'] / perf_data['total_requests']
        perf_data['max_time'] = max(perf_data['max_time'], processing_time)
        perf_data['min_time'] = min(perf_data['min_time'], processing_time)
        
        if processing_time > self.slow_request_threshold:
            perf_data['slow_requests'] += 1
        
        # Store updated data
        cache.set(cache_key, perf_data, 3600)  # 1 hour
    
    def _normalize_endpoint(self, path):
        """Normalize endpoint path for grouping"""
        # Replace IDs and UUIDs with placeholders for better grouping
        import re
        
        # Replace numeric IDs
        path = re.sub(r'/\d+/', '/{id}/', path)
        
        # Replace UUIDs
        uuid_pattern = r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/'
        path = re.sub(uuid_pattern, '/{uuid}/', path, flags=re.IGNORECASE)
        
        return path
    
    def get_performance_stats(self):
        """Get performance statistics"""
        stats = {}
        
        for endpoint, requests in self.performance_cache.items():
            if requests:
                times = [r['processing_time'] for r in requests]
                stats[endpoint] = {
                    'total_requests': len(requests),
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times),
                    'slow_requests': len([t for t in times if t > self.slow_request_threshold]),
                    'success_rate': len([r for r in requests if 200 <= r['status_code'] < 300]) / len(requests) * 100
                }
        
        return stats

# Middleware stack for optimal performance
PERFORMANCE_MIDDLEWARE = [
    'core.performance.api_middleware.APIPerformanceMiddleware',
    'core.performance.api_middleware.AdvancedRateLimitMiddleware', 
    'core.performance.api_middleware.SmartCacheMiddleware',
    'core.performance.api_middleware.ResponseCompressionMiddleware',
]

# Export middleware classes
__all__ = [
    'ResponseCompressionMiddleware',
    'SmartCacheMiddleware', 
    'AdvancedRateLimitMiddleware',
    'APIPerformanceMiddleware',
    'PERFORMANCE_MIDDLEWARE'
]