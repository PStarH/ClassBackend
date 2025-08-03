"""
增强的JWT认证系统
支持访问token/刷新token、自动续期、设备管理等功能
基于建议的最佳实践实现
"""
import jwt
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from decouple import config

logger = logging.getLogger(__name__)

User = get_user_model()

# JWT配置
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=settings.SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_LIFETIME = config('JWT_ACCESS_TOKEN_LIFETIME', default=900, cast=int)  # 15分钟
JWT_REFRESH_TOKEN_LIFETIME = config('JWT_REFRESH_TOKEN_LIFETIME', default=604800, cast=int)  # 7天
JWT_BLACKLIST_CACHE_TTL = config('JWT_BLACKLIST_CACHE_TTL', default=86400, cast=int)  # 24小时


class JWTError(AuthenticationFailed):
    """JWT相关错误"""
    pass


class TokenExpiredError(JWTError):
    """Token过期错误"""
    pass


class TokenBlacklistedError(JWTError):
    """Token已被列入黑名单错误"""
    pass


class DeviceManager:
    """设备管理器 - 管理用户设备和会话"""
    
    @staticmethod
    def generate_device_id(request) -> str:
        """生成设备ID"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = DeviceManager.get_client_ip(request)
        
        # 简单的设备指纹
        import hashlib
        device_string = f"{user_agent}:{ip_address}"
        device_id = hashlib.md5(device_string.encode()).hexdigest()[:16]
        
        return device_id
    
    @staticmethod
    def get_client_ip(request) -> str:
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    @staticmethod
    def register_device(user_id: int, device_id: str, request) -> Dict[str, Any]:
        """注册设备"""
        device_info = {
            'device_id': device_id,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'ip_address': DeviceManager.get_client_ip(request),
            'last_seen': timezone.now().isoformat(),
            'is_active': True
        }
        
        # 存储到缓存
        cache_key = f"device:{user_id}:{device_id}"
        cache.set(cache_key, device_info, 86400 * 30)  # 30天
        
        return device_info
    
    @staticmethod
    def is_device_trusted(user_id: int, device_id: str) -> bool:
        """检查设备是否受信任"""
        cache_key = f"device:{user_id}:{device_id}"
        device_info = cache.get(cache_key)
        
        return device_info is not None and device_info.get('is_active', False)
    
    @staticmethod
    def revoke_device(user_id: int, device_id: str) -> bool:
        """撤销设备"""
        cache_key = f"device:{user_id}:{device_id}"
        device_info = cache.get(cache_key)
        
        if device_info:
            device_info['is_active'] = False
            cache.set(cache_key, device_info, 86400 * 30)
            return True
        return False


class JWTTokenManager:
    """JWT Token管理器"""
    
    @staticmethod
    def generate_tokens(user, request) -> Tuple[str, str]:
        """生成访问token和刷新token"""
        now = timezone.now()
        device_id = DeviceManager.generate_device_id(request)
        jti = str(uuid.uuid4())  # JWT ID，用于黑名单
        
        # 注册设备
        DeviceManager.register_device(user.id, device_id, request)
        
        # 访问token payload
        access_payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'device_id': device_id,
            'jti': jti,
            'token_type': 'access',
            'iat': now,
            'exp': now + timedelta(seconds=JWT_ACCESS_TOKEN_LIFETIME),
        }
        
        # 刷新token payload
        refresh_jti = str(uuid.uuid4())
        refresh_payload = {
            'user_id': user.id,
            'device_id': device_id,
            'jti': refresh_jti,
            'token_type': 'refresh',
            'iat': now,
            'exp': now + timedelta(seconds=JWT_REFRESH_TOKEN_LIFETIME),
        }
        
        # 生成tokens
        access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # 缓存刷新token映射
        cache_key = f"refresh_token:{refresh_jti}"
        cache.set(cache_key, {
            'user_id': user.id,
            'device_id': device_id,
            'access_jti': jti,
            'created_at': now.isoformat()
        }, JWT_REFRESH_TOKEN_LIFETIME)
        
        logger.info(f"Generated tokens for user {user.id}, device {device_id}")
        
        return access_token, refresh_token
    
    @staticmethod
    def decode_token(token: str, verify_exp: bool = True) -> Dict[str, Any]:
        """解码token"""
        try:
            options = {'verify_exp': verify_exp}
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options=options)
            return payload
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise JWTError(f"Invalid token: {str(e)}")
    
    @staticmethod
    def is_token_blacklisted(jti: str) -> bool:
        """检查token是否在黑名单中"""
        blacklist_key = f"blacklist_token:{jti}"
        return cache.get(blacklist_key) is not None
    
    @staticmethod
    def blacklist_token(jti: str, exp_time: datetime = None):
        """将token加入黑名单"""
        blacklist_key = f"blacklist_token:{jti}"
        
        # 计算TTL - 只需要缓存到token过期时间
        if exp_time:
            ttl = max(int((exp_time - timezone.now()).total_seconds()), 0)
        else:
            ttl = JWT_BLACKLIST_CACHE_TTL
        
        cache.set(blacklist_key, True, ttl)
        logger.info(f"Blacklisted token {jti}")
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> str:
        """使用刷新token生成新的访问token"""
        try:
            payload = JWTTokenManager.decode_token(refresh_token)
            
            if payload.get('token_type') != 'refresh':
                raise JWTError("Invalid refresh token")
            
            jti = payload.get('jti')
            user_id = payload.get('user_id')
            device_id = payload.get('device_id')
            
            # 检查刷新token是否有效
            cache_key = f"refresh_token:{jti}"
            token_data = cache.get(cache_key)
            
            if not token_data:
                raise JWTError("Refresh token not found or expired")
            
            # 检查设备是否受信任
            if not DeviceManager.is_device_trusted(user_id, device_id):
                raise JWTError("Device not trusted")
            
            # 获取用户
            try:
                user = User.objects.get(id=user_id, is_active=True)
            except User.DoesNotExist:
                raise JWTError("User not found or inactive")
            
            # 生成新的访问token
            now = timezone.now()
            new_jti = str(uuid.uuid4())
            
            access_payload = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'device_id': device_id,
                'jti': new_jti,
                'token_type': 'access',
                'iat': now,
                'exp': now + timedelta(seconds=JWT_ACCESS_TOKEN_LIFETIME),
            }
            
            # 将旧的访问token加入黑名单
            old_access_jti = token_data.get('access_jti')
            if old_access_jti:
                JWTTokenManager.blacklist_token(old_access_jti)
            
            # 更新刷新token映射
            token_data['access_jti'] = new_jti
            cache.set(cache_key, token_data, JWT_REFRESH_TOKEN_LIFETIME)
            
            new_access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
            
            logger.info(f"Refreshed access token for user {user_id}")
            return new_access_token
            
        except JWTError:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise JWTError(f"Token refresh failed: {str(e)}")
    
    @staticmethod
    def logout_user(access_token: str, refresh_token: Optional[str] = None):
        """用户登出 - 将tokens加入黑名单"""
        try:
            # 处理访问token
            access_payload = JWTTokenManager.decode_token(access_token, verify_exp=False)
            access_jti = access_payload.get('jti')
            access_exp = datetime.fromtimestamp(access_payload.get('exp'), tz=timezone.utc)
            
            if access_jti:
                JWTTokenManager.blacklist_token(access_jti, access_exp)
            
            # 处理刷新token
            if refresh_token:
                refresh_payload = JWTTokenManager.decode_token(refresh_token, verify_exp=False)
                refresh_jti = refresh_payload.get('jti')
                refresh_exp = datetime.fromtimestamp(refresh_payload.get('exp'), tz=timezone.utc)
                
                if refresh_jti:
                    JWTTokenManager.blacklist_token(refresh_jti, refresh_exp)
                    
                    # 删除刷新token映射
                    cache_key = f"refresh_token:{refresh_jti}"
                    cache.delete(cache_key)
            
            logger.info(f"User logged out, tokens blacklisted")
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise JWTError(f"Logout failed: {str(e)}")
    
    @staticmethod
    def logout_all_devices(user_id: int):
        """登出所有设备"""
        try:
            # 这里需要一个更复杂的实现来找到用户的所有活跃token
            # 简化版本：标记用户需要重新认证
            cache_key = f"user_token_version:{user_id}"
            current_version = cache.get(cache_key, 0)
            cache.set(cache_key, current_version + 1, 86400 * 30)  # 30天
            
            logger.info(f"All devices logged out for user {user_id}")
            
        except Exception as e:
            logger.error(f"Logout all devices failed: {e}")


class EnhancedJWTAuthentication(BaseAuthentication):
    """增强的JWT认证类"""
    
    def authenticate(self, request):
        """认证请求"""
        token = self.get_token_from_request(request)
        
        if not token:
            return None
        
        try:
            payload = JWTTokenManager.decode_token(token)
            
            # 检查token类型
            if payload.get('token_type') != 'access':
                raise JWTError("Invalid token type")
            
            # 检查是否在黑名单中
            jti = payload.get('jti')
            if jti and JWTTokenManager.is_token_blacklisted(jti):
                raise TokenBlacklistedError("Token has been blacklisted")
            
            # 获取用户
            user_id = payload.get('user_id')
            try:
                user = User.objects.get(id=user_id, is_active=True)
            except User.DoesNotExist:
                raise JWTError("User not found or inactive")
            
            # 检查设备
            device_id = payload.get('device_id')
            if device_id and not DeviceManager.is_device_trusted(user_id, device_id):
                raise JWTError("Device not trusted")
            
            # 检查用户token版本（用于全设备登出）
            cache_key = f"user_token_version:{user_id}"
            current_version = cache.get(cache_key, 0)
            token_version = payload.get('version', 0)
            
            if token_version < current_version:
                raise JWTError("Token has been invalidated")
            
            # 更新最后活跃时间
            self.update_last_activity(user, request)
            
            return (user, payload)
            
        except JWTError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise AuthenticationFailed(f"Authentication failed: {str(e)}")
    
    def get_token_from_request(self, request) -> Optional[str]:
        """从请求中获取token"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # 也可以从cookie中获取
        return request.COOKIES.get('access_token')
    
    def update_last_activity(self, user, request):
        """更新用户最后活跃时间"""
        try:
            cache_key = f"user_activity:{user.id}"
            activity_data = {
                'last_activity': timezone.now().isoformat(),
                'ip_address': DeviceManager.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
            }
            cache.set(cache_key, activity_data, 3600)  # 1小时
        except Exception as e:
            logger.error(f"Failed to update user activity: {e}")
    
    def authenticate_header(self, request):
        """返回认证头格式"""
        return 'Bearer'


