"""
学习会话模型 - 仅保留核心的 StudySession 模型
"""
from django.db import models
from django.conf import settings
from core.models.base import BaseModel
from core.models.mixins import TimestampMixin


class StudySession(BaseModel, TimestampMixin):
    """学习会话模型 - 符合数据库标准化要求的 study_sessions 表"""
    
    # 用户外键关联 - 必需字段，确保数据完整性
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='study_sessions',
        verbose_name='用户',
        help_text='学习会话所属用户'
    )
    
    start_time = models.DateTimeField(verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name='学习时长(分钟)'
    )
    content_covered = models.TextField(blank=True, verbose_name='学习内容')
    effectiveness_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, '很差'), (2, '较差'), (3, '一般'), (4, '良好'), (5, '优秀')],
        verbose_name='学习效果评分(1-5)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='当前是否在进行中'
    )
    notes = models.TextField(blank=True, verbose_name='学习笔记')
    
    # 可选的外键关联，用于扩展功能（暂时保留为可空）
    goal_id = models.UUIDField(null=True, blank=True, verbose_name='学习目标ID')
    learning_plan_id = models.UUIDField(null=True, blank=True, verbose_name='学习计划ID')
    
    class Meta:
        db_table = 'study_sessions'
        verbose_name = '学习会话'
        verbose_name_plural = '学习会话'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),  # 用户查询学习记录
            models.Index(fields=['user', 'is_active']),   # 查询用户活跃会话
            models.Index(fields=['is_active', 'start_time']),  # 查询所有活跃会话
            models.Index(fields=['goal_id', 'start_time']),    # 按目标查询
            models.Index(fields=['learning_plan_id', 'start_time']),  # 按计划查询
            models.Index(fields=['start_time']),  # 时间范围查询
        ]
        constraints = [
            # 确保结束时间晚于开始时间
            models.CheckConstraint(
                check=models.Q(end_time__isnull=True) | models.Q(end_time__gt=models.F('start_time')),
                name='study_sessions_end_time_after_start'
            ),
            # 确保效果评分在有效范围内
            models.CheckConstraint(
                check=models.Q(effectiveness_rating__isnull=True) | 
                      models.Q(effectiveness_rating__gte=1, effectiveness_rating__lte=5),
                name='study_sessions_effectiveness_rating_range'
            ),
            # 确保持续时间非负
            models.CheckConstraint(
                check=models.Q(duration_minutes__gte=0),
                name='study_sessions_duration_non_negative'
            ),
        ]
    
    def __str__(self):
        return f"学习会话 - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """重写保存方法，自动计算持续时间"""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            self.duration_minutes = int(duration.total_seconds() / 60)
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """判断学习会话是否已完成"""
        return self.end_time is not None
    
    @property
    def duration_display(self):
        """友好显示学习时长"""
        if self.duration_minutes == 0:
            return "0分钟"
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours > 0:
            return f"{hours}小时{minutes}分钟" if minutes > 0 else f"{hours}小时"
        return f"{minutes}分钟"
    
    def complete_session(self, end_time=None, effectiveness_rating=None, notes=""):
        """完成学习会话"""
        from django.utils import timezone
        
        if not end_time:
            end_time = timezone.now()
        
        self.end_time = end_time
        self.is_active = False
        
        if effectiveness_rating:
            self.effectiveness_rating = effectiveness_rating
        if notes:
            self.notes = notes
            
        self.save()
        return self
