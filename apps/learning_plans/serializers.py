"""
学习计划序列化器
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import LearningGoal, LearningPlan, LearningPlanGoal, StudySession


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class LearningGoalSerializer(serializers.ModelSerializer):
    """学习目标序列化器"""
    
    difficulty_display = serializers.CharField(
        source='get_difficulty_display',
        read_only=True
    )
    goal_type_display = serializers.CharField(
        source='get_goal_type_display',
        read_only=True
    )
    
    class Meta:
        model = LearningGoal
        fields = [
            'id', 'title', 'description', 'goal_type', 'goal_type_display',
            'difficulty', 'difficulty_display', 'estimated_hours',
            'created_at', 'updated_at'
        ]


class LearningPlanGoalSerializer(serializers.ModelSerializer):
    """学习计划目标序列化器"""
    
    learning_goal = LearningGoalSerializer(read_only=True)
    learning_goal_id = serializers.IntegerField(write_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = LearningPlanGoal
        fields = [
            'id', 'learning_goal', 'learning_goal_id', 'status', 'status_display',
            'order', 'actual_hours', 'completion_date', 'notes',
            'created_at', 'updated_at'
        ]


class LearningPlanListSerializer(serializers.ModelSerializer):
    """学习计划列表序列化器"""
    
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    progress_percentage = serializers.ReadOnlyField()
    goals_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningPlan
        fields = [
            'id', 'title', 'description', 'user', 'status', 'status_display',
            'start_date', 'target_end_date', 'actual_end_date',
            'total_estimated_hours', 'progress_percentage', 'goals_count',
            'created_at', 'updated_at'
        ]
    
    def get_goals_count(self, obj):
        return obj.goals.count()


class LearningPlanDetailSerializer(serializers.ModelSerializer):
    """学习计划详情序列化器"""
    
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    progress_percentage = serializers.ReadOnlyField()
    plan_goals = LearningPlanGoalSerializer(
        source='learningplangoal_set',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = LearningPlan
        fields = [
            'id', 'title', 'description', 'user', 'status', 'status_display',
            'start_date', 'target_end_date', 'actual_end_date',
            'total_estimated_hours', 'progress_percentage', 'plan_goals',
            'ai_recommendations', 'created_at', 'updated_at'
        ]


class LearningPlanCreateSerializer(serializers.ModelSerializer):
    """学习计划创建序列化器"""
    
    goal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = LearningPlan
        fields = [
            'title', 'description', 'start_date', 'target_end_date',
            'goal_ids'
        ]
    
    def create(self, validated_data):
        goal_ids = validated_data.pop('goal_ids', [])
        user = self.context['request'].user
        
        learning_plan = LearningPlan.objects.create(
            user=user,
            **validated_data
        )
        
        # 添加目标到计划中
        if goal_ids:
            goals = LearningGoal.objects.filter(id__in=goal_ids)
            for i, goal in enumerate(goals):
                LearningPlanGoal.objects.create(
                    learning_plan=learning_plan,
                    learning_goal=goal,
                    order=i + 1
                )
            
            # 计算总预估时长
            total_hours = sum(goal.estimated_hours for goal in goals)
            learning_plan.total_estimated_hours = total_hours
            learning_plan.save()
        
        return learning_plan


class LearningPlanUpdateSerializer(serializers.ModelSerializer):
    """学习计划更新序列化器"""
    
    class Meta:
        model = LearningPlan
        fields = [
            'title', 'description', 'status', 'start_date',
            'target_end_date', 'actual_end_date'
        ]


class StudySessionSerializer(serializers.ModelSerializer):
    """学习会话序列化器"""
    
    learning_plan_title = serializers.CharField(
        source='learning_plan.title',
        read_only=True
    )
    goal_title = serializers.CharField(
        source='goal.title',
        read_only=True
    )
    
    class Meta:
        model = StudySession
        fields = [
            'id', 'learning_plan', 'learning_plan_title', 'goal', 'goal_title',
            'start_time', 'end_time', 'duration_minutes', 'content_covered',
            'effectiveness_rating', 'notes', 'created_at', 'updated_at'
        ]


class StudySessionCreateSerializer(serializers.ModelSerializer):
    """学习会话创建序列化器"""
    
    class Meta:
        model = StudySession
        fields = [
            'learning_plan', 'goal', 'start_time', 'end_time',
            'duration_minutes', 'content_covered', 'effectiveness_rating', 'notes'
        ]
    
    def validate(self, data):
        # 验证目标属于该学习计划
        if data['goal'] not in data['learning_plan'].goals.all():
            raise serializers.ValidationError(
                "所选目标不属于该学习计划"
            )
        
        # 验证结束时间晚于开始时间
        if data.get('end_time') and data['end_time'] <= data['start_time']:
            raise serializers.ValidationError(
                "结束时间必须晚于开始时间"
            )
        
        # 验证效果评分范围
        rating = data.get('effectiveness_rating')
        if rating is not None and not (1 <= rating <= 5):
            raise serializers.ValidationError(
                "学习效果评分必须在1-5之间"
            )
        
        return data


class AILearningPlanRequestSerializer(serializers.Serializer):
    """AI学习计划生成请求序列化器"""
    
    learning_goals = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=1,
        max_length=10,
        help_text="学习目标列表，最多10个"
    )
    current_level = serializers.ChoiceField(
        choices=[
            ('beginner', '初级'),
            ('intermediate', '中级'),
            ('advanced', '高级')
        ],
        default='beginner',
        help_text="当前水平"
    )
    available_hours_per_week = serializers.IntegerField(
        min_value=1,
        max_value=168,
        default=10,
        help_text="每周可用学习时间（小时）"
    )
    target_duration_weeks = serializers.IntegerField(
        min_value=1,
        max_value=52,
        default=12,
        help_text="目标学习周数"
    )
    learning_style = serializers.ChoiceField(
        choices=[
            ('visual', '视觉型'),
            ('auditory', '听觉型'),
            ('kinesthetic', '动觉型'),
            ('mixed', '混合型')
        ],
        default='mixed',
        help_text="学习风格"
    )
    specific_requirements = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        help_text="特殊要求或偏好"
    )


class AILearningPlanResponseSerializer(serializers.Serializer):
    """AI学习计划生成响应序列化器"""
    
    plan_title = serializers.CharField()
    plan_description = serializers.CharField()
    estimated_total_hours = serializers.IntegerField()
    recommended_goals = serializers.ListField(
        child=serializers.DictField()
    )
    weekly_schedule = serializers.DictField()
    milestones = serializers.ListField(
        child=serializers.DictField()
    )
    resources = serializers.ListField(
        child=serializers.DictField()
    )
    tips_and_strategies = serializers.ListField(
        child=serializers.CharField()
    )
