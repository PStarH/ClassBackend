"""
学习计划应用配置
"""
from django.apps import AppConfig


class LearningPlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.learning_plans'
    verbose_name = '学习计划'
