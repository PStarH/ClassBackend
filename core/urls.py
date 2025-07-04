"""
核心应用的 URL 配置
"""
from django.urls import path, include
from . import views

app_name = 'core'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('cache-stats/', views.cache_stats, name='cache_stats'),
    # 性能监控API
    path('monitoring/', include('core.monitoring.urls')),
]
