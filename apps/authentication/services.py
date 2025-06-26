"""
用户认证服务
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import string
import secrets

from .models import User, UserSession


class AuthenticationService:
    """用户认证服务类"""
    
    @staticmethod
    def create_user(email, username, password):
        """创建用户"""
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password
        )
        return user
    
    @staticmethod
    def authenticate_user(email, password):
        """验证用户登录"""
        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and user.is_active:
                return user
            return None
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def create_session(user, request):
        """创建用户会话"""
        # 生成安全的token
        token = secrets.token_urlsafe(32)
        
        # 获取客户端信息
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = AuthenticationService.get_client_ip(request)
        
        # 创建会话，有效期7天
        session = UserSession.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(days=7),
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # 更新用户最后登录时间
        user.update_last_login()
        
        return session
    
    @staticmethod
    def get_client_ip(request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def invalidate_session(session_id):
        """注销会话"""
        try:
            session = UserSession.objects.get(session_id=session_id, is_active=True)
            session.is_active = False
            session.save()
            return True
        except UserSession.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_from_token(token):
        """通过token获取用户"""
        try:
            session = UserSession.objects.get(
                token=token,
                is_active=True,
                expires_at__gt=timezone.now()
            )
            session.refresh_activity()
            return session.user
        except UserSession.DoesNotExist:
            return None
    
    @staticmethod
    def cleanup_expired_sessions():
        """清理过期会话"""
        expired_sessions = UserSession.objects.filter(
            expires_at__lt=timezone.now()
        )
        count = expired_sessions.count()
        expired_sessions.delete()
        return count
    
    @staticmethod
    def get_user_active_sessions(user):
        """获取用户的活跃会话"""
        return UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-created_at')


class UserService:
    """用户管理服务类"""
    
    @staticmethod
    def update_user_info(user, username=None, email=None):
        """更新用户信息"""
        if username:
            user.username = username
        if email:
            # 检查邮箱是否已被其他用户使用
            if User.objects.filter(email=email).exclude(uuid=user.uuid).exists():
                raise ValueError("该邮箱已被其他用户使用")
            user.email = email
        
        user.save()
        return user
    
    @staticmethod
    def change_password(user, old_password, new_password):
        """修改密码"""
        if not user.check_password(old_password):
            raise ValueError("当前密码错误")
        
        user.set_password(new_password)
        user.save()
        
        # 注销所有其他会话
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        return user
    
    @staticmethod
    def deactivate_user(user):
        """停用用户账户"""
        user.is_active = False
        user.save()
        
        # 注销所有会话
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        return user
    
    @staticmethod
    def get_user_stats(user):
        """获取用户统计信息"""
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        total_sessions = UserSession.objects.filter(user=user).count()
        
        return {
            'active_sessions': active_sessions,
            'total_sessions': total_sessions,
            'last_login': user.last_login,
            'created_at': user.created_at,
        }
