"""
数据安全验证器
"""
import re
import hashlib
import secrets
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.conf import settings


class DataSecurityValidator:
    """数据安全验证器"""
    
    @staticmethod
    def validate_email_format(email):
        """验证邮箱格式"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(_('邮箱格式不正确'))
        return email.lower()
    
    @staticmethod
    def validate_password_strength(password):
        """验证密码强度"""
        if len(password) < 8:
            raise ValidationError(_('密码长度至少8位'))
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('密码必须包含至少一个大写字母'))
        
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('密码必须包含至少一个小写字母'))
        
        if not re.search(r'\d', password):
            raise ValidationError(_('密码必须包含至少一个数字'))
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_('密码必须包含至少一个特殊字符'))
        
        # 检查常见弱密码
        common_passwords = [
            'password', '123456', 'qwerty', 'abc123', 
            'password123', '12345678', 'admin', 'root'
        ]
        if password.lower() in common_passwords:
            raise ValidationError(_('密码不能使用常见弱密码'))
        
        return password
    
    @staticmethod
    def validate_user_input(data, max_length=1000):
        """验证用户输入，防止XSS和SQL注入"""
        if not isinstance(data, str):
            return data
        
        # 长度限制
        if len(data) > max_length:
            raise ValidationError(_(f'输入长度不能超过{max_length}个字符'))
        
        # 基本XSS防护
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'javascript:',
            r'on\w+\s*=',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, data, re.IGNORECASE | re.DOTALL):
                raise ValidationError(_('输入包含不安全的内容'))
        
        return data
    
    @staticmethod
    def validate_file_upload(file):
        """验证文件上传安全性"""
        if not file:
            return None
        
        # 文件大小限制 (10MB)
        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            raise ValidationError(_('文件大小不能超过10MB'))
        
        # 允许的文件类型
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'application/json',
            'application/vnd.ms-excel', 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        
        if file.content_type not in allowed_types:
            raise ValidationError(_('不支持的文件类型'))
        
        # 文件名安全检查
        filename = file.name
        if not filename:
            raise ValidationError(_('文件名不能为空'))
        
        # 检查危险的文件扩展名
        dangerous_extensions = [
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', 
            '.js', '.jar', '.php', '.asp', '.aspx', '.sh'
        ]
        
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if f'.{file_ext}' in dangerous_extensions:
            raise ValidationError(_('不允许上传此类型的文件'))
        
        return file
    
    @staticmethod
    def generate_secure_token(length=32):
        """生成安全的随机令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_sensitive_data(data):
        """对敏感数据进行哈希处理"""
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
    
    @staticmethod
    def validate_api_key(api_key):
        """验证API密钥格式"""
        if not api_key:
            raise ValidationError(_('API密钥不能为空'))
        
        if len(api_key) < 32:
            raise ValidationError(_('API密钥长度不足'))
        
        # 检查是否只包含安全字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', api_key):
            raise ValidationError(_('API密钥包含无效字符'))
        
        return api_key


class RateLimitValidator:
    """速率限制验证器"""
    
    @staticmethod
    def validate_request_frequency(user_id, action, max_requests=5, window_seconds=60):
        """验证请求频率"""
        from django.core.cache import cache
        
        cache_key = f"rate_limit:{user_id}:{action}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= max_requests:
            raise ValidationError(_(f'操作过于频繁，请{window_seconds}秒后再试'))
        
        cache.set(cache_key, current_count + 1, window_seconds)
        return True


class DataPrivacyValidator:
    """数据隐私验证器"""
    
    SENSITIVE_FIELDS = ['password', 'phone', 'id_card', 'credit_card']
    
    @staticmethod
    def mask_sensitive_data(data, field_name):
        """对敏感数据进行脱敏处理"""
        if not data or field_name not in DataPrivacyValidator.SENSITIVE_FIELDS:
            return data
        
        if field_name == 'password':
            return '******'
        elif field_name == 'phone':
            return f"{data[:3]}****{data[-4:]}" if len(data) >= 7 else '****'
        elif field_name == 'email':
            parts = data.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = f"{username[:2]}****{username[-1:]}" if len(username) > 3 else '****'
                return f"{masked_username}@{domain}"
        
        return '****'
    
    @staticmethod
    def validate_personal_info_access(user, target_user_id):
        """验证个人信息访问权限"""
        if not user.is_authenticated:
            raise ValidationError(_('用户未认证'))
        
        if str(user.uuid) != str(target_user_id) and not user.is_staff:
            raise ValidationError(_('无权限访问其他用户的个人信息'))
        
        return True
