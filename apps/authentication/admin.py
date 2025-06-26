"""
用户认证管理后台配置
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserSession, UserSettings


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """自定义用户管理"""
    
    list_display = ['email', 'username', 'is_active', 'is_staff', 'created_at', 'last_login']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'username']
    ordering = ['-created_at']
    readonly_fields = ['uuid', 'created_at', 'last_login']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
        (_('System'), {'fields': ('uuid',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2'),
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """用户会话管理"""
    
    list_display = ['session_id', 'user', 'is_active', 'created_at', 
                   'last_activity', 'expires_at', 'ip_address']
    list_filter = ['is_active', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__username', 'ip_address']
    readonly_fields = ['session_id', 'token', 'created_at', 'last_activity']
    ordering = ['-created_at']
    
    fieldsets = (
        ('会话信息', {
            'fields': ('session_id', 'user', 'is_active')
        }),
        ('安全信息', {
            'fields': ('token', 'expires_at')
        }),
        ('客户端信息', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('时间信息', {
            'fields': ('created_at', 'last_activity')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """动态设置只读字段"""
        if obj:  # 编辑现有对象
            return self.readonly_fields + ('user',)
        return self.readonly_fields


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    """用户设置管理"""
    
    list_display = ['user_uuid', 'preferred_pace', 'preferred_style', 
                   'tone', 'feedback_frequency', 'education_level', 
                   'created_at', 'updated_at']
    list_filter = ['preferred_pace', 'preferred_style', 'tone', 
                  'feedback_frequency', 'education_level', 'created_at']
    search_fields = ['user_uuid__email', 'user_uuid__username', 'major']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user_uuid',)
        }),
        ('学习偏好', {
            'fields': ('preferred_pace', 'preferred_style', 'tone', 'feedback_frequency')
        }),
        ('教育背景', {
            'fields': ('education_level', 'major')
        }),
        ('技能与备注', {
            'fields': ('skills', 'notes')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """动态设置只读字段"""
        if obj:  # 编辑现有对象
            return self.readonly_fields + ('user_uuid',)
        return self.readonly_fields
    
    def get_skills_display(self, obj):
        """显示技能列表"""
        return obj.get_skills_display()
    get_skills_display.short_description = '技能列表'
