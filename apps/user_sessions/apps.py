"""
用户会话应用配置
"""
from django.apps import AppConfig


class UserSessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user_sessions'
    verbose_name = '用户会话'
