"""
学生笔记和问题追踪模型
"""
import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.authentication.models import User
from apps.courses.models import CourseProgress
from .models import StudySession


class StudentQuestion(models.Model):
    """学生问题记录"""
    
    QUESTION_TYPES = [
        ('concept', '概念理解'),
        ('application', '应用实践'),
        ('theory', '理论深入'),
        ('technical', '技术细节'),
        ('general', '一般问题'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('basic', '基础'),
        ('intermediate', '中级'),
        ('advanced', '高级'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='学生'
    )
    
    course_progress = models.ForeignKey(
        CourseProgress,
        on_delete=models.CASCADE,
        related_name='student_questions',
        null=True,
        blank=True,
        verbose_name='相关课程进度'
    )
    
    study_session = models.ForeignKey(
        StudySession,
        on_delete=models.CASCADE,
        related_name='questions',
        null=True,
        blank=True,
        verbose_name='相关学习会话'
    )
    
    question_text = models.TextField(
        verbose_name='问题内容'
    )
    
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='general',
        verbose_name='问题类型'
    )
    
    difficulty_level = models.CharField(
        max_length=20,
        choices=DIFFICULTY_LEVELS,
        default='basic',
        verbose_name='问题难度'
    )
    
    context = models.TextField(
        blank=True,
        verbose_name='问题上下文',
        help_text='问题出现时的学习情境和背景'
    )
    
    ai_response = models.TextField(
        blank=True,
        verbose_name='AI回答'
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name='是否已解决'
    )
    
    teacher_notes = models.TextField(
        blank=True,
        verbose_name='教师备注'
    )
    
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        verbose_name='标签',
        help_text='用于分类和检索的标签'
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
        db_table = 'student_questions'
        verbose_name = '学生问题'
        verbose_name_plural = '学生问题'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['question_type', 'difficulty_level']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['course_progress', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.question_text[:50]}..."


class StudentLearningPattern(models.Model):
    """学生学习模式分析"""
    
    LEARNING_STRENGTHS = [
        ('visual', '视觉学习'),
        ('auditory', '听觉学习'),
        ('kinesthetic', '动手学习'),
        ('reading', '阅读学习'),
        ('logical', '逻辑思维'),
        ('creative', '创意思维'),
    ]
    
    WEAKNESS_AREAS = [
        ('attention', '注意力不集中'),
        ('comprehension', '理解困难'),
        ('memory', '记忆问题'),
        ('application', '应用困难'),
        ('speed', '学习速度慢'),
        ('motivation', '学习动机不足'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='learning_pattern',
        verbose_name='学生'
    )
    
    strengths = ArrayField(
        models.CharField(max_length=20, choices=LEARNING_STRENGTHS),
        default=list,
        blank=True,
        verbose_name='学习优势'
    )
    
    weaknesses = ArrayField(
        models.CharField(max_length=20, choices=WEAKNESS_AREAS),
        default=list,
        blank=True,
        verbose_name='学习弱项'
    )
    
    frequent_question_types = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
        verbose_name='常见问题类型',
        help_text='基于历史问题分析得出的常见问题类型'
    )
    
    preferred_learning_time = models.JSONField(
        default=dict,
        verbose_name='偏好学习时间',
        help_text='基于学习会话分析得出的最佳学习时间段'
    )
    
    attention_span_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name='注意力持续时间(分钟)',
        help_text='基于学习会话效果分析得出的平均注意力持续时间'
    )
    
    difficulty_progression_rate = models.FloatField(
        default=1.0,
        verbose_name='难度提升率',
        help_text='学生适应难度提升的速度，1.0为标准速度'
    )
    
    concept_mastery_patterns = models.JSONField(
        default=dict,
        verbose_name='概念掌握模式',
        help_text='不同类型概念的掌握速度和模式'
    )
    
    last_analyzed = models.DateTimeField(
        auto_now=True,
        verbose_name='最后分析时间'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'student_learning_patterns'
        verbose_name = '学生学习模式'
        verbose_name_plural = '学生学习模式'
        indexes = [
            models.Index(fields=['last_analyzed']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - 学习模式分析"


class TeacherNotes(models.Model):
    """教师对学生的观察笔记"""
    
    NOTE_TYPES = [
        ('progress', '学习进度观察'),
        ('behavior', '学习行为观察'),
        ('difficulty', '困难点分析'),
        ('strength', '优势发现'),
        ('recommendation', '改进建议'),
        ('milestone', '重要里程碑'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_notes',
        verbose_name='学生'
    )
    
    course_progress = models.ForeignKey(
        CourseProgress,
        on_delete=models.CASCADE,
        related_name='teacher_notes',
        null=True,
        blank=True,
        verbose_name='相关课程进度'
    )
    
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPES,
        default='progress',
        verbose_name='笔记类型'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium',
        verbose_name='优先级'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='标题'
    )
    
    content = models.TextField(
        verbose_name='笔记内容'
    )
    
    observations = models.JSONField(
        default=dict,
        verbose_name='具体观察数据',
        help_text='结构化的观察数据，如学习时长、错误模式等'
    )
    
    action_items = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
        verbose_name='行动项',
        help_text='基于观察得出的具体行动建议'
    )
    
    follow_up_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='跟进日期'
    )
    
    is_shared_with_student = models.BooleanField(
        default=False,
        verbose_name='是否与学生分享'
    )
    
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        verbose_name='标签'
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
        db_table = 'teacher_notes'
        verbose_name = '教师笔记'
        verbose_name_plural = '教师笔记'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['note_type', 'priority']),
            models.Index(fields=['follow_up_date']),
            models.Index(fields=['course_progress', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"
