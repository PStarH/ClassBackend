"""
课程模型
"""
import uuid
from django.db import models
from django.db.models import F
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from apps.authentication.models import User


class CourseContent(models.Model):
    """课程内容模型"""
    
    content_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='内容唯一标识符'
    )
    
    outline = models.JSONField(
        default=dict,
        verbose_name='课程大纲',
        help_text='课程大纲，结构化 JSON 格式'
    )
    
    chapters = models.JSONField(
        default=list,
        verbose_name='章节内容',
        help_text='每一章的内容，数组格式，如：[{ "title": "Intro", "text": "..." }, ...]'
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
        db_table = 'course_contents'  # 按照规范使用复数形式
        verbose_name = '课程内容'
        verbose_name_plural = '课程内容'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['created_at']),  # 按创建时间查询
            models.Index(fields=['updated_at']),  # 按更新时间查询
        ]
        constraints = [
            # 确保大纲和章节字段不为空对象
            models.CheckConstraint(
                check=~models.Q(outline__exact={}),
                name='course_contents_outline_not_empty'
            ),
        ]
    
    def __str__(self):
        """返回课程内容的字符串表示"""
        # 尝试从大纲中获取标题
        if isinstance(self.outline, dict) and 'title' in self.outline:
            return f"课程内容: {self.outline['title']}"
        elif isinstance(self.chapters, list) and len(self.chapters) > 0:
            first_chapter = self.chapters[0]
            if isinstance(first_chapter, dict) and 'title' in first_chapter:
                return f"课程内容: {first_chapter['title']} (共{len(self.chapters)}章)"
        return f"课程内容: {str(self.content_id)[:8]}"
    
    @property
    def chapter_count(self):
        """获取章节数量"""
        if isinstance(self.chapters, list):
            return len(self.chapters)
        return 0
    
    @property
    def total_content_length(self):
        """计算内容总长度（字符数）"""
        total_length = 0
        if isinstance(self.chapters, list):
            for chapter in self.chapters:
                if isinstance(chapter, dict) and 'text' in chapter:
                    total_length += len(str(chapter['text']))
        return total_length
    
    def get_chapter_by_index(self, index):
        """根据索引获取章节"""
        if isinstance(self.chapters, list) and 0 <= index < len(self.chapters):
            return self.chapters[index]
        return None
    
    def add_chapter(self, title, text, position=None):
        """添加新章节"""
        if not isinstance(self.chapters, list):
            self.chapters = []
        
        new_chapter = {
            'title': title,
            'text': text,
            'created_at': timezone.now().isoformat()
        }
        
        if position is None or position >= len(self.chapters):
            self.chapters.append(new_chapter)
        else:
            self.chapters.insert(position, new_chapter)
        
        self.save(update_fields=['chapters', 'updated_at'])
        return new_chapter
    
    def update_chapter(self, index, title=None, text=None):
        """更新指定章节"""
        if not isinstance(self.chapters, list) or index < 0 or index >= len(self.chapters):
            return False
        
        chapter = self.chapters[index]
        if not isinstance(chapter, dict):
            return False
        
        if title is not None:
            chapter['title'] = title
        if text is not None:
            chapter['text'] = text
        chapter['updated_at'] = timezone.now().isoformat()
        
        self.save(update_fields=['chapters', 'updated_at'])
        return True
    
    def remove_chapter(self, index):
        """删除指定章节"""
        if not isinstance(self.chapters, list) or index < 0 or index >= len(self.chapters):
            return False
        
        self.chapters.pop(index)
        self.save(update_fields=['chapters', 'updated_at'])
        return True
    
    def update_outline(self, outline_data):
        """更新课程大纲"""
        self.outline = outline_data
        self.save(update_fields=['outline', 'updated_at'])


