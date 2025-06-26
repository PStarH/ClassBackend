"""
学习会话管理后台
"""
from django.contrib import admin
from .models import StudySession


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    """学习会话管理"""
    
    list_display = [
        'id', 'start_time', 'end_time', 'duration_display',
        'effectiveness_rating', 'is_active', 'is_completed'
    ]
    list_filter = [
        'is_active', 'effectiveness_rating', 'start_time', 'end_time'
    ]
    search_fields = ['content_covered', 'notes']
    ordering = ['-start_time']
    readonly_fields = ['id', 'created_at', 'updated_at', 'duration_minutes', 'duration_display', 'is_completed']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'start_time', 'end_time', 'duration_minutes', 'duration_display', 'is_active')
        }),
        ('学习内容', {
            'fields': ('content_covered', 'effectiveness_rating', 'notes')
        }),
        ('关联信息', {
            'fields': ('goal_id', 'learning_plan_id'),
            'classes': ('collapse',)
        }),
        ('时间戳', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_completed(self, obj):
        """是否已完成"""
        return obj.is_completed
    is_completed.boolean = True
    is_completed.short_description = '已完成'
    
    actions = ['complete_sessions', 'activate_sessions']
    
    def complete_sessions(self, request, queryset):
        """批量完成学习会话"""
        from django.utils import timezone
        updated = 0
        for session in queryset.filter(is_active=True, end_time__isnull=True):
            session.complete_session()
            updated += 1
        self.message_user(request, f'成功完成 {updated} 个学习会话')
    complete_sessions.short_description = '完成选中的学习会话'
    
    def activate_sessions(self, request, queryset):
        """批量激活学习会话"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个学习会话')
    activate_sessions.short_description = '激活选中的学习会话'
