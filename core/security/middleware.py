"""
数据加密中间件
"""
import json
import logging
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class DataEncryptionMiddleware(MiddlewareMixin):
    """数据加密中间件"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def _get_or_create_encryption_key(self):
        """获取或创建加密密钥"""
        key = cache.get('encryption_key')
        if not key:
            key = Fernet.generate_key()
            cache.set('encryption_key', key, 86400 * 30)  # 30天过期
        return key
    
    def process_request(self, request):
        """处理请求，解密敏感数据"""
        if request.content_type == 'application/json' and hasattr(request, 'body'):
            try:
                data = json.loads(request.body.decode('utf-8'))
                decrypted_data = self._decrypt_sensitive_fields(data)
                
                # 重新设置request.body
                request._body = json.dumps(decrypted_data).encode('utf-8')
                
            except Exception as e:
                logger.error(f"Request decryption error: {str(e)}")
        
        return None
    
    def process_response(self, request, response):
        """处理响应，加密敏感数据"""
        if (response.get('Content-Type', '').startswith('application/json') and 
            hasattr(response, 'content')):
            try:
                data = json.loads(response.content.decode('utf-8'))
                encrypted_data = self._encrypt_sensitive_fields(data)
                
                response.content = json.dumps(encrypted_data).encode('utf-8')
                response['Content-Length'] = str(len(response.content))
                
            except Exception as e:
                logger.error(f"Response encryption error: {str(e)}")
        
        return response
    
    def _encrypt_sensitive_fields(self, data):
        """加密敏感字段"""
        if isinstance(data, dict):
            sensitive_fields = ['password', 'phone', 'id_card', 'api_key']
            for field in sensitive_fields:
                if field in data and data[field]:
                    try:
                        encrypted_value = self.cipher_suite.encrypt(
                            str(data[field]).encode('utf-8')
                        )
                        data[field] = encrypted_value.decode('utf-8')
                    except Exception as e:
                        logger.error(f"Field encryption error for {field}: {str(e)}")
            
            # 递归处理嵌套字典
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = self._encrypt_sensitive_fields(value)
                    
        elif isinstance(data, list):
            return [self._encrypt_sensitive_fields(item) for item in data]
        
        return data
    
    def _decrypt_sensitive_fields(self, data):
        """解密敏感字段"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['password', 'phone', 'id_card', 'api_key'] and value:
                    try:
                        decrypted_value = self.cipher_suite.decrypt(
                            value.encode('utf-8')
                        )
                        data[key] = decrypted_value.decode('utf-8')
                    except Exception as e:
                        logger.error(f"Field decryption error for {key}: {str(e)}")
                elif isinstance(value, (dict, list)):
                    data[key] = self._decrypt_sensitive_fields(value)
                    
        elif isinstance(data, list):
            return [self._decrypt_sensitive_fields(item) for item in data]
        
        return data


class SecurityHeadersMiddleware(MiddlewareMixin):
    """安全头中间件"""
    
    def process_response(self, request, response):
        """添加安全响应头"""
        # 防止点击劫持
        response['X-Frame-Options'] = 'DENY'
        
        # 防止MIME类型嗅探
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS保护
        response['X-XSS-Protection'] = '1; mode=block'
        
        # 内容安全策略
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # 严格传输安全
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # 引用者策略
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 权限策略
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "fullscreen=(self)"
        )
        
        return response


class AuditLogMiddleware(MiddlewareMixin):
    """审计日志中间件"""
    
    def process_request(self, request):
        """记录请求审计日志"""
        # 记录敏感操作
        sensitive_paths = [
            '/auth/login/', '/auth/logout/', '/auth/register/',
            '/auth/password/change/', '/auth/settings/'
        ]
        
        if any(request.path.startswith(path) for path in sensitive_paths):
            self._log_security_event(request, 'REQUEST')
        
        return None
    
    def process_response(self, request, response):
        """记录响应审计日志"""
        # 记录失败的认证尝试
        if (request.path.startswith('/auth/') and 
            response.status_code in [401, 403]):
            self._log_security_event(request, 'AUTH_FAILURE', response.status_code)
        
        return response
    
    def _log_security_event(self, request, event_type, status_code=None):
        """记录安全事件"""
        user_id = getattr(request.user, 'uuid', 'anonymous')
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        log_data = {
            'event_type': event_type,
            'user_id': str(user_id),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'path': request.path,
            'method': request.method,
            'timestamp': cache.get('current_timestamp', ''),
            'status_code': status_code,
        }
        
        # 记录到专门的安全日志
        security_logger = logging.getLogger('security')
        security_logger.info(f"Security Event: {json.dumps(log_data)}")
        
        # 同时存储到缓存中用于实时监控
        cache_key = f"security_events:{ip_address}"
        events = cache.get(cache_key, [])
        events.append(log_data)
        
        # 只保留最近100个事件
        events = events[-100:]
        cache.set(cache_key, events, 3600)  # 1小时过期
    
    def _get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
