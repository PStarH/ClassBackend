"""
课程序列化器
"""
from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import CourseProgress, CourseContent


class CourseContentSerializer(serializers.ModelSerializer):
    """课程内容序列化器"""
    
    chapter_count = serializers.ReadOnlyField()
    total_content_length = serializers.ReadOnlyField()
    
    class Meta:
        model = CourseContent
        fields = [
            'content_id', 'outline', 'chapters', 'chapter_count',
            'total_content_length', 'created_at', 'updated_at'
        ]
        read_only_fields = ['content_id', 'created_at', 'updated_at']
    
    def validate_outline(self, value):
        """验证课程大纲格式"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("课程大纲必须是字典格式")
        return value
    
    def validate_chapters(self, value):
        """验证章节格式"""
        if not isinstance(value, list):
            raise serializers.ValidationError("章节必须是数组格式")
        
        for i, chapter in enumerate(value):
            if not isinstance(chapter, dict):
                raise serializers.ValidationError(f"第{i+1}章必须是字典格式")
            
            if 'title' not in chapter:
                raise serializers.ValidationError(f"第{i+1}章缺少标题")
            
            if 'text' not in chapter:
                raise serializers.ValidationError(f"第{i+1}章缺少内容")
        
        return value


class CourseContentCreateSerializer(serializers.ModelSerializer):
    """课程内容创建序列化器"""
    
    class Meta:
        model = CourseContent
        fields = ['outline', 'chapters']
    
    def validate_outline(self, value):
        """验证课程大纲格式"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("课程大纲必须是字典格式")
        return value
    
    def validate_chapters(self, value):
        """验证章节格式"""
        if not isinstance(value, list):
            raise serializers.ValidationError("章节必须是数组格式")
        
        for i, chapter in enumerate(value):
            if not isinstance(chapter, dict):
                raise serializers.ValidationError(f"第{i+1}章必须是字典格式")
            
            if 'title' not in chapter:
                raise serializers.ValidationError(f"第{i+1}章缺少标题")
            
            if 'text' not in chapter:
                raise serializers.ValidationError(f"第{i+1}章缺少内容")
        
        return value


class ChapterSerializer(serializers.Serializer):
    """章节序列化器"""
    
    title = serializers.CharField(max_length=200, help_text="章节标题")
    text = serializers.CharField(help_text="章节内容")
    position = serializers.IntegerField(
        required=False, 
        min_value=0,
        help_text="章节位置（可选）"
    )


class CourseProgressSerializer(serializers.ModelSerializer):
    """课程进度序列化器"""
    
    completion_progress = serializers.ReadOnlyField()
    learning_efficiency = serializers.ReadOnlyField()
    proficiency_level_name = serializers.ReadOnlyField()
    difficulty_level_name = serializers.ReadOnlyField()
    content_detail = CourseContentSerializer(source='content_id', read_only=True)
    
    class Meta:
        model = CourseProgress
        fields = [
            'course_uuid', 'user_uuid', 'subject_name', 'content_id', 'content_detail',
            'user_experience', 'proficiency_level', 'proficiency_level_name',
            'learning_hour_week', 'learning_hour_total', 'est_finish_hour',
            'difficulty', 'difficulty_level_name', 'feedback',
            'completion_progress', 'learning_efficiency',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'course_uuid', 'user_uuid', 'completion_progress', 
            'learning_efficiency', 'created_at', 'updated_at'
        ]
    
    def validate_proficiency_level(self, value):
        """验证掌握程度"""
        if not (0 <= value <= 100):
            raise serializers.ValidationError("掌握程度必须在0-100之间")
        return value
    
    def validate_difficulty(self, value):
        """验证难度等级"""
        if not (1 <= value <= 10):
            raise serializers.ValidationError("难度等级必须在1-10之间")
        return value
    
    def validate_learning_hour_week(self, value):
        """验证本周学习时长"""
        if value < 0:
            raise serializers.ValidationError("学习时长不能为负数")
        if value > 168:  # 一周最多168小时
            raise serializers.ValidationError("一周学习时长不能超过168小时")
        return value
    
    def validate_learning_hour_total(self, value):
        """验证总学习时长"""
        if value < 0:
            raise serializers.ValidationError("总学习时长不能为负数")
        return value
    
    def validate_est_finish_hour(self, value):
        """验证预计完成时长"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("预计完成时长必须大于0")
        return value
    
    def validate_feedback(self, value):
        """验证反馈数据"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("反馈必须是字典格式")
        
        # 检查反馈内容长度
        for key, content in value.items():
            if isinstance(content, str) and len(content) > 1000:
                raise serializers.ValidationError(f"反馈内容'{key}'不能超过1000字符")
        
        return value


class CourseProgressCreateSerializer(CourseProgressSerializer):
    """课程进度创建序列化器"""
    
    def create(self, validated_data):
        """创建课程进度"""
        user = self.context['request'].user
        validated_data['user_uuid'] = user
        return super().create(validated_data)


class CourseProgressUpdateSerializer(CourseProgressSerializer):
    """课程进度更新序列化器"""
    
    class Meta(CourseProgressSerializer.Meta):
        # 更新时某些字段可选
        extra_kwargs = {
            'subject_name': {'required': False},
            'content_id': {'required': False},
            'difficulty': {'required': False},
        }


class CourseProgressStatsSerializer(serializers.Serializer):
    """课程进度统计序列化器"""
    
    total_courses = serializers.IntegerField(read_only=True)
    completed_courses = serializers.IntegerField(read_only=True)
    in_progress_courses = serializers.IntegerField(read_only=True)
    total_learning_hours = serializers.IntegerField(read_only=True)
    average_proficiency = serializers.FloatField(read_only=True)
    subjects = serializers.ListField(read_only=True)
    completion_rate = serializers.FloatField(read_only=True)


class FeedbackSerializer(serializers.Serializer):
    """反馈序列化器"""
    
    feedback_type = serializers.CharField(
        max_length=50,
        help_text='反馈类型，如：课程、内容、难度等'
    )
    content = serializers.CharField(
        max_length=1000,
        help_text='反馈内容'
    )
    
    def validate_feedback_type(self, value):
        """验证反馈类型"""
        if not value.strip():
            raise serializers.ValidationError("反馈类型不能为空")
        return value.strip()
    
    def validate_content(self, value):
        """验证反馈内容"""
        if not value.strip():
            raise serializers.ValidationError("反馈内容不能为空")
        return value.strip()


class LearningHoursUpdateSerializer(serializers.Serializer):
    """学习时长更新序列化器"""
    
    hours = serializers.IntegerField(
        validators=[MinValueValidator(0)],
        help_text='要增加的学习时长（小时）'
    )
    
    update_type = serializers.ChoiceField(
        choices=[('add', '增加'), ('set_weekly', '设置本周')],
        default='add',
        help_text='更新类型：add-增加总时长，set_weekly-设置本周时长'
    )
