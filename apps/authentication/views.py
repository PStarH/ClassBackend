"""
用户认证视图
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse
from datetime import timedelta
import random
import string

from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserProfileSerializer,
    EmailVerificationSerializer,
    PasswordChangeSerializer
)
from .models import UserProfile, EmailVerification


class UserRegistrationView(generics.CreateAPIView):
    """用户注册视图"""
    
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="用户注册",
        description="通过邮箱注册新用户账号",
        responses={
            201: OpenApiResponse(
                response=UserSerializer,
                description="注册成功"
            ),
            400: OpenApiResponse(description="注册失败，参数错误")
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # 创建认证令牌
            token, created = Token.objects.get_or_create(user=user)
            
            # 返回用户信息和令牌
            user_serializer = UserSerializer(user)
            
            return Response({
                'message': '注册成功',
                'user': user_serializer.data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(
    summary="用户登录",
    description="用户登录获取认证令牌",
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description="登录成功"
        ),
        401: OpenApiResponse(description="登录失败，凭据无效")
    }
)
def login_view(request):
    """用户登录"""
    serializer = UserLoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # 创建或获取认证令牌
        token, created = Token.objects.get_or_create(user=user)
        
        # 更新最后登录时间
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # 返回用户信息和令牌
        user_serializer = UserSerializer(user)
        
        return Response({
            'message': '登录成功',
            'user': user_serializer.data,
            'token': token.key
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="用户退出",
    description="用户退出登录，删除认证令牌",
    responses={
        200: OpenApiResponse(description="退出成功"),
        401: OpenApiResponse(description="未认证")
    }
)
def logout_view(request):
    """用户退出"""
    try:
        # 删除用户的认证令牌
        token = Token.objects.get(user=request.user)
        token.delete()
        
        return Response({
            'message': '退出成功'
        }, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({
            'message': '退出成功'
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """用户资料视图"""
    
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    @extend_schema(
        summary="获取用户资料",
        description="获取当前用户的详细资料",
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="获取成功"
            ),
            401: OpenApiResponse(description="未认证")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="更新用户资料",
        description="更新当前用户的基本信息",
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="更新成功"
            ),
            400: OpenApiResponse(description="更新失败，参数错误"),
            401: OpenApiResponse(description="未认证")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """用户详细资料视图"""
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    @extend_schema(
        summary="获取用户详细资料",
        description="获取当前用户的详细资料设置",
        responses={
            200: OpenApiResponse(
                response=UserProfileSerializer,
                description="获取成功"
            ),
            401: OpenApiResponse(description="未认证")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    @extend_schema(
        summary="更新用户详细资料",
        description="更新当前用户的详细资料设置",
        responses={
            200: OpenApiResponse(
                response=UserProfileSerializer,
                description="更新成功"
            ),
            400: OpenApiResponse(description="更新失败，参数错误"),
            401: OpenApiResponse(description="未认证")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@extend_schema(
    summary="修改密码",
    description="修改当前用户的登录密码",
    request=PasswordChangeSerializer,
    responses={
        200: OpenApiResponse(description="密码修改成功"),
        400: OpenApiResponse(description="密码修改失败，参数错误"),
        401: OpenApiResponse(description="未认证")
    }
)
def change_password_view(request):
    """修改密码"""
    serializer = PasswordChangeSerializer(data=request.data)
    
    if serializer.is_valid():
        user = request.user
        
        # 验证旧密码
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                'error': '当前密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 设置新密码
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # 删除旧的认证令牌，强制重新登录
        try:
            token = Token.objects.get(user=user)
            token.delete()
        except Token.DoesNotExist:
            pass
        
        return Response({
            'message': '密码修改成功，请重新登录'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def generate_verification_code():
    """生成6位随机验证码"""
    return ''.join(random.choices(string.digits, k=6))


@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(
    summary="发送邮箱验证码",
    description="向指定邮箱发送验证码",
    request=EmailVerificationSerializer,
    responses={
        200: OpenApiResponse(description="验证码发送成功"),
        400: OpenApiResponse(description="发送失败，参数错误")
    }
)
def send_verification_code(request):
    """发送邮箱验证码"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'error': '请提供邮箱地址'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 检查邮箱是否已注册
    if User.objects.filter(email=email).exists():
        return Response({
            'error': '该邮箱已被注册'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 生成验证码
    verification_code = generate_verification_code()
    
    # 创建验证记录
    verification = EmailVerification.objects.create(
        user=None,  # 注册时还没有用户对象
        email=email,
        verification_code=verification_code,
        expires_at=timezone.now() + timedelta(minutes=10)  # 10分钟有效期
    )
    
    # 发送邮件（开发环境会在控制台显示）
    try:
        send_mail(
            subject='教育平台 - 邮箱验证码',
            message=f'您的验证码是：{verification_code}，10分钟内有效。',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return Response({
            'message': '验证码已发送到您的邮箱'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'error': '验证码发送失败，请稍后重试'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@extend_schema(
    summary="验证邮箱验证码",
    description="验证邮箱验证码是否正确",
    responses={
        200: OpenApiResponse(description="验证码正确"),
        400: OpenApiResponse(description="验证码错误或已过期")
    }
)
def verify_email_code(request):
    """验证邮箱验证码"""
    email = request.data.get('email')
    verification_code = request.data.get('verification_code')
    
    if not email or not verification_code:
        return Response({
            'error': '请提供邮箱和验证码'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerification.objects.filter(
            email=email,
            verification_code=verification_code,
            is_verified=False
        ).latest('created_at')
        
        if verification.is_expired:
            return Response({
                'error': '验证码已过期'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 标记为已验证
        verification.is_verified = True
        verification.verified_at = timezone.now()
        verification.save()
        
        return Response({
            'message': '邮箱验证成功'
        }, status=status.HTTP_200_OK)
    
    except EmailVerification.DoesNotExist:
        return Response({
            'error': '验证码错误'
        }, status=status.HTTP_400_BAD_REQUEST)
