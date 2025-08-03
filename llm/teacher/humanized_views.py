"""
Humanized AI Teacher API Views
提供人性化AI教师交互的API端点
"""
import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..services.humanized_teacher_service import get_humanized_teacher_service
from apps.authentication.models import User


class HumanizedTeacherView(View):
    """人性化AI教师视图"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    async def post(self, request):
        """处理AI教师交互请求"""
        
        try:
            # 解析请求数据
            data = json.loads(request.body)
            question = data.get('question', '').strip()
            user_id = data.get('user_id')
            context = data.get('context', {})
            
            # 验证必需参数
            if not question:
                return JsonResponse({
                    'success': False,
                    'error': 'Question is required'
                }, status=400)
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'error': 'User ID is required'
                }, status=400)
            
            # 验证用户存在
            try:
                user = User.objects.get(uuid=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'User not found'
                }, status=404)
            
            # 获取人性化教师服务
            teacher_service = get_humanized_teacher_service()
            
            # 生成个性化回应
            result = await teacher_service.generate_personalized_response(
                user_id=user_id,
                question=question,
                context=context
            )
            
            if result['success']:
                response_data = {
                    'success': True,
                    'response': result['response'],
                    'metadata': {
                        'emotional_tone': result['emotional_tone'],
                        'learning_style_adapted': result['learning_style_adapted'],
                        'teaching_strategy': result['teaching_strategy'],
                        'encouragement_level': result['encouragement_level'],
                        'personalization_applied': result['personalization_applied']
                    },
                    'next_steps': result['next_steps'],
                    'timestamp': timezone.now().isoformat()
                }
                
                return JsonResponse(response_data)
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'fallback_response': result.get('fallback_response')
                }, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON format'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_help(request):
    """快速帮助端点 - 为登录用户提供即时帮助"""
    
    try:
        question = request.data.get('question', '').strip()
        context = request.data.get('context', {})
        
        if not question:
            return Response({
                'success': False,
                'error': 'Question is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取当前用户ID
        user_id = str(request.user.uuid)
        
        # 获取教师服务
        teacher_service = get_humanized_teacher_service()
        
        # 使用异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                teacher_service.generate_personalized_response(
                    user_id=user_id,
                    question=question,
                    context=context
                )
            )
        finally:
            loop.close()
        
        if result['success']:
            return Response({
                'success': True,
                'response': result['response'],
                'metadata': {
                    'emotional_tone': result['emotional_tone'],
                    'learning_style_adapted': result['learning_style_adapted'],
                    'teaching_strategy': result['teaching_strategy'],
                    'encouragement_level': result['encouragement_level']
                },
                'next_steps': result['next_steps']
            })
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'fallback_response': result.get('fallback_response')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def teacher_status(request):
    """获取AI教师服务状态"""
    
    try:
        teacher_service = get_humanized_teacher_service()
        
        status_info = {
            'service_available': teacher_service.is_available(),
            'features': {
                'emotional_adaptation': True,
                'learning_style_personalization': True,
                'difficulty_detection': True,
                'progress_tracking': True,
                'multilingual_support': False  # 可以后续添加
            },
            'personality_traits': list(teacher_service.personality_traits.keys()),
            'supported_emotions': list(teacher_service.emotional_responses.keys()),
            'learning_styles': list(teacher_service.learning_style_adaptations.keys()),
            'version': '2.0.0',
            'last_updated': '2025-01-01'
        }
        
        return Response({
            'success': True,
            'status': status_info
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Unable to retrieve status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def feedback(request):
    """用户反馈端点 - 收集用户对AI教师的反馈"""
    
    try:
        interaction_id = request.data.get('interaction_id')
        rating = request.data.get('rating')  # 1-5
        feedback_text = request.data.get('feedback', '').strip()
        helpful = request.data.get('helpful')  # True/False
        
        # 验证评分
        if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
            return Response({
                'success': False,
                'error': 'Rating must be an integer between 1 and 5'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 这里可以将反馈存储到数据库
        # 暂时返回成功响应
        feedback_data = {
            'user_id': str(request.user.uuid),
            'interaction_id': interaction_id,
            'rating': rating,
            'feedback': feedback_text,
            'helpful': helpful,
            'timestamp': timezone.now().isoformat()
        }
        
        # TODO: 存储到数据库
        # UserFeedback.objects.create(**feedback_data)
        
        return Response({
            'success': True,
            'message': 'Thank you for your feedback! It helps us improve the AI teacher.',
            'feedback_recorded': feedback_data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Unable to process feedback: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def learning_suggestions(request):
    """获取个性化学习建议"""
    
    try:
        user_id = str(request.user.uuid)
        teacher_service = get_humanized_teacher_service()
        
        # 模拟生成学习建议
        suggestions = {
            'daily_goals': [
                "Complete 2-3 coding exercises",
                "Review one new concept",
                "Practice debugging skills"
            ],
            'focus_areas': [
                "Python loops and iteration",
                "Function definition and calling",
                "Error handling basics"
            ],
            'recommended_resources': [
                {
                    'title': 'Interactive Python Tutorial',
                    'type': 'tutorial',
                    'difficulty': 'beginner',
                    'estimated_time': '30 minutes'
                },
                {
                    'title': 'Coding Practice Problems',
                    'type': 'exercises',
                    'difficulty': 'intermediate',
                    'estimated_time': '45 minutes'
                }
            ],
            'motivation_message': "You're making great progress! Keep up the consistent practice. 🌟",
            'next_milestone': "Complete 10 Python exercises to earn your 'Loop Master' badge!"
        }
        
        return Response({
            'success': True,
            'suggestions': suggestions,
            'personalized_for': request.user.email,
            'generated_at': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Unable to generate suggestions: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 异步视图适配器
def async_view(async_func):
    """将异步视图函数适配为同步"""
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()
    return wrapper