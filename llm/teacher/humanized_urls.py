"""
Humanized AI Teacher URLs
人性化AI教师的URL配置
"""
from django.urls import path
from . import humanized_views

app_name = 'humanized_teacher'

urlpatterns = [
    # 主要AI教师交互端点
    path('chat/', humanized_views.HumanizedTeacherView.as_view(), name='chat'),
    
    # 快速帮助（需要认证）
    path('quick-help/', humanized_views.quick_help, name='quick_help'),
    
    # 服务状态
    path('status/', humanized_views.teacher_status, name='status'),
    
    # 用户反馈
    path('feedback/', humanized_views.feedback, name='feedback'),
    
    # 学习建议
    path('suggestions/', humanized_views.learning_suggestions, name='suggestions'),
]