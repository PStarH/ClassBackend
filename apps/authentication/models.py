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


class User(AbstractBaseUser, PermissionsMixin):
    """自定义用户模型"""
    
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
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'
        
    def __str__(self):
        return self.email
    
    def set_password(self, raw_password):
        """设置密码"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """验证密码"""
        return check_password(raw_password, self.password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class UserSession(models.Model):
    """用户会话模型 - 用于管理用户登录会话"""
    
    session_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='访问令牌'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    
    # 设备信息
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = '用户会话'
        verbose_name_plural = '用户会话'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.session_id}"
    
    @property
    def is_expired(self):
        """检查会话是否过期"""
        return timezone.now() > self.expires_at
    
    def refresh_activity(self):
        """刷新活动时间"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


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