class JWTTokenRefreshMiddleware:
    """JWT Token自动刷新中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # 检查是否需要刷新token
        if hasattr(request, 'user') and request.user.is_authenticated:
            self.maybe_refresh_token(request, response)
        
        return response
    
    def maybe_refresh_token(self, request, response):
        """检查并刷新token"""
        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not auth_header.startswith('Bearer '):
                return
            
            token = auth_header[7:]
            payload = JWTTokenManager.decode_token(token, verify_exp=False)
            
            # 检查token是否即将过期（剩余时间少于5分钟）
            exp_time = datetime.fromtimestamp(payload.get('exp'), tz=timezone.utc)
            time_left = exp_time - timezone.now()
            
            if time_left.total_seconds() < 300:  # 5分钟
                refresh_token = request.COOKIES.get('refresh_token')
                if refresh_token:
                    try:
                        new_access_token = JWTTokenManager.refresh_access_token(refresh_token)
                        
                        # 在响应头中返回新token
                        response['X-New-Access-Token'] = new_access_token
                        
                        logger.info(f"Auto-refreshed token for user {request.user.id}")
                        
                    except JWTError as e:
                        logger.warning(f"Auto-refresh failed: {e}")
        
        except Exception as e:
            logger.error(f"Token refresh middleware error: {e}")


# 导出主要组件
__all__ = [
    'EnhancedJWTAuthentication',
    'JWTTokenManager',
    'DeviceManager',
    'JWTTokenRefreshMiddleware',
    'JWTError',
    'TokenExpiredError',
    'TokenBlacklistedError',
]