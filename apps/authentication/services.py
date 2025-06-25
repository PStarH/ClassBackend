"""
用户认证服务
"""
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import string

from .models import UserProfile, EmailVerification


class AuthenticationService:
    """用户认证服务类"""
    
    @staticmethod
    def create_user_with_profile(username, email, password, **kwargs):
        """创建用户并自动创建资料"""
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=kwargs.get('first_name', ''),
            last_name=kwargs.get('last_name', ''),
            is_active=True
        )
        
        # 创建用户资料
        profile_data = {
            'phone': kwargs.get('phone', ''),
            'bio': kwargs.get('bio', ''),
            'learning_style': kwargs.get('learning_style', 'mixed'),
            'timezone': kwargs.get('timezone', 'Asia/Shanghai'),
        }
        
        UserProfile.objects.create(user=user, **profile_data)
        
        return user
    
    @staticmethod
    def generate_verification_code():
        """生成6位数字验证码"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def send_email_verification(email, purpose='registration'):
        """发送邮箱验证码"""
        # 检查邮箱是否已注册（仅注册时检查）
        if purpose == 'registration' and User.objects.filter(email=email).exists():
            raise ValueError('该邮箱已被注册')
        
        # 生成验证码
        verification_code = AuthenticationService.generate_verification_code()
        
        # 创建验证记录
        verification = EmailVerification.objects.create(
            email=email,
            verification_code=verification_code,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # 发送邮件
        subject_map = {
            'registration': '教育平台 - 注册验证码',
            'reset_password': '教育平台 - 密码重置验证码',
            'change_email': '教育平台 - 邮箱变更验证码',
        }
        
        subject = subject_map.get(purpose, '教育平台 - 验证码')
        message = f'您的验证码是：{verification_code}，10分钟内有效。请勿泄露给他人。'
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return verification
        except Exception as e:
            # 删除创建的验证记录
            verification.delete()
            raise e
    
    @staticmethod
    def verify_email_code(email, verification_code):
        """验证邮箱验证码"""
        try:
            verification = EmailVerification.objects.filter(
                email=email,
                verification_code=verification_code,
                is_verified=False
            ).latest('created_at')
            
            if verification.is_expired:
                raise ValueError('验证码已过期')
            
            # 标记为已验证
            verification.is_verified = True
            verification.verified_at = timezone.now()
            verification.save()
            
            return verification
        
        except EmailVerification.DoesNotExist:
            raise ValueError('验证码错误')
    
    @staticmethod
    def get_user_stats(user):
        """获取用户统计信息"""
        from apps.learning_plans.models import LearningPlan, StudySession
        
        stats = {
            'total_learning_plans': LearningPlan.objects.filter(user=user).count(),
            'active_learning_plans': LearningPlan.objects.filter(
                user=user, status='active'
            ).count(),
            'completed_learning_plans': LearningPlan.objects.filter(
                user=user, status='completed'
            ).count(),
            'total_study_hours': 0,
            'study_sessions_count': 0,
        }
        
        # 计算学习时长
        study_sessions = StudySession.objects.filter(
            learning_plan__user=user
        )
        
        stats['study_sessions_count'] = study_sessions.count()
        
        total_minutes = sum(
            session.duration_minutes for session in study_sessions
        )
        stats['total_study_hours'] = round(total_minutes / 60, 2)
        
        return stats
