"""
用户认证视图
"""
import logging
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User, UserSettings
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    LoginResponseSerializer,
    UserSettingsSerializer,
    UserSettingsCreateSerializer,
    UserSettingsUpdateSerializer
)
from .services import AuthenticationService
from .authentication import TokenAuthentication

logger = logging.getLogger(__name__)


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
        """用户注册"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            user = AuthenticationService.create_user(
                email=serializer.validated_data['email'],
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            
            response_serializer = UserSerializer(user)
            return Response({
                'success': True,
                'message': '注册成功',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"用户注册失败: {str(e)}")
            return Response({
                'success': False,
                'message': '注册失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """用户登录视图"""
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="用户登录",
        description="通过邮箱和密码登录",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description="登录成功"
            ),
            401: OpenApiResponse(description="登录失败")
        }
    )
    def post(self, request):
        """用户登录"""
        try:
            serializer = UserLoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            user = serializer.validated_data['user']
            
            response_data = {
                'user': UserSerializer(user).data
            }
            
            return Response({
                'success': True,
                'message': '登录成功',
                'data': response_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"用户登录失败: {str(e)}")
            return Response({
                'success': False,
                'message': '登录失败',
                'error': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)


class UserLogoutView(APIView):
    """用户登出视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="用户登出",
        description="注销当前会话",
        responses={
            200: OpenApiResponse(description="登出成功"),
            401: OpenApiResponse(description="未授权")
        }
    )
    def post(self, request):
        """用户登出"""
        try:
            return Response({
                'success': True,
                'message': '登出成功'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"用户登出失败: {str(e)}")
            return Response({
                'success': False,
                'message': '登出失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """用户详情视图"""
    
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """获取当前用户"""
        return self.request.user
    
    def get_serializer_class(self):
        """根据请求方法返回不同的序列化器"""
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    @extend_schema(
        summary="获取用户信息",
        description="获取当前登录用户的详细信息",
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="获取成功"
            ),
            401: OpenApiResponse(description="未授权")
        }
    )
    def get(self, request, *args, **kwargs):
        """获取用户信息"""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取用户信息失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="更新用户信息",
        description="更新当前用户的基本信息",
        request=UserUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSerializer,
                description="更新成功"
            ),
            400: OpenApiResponse(description="更新失败")
        }
    )
    def put(self, request, *args, **kwargs):
        """更新用户信息"""
        try:
            user = self.get_object()
            serializer = self.get_serializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            
            updated_user = serializer.save()
            
            response_serializer = UserSerializer(updated_user)
            return Response({
                'success': True,
                'message': '用户信息更新成功',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"更新用户信息失败: {str(e)}")
            return Response({
                'success': False,
                'message': '更新用户信息失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="删除用户账户",
        description="停用当前用户账户",
        responses={
            200: OpenApiResponse(description="账户已停用"),
            400: OpenApiResponse(description="操作失败")
        }
    )
    def delete(self, request, *args, **kwargs):
        """删除用户账户"""
        try:
            user = self.get_object()
            AuthenticationService.deactivate_user(user)
            
            return Response({
                'success': True,
                'message': '账户已停用'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"停用用户账户失败: {str(e)}")
            return Response({
                'success': False,
                'message': '停用用户账户失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """密码修改视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="修改密码",
        description="修改当前用户的登录密码",
        request=PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(description="密码修改成功"),
            400: OpenApiResponse(description="密码修改失败")
        }
    )
    def post(self, request):
        """修改密码"""
        try:
            serializer = PasswordChangeSerializer(
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            
            AuthenticationService.change_password(
                request.user,
                serializer.validated_data['old_password'],
                serializer.validated_data['new_password']
            )
            
            return Response({
                'success': True,
                'message': '密码修改成功，请重新登录'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"密码修改失败: {str(e)}")
            return Response({
                'success': False,
                'message': '密码修改失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)





class UserStatsView(APIView):
    """用户统计信息视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取用户统计信息",
        description="获取当前用户的统计数据",
        responses={
            200: OpenApiResponse(description="获取成功")
        }
    )
    def get(self, request):
        """获取用户统计信息"""
        try:
            # Simple user stats implementation
            stats = {
                'user_uuid': str(request.user.uuid),
                'username': request.user.username,
                'email': request.user.email,
                'is_active': request.user.is_active,
                'date_joined': request.user.date_joined,
                'last_login': request.user.last_login
            }
            
            return Response({
                'success': True,
                'data': stats
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"获取用户统计信息失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取用户统计信息失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserSettingsView(APIView):
    """用户设置视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取用户设置",
        description="获取当前用户的设置信息",
        responses={
            200: OpenApiResponse(
                response=UserSettingsSerializer,
                description="获取成功"
            ),
            404: OpenApiResponse(description="用户设置不存在")
        }
    )
    def get(self, request):
        """获取用户设置"""
        try:
            settings = UserSettings.objects.get(user_uuid=request.user)
            serializer = UserSettingsSerializer(settings)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except UserSettings.DoesNotExist:
            return Response({
                'success': False,
                'message': '用户设置不存在，请先创建用户设置'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"获取用户设置失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取用户设置失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="创建用户设置",
        description="为当前用户创建设置信息（注册后必填）",
        request=UserSettingsCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=UserSettingsSerializer,
                description="创建成功"
            ),
            400: OpenApiResponse(description="创建失败，参数错误"),
            409: OpenApiResponse(description="用户设置已存在")
        }
    )
    def post(self, request):
        """创建用户设置"""
        try:
            # 检查用户是否已有设置
            if UserSettings.objects.filter(user_uuid=request.user).exists():
                return Response({
                    'success': False,
                    'message': '用户设置已存在，请使用PUT方法更新'
                }, status=status.HTTP_409_CONFLICT)
            
            serializer = UserSettingsCreateSerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                settings = serializer.save()
                response_serializer = UserSettingsSerializer(settings)
                
                logger.info(f"用户 {request.user.email} 创建设置成功")
                return Response({
                    'success': True,
                    'message': '用户设置创建成功',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': '创建用户设置失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"创建用户设置失败: {str(e)}")
            return Response({
                'success': False,
                'message': '创建用户设置失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="更新用户设置",
        description="更新当前用户的设置信息",
        request=UserSettingsUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=UserSettingsSerializer,
                description="更新成功"
            ),
            400: OpenApiResponse(description="更新失败，参数错误"),
            404: OpenApiResponse(description="用户设置不存在")
        }
    )
    def put(self, request):
        """更新用户设置"""
        try:
            settings = UserSettings.objects.get(user_uuid=request.user)
            serializer = UserSettingsUpdateSerializer(
                settings,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                settings = serializer.save()
                response_serializer = UserSettingsSerializer(settings)
                
                logger.info(f"用户 {request.user.email} 更新设置成功")
                return Response({
                    'success': True,
                    'message': '用户设置更新成功',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': '更新用户设置失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except UserSettings.DoesNotExist:
            return Response({
                'success': False,
                'message': '用户设置不存在，请先创建用户设置'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"更新用户设置失败: {str(e)}")
            return Response({
                'success': False,
                'message': '更新用户设置失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserSettingsSkillsView(APIView):
    """用户技能管理视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="添加用户技能",
        description="为用户添加新技能",
        request={'type': 'object', 'properties': {'skill': {'type': 'string'}}},
        responses={
            200: OpenApiResponse(description="添加成功"),
            400: OpenApiResponse(description="添加失败")
        }
    )
    def post(self, request):
        """添加技能"""
        try:
            skill = request.data.get('skill', '').strip()
            if not skill:
                return Response({
                    'success': False,
                    'message': '技能名称不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            settings = UserSettings.objects.get(user_uuid=request.user)
            
            if skill in settings.skills:
                return Response({
                    'success': False,
                    'message': '技能已存在'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            settings.add_skill(skill)
            
            return Response({
                'success': True,
                'message': '技能添加成功',
                'data': {'skills': settings.skills}
            }, status=status.HTTP_200_OK)
            
        except UserSettings.DoesNotExist:
            return Response({
                'success': False,
                'message': '用户设置不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"添加技能失败: {str(e)}")
            return Response({
                'success': False,
                'message': '添加技能失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="删除用户技能",
        description="删除用户的指定技能",
        request={'type': 'object', 'properties': {'skill': {'type': 'string'}}},
        responses={
            200: OpenApiResponse(description="删除成功"),
            400: OpenApiResponse(description="删除失败")
        }
    )
    def delete(self, request):
        """删除技能"""
        try:
            skill = request.data.get('skill', '').strip()
            if not skill:
                return Response({
                    'success': False,
                    'message': '技能名称不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            settings = UserSettings.objects.get(user_uuid=request.user)
            
            if skill not in settings.skills:
                return Response({
                    'success': False,
                    'message': '技能不存在'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            settings.remove_skill(skill)
            
            return Response({
                'success': True,
                'message': '技能删除成功',
                'data': {'skills': settings.skills}
            }, status=status.HTTP_200_OK)
            
        except UserSettings.DoesNotExist:
            return Response({
                'success': False,
                'message': '用户设置不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"删除技能失败: {str(e)}")
            return Response({
                'success': False,
                'message': '删除技能失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
