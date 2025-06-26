"""
课程视图
"""
import logging
from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Avg, Sum, Count, Q, F
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import CourseProgress, CourseContent
from .serializers import (
    CourseProgressSerializer,
    CourseProgressCreateSerializer,
    CourseProgressUpdateSerializer,
    CourseProgressStatsSerializer,
    FeedbackSerializer,
    LearningHoursUpdateSerializer,
    CourseContentSerializer,
    CourseContentCreateSerializer,
    ChapterSerializer
)
from apps.authentication.authentication import TokenAuthentication

logger = logging.getLogger(__name__)


class CourseProgressListCreateView(generics.ListCreateAPIView):
    """课程进度列表和创建视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CourseProgressCreateSerializer
        return CourseProgressSerializer
    
    def get_queryset(self):
        """获取当前用户的课程进度"""
        return CourseProgress.objects.filter(user_uuid=self.request.user)
    
    @extend_schema(
        summary="获取课程进度列表",
        description="获取当前用户的所有课程进度",
        responses={
            200: OpenApiResponse(
                response=CourseProgressSerializer(many=True),
                description="获取成功"
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """获取课程进度列表"""
        try:
            queryset = self.get_queryset()
            
            # 支持按学科过滤
            subject = request.query_params.get('subject')
            if subject:
                queryset = queryset.filter(subject_name__icontains=subject)
            
            # 支持按完成状态过滤
            completed = request.query_params.get('completed')
            if completed is not None:
                if completed.lower() in ['true', '1']:
                    queryset = queryset.filter(
                        learning_hour_total__gte=F('est_finish_hour')
                    )
                elif completed.lower() in ['false', '0']:
                    queryset = queryset.filter(
                        Q(est_finish_hour__isnull=True) |
                        Q(learning_hour_total__lt=F('est_finish_hour'))
                    )
            
            serializer = self.get_serializer(queryset, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data,
                'count': queryset.count()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"获取课程进度列表失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取课程进度列表失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="创建课程进度",
        description="为当前用户创建新的课程进度记录",
        request=CourseProgressCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=CourseProgressSerializer,
                description="创建成功"
            ),
            400: OpenApiResponse(description="创建失败")
        }
    )
    def post(self, request, *args, **kwargs):
        """创建课程进度"""
        try:
            serializer = self.get_serializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                progress = serializer.save()
                response_serializer = CourseProgressSerializer(progress)
                
                logger.info(f"用户 {request.user.email} 创建课程进度: {progress.subject_name}")
                return Response({
                    'success': True,
                    'message': '课程进度创建成功',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'message': '创建课程进度失败',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"创建课程进度失败: {str(e)}")
            return Response({
                'success': False,
                'message': '创建课程进度失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CourseProgressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """课程进度详情视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'course_uuid'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CourseProgressUpdateSerializer
        return CourseProgressSerializer
    
    def get_queryset(self):
        """获取当前用户的课程进度"""
        return CourseProgress.objects.filter(user_uuid=self.request.user)
    
    @extend_schema(
        summary="获取课程进度详情",
        description="获取指定课程的进度详情",
        responses={
            200: OpenApiResponse(
                response=CourseProgressSerializer,
                description="获取成功"
            ),
            404: OpenApiResponse(description="课程进度不存在")
        }
    )
    def get(self, request, *args, **kwargs):
        """获取课程进度详情"""
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"获取课程进度详情失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取课程进度详情失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CourseProgressStatsView(APIView):
    """课程进度统计视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="获取课程进度统计",
        description="获取当前用户的课程学习统计数据",
        responses={
            200: OpenApiResponse(
                response=CourseProgressStatsSerializer,
                description="获取成功"
            )
        }
    )
    def get(self, request):
        """获取课程进度统计"""
        try:
            user_progresses = CourseProgress.objects.filter(user_uuid=request.user)
            
            # 基础统计
            total_courses = user_progresses.count()
            completed_courses = sum(1 for p in user_progresses if p.is_completed())
            in_progress_courses = total_courses - completed_courses
            
            # 学习时长统计
            total_learning_hours = user_progresses.aggregate(
                total=Sum('learning_hour_total')
            )['total'] or 0
            
            # 平均掌握程度
            average_proficiency = user_progresses.aggregate(
                avg=Avg('proficiency_level')
            )['avg'] or 0
            
            # 学科列表
            subjects = list(user_progresses.values_list(
                'subject_name', flat=True
            ).distinct())
            
            # 完成率
            completion_rate = (completed_courses / total_courses * 100) if total_courses > 0 else 0
            
            stats_data = {
                'total_courses': total_courses,
                'completed_courses': completed_courses,
                'in_progress_courses': in_progress_courses,
                'total_learning_hours': total_learning_hours,
                'average_proficiency': round(average_proficiency, 2),
                'subjects': subjects,
                'completion_rate': round(completion_rate, 2)
            }
            
            serializer = CourseProgressStatsSerializer(stats_data)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"获取课程进度统计失败: {str(e)}")
            return Response({
                'success': False,
                'message': '获取课程进度统计失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CourseProgressFeedbackView(APIView):
    """课程进度反馈视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="添加课程反馈",
        description="为指定课程添加反馈",
        request=FeedbackSerializer,
        responses={
            200: OpenApiResponse(description="添加成功"),
            404: OpenApiResponse(description="课程进度不存在")
        }
    )
    def post(self, request, course_uuid):
        """添加课程反馈"""
        try:
            progress = CourseProgress.objects.get(
                course_uuid=course_uuid,
                user_uuid=request.user
            )
            
            serializer = FeedbackSerializer(data=request.data)
            if serializer.is_valid():
                feedback_type = serializer.validated_data['feedback_type']
                content = serializer.validated_data['content']
                
                progress.add_feedback(feedback_type, content)
                
                logger.info(f"用户 {request.user.email} 添加课程反馈: {progress.subject_name}")
                return Response({
                    'success': True,
                    'message': '反馈添加成功',
                    'data': {'feedback': progress.feedback}
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': '反馈数据无效',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except CourseProgress.DoesNotExist:
            return Response({
                'success': False,
                'message': '课程进度不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"添加课程反馈失败: {str(e)}")
            return Response({
                'success': False,
                'message': '添加课程反馈失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CourseProgressLearningHoursView(APIView):
    """课程学习时长管理视图"""
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="更新学习时长",
        description="更新指定课程的学习时长",
        request=LearningHoursUpdateSerializer,
        responses={
            200: OpenApiResponse(description="更新成功"),
            404: OpenApiResponse(description="课程进度不存在")
        }
    )
    def post(self, request, course_uuid):
        """更新学习时长"""
        try:
            progress = CourseProgress.objects.get(
                course_uuid=course_uuid,
                user_uuid=request.user
            )
            
            serializer = LearningHoursUpdateSerializer(data=request.data)
            if serializer.is_valid():
                hours = serializer.validated_data['hours']
                update_type = serializer.validated_data['update_type']
                
                if update_type == 'add':
                    progress.add_learning_hours(hours)
                elif update_type == 'set_weekly':
                    progress.update_weekly_hours(hours)
                
                response_serializer = CourseProgressSerializer(progress)
                
                logger.info(f"用户 {request.user.email} 更新学习时长: {progress.subject_name}")
                return Response({
                    'success': True,
                    'message': '学习时长更新成功',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': False,
                'message': '时长数据无效',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except CourseProgress.DoesNotExist:
            return Response({
                'success': False,
                'message': '课程进度不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"更新学习时长失败: {str(e)}")
            return Response({
                'success': False,
                'message': '更新学习时长失败',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CourseContentViewSet(viewsets.ModelViewSet):
    """课程内容视图集"""
    
    queryset = CourseContent.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CourseContentCreateSerializer
        return CourseContentSerializer
    
    @extend_schema(
        summary="获取课程内容列表",
        description="获取所有课程内容的列表"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary="创建课程内容",
        description="创建新的课程内容，包含大纲和章节"
    )
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            content = serializer.save()
            
            response_serializer = CourseContentSerializer(content)
            logger.info(f"创建课程内容成功: {content.content_id}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"创建课程内容失败: {str(e)}")
            return Response(
                {"error": f"创建课程内容失败: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="获取课程内容详情",
        description="获取指定课程内容的详细信息"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary="更新课程内容",
        description="更新指定课程内容的信息"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @extend_schema(
        summary="删除课程内容",
        description="删除指定的课程内容"
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @extend_schema(
        summary="添加章节",
        description="为课程内容添加新章节",
        request=ChapterSerializer
    )
    @action(detail=True, methods=['post'])
    def add_chapter(self, request, pk=None):
        """添加章节"""
        try:
            content = self.get_object()
            serializer = ChapterSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            chapter = content.add_chapter(
                title=serializer.validated_data['title'],
                text=serializer.validated_data['text'],
                position=serializer.validated_data.get('position')
            )
            
            logger.info(f"为课程内容 {content.content_id} 添加章节: {chapter['title']}")
            return Response(chapter, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"添加章节失败: {str(e)}")
            return Response(
                {"error": f"添加章节失败: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="更新章节",
        description="更新指定章节的内容",
        request=ChapterSerializer
    )
    @action(detail=True, methods=['put'], url_path='chapters/(?P<chapter_index>[^/.]+)')
    def update_chapter(self, request, pk=None, chapter_index=None):
        """更新章节"""
        try:
            content = self.get_object()
            index = int(chapter_index)
            
            serializer = ChapterSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            
            success = content.update_chapter(
                index=index,
                title=serializer.validated_data.get('title'),
                text=serializer.validated_data.get('text')
            )
            
            if success:
                updated_chapter = content.get_chapter_by_index(index)
                logger.info(f"更新课程内容 {content.content_id} 第{index+1}章")
                return Response(updated_chapter)
            else:
                return Response(
                    {"error": "章节索引无效"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except (ValueError, IndexError):
            return Response(
                {"error": "无效的章节索引"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"更新章节失败: {str(e)}")
            return Response(
                {"error": f"更新章节失败: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        summary="删除章节",
        description="删除指定的章节"
    )
    @action(detail=True, methods=['delete'], url_path='chapters/(?P<chapter_index>[^/.]+)')
    def delete_chapter(self, request, pk=None, chapter_index=None):
        """删除章节"""
        try:
            content = self.get_object()
            index = int(chapter_index)
            
            success = content.remove_chapter(index)
            
            if success:
                logger.info(f"删除课程内容 {content.content_id} 第{index+1}章")
                return Response({"message": "章节删除成功"})
            else:
                return Response(
                    {"error": "章节索引无效"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except (ValueError, IndexError):
            return Response(
                {"error": "无效的章节索引"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"删除章节失败: {str(e)}")
            return Response(
                {"error": f"删除章节失败: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
