"""
用户认证 URL 配置
"""
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # 用户注册
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    
    # 用户登录/退出
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # 用户信息管理 (GET, PUT, DELETE)
    path('user/', views.UserDetailView.as_view(), name='user-detail'),
    
    # 密码管理
    path('password/change/', views.PasswordChangeView.as_view(), name='change-password'),
    
    # 用户统计信息
    path('stats/', views.UserStatsView.as_view(), name='user-stats'),
    
    # 用户设置管理
    path('settings/', views.UserSettingsView.as_view(), name='user-settings'),
    path('settings/skills/', views.UserSettingsSkillsView.as_view(), name='user-settings-skills'),
]
