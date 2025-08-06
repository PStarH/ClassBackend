"""
学习会话视图
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.utils import timezone
from django.db import models
from django.db.models import Avg, Sum, Count
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

from core.views import BaseAPIView, CachedAPIView
from core.cache import APICacheManager, cache_result, UserCacheManager
from .models import StudySession
from .serializers import (
    StudySessionSerializer,
    StudySessionCreateSerializer,
    StudySessionCompleteSerializer,
    StudySessionStatsSerializer
)

logger = logging.getLogger(__name__)


class StudySessionViewSet(viewsets.ModelViewSet):
    """学习会话视图集"""
    
    serializer_class = StudySessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """获取查询集"""
        queryset = StudySession.objects.select_related(
            'user', 
            'course_progress'
        ).order_by('-start_time')
        
        # 按状态过滤
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)
        
        # 按完成状态过滤
        is_completed = self.request.query_params.get('is_completed')
        if is_completed is not None:
            is_completed = is_completed.lower() == 'true'
            if is_completed:
                queryset = queryset.filter(end_time__isnull=False)
            else:
                queryset = queryset.filter(end_time__isnull=True)
        
        # 按日期范围过滤
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                queryset = queryset.filter(start_time__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                queryset = queryset.filter(start_time__lte=end_date)
            except ValueError:
                pass
        
        # 按学习目标过滤
        goal_id = self.request.query_params.get('goal_id')
        if goal_id:
            queryset = queryset.filter(goal_id=goal_id)
        
        # 按学习计划过滤
        learning_plan_id = self.request.query_params.get('learning_plan_id')
        if learning_plan_id:
            queryset = queryset.filter(learning_plan_id=learning_plan_id)
        
        return queryset.order_by('-start_time')
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return StudySessionCreateSerializer
        elif self.action == 'complete':
            return StudySessionCompleteSerializer
        return StudySessionSerializer
    
    @extend_schema(
        summary="创建学习会话",
        description="创建新的学习会话记录"
    )
    def create(self, request, *args, **kwargs):
        """创建学习会话"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 自动设置为活跃状态
        study_session = serializer.save(is_active=True)
        
        logger.info(f"创建学习会话: {study_session.id}")
        
        return Response(
            StudySessionSerializer(study_session).data,
            status=status.HTTP_201_CREATED
        )
    
    @extend_schema(
        summary="完成学习会话",
        description="完成正在进行的学习会话",
        request=StudySessionCompleteSerializer
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """完成学习会话"""
        study_session = self.get_object()
        
        if not study_session.is_active:
            return Response(
                {'error': '学习会话已经完成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(study_session, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 完成会话
        end_time = serializer.validated_data.get('end_time', timezone.now())
        effectiveness_rating = serializer.validated_data.get('effectiveness_rating')
        notes = serializer.validated_data.get('notes', '')
        
        study_session.complete_session(
            end_time=end_time,
            effectiveness_rating=effectiveness_rating,
            notes=notes
        )
        
        logger.info(f"完成学习会话: {study_session.id}")
        
        return Response(
            StudySessionSerializer(study_session).data,
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        summary="获取学习统计",
        description="获取学习会话的统计信息"
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取学习统计"""
        queryset = self.get_queryset()
        
        # 基础统计
        total_sessions = queryset.count()
        total_duration = queryset.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0
        
        # 平均时长
        avg_duration = queryset.aggregate(
            avg=Avg('duration_minutes')
        )['avg'] or 0
        
        # 平均评分
        avg_rating = queryset.filter(
            effectiveness_rating__isnull=False
        ).aggregate(
            avg=Avg('effectiveness_rating')
        )['avg'] or 0
        
        # 状态统计
        active_count = queryset.filter(is_active=True).count()
        completed_count = queryset.filter(end_time__isnull=False).count()
        
        # 格式化显示时长
        hours = total_duration // 60
        minutes = total_duration % 60
        total_duration_display = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"
        
        stats_data = {
            'total_sessions': total_sessions,
            'total_duration_minutes': total_duration,
            'total_duration_display': total_duration_display,
            'average_duration_minutes': round(avg_duration, 2),
            'average_effectiveness_rating': round(avg_rating, 2),
            'active_sessions_count': active_count,
            'completed_sessions_count': completed_count
        }
        
        serializer = StudySessionStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @extend_schema(
        summary="激活学习会话",
        description="重新激活已暂停的学习会话"
    )
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活学习会话"""
        study_session = self.get_object()
        
        if study_session.is_completed:
            return Response(
                {'error': '已完成的会话无法重新激活'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        study_session.is_active = True
        study_session.save()
        
        logger.info(f"激活学习会话: {study_session.id}")
        
        return Response(
            StudySessionSerializer(study_session).data,
            status=status.HTTP_200_OK
        )
    
    @extend_schema(
        summary="暂停学习会话",
        description="暂停正在进行的学习会话"
    )
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停学习会话"""
        study_session = self.get_object()
        
        if not study_session.is_active:
            return Response(
                {'error': '会话已经暂停或完成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        study_session.is_active = False
        study_session.save()
        
        logger.info(f"暂停学习会话: {study_session.id}")
        
        return Response(
            StudySessionSerializer(study_session).data,
            status=status.HTTP_200_OK
        )
