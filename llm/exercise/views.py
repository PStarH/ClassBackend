from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
import json

from ..services.exercise_service import exercise_service


@api_view(['POST'])
@csrf_exempt
def generate_exercises(request):
    """
    生成个性化练习题
    
    请求参数：
    - user_id: 用户ID (必需)
    - course_progress_id: 课程进度ID (可选)
    - study_session_id: 学习会话ID (可选)
    - num_questions: 题目数量 (可选，系统会自动调整)
    
    返回：
    - success: 是否成功
    - exercises: 练习题列表
    - metadata: 元数据信息
    """
    if not exercise_service or not exercise_service.is_available():
        return JsonResponse(
            {'error': 'AI service is not available. Please check configuration.'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    user_id = request.data.get('user_id')
    if not user_id:
        return JsonResponse(
            {'error': 'Missing user_id in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    course_progress_id = request.data.get('course_progress_id')
    study_session_id = request.data.get('study_session_id')
    num_questions = request.data.get('num_questions')
    
    # 验证num_questions参数
    if num_questions is not None:
        try:
            num_questions = int(num_questions)
            if num_questions < 1 or num_questions > 20:
                return JsonResponse(
                    {'error': 'num_questions must be between 1 and 20'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return JsonResponse(
                {'error': 'num_questions must be a valid integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    try:
        result = exercise_service.generate_exercises(
            user_id=user_id,
            course_progress_id=course_progress_id,
            study_session_id=study_session_id,
            num_questions=num_questions
        )
        
        if result.get('success'):
            # 验证和标准化练习题格式
            validated_exercises = exercise_service.validate_exercise_format(result['exercises'])
            result['exercises'] = validated_exercises
            return JsonResponse(result)
        else:
            return JsonResponse(
                result,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to generate exercises', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@csrf_exempt
def generate_exercises_by_content(request):
    """
    根据指定内容生成练习题
    
    请求参数：
    - user_id: 用户ID (必需)
    - subject_name: 学科名称 (必需)
    - content: 学习内容 (必需)
    - difficulty: 难度等级 1-10 (可选，默认5)
    - num_questions: 题目数量 (可选，默认5)
    """
    if not exercise_service or not exercise_service.is_available():
        return JsonResponse(
            {'error': 'AI service is not available. Please check configuration.'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    user_id = request.data.get('user_id')
    subject_name = request.data.get('subject_name')
    content = request.data.get('content')
    
    if not all([user_id, subject_name, content]):
        return JsonResponse(
            {'error': 'Missing required parameters: user_id, subject_name, content'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    difficulty = request.data.get('difficulty', 5)
    num_questions = request.data.get('num_questions', 5)
    
    # 验证参数
    try:
        difficulty = int(difficulty)
        if difficulty < 1 or difficulty > 10:
            difficulty = 5
        
        num_questions = int(num_questions)
        if num_questions < 1 or num_questions > 20:
            num_questions = 5
    except ValueError:
        return JsonResponse(
            {'error': 'difficulty and num_questions must be valid integers'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # 构造用户学习数据
        user_data = {
            'subject_name': subject_name,
            'content_covered': [content],
            'difficulty': difficulty,
            'proficiency_level': 50,  # 默认中等熟练度
            'learning_hour_week': 5,  # 默认每周5小时
            'learning_hour_total': 20,  # 默认总计20小时
            'feedback': {}
        }
        
        # 生成练习题
        exercises = exercise_service._generate_exercises_with_ai(user_data, num_questions)
        validated_exercises = exercise_service.validate_exercise_format(exercises)
        
        result = {
            'success': True,
            'exercises': validated_exercises,
            'metadata': {
                'user_id': user_id,
                'subject_name': subject_name,
                'content': content[:100] + '...' if len(content) > 100 else content,
                'difficulty': difficulty,
                'num_questions': num_questions,
                'generated_at': datetime.now().isoformat()
            }
        }
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to generate exercises', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def exercise_service_status(request):
    """检查练习题服务状态"""
    try:
        is_available = exercise_service and exercise_service.is_available()
        service_info = {
            'service': 'exercise_generation',
            'status': 'available' if is_available else 'unavailable',
            'description': '练习题生成服务',
            'endpoints': {
                'generate_exercises': '/llm/exercise/generate/',
                'generate_by_content': '/llm/exercise/generate-by-content/',
                'service_status': '/llm/exercise/status/'
            }
        }
        
        if is_available:
            service_info.update({
                'features': [
                    '基于学习进度的个性化出题',
                    '根据熟练度和学习时长调整题量',
                    '仅基于已学内容出题',
                    '支持多种难度等级',
                    '提供详细答案解析'
                ],
                'supported_question_types': ['multiple_choice'],
                'question_count_range': [1, 20]
            })
        
        return JsonResponse(service_info)
        
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to get service status', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
