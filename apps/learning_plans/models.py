"""
学习计划模型
"""
from django.db import models
from django.contrib.auth.models import User
from core.models.base import BaseModel
from core.models.mixins import TimestampMixin, SoftDeleteMixin


class LearningGoal(BaseModel, TimestampMixin):
    """学习目标模型"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', '初级'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
    ]
    
    GOAL_TYPE_CHOICES = [
        ('skill', '技能目标'),
        ('knowledge', '知识目标'),
        ('certification', '认证目标'),
        ('project', '项目目标'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='目标标题')
    description = models.TextField(verbose_name='目标描述')
    goal_type = models.CharField(
        max_length=20, 
        choices=GOAL_TYPE_CHOICES,
        default='skill',
        verbose_name='目标类型'
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default='beginner',
        verbose_name='难度等级'
    )
    estimated_hours = models.PositiveIntegerField(
        default=0,
        verbose_name='预估学习时长(小时)'
    )
    
    class Meta:
        db_table = 'learning_goals'
        verbose_name = '学习目标'
        verbose_name_plural = '学习目标'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class LearningPlan(BaseModel, TimestampMixin, SoftDeleteMixin):
    """学习计划模型"""
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('paused', '已暂停'),
        ('cancelled', '已取消'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_plans',
        verbose_name='用户'
    )
    title = models.CharField(max_length=200, verbose_name='计划标题')
    description = models.TextField(blank=True, verbose_name='计划描述')
    goals = models.ManyToManyField(
        LearningGoal,
        through='LearningPlanGoal',
        related_name='learning_plans',
        verbose_name='学习目标'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='状态'
    )
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    target_end_date = models.DateField(null=True, blank=True, verbose_name='目标结束日期')
    actual_end_date = models.DateField(null=True, blank=True, verbose_name='实际结束日期')
    total_estimated_hours = models.PositiveIntegerField(
        default=0,
        verbose_name='总预估时长(小时)'
    )
    ai_recommendations = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='AI推荐内容'
    )
    
    class Meta:
        db_table = 'learning_plans'
        verbose_name = '学习计划'
        verbose_name_plural = '学习计划'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['start_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    @property
    def progress_percentage(self):
        """计算进度百分比"""
        if not self.goals.exists():
            return 0
        
        completed_goals = self.learningplangoal_set.filter(
            status='completed'
        ).count()
        total_goals = self.goals.count()
        
        return round((completed_goals / total_goals) * 100, 2) if total_goals > 0 else 0


class LearningPlanGoal(BaseModel, TimestampMixin):
    """学习计划目标关联模型"""
    
    STATUS_CHOICES = [
        ('not_started', '未开始'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('skipped', '已跳过'),
    ]
    
    learning_plan = models.ForeignKey(
        LearningPlan,
        on_delete=models.CASCADE,
        verbose_name='学习计划'
    )
    learning_goal = models.ForeignKey(
        LearningGoal,
        on_delete=models.CASCADE,
        verbose_name='学习目标'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        verbose_name='状态'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='顺序')
    actual_hours = models.PositiveIntegerField(
        default=0,
        verbose_name='实际学习时长(小时)'
    )
    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间'
    )
    notes = models.TextField(blank=True, verbose_name='学习笔记')
    
    class Meta:
        db_table = 'learning_plan_goals'
        verbose_name = '学习计划目标'
        verbose_name_plural = '学习计划目标'
        unique_together = ['learning_plan', 'learning_goal']
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.learning_plan.title} - {self.learning_goal.title}"


class StudySession(BaseModel, TimestampMixin):
    """学习会话模型"""
    
    learning_plan = models.ForeignKey(
        LearningPlan,
        on_delete=models.CASCADE,
        related_name='study_sessions',
        verbose_name='学习计划'
    )
    goal = models.ForeignKey(
        LearningGoal,
        on_delete=models.CASCADE,
        related_name='study_sessions',
        verbose_name='学习目标'
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
        verbose_name='学习效果评分(1-5)'
    )
    notes = models.TextField(blank=True, verbose_name='学习笔记')
    
    class Meta:
        db_table = 'study_sessions'
        verbose_name = '学习会话'
        verbose_name_plural = '学习会话'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['learning_plan', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.learning_plan.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
