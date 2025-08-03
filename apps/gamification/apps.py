"""
Gamification Apps Configuration
游戏化应用配置
"""
from django.apps import AppConfig


class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gamification'
    verbose_name = 'Gamification System'
    
    def ready(self):
        # 导入信号处理器
        import apps.gamification.signals