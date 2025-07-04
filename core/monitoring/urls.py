"""
性能监控 API 路由配置
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # 性能仪表盘
    path('dashboard/', views.performance_dashboard, name='dashboard'),
    
    # 慢操作分析
    path('slow-operations/', views.slow_operations, name='slow_operations'),
    
    # 数据库统计
    path('database-stats/', views.database_stats, name='database_stats'),
    
    # 成本分析
    path('cost-analysis/', views.cost_analysis, name='cost_analysis'),
    
    # 系统健康
    path('health/', views.system_health, name='system_health'),
    
    # 性能指标摘要
    path('metrics/', views.metrics_summary, name='metrics'),
    
    # 清空指标
    path('clear-metrics/', views.clear_metrics, name='clear_metrics'),
    
    # 导出指标
    path('export/', views.export_metrics, name='export_metrics'),
]
