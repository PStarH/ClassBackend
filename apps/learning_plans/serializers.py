"""
学习会话序列化器
"""
from rest_framework import serializers
from .models import StudySession


class StudySessionSerializer(serializers.ModelSerializer):
    """学习会话序列化器"""
    
    effectiveness_rating_display = serializers.CharField(
        source='get_effectiveness_rating_display',
        read_only=True
    )
    duration_display = serializers.CharField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = StudySession
        fields = [
            'id', 'start_time', 'end_time', 'duration_minutes', 
            'duration_display', 'content_covered', 'effectiveness_rating',
            'effectiveness_rating_display', 'is_active', 'notes',
            'goal_id', 'learning_plan_id', 'is_completed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'duration_minutes', 'created_at', 'updated_at']
    
    def validate(self, data):
        """验证数据"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if end_time and start_time and end_time <= start_time:
            raise serializers.ValidationError(
                "结束时间必须晚于开始时间"
            )
        
        effectiveness_rating = data.get('effectiveness_rating')
        if effectiveness_rating is not None and (effectiveness_rating < 1 or effectiveness_rating > 5):
            raise serializers.ValidationError(
                "学习效果评分必须在1-5之间"
            )
        
        return data


class StudySessionCreateSerializer(StudySessionSerializer):
    """学习会话创建序列化器"""
    
    class Meta(StudySessionSerializer.Meta):
        fields = [
            'start_time', 'content_covered', 'notes',
            'goal_id', 'learning_plan_id'
        ]


class StudySessionCompleteSerializer(serializers.Serializer):
    """学习会话完成序列化器"""
    
    end_time = serializers.DateTimeField(required=False)
    effectiveness_rating = serializers.IntegerField(
        min_value=1, 
        max_value=5, 
        required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_end_time(self, value):
        """验证结束时间"""
        instance = self.instance
        if instance and instance.start_time and value <= instance.start_time:
            raise serializers.ValidationError(
                "结束时间必须晚于开始时间"
            )
        return value


class StudySessionStatsSerializer(serializers.Serializer):
    """学习会话统计序列化器"""
    
    total_sessions = serializers.IntegerField()
    total_duration_minutes = serializers.IntegerField() 
    average_duration_minutes = serializers.FloatField()
    total_duration_display = serializers.CharField()
    average_effectiveness_rating = serializers.FloatField()
    active_sessions_count = serializers.IntegerField()
    completed_sessions_count = serializers.IntegerField()
