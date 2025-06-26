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
    
    # 课程关联 - 添加与课程进度的关联
    course_progress = models.ForeignKey(
        'courses.CourseProgress',
        on_delete=models.CASCADE,
        related_name='study_sessions',
        null=True,
        blank=True,
        verbose_name='关联课程进度',
        help_text='学习会话关联的课程进度记录'
    )
    
    # 学习主题/类别
    subject_category = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='学习主题',
        help_text='学习内容的主题分类'
    )
    
    # 可选的外键关联，用于扩展功能（暂时保留为可空）
    goal_id = models.UUIDField(null=True, blank=True, verbose_name='学习目标ID')
    learning_plan_id = models.UUIDField(null=True, blank=True, verbose_name='学习计划ID')
    
    # 学习统计字段
    break_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='休息次数',
        help_text='学习过程中的休息次数'
    )
    
    focus_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='专注度评分',
        help_text='学习专注度评分(0-1)'
    )
    
    # 学习环境记录
    learning_environment = models.CharField(
        max_length=50,
        choices=[
            ('home', '家中'),
            ('library', '图书馆'),
            ('cafe', '咖啡厅'),
            ('classroom', '教室'),
            ('online', '在线'),
            ('other', '其他')
        ],
        default='other',
        verbose_name='学习环境'
    )
    
    # 学习设备
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('mobile', '手机'),
            ('tablet', '平板'),
            ('laptop', '笔记本'),
            ('desktop', '台式机'),
            ('other', '其他')
        ],
        default='other',
        verbose_name='学习设备'
    )

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
            # 新增索引
            models.Index(fields=['user', 'subject_category', 'start_time']),  # 按主题查询
            models.Index(fields=['course_progress', 'start_time']),  # 按课程查询
            models.Index(fields=['effectiveness_rating', 'start_time']),  # 按效果查询
            models.Index(fields=['learning_environment']),  # 按环境分析
            models.Index(fields=['user', 'end_time']),  # 完成时间查询
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
            # 确保专注度评分在有效范围内
            models.CheckConstraint(
                check=models.Q(focus_score__isnull=True) | 
                      models.Q(focus_score__gte=0, focus_score__lte=1),
                name='study_sessions_focus_score_range'
            ),
            # 确保休息次数非负
            models.CheckConstraint(
                check=models.Q(break_count__gte=0),
                name='study_sessions_break_count_non_negative'
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
    
    @property
    def efficiency_score(self):
        """计算学习效率评分"""
        if self.duration_minutes == 0:
            return 0
        
        base_score = (self.effectiveness_rating or 3) / 5  # 标准化到0-1
        
        # 考虑专注度
        if self.focus_score:
            focus_factor = self.focus_score
        else:
            focus_factor = 0.7  # 默认专注度
        
        # 考虑休息频率（适度休息有益）
        if self.duration_minutes > 0:
            break_frequency = self.break_count / (self.duration_minutes / 60)  # 每小时休息次数
            if 0.5 <= break_frequency <= 2:  # 理想休息频率
                break_factor = 1.0
            elif break_frequency < 0.5:
                break_factor = 0.8  # 休息太少
            else:
                break_factor = 0.6  # 休息太频繁
        else:
            break_factor = 1.0
        
        return round(base_score * focus_factor * break_factor, 2)
    
    @property
    def is_productive_session(self):
        """判断是否为高效学习会话"""
        return (
            self.duration_minutes >= 25 and  # 至少25分钟
            (self.effectiveness_rating or 0) >= 3 and  # 效果评分>=3
            self.efficiency_score >= 0.6  # 效率评分>=0.6
        )
    
    def get_session_insights(self):
        """获取学习会话洞察"""
        insights = []
        
        if self.duration_minutes < 15:
            insights.append("学习时间较短，建议延长学习时间")
        elif self.duration_minutes > 120:
            insights.append("学习时间较长，注意适当休息")
        
        if self.break_count == 0 and self.duration_minutes > 60:
            insights.append("长时间学习建议适当休息")
        
        if (self.effectiveness_rating or 0) <= 2:
            insights.append("学习效果不佳，建议调整学习方法或环境")
        
        if self.focus_score and self.focus_score < 0.5:
            insights.append("专注度较低，建议减少干扰因素")
        
        return insights
