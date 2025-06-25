"""
用户认证模型
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from core.models.base import BaseModel
from core.models.mixins import TimestampMixin


class UserProfile(BaseModel, TimestampMixin):
    """用户资料扩展模型"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='手机号'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='头像'
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name='个人简介'
    )
    
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='出生日期'
    )
    
    # 学习偏好
    learning_style = models.CharField(
        max_length=20,
        choices=[
            ('visual', '视觉型'),
            ('auditory', '听觉型'),
            ('kinesthetic', '动觉型'),
            ('reading', '阅读型'),
            ('mixed', '混合型'),
        ],
        default='mixed',
        verbose_name='学习风格'
    )
    
    timezone = models.CharField(
        max_length=50,
        default='Asia/Shanghai',
        verbose_name='时区'
    )
    
    # 通知设置
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='邮件通知'
    )
    
    # 隐私设置
    is_profile_public = models.BooleanField(
        default=False,
        verbose_name='公开个人资料'
    )
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'
        
    def __str__(self):
        return f"{self.user.username}的资料"


class EmailVerification(BaseModel, TimestampMixin):
    """邮箱验证模型"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name='用户'
    )
    
    email = models.EmailField(
        validators=[EmailValidator()],
        verbose_name='邮箱'
    )
    
    verification_code = models.CharField(
        max_length=6,
        verbose_name='验证码'
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name='是否已验证'
    )
    
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='验证时间'
    )
    
    expires_at = models.DateTimeField(
        verbose_name='过期时间'
    )
    
    class Meta:
        db_table = 'email_verifications'
        verbose_name = '邮箱验证'
        verbose_name_plural = '邮箱验证'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.email} - {self.verification_code}"
    
    @property
    def is_expired(self):
        """检查验证码是否过期"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
