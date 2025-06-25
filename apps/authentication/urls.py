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
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # 用户资料
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/detail/', views.UserProfileDetailView.as_view(), name='profile-detail'),
    
    # 密码管理
    path('password/change/', views.change_password_view, name='change-password'),
    
    # 邮箱验证
    path('email/send-code/', views.send_verification_code, name='send-verification-code'),
    path('email/verify/', views.verify_email_code, name='verify-email'),
]
