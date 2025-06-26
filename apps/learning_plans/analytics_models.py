"""
学习分析模型 - 用于深度分析学习行为和效果
"""
from django.db import models
from django.conf import settings
from core.models.base import BaseModel
from core.models.mixins import TimestampMixin


class LearningAnalytics(BaseModel, TimestampMixin):
    """学习分析数据模型"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_analytics',
        verbose_name='用户'
    )
    
    # 时间维度
    analysis_date = models.DateField(verbose_name='分析日期')
    week_of_year = models.PositiveSmallIntegerField(verbose_name='年度第几周')
    month = models.PositiveSmallIntegerField(verbose_name='月份')
    
    # 学习统计
    total_study_time = models.PositiveIntegerField(
        default=0,
        verbose_name='总学习时间(分钟)'
    )
    session_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='学习会话数量'
    )
    average_session_duration = models.FloatField(
        default=0.0,
        verbose_name='平均会话时长(分钟)'
    )
    
    # 效果统计
    average_effectiveness = models.FloatField(
        default=0.0,
        verbose_name='平均学习效果评分'
    )
    productive_sessions_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='高效学习会话数量'
    )
    productivity_rate = models.FloatField(
        default=0.0,
        verbose_name='学习效率比率'
    )
    
    # 学习模式
    most_productive_hour = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='最高效学习时段'
    )
    preferred_environment = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='偏好学习环境'
    )
    preferred_device = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='偏好学习设备'
    )
    
    # 进步趋势
    improvement_trend = models.CharField(
        max_length=20,
        choices=[
            ('improving', '进步中'),
            ('stable', '稳定'),
            ('declining', '下降'),
            ('unknown', '未知')
        ],
        default='unknown',
        verbose_name='进步趋势'
    )
    
    class Meta:
        db_table = 'learning_analytics'
        verbose_name = '学习分析'
        verbose_name_plural = '学习分析'
        unique_together = ['user', 'analysis_date']
        ordering = ['-analysis_date']
        indexes = [
            models.Index(fields=['user', 'analysis_date']),
            models.Index(fields=['week_of_year', 'user']),
            models.Index(fields=['month', 'user']),
            models.Index(fields=['productivity_rate']),
            models.Index(fields=['improvement_trend']),
        ]


class LearningGoal(BaseModel, TimestampMixin):
    """学习目标模型 - 重新实现更完善的目标管理"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_goals',
        verbose_name='用户'
    )
    
    title = models.CharField(max_length=200, verbose_name='目标标题')
    description = models.TextField(verbose_name='目标描述')
    
    # 目标分类
    goal_type = models.CharField(
        max_length=20,
        choices=[
            ('skill', '技能目标'),
            ('knowledge', '知识目标'),
            ('certification', '认证目标'),
            ('project', '项目目标'),
            ('habit', '习惯目标'),
        ],
        default='skill',
        verbose_name='目标类型'
    )
    
    # 优先级
    priority = models.CharField(
        max_length=10,
        choices=[
            ('high', '高'),
            ('medium', '中'),
            ('low', '低'),
        ],
        default='medium',
        verbose_name='优先级'
    )
    
    # 时间管理
    target_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='目标完成日期'
    )
    estimated_hours = models.PositiveIntegerField(
        default=0,
        verbose_name='预估学习时长(小时)'
    )
    
    # 进度跟踪
    current_progress = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='当前进度百分比(0-100)'
    )
    
    # 状态管理
    status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', '未开始'),
            ('in_progress', '进行中'),
            ('completed', '已完成'),
            ('paused', '暂停'),
            ('cancelled', '已取消'),
        ],
        default='not_started',
        verbose_name='目标状态'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )
    
    class Meta:
        db_table = 'learning_goals_v2'
        verbose_name = '学习目标'
        verbose_name_plural = '学习目标'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'priority', 'target_date']),
            models.Index(fields=['goal_type', 'status']),
            models.Index(fields=['target_date']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(current_progress__gte=0, current_progress__lte=100),
                name='learning_goals_progress_range'
            ),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    @property
    def is_overdue(self):
        """判断目标是否逾期"""
        if not self.target_date or self.status in ['completed', 'cancelled']:
            return False
        
        from django.utils import timezone
        return timezone.now().date() > self.target_date
    
    def mark_completed(self):
        """标记目标为已完成"""
        from django.utils import timezone
        self.status = 'completed'
        self.current_progress = 100
        self.completed_at = timezone.now()
        self.save()


class LearningStreak(BaseModel, TimestampMixin):
    """学习连续性记录"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_streaks',
        verbose_name='用户'
    )
    
    streak_date = models.DateField(verbose_name='连续学习日期')
    daily_minutes = models.PositiveIntegerField(verbose_name='当日学习分钟数')
    session_count = models.PositiveSmallIntegerField(verbose_name='当日学习会话数')
    
    # 连续性统计
    current_streak = models.PositiveIntegerField(
        default=1,
        verbose_name='当前连续天数'
    )
    longest_streak = models.PositiveIntegerField(
        default=1,
        verbose_name='最长连续天数'
    )
    
    class Meta:
        db_table = 'learning_streaks'
        verbose_name = '学习连续性'
        verbose_name_plural = '学习连续性'
        unique_together = ['user', 'streak_date']
        ordering = ['-streak_date']
        indexes = [
            models.Index(fields=['user', 'streak_date']),
            models.Index(fields=['current_streak']),
            models.Index(fields=['longest_streak']),
        ]
