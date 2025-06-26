"""
学习会话应用路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudySessionViewSet

app_name = 'learning_plans'

# 注册视图集路由
router = DefaultRouter()
router.register(r'sessions', StudySessionViewSet, basename='study-sessions')

urlpatterns = [
    # API 路由
    path('', include(router.urls)),
]
