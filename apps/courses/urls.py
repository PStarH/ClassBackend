"""
课程 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'courses'

# 注册视图集路由
router = DefaultRouter()
router.register(r'content', views.CourseContentViewSet, basename='course-content')

urlpatterns = [
    # 课程内容管理 (RESTful API)
    path('', include(router.urls)),
    
    # 课程进度管理
    path('progress/', views.CourseProgressListCreateView.as_view(), name='progress-list-create'),
    path('progress/<uuid:course_uuid>/', views.CourseProgressDetailView.as_view(), name='progress-detail'),
    
    # 课程统计
    path('stats/', views.CourseProgressStatsView.as_view(), name='progress-stats'),
    
    # 课程反馈
    path('progress/<uuid:course_uuid>/feedback/', views.CourseProgressFeedbackView.as_view(), name='progress-feedback'),
    
    # 学习时长管理
    path('progress/<uuid:course_uuid>/hours/', views.CourseProgressLearningHoursView.as_view(), name='progress-hours'),
]
