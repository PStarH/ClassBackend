"""
学习计划应用路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LearningGoalViewSet,
    LearningPlanViewSet,
    StudySessionViewSet,
    AILearningPlanView
)

app_name = 'learning_plans'

# 注册视图集路由
router = DefaultRouter()
router.register(r'goals', LearningGoalViewSet, basename='learning-goals')
router.register(r'plans', LearningPlanViewSet, basename='learning-plans')
router.register(r'sessions', StudySessionViewSet, basename='study-sessions')

urlpatterns = [
    # API 路由
    path('api/', include(router.urls)),
    
    # AI 相关路由
    path('api/ai/generate-plan/', AILearningPlanView.as_view(), name='ai-generate-plan'),
]
