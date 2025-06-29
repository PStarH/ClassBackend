"""
主路由配置
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# API 版本
API_VERSION = 'v1'

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),
    
    # API 路由
    path(f'api/{API_VERSION}/', include([
        # 核心功能
        path('', include('core.urls')),
        
        # 用户认证
        path('auth/', include('apps.authentication.urls')),
        
        # 学习计划 (包含学习记录)
        path('learning-plans/', include('apps.learning_plans.urls')),
        
        # 课程管理
        path('courses/', include('apps.courses.urls')),
        
        # AI服务 (大模型/AI服务)
        path('ai/', include('apps.ai_services.urls')),
    ])),
    
    # 健康检查
    path('health/', TemplateView.as_view(template_name='health.html'), name='health_check'),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # 开发环境 API 文档
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# 404 处理
handler404 = 'core.views.custom_404'
handler500 = 'core.views.custom_500'
