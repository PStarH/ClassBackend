"""
学习会话模型 - 仅保留核心的 StudySession 模型
"""
from django.db import models
from core.models.base import BaseModel
from core.models.mixins import TimestampMixin


class StudySession(BaseModel, TimestampMixin):
    """学习会话模型 - 符合数据库标准化要求的 study_sessions 表"""
    
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
            models.Index(fields=['is_active', 'start_time']),
            models.Index(fields=['goal_id', 'start_time']),
            models.Index(fields=['learning_plan_id', 'start_time']),
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
