"""
学习计划视图
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

try:
    from drf_spectacular.utils import extend_schema, OpenApiParameter
    from drf_spectacular.types import OpenApiTypes
    HAS_SPECTACULAR = True
except ImportError:
    # Fallback decorators when drf_spectacular is not available
    def extend_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class OpenApiParameter:
        QUERY = 'query'
    
    class OpenApiTypes:
        INT = 'int'
    
    HAS_SPECTACULAR = False

from core.views import BaseAPIView
from .models import LearningGoal, LearningPlan, LearningPlanGoal, StudySession
from .serializers import (
    LearningGoalSerializer,
    LearningPlanListSerializer,
    LearningPlanDetailSerializer,
    LearningPlanCreateSerializer,
    LearningPlanUpdateSerializer,
    LearningPlanGoalSerializer,
    StudySessionSerializer,
    StudySessionCreateSerializer,
    AILearningPlanRequestSerializer,
    AILearningPlanResponseSerializer
)
from .services import (
    LearningGoalService,
    LearningPlanService,
    StudySessionService,
    AILearningPlanService
)

logger = logging.getLogger(__name__)


class LearningGoalViewSet(viewsets.ModelViewSet):
    """学习目标视图集"""
    
    queryset = LearningGoal.objects.all()
    serializer_class = LearningGoalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 按难度筛选
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # 按类型筛选
        goal_type = self.request.query_params.get('goal_type')
        if goal_type:
            queryset = queryset.filter(goal_type=goal_type)
        
        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = LearningGoalService.search_goals(search)
        
        return queryset.order_by('-created_at')
    
    @extend_schema(
        summary="创建学习目标",
        description="创建一个新的学习目标"
    )
    def create(self, request, *args, **kwargs):
        try:
            goal = LearningGoalService.create_goal(request.data)
            serializer = self.get_serializer(goal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建学习目标失败: {str(e)}")
            return Response(
                {"error": "创建学习目标失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="获取推荐目标",
        description="根据用户偏好获取推荐的学习目标"
    )
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        try:
            difficulty = request.query_params.get('difficulty', 'beginner')
            goal_type = request.query_params.get('goal_type', 'skill')
            
            goals = LearningGoalService.get_goals_by_difficulty(difficulty)
            if goal_type:
                goals = goals.filter(goal_type=goal_type)
            
            goals = goals[:10]  # 限制推荐数量
            serializer = self.get_serializer(goals, many=True)
            
            return Response({
                "recommendations": serializer.data,
                "count": len(serializer.data)
            })
        except Exception as e:
            logger.error(f"获取推荐目标失败: {str(e)}")
            return Response(
                {"error": "获取推荐目标失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LearningPlanViewSet(viewsets.ModelViewSet):
    """学习计划视图集"""
    
    queryset = LearningPlan.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LearningPlanCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LearningPlanUpdateSerializer
        elif self.action == 'retrieve':
            return LearningPlanDetailSerializer
        else:
            return LearningPlanListSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(user=self.request.user)
        
        # 按状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    @extend_schema(
        summary="创建学习计划",
        description="创建一个新的学习计划"
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            plan = serializer.save()
            
            detail_serializer = LearningPlanDetailSerializer(plan)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建学习计划失败: {str(e)}")
            return Response(
                {"error": "创建学习计划失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="更新计划状态",
        description="更新学习计划的状态"
    )
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        try:
            plan = self.get_object()
            new_status = request.data.get('status')
            
            if not new_status:
                return Response(
                    {"error": "状态参数必需"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_plan = LearningPlanService.update_plan_status(plan, new_status)
            serializer = LearningPlanDetailSerializer(updated_plan)
            
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"更新计划状态失败: {str(e)}")
            return Response(
                {"error": "更新计划状态失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="添加目标到计划",
        description="向学习计划添加新的学习目标"
    )
    @action(detail=True, methods=['post'])
    def add_goal(self, request, pk=None):
        try:
            plan = self.get_object()
            goal_id = request.data.get('goal_id')
            order = request.data.get('order')
            
            if not goal_id:
                return Response(
                    {"error": "目标ID必需"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            goal = LearningGoal.objects.get(id=goal_id)
            plan_goal = LearningPlanService.add_goal_to_plan(plan, goal, order)
            
            serializer = LearningPlanGoalSerializer(plan_goal)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except LearningGoal.DoesNotExist:
            return Response(
                {"error": "学习目标不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"添加目标到计划失败: {str(e)}")
            return Response(
                {"error": "添加目标到计划失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="完成计划目标",
        description="标记学习计划中的目标为已完成"
    )
    @action(detail=True, methods=['patch'], url_path='goals/(?P<goal_id>[^/.]+)/complete')
    def complete_goal(self, request, pk=None, goal_id=None):
        try:
            plan = self.get_object()
            actual_hours = request.data.get('actual_hours', 0)
            notes = request.data.get('notes', '')
            
            plan_goal = LearningPlanGoal.objects.get(
                learning_plan=plan,
                learning_goal_id=goal_id
            )
            
            completed_goal = LearningPlanService.complete_goal_in_plan(
                plan_goal, actual_hours, notes
            )
            
            serializer = LearningPlanGoalSerializer(completed_goal)
            return Response(serializer.data)
        except LearningPlanGoal.DoesNotExist:
            return Response(
                {"error": "计划目标不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"完成计划目标失败: {str(e)}")
            return Response(
                {"error": "完成计划目标失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="获取计划统计",
        description="获取学习计划的统计信息"
    )
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        try:
            plan = self.get_object()
            stats = LearningPlanService.get_plan_statistics(plan)
            return Response(stats)
        except Exception as e:
            logger.error(f"获取计划统计失败: {str(e)}")
            return Response(
                {"error": "获取计划统计失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudySessionViewSet(viewsets.ModelViewSet):
    """学习会话视图集"""
    
    queryset = StudySession.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return StudySessionCreateSerializer
        return StudySessionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            learning_plan__user=self.request.user
        )
        
        # 按学习计划筛选
        plan_id = self.request.query_params.get('plan_id')
        if plan_id:
            queryset = queryset.filter(learning_plan_id=plan_id)
        
        # 按日期范围筛选
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__date__lte=end_date)
        
        return queryset.order_by('-start_time')
    
    @extend_schema(
        summary="创建学习会话",
        description="创建一个新的学习会话"
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            session = StudySessionService.create_session(serializer.validated_data)
            
            response_serializer = StudySessionSerializer(session)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建学习会话失败: {str(e)}")
            return Response(
                {"error": "创建学习会话失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="结束学习会话",
        description="结束当前的学习会话"
    )
    @action(detail=True, methods=['patch'])
    def end_session(self, request, pk=None):
        try:
            session = self.get_object()
            end_time = request.data.get('end_time', timezone.now())
            effectiveness_rating = request.data.get('effectiveness_rating')
            notes = request.data.get('notes', '')
            
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            ended_session = StudySessionService.end_session(
                session, end_time, effectiveness_rating, notes
            )
            
            serializer = StudySessionSerializer(ended_session)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"结束学习会话失败: {str(e)}")
            return Response(
                {"error": "结束学习会话失败"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="获取学习统计",
        description="获取用户的学习会话统计信息",
        parameters=[
            OpenApiParameter(
                name='days',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='统计天数，默认30天'
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            stats = StudySessionService.get_session_statistics(request.user, days)
            return Response(stats)
        except Exception as e:
            logger.error(f"获取学习统计失败: {str(e)}")
            return Response(
                {"error": "获取学习统计失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AILearningPlanView(BaseAPIView):
    """AI学习计划生成视图"""
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="生成AI学习计划",
        description="基于用户需求生成个性化学习计划",
        request=AILearningPlanRequestSerializer,
        responses=AILearningPlanResponseSerializer
    )
    def post(self, request):
        try:
            serializer = AILearningPlanRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            ai_service = AILearningPlanService()
            
            # 转换为请求对象
            from infrastructure.ai.schemas.learning_plan_schemas import LearningPlanGenerationRequest
            
            ai_request = LearningPlanGenerationRequest(
                learning_goals=serializer.validated_data['learning_goals'],
                current_level=serializer.validated_data['current_level'],
                available_hours_per_week=serializer.validated_data['available_hours_per_week'],
                target_duration_weeks=serializer.validated_data['target_duration_weeks'],
                learning_style=serializer.validated_data['learning_style'],
                specific_requirements=serializer.validated_data.get('specific_requirements', '')
            )
            
            # 生成AI计划 (同步调用)
            ai_response = ai_service.generate_learning_plan(ai_request)
            
            # 序列化响应
            response_serializer = AILearningPlanResponseSerializer(ai_response.__dict__)
            
            return Response(response_serializer.data)
        except Exception as e:
            logger.error(f"AI学习计划生成失败: {str(e)}")
            return Response(
                {"error": "AI学习计划生成失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
