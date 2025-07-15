"""
AI 服务 URL 配置
"""
from django.urls import path, include
from . import views

urlpatterns = [
    # AI Service Status
    path('status/', views.service_status, name='ai_service_status'),
    
    # AI Exercise Generation
    path('exercises/generate/', views.generate_exercises, name='generate_exercises'),
    
    # AI Teaching Help
    path('teaching/help/', views.get_teaching_help, name='get_teaching_help'),
    
    # AI Learning Advice
    path('advice/', views.get_learning_advice, name='get_learning_advice'),
    
    # Include module-specific URLs
    path('advisor/', include('llm.advisor.urls')),
    path('teacher/', include('llm.teacher.urls')),
    path('exercise/', include('llm.exercise.urls')),
]
