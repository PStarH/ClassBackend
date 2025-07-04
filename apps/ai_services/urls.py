"""
AI 服务 URL 配置
"""
from django.urls import path, include

urlpatterns = [
    # AI 服务 API 端点将在这里定义
    path('advisor/', include('llm.advisor.urls')),
    path('teacher/', include('llm.teacher.urls')),
    path('exercise/', include('llm.exercise.urls')),
]
