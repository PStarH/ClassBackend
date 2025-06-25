"""
用户认证管理后台配置
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, EmailVerification


class UserProfileInline(admin.StackedInline):
    """用户资料内联"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = '用户资料'
    fields = ['phone', 'bio', 'birth_date', 'learning_style', 
              'timezone', 'email_notifications', 'is_profile_public']


class UserAdmin(BaseUserAdmin):
    """扩展的用户管理"""
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'first_name', 'last_name', 
                   'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'date_joined']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """用户资料管理"""
    
    list_display = ['user', 'phone', 'learning_style', 'timezone', 
                   'email_notifications', 'created_at']
    list_filter = ['learning_style', 'timezone', 'email_notifications', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('用户信息', {
            'fields': ('user',)
        }),
        ('基础资料', {
            'fields': ('phone', 'bio', 'birth_date')
        }),
        ('学习偏好', {
            'fields': ('learning_style', 'timezone')
        }),
        ('设置', {
            'fields': ('email_notifications', 'is_profile_public')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """邮箱验证管理"""
    
    list_display = ['email', 'verification_code', 'is_verified', 
                   'created_at', 'expires_at']
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['email', 'verification_code']
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    
    fieldsets = (
        ('验证信息', {
            'fields': ('user', 'email', 'verification_code')
        }),
        ('状态', {
            'fields': ('is_verified', 'verified_at', 'expires_at')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


# 重新注册User模型
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
