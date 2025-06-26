"""
课程管理后台配置
"""
from django.contrib import admin
from .models import CourseProgress, CourseContent


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    """课程进度管理"""
    
    list_display = [
        'course_uuid', 'user_uuid', 'subject_name', 
        'proficiency_level_name', 'difficulty_level_name',
        'learning_hour_week', 'learning_hour_total', 
        'est_finish_hour', 'completion_progress', 'updated_at'
    ]
    
    list_filter = [
        'subject_name', 'proficiency_level', 'difficulty',
        'created_at', 'updated_at'
    ]
    
    search_fields = [
        'user_uuid__email', 'user_uuid__username', 
        'subject_name', 'content_id__content_id'
    ]
    
    readonly_fields = [
        'course_uuid', 'created_at', 'updated_at',
        'completion_progress', 'learning_efficiency'
    ]
    
    ordering = ['-updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('course_uuid', 'user_uuid', 'subject_name', 'content_id')
        }),
        ('学习状态', {
            'fields': ('proficiency_level', 'difficulty', 'user_experience')
        }),
        ('学习时长', {
            'fields': ('learning_hour_week', 'learning_hour_total', 'est_finish_hour')
        }),
        ('反馈信息', {
            'fields': ('feedback',)
        }),
        ('统计信息', {
            'fields': ('completion_progress', 'learning_efficiency'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def completion_progress(self, obj):
        """显示完成进度"""
        progress = obj.get_completion_progress()
        return f"{progress:.1f}%"
    completion_progress.short_description = '完成进度'
    
    def learning_efficiency(self, obj):
        """显示学习效率"""
        efficiency = obj.get_learning_efficiency()
        return f"{efficiency:.2f}"
    learning_efficiency.short_description = '学习效率'
    
    def proficiency_level_name(self, obj):
        """显示掌握程度名称"""
        return obj.proficiency_level_name
    proficiency_level_name.short_description = '掌握程度'
    
    def difficulty_level_name(self, obj):
        """显示难度等级名称"""
        return obj.difficulty_level_name
    difficulty_level_name.short_description = '难度等级'
    
    def get_readonly_fields(self, request, obj=None):
        """动态设置只读字段"""
        if obj:  # 编辑现有对象
            return self.readonly_fields + ('user_uuid', 'content_id')
        return self.readonly_fields


@admin.register(CourseContent)
class CourseContentAdmin(admin.ModelAdmin):
    """课程内容管理"""
    
    list_display = [
        'content_id', 'outline_title', 'chapter_count', 
        'total_content_length', 'created_at', 'updated_at'
    ]
    
    list_filter = ['created_at', 'updated_at']
    
    search_fields = ['content_id', 'outline']
    
    readonly_fields = [
        'content_id', 'created_at', 'updated_at',
        'chapter_count', 'total_content_length'
    ]
    
    ordering = ['-updated_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('content_id', 'outline')
        }),
        ('章节内容', {
            'fields': ('chapters',)
        }),
        ('统计信息', {
            'fields': ('chapter_count', 'total_content_length'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def outline_title(self, obj):
        """显示大纲标题"""
        if isinstance(obj.outline, dict) and 'title' in obj.outline:
            return obj.outline['title']
        return "无标题"
    outline_title.short_description = '大纲标题'
    
    def chapter_count(self, obj):
        """显示章节数量"""
        return obj.chapter_count
    chapter_count.short_description = '章节数量'
    
    def total_content_length(self, obj):
        """显示内容总长度"""
        length = obj.total_content_length
        if length > 1000:
            return f"{length // 1000}K+ 字符"
        return f"{length} 字符"
    total_content_length.short_description = '内容长度'
