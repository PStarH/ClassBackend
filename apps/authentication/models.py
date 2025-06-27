"""
用户认证模型
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import EmailValidator
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.postgres.fields import ArrayField
from core.security.mixins import AuditMixin, SoftDeleteMixin, RowLevelSecurityMixin
from core.security.validators import DataSecurityValidator
import secrets
import hashlib
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, email, username, password=None, **extra_fields):
        """创建普通用户"""
        if not email:
            raise ValueError('用户必须有邮箱地址')
        if not username:
            raise ValueError('用户必须有用户名')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, AuditMixin, SoftDeleteMixin, RowLevelSecurityMixin):
    """自定义用户模型 - 增强安全性"""
    
    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='用户UUID'
    )
    
    email = models.EmailField(
        unique=True,
        max_length=255,
        validators=[EmailValidator()],
        verbose_name='邮箱地址'
    )
    
    username = models.CharField(
        max_length=100,
        verbose_name='用户名'
    )
    
    password = models.CharField(
        max_length=255,
        verbose_name='密码'
    )
    
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最近登录时间'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='注册时间'
    )
    
    # Django权限系统必需字段
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # 安全增强字段
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='失败登录次数'
    )
    
    last_failed_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='最后失败登录时间'
    )
    
    account_locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='账户锁定至'
    )
    
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='密码修改时间'
    )
    
    two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name='是否启用双因素认证'
    )
    
    two_factor_secret = models.CharField(
        max_length=32,
        blank=True,
        verbose_name='双因素认证密钥'
    )
    
    # 安全验证字段
    email_verified = models.BooleanField(
        default=False,
        verbose_name='邮箱是否验证'
    )
    
    email_verification_token = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='邮箱验证令牌'
    )
    
    phone_verified = models.BooleanField(
        default=False,
        verbose_name='手机是否验证'
    )
    
    # 隐私设置
    profile_visibility = models.CharField(
        max_length=20,
        choices=[
            ('public', '公开'),
            ('private', '私有'),
            ('friends', '仅好友'),
        ],
        default='private',
        verbose_name='个人资料可见性'
    )
    
    data_processing_consent = models.BooleanField(
        default=False,
        verbose_name='数据处理同意'
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        
    def __str__(self):
        return self.email
    
    def clean(self):
        """数据验证"""
        super().clean()
        
        # 验证邮箱格式
        if self.email:
            self.email = DataSecurityValidator.validate_email_format(self.email)
        
        # 验证用户名
        if self.username:
            DataSecurityValidator.validate_user_input(self.username, max_length=150)
    
    def set_password(self, raw_password):
        """设置密码并记录修改时间"""
        # 验证密码强度
        DataSecurityValidator.validate_password_strength(raw_password)
        
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()
        self.failed_login_attempts = 0  # 重置失败次数
        self.account_locked_until = None  # 解锁账户
    
    def record_failed_login(self):
        """记录失败登录"""
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        
        # 超过5次失败登录，锁定账户30分钟
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=30)
        
        self.save(update_fields=['failed_login_attempts', 'last_failed_login', 'account_locked_until'])
    
    def is_account_locked(self):
        """检查账户是否被锁定"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def unlock_account(self):
        """解锁账户"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save(update_fields=['failed_login_attempts', 'account_locked_until'])
    
    def generate_email_verification_token(self):
        """生成邮箱验证令牌"""
        self.email_verification_token = DataSecurityValidator.generate_secure_token()
        self.save(update_fields=['email_verification_token'])
        return self.email_verification_token
    
    def verify_email(self, token):
        """验证邮箱"""
        if self.email_verification_token == token:
            self.email_verified = True
            self.email_verification_token = ''
            self.save(update_fields=['email_verified', 'email_verification_token'])
            return True
        return False
    
    def enable_two_factor(self):
        """启用双因素认证"""
        if not self.two_factor_secret:
            self.two_factor_secret = DataSecurityValidator.generate_secure_token(16)
        self.two_factor_enabled = True
        self.save(update_fields=['two_factor_enabled', 'two_factor_secret'])
        return self.two_factor_secret
    
    def disable_two_factor(self):
        """禁用双因素认证"""
        self.two_factor_enabled = False
        self.two_factor_secret = ''
        self.save(update_fields=['two_factor_enabled', 'two_factor_secret'])
    
    def get_security_summary(self):
        """获取安全摘要"""
        return {
            'email_verified': self.email_verified,
            'phone_verified': self.phone_verified,
            'two_factor_enabled': self.two_factor_enabled,
            'account_locked': self.is_account_locked(),
            'password_age_days': (timezone.now() - (self.password_changed_at or self.date_joined)).days,
            'failed_login_attempts': self.failed_login_attempts,
            'last_login_ago': (timezone.now() - self.last_login).days if self.last_login else None,
        }
    
    def should_force_password_change(self):
        """检查是否应该强制修改密码"""
        if not self.password_changed_at:
            return True  # 从未修改过密码
        
        # 密码超过90天需要修改
        password_age = timezone.now() - self.password_changed_at
        return password_age > timedelta(days=90)


class UserSettings(models.Model):
    """用户设置模型 - 存储用户的学习偏好和设置"""
    
    # 学习节奏选择 - 按照规范调整
    PACE_CHOICES = [
        ('Very Detailed', '非常详细'),
        ('Detailed', '详细'),
        ('Moderate', '适中'),
        ('Fast', '快速'),
        ('Ultra Fast', '超快'),
    ]
    
    # 学习风格选择 - 按照规范调整
    STYLE_CHOICES = [
        ('Visual', '视觉型'),
        ('Text', '文本型'),
        ('Practical', '实践型'),
    ]
    
    # 语调风格选择
    TONE_CHOICES = [
        ('friendly', '友好'),
        ('professional', '专业'),
        ('encouraging', '鼓励'),
        ('casual', '随意'),
        ('formal', '正式'),
    ]
    
    # 反馈频率选择
    FEEDBACK_CHOICES = [
        ('immediate', '即时反馈'),
        ('lesson_end', '课程结束'),
        ('daily', '每日'),
        ('weekly', '每周'),
        ('monthly', '每月'),
    ]
    
    # 教育水平选择
    EDUCATION_CHOICES = [
        ('high_school', '高中'),
        ('undergraduate', '本科'),
        ('graduate', '研究生'),
        ('phd', '博士'),
        ('professional', '职业培训'),
        ('other', '其他'),
    ]
    
    user_uuid = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='settings',
        verbose_name='用户'
    )
    
    preferred_pace = models.CharField(
        max_length=20,
        choices=PACE_CHOICES,
        default='Moderate',
        verbose_name='偏好学习节奏'
    )
    
    preferred_style = models.CharField(
        max_length=20,
        choices=STYLE_CHOICES,
        default='Practical',
        verbose_name='偏好学习风格'
    )
    
    tone = models.CharField(
        max_length=20,
        choices=TONE_CHOICES,
        default='friendly',
        verbose_name='语调风格'
    )
    
    feedback_frequency = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        default='lesson_end',
        verbose_name='反馈频率'
    )
    
    major = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='专业'
    )
    
    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_CHOICES,
        blank=True,
        verbose_name='教育水平'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='备注'
    )
    
    # 技能列表 - 使用PostgreSQL ArrayField存储字符串数组
    skills = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name='技能列表',
        help_text='用户掌握的技能列表，字符串数组格式'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        db_table = 'user_settings'
        verbose_name = '用户设置'
        verbose_name_plural = '用户设置'
        indexes = [
            models.Index(fields=['updated_at']),  # 查询最近更新的设置
            models.Index(fields=['preferred_pace']),  # 按学习节奏分析
            models.Index(fields=['preferred_style']),  # 按学习风格分析
            models.Index(fields=['education_level']),  # 按教育水平分析
        ]
        constraints = [
            # 确保技能数组不超过合理数量
            models.CheckConstraint(
                check=models.Q(skills__len__lte=50),
                name='user_settings_skills_max_count'
            ),
        ]
    
    def __str__(self):
        return f"{self.user_uuid.email} - 用户设置"
    
    def add_skill(self, skill):
        """添加技能"""
        if skill and skill not in self.skills:
            self.skills.append(skill)
            self.save(update_fields=['skills'])
    
    def remove_skill(self, skill):
        """移除技能"""
        if skill in self.skills:
            self.skills.remove(skill)
            self.save(update_fields=['skills'])
    
    def get_skills_display(self):
        """获取技能显示字符串"""
        return ', '.join(self.skills) if self.skills else '暂无技能'


class UserSession(models.Model, AuditMixin):
    """用户会话模型 - 增强安全性"""
    
    # ...existing fields...
    
    # 安全增强字段
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP地址'
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name='用户代理'
    )
    
    device_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='设备指纹'
    )
    
    location_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='位置信息'
    )
    
    is_suspicious = models.BooleanField(
        default=False,
        verbose_name='是否可疑'
    )
    
    security_flags = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='安全标记'
    )
    
    # ...existing code...
    
    def mark_as_suspicious(self, reason):
        """标记为可疑会话"""
        self.is_suspicious = True
        self.security_flags['suspicious_reason'] = reason
        self.security_flags['flagged_at'] = timezone.now().isoformat()
        self.save(update_fields=['is_suspicious', 'security_flags'])
    
    def check_security_anomalies(self, request):
        """检查安全异常"""
        anomalies = []
        
        # 检查IP地址变化
        if self.ip_address and self.ip_address != self._get_client_ip(request):
            anomalies.append('IP地址变化')
        
        # 检查用户代理变化
        current_user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self.user_agent and self.user_agent != current_user_agent:
            anomalies.append('用户代理变化')
        
        # 检查会话时长
        if self.created_at:
            session_duration = timezone.now() - self.created_at
            if session_duration > timedelta(hours=24):
                anomalies.append('会话时长过长')
        
        if anomalies:
            self.mark_as_suspicious(', '.join(anomalies))
        
        return anomalies
    
    def _get_client_ip(self, request):
        """获取客户端IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    # ...existing code...