class CourseProgress(models.Model):
    """课程进度模型"""
    
    # 熟练程度等级选择
    PROFICIENCY_CHOICES = [
        (0, '初学者'),
        (25, '基础'),
        (50, '中级'),
        (75, '高级'),
        (100, '专家'),
    ]
    
    # 难度等级选择
    DIFFICULTY_CHOICES = [
        (1, '极易'),
        (2, '简单'),
        (3, '容易'),
        (4, '适中偏易'),
        (5, '适中'),
        (6, '适中偏难'),
        (7, '困难'),
        (8, '很难'),
        (9, '极难'),
        (10, '专家级'),
    ]
    
    course_uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='课程进度ID'
    )
    
    user_uuid = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_progresses',
        verbose_name='用户'
    )
    
    subject_name = models.CharField(
        max_length=100,
        verbose_name='学科名称',
        help_text='课程所属学科名称'
    )
    
    content_id = models.ForeignKey(
        CourseContent,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name='课程内容',
        help_text='关联的课程内容',
        db_column='content_id'  # 确保数据库列名为 content_id
    )
    
    user_experience = models.TextField(
        blank=True,
        verbose_name='用户经验描述',
        help_text='用户自我描述的相关经验和背景'
    )
    
    proficiency_level = models.IntegerField(
        choices=PROFICIENCY_CHOICES,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='掌握程度',
        help_text='用户对该学科的掌握程度（0-100）'
    )
    
    learning_hour_week = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='本周学习时长',
        help_text='最近一周的学习时长（小时）'
    )
    
    learning_hour_total = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='累计学习时长',
        help_text='总计学习时长（小时）'
    )
    
    est_finish_hour = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name='预计完成时长',
        help_text='预计完成课程所需时长（小时）'
    )
    
    difficulty = models.IntegerField(
        choices=DIFFICULTY_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='课程难度',
        help_text='课程难度评分（1-10）'
    )
    
    feedback = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='用户反馈',
        help_text='用户对课程和内容的反馈信息'
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
        db_table = 'course_progress'
        verbose_name = '课程进度'
        verbose_name_plural = '课程进度'
        # 确保用户对同一个课程内容只能有一个进度记录
        unique_together = ['user_uuid', 'content_id']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user_uuid', 'updated_at']),  # 用户查询自己的课程
            models.Index(fields=['subject_name']),  # 按学科查询
            models.Index(fields=['proficiency_level']),  # 按掌握程度分析
            models.Index(fields=['difficulty']),  # 按难度分析
            models.Index(fields=['created_at']),  # 按创建时间查询
            models.Index(fields=['learning_hour_total']),  # 按学习时长分析
        ]
        constraints = [
            # 确保学习时长非负
            models.CheckConstraint(
                check=models.Q(learning_hour_week__gte=0),
                name='course_progress_weekly_hours_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(learning_hour_total__gte=0),
                name='course_progress_total_hours_non_negative'
            ),
            # 确保预计完成时长大于0（如果设置）
            models.CheckConstraint(
                check=models.Q(est_finish_hour__isnull=True) | models.Q(est_finish_hour__gt=0),
                name='course_progress_est_finish_hour_positive'
            ),
            # 确保掌握程度在有效范围内
            models.CheckConstraint(
                check=models.Q(proficiency_level__gte=0, proficiency_level__lte=100),
                name='course_progress_proficiency_range'
            ),
            # 确保难度等级在有效范围内
            models.CheckConstraint(
                check=models.Q(difficulty__gte=1, difficulty__lte=10),
                name='course_progress_difficulty_range'
            ),
        ]
    
    def __str__(self):
        return f"{self.user_uuid.email} - {self.subject_name}"
    
    @property
    def proficiency_percentage(self):
        """获取掌握程度百分比"""
        return self.proficiency_level
    
    @property
    def difficulty_level_name(self):
        """获取难度等级名称"""
        return self.get_difficulty_display()
    
    @property
    def proficiency_level_name(self):
        """获取掌握程度等级名称"""
        return self.get_proficiency_level_display()
    
    def add_learning_hours(self, hours):
        """增加学习时长 - 使用原子操作防止竞争条件"""
        if hours > 0:
            # 使用F表达式进行原子更新，防止竞争条件
            CourseProgress.objects.filter(
                course_uuid=self.course_uuid
            ).update(
                learning_hour_total=F('learning_hour_total') + hours,
                updated_at=timezone.now()
            )
            # 刷新实例以获取最新值
            self.refresh_from_db(fields=['learning_hour_total', 'updated_at'])
    
    def update_weekly_hours(self, hours):
        """更新本周学习时长"""
        self.learning_hour_week = hours
        self.save(update_fields=['learning_hour_week', 'updated_at'])
    
    def add_feedback(self, feedback_type, content):
        """添加反馈"""
        if not isinstance(self.feedback, dict):
            self.feedback = {}
        self.feedback[feedback_type] = content
        self.save(update_fields=['feedback', 'updated_at'])
    
    def get_completion_progress(self):
        """计算完成进度（基于学习时长和预计时长）"""
        if self.est_finish_hour and self.est_finish_hour > 0:
            progress = (self.learning_hour_total / self.est_finish_hour) * 100
            return min(progress, 100)  # 最大100%
        return 0
    
    def is_completed(self):
        """判断课程是否完成"""
        return self.get_completion_progress() >= 100
    
    def get_learning_efficiency(self):
        """计算学习效率（掌握程度/学习时长）"""
        if self.learning_hour_total > 0:
            return self.proficiency_level / self.learning_hour_total
        return 0
