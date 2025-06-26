"""
学习计划应用配置
"""
from django.apps import AppConfig


class LearningPlansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.learning_plans'
    verbose_name = '学习计划'
    
    def ready(self):
        """应用准备就绪时执行"""
        # 导入信号处理器
        try:
            from . import cache_signals
            cache_signals.connect_cache_signals()
        except ImportError:
            pass
