"""
学习计划管理后台配置
"""
from django.contrib import admin
from .models import LearningGoal, LearningPlan, LearningPlanGoal, StudySession


@admin.register(LearningGoal)
class LearningGoalAdmin(admin.ModelAdmin):
    """学习目标管理"""
    
    list_display = [
        'title', 'goal_type', 'difficulty', 'estimated_hours',
        'created_at', 'updated_at'
    ]
    list_filter = ['goal_type', 'difficulty', 'created_at']
    search_fields = ['title', 'description']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'description')
        }),
        ('分类信息', {
            'fields': ('goal_type', 'difficulty', 'estimated_hours')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


class LearningPlanGoalInline(admin.TabularInline):
    """学习计划目标内联"""
    
    model = LearningPlanGoal
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = [
        'learning_goal', 'status', 'order', 'actual_hours',
        'completion_date', 'notes'
    ]
    autocomplete_fields = ['learning_goal']


@admin.register(LearningPlan)
class LearningPlanAdmin(admin.ModelAdmin):
    """学习计划管理"""
    
    list_display = [
        'title', 'user', 'status', 'progress_percentage',
        'total_estimated_hours', 'start_date', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'start_date']
    search_fields = ['title', 'description', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'progress_percentage']
    inlines = [LearningPlanGoalInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'title', 'description', 'status')
        }),
        ('时间安排', {
            'fields': ('start_date', 'target_end_date', 'actual_end_date')
        }),
        ('进度信息', {
            'fields': ('total_estimated_hours', 'progress_percentage')
        }),
        ('AI 推荐', {
            'fields': ('ai_recommendations',),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('created_at', 'updated_at', 'is_deleted'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """包含软删除的记录"""
        return self.model.objects.all()


@admin.register(LearningPlanGoal)
class LearningPlanGoalAdmin(admin.ModelAdmin):
    """学习计划目标管理"""
    
    list_display = [
        'learning_plan', 'learning_goal', 'status', 'order',
        'actual_hours', 'completion_date'
    ]
    list_filter = ['status', 'completion_date', 'created_at']
    search_fields = [
        'learning_plan__title', 'learning_goal__title',
        'learning_plan__user__username'
    ]
    ordering = ['learning_plan', 'order']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['learning_plan', 'learning_goal']
    
    fieldsets = (
        ('关联信息', {
            'fields': ('learning_plan', 'learning_goal')
        }),
        ('状态信息', {
            'fields': ('status', 'order', 'actual_hours', 'completion_date')
        }),
        ('学习笔记', {
            'fields': ('notes',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    """学习会话管理"""
    
    list_display = [
        'learning_plan', 'goal', 'start_time', 'duration_minutes',
        'effectiveness_rating', 'created_at'
    ]
    list_filter = [
        'effectiveness_rating', 'start_time', 'created_at'
    ]
    search_fields = [
        'learning_plan__title', 'goal__title',
        'learning_plan__user__username'
    ]
    ordering = ['-start_time']
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['learning_plan', 'goal']
    
    fieldsets = (
        ('关联信息', {
            'fields': ('learning_plan', 'goal')
        }),
        ('时间信息', {
            'fields': ('start_time', 'end_time', 'duration_minutes')
        }),
        ('学习内容', {
            'fields': ('content_covered', 'effectiveness_rating')
        }),
        ('学习笔记', {
            'fields': ('notes',)
        }),
        ('系统信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """根据对象状态设置只读字段"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        # 如果会话已结束，duration_minutes 应该是只读的
        if obj and obj.end_time:
            readonly_fields.append('duration_minutes')
        
        return readonly_fields


# 自定义管理站点配置
admin.site.site_header = "学习计划管理系统"
admin.site.site_title = "学习计划后台"
admin.site.index_title = "欢迎使用学习计划管理系统"
