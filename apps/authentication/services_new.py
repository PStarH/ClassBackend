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

from .models import User


class AuthenticationService:
    """用户认证服务类"""
    
    @staticmethod
    def create_user(email, username, password):
        """创建用户"""
        try:
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password
            )
            return {'success': True, 'user': user}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def authenticate_user(email, password):
        """验证用户"""
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                user.update_last_login()
                return {'success': True, 'user': user}
            return {'success': False, 'error': '密码错误'}
        except User.DoesNotExist:
            return {'success': False, 'error': '用户不存在'}
    
    @staticmethod
    def send_verification_email(user, verification_code):
        """发送验证邮件"""
        try:
            subject = f'{settings.SITE_NAME} - 邮箱验证'
            message = f'''
            您好 {user.username}，
            
            您的验证码是：{verification_code}
            
            请在15分钟内使用此验证码完成邮箱验证。
            
            如果您没有注册{settings.SITE_NAME}账户，请忽略此邮件。
            
            {settings.SITE_NAME} 团队
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False
    
    @staticmethod
    def generate_verification_code():
        """生成6位数字验证码"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def generate_reset_token():
        """生成密码重置令牌"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_password_strength(password):
        """验证密码强度"""
        if len(password) < 8:
            return {'valid': False, 'error': '密码至少需要8个字符'}
        
        if not any(c.isupper() for c in password):
            return {'valid': False, 'error': '密码需要包含至少一个大写字母'}
        
        if not any(c.islower() for c in password):
            return {'valid': False, 'error': '密码需要包含至少一个小写字母'}
        
        if not any(c.isdigit() for c in password):
            return {'valid': False, 'error': '密码需要包含至少一个数字'}
        
        return {'valid': True}
    
    @staticmethod
    def change_password(user, old_password, new_password):
        """修改密码"""
        if not user.check_password(old_password):
            return {'success': False, 'error': '原密码错误'}
        
        password_validation = AuthenticationService.validate_password_strength(new_password)
        if not password_validation['valid']:
            return {'success': False, 'error': password_validation['error']}
        
        user.set_password(new_password)
        user.save()
        return {'success': True}
    
    @staticmethod
    def deactivate_user(user):
        """停用用户账户"""
        user.is_active = False
        user.save()
    
    @staticmethod
    def activate_user(user):
        """激活用户账户"""
        user.is_active = True
        user.save()
