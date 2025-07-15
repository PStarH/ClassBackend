"""
AI Services API Views
This module provides API endpoints for AI-powered services.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_status(request):
    """
    Get the status of all AI services
    """
    try:
        from llm.services.exercise_service import get_exercise_service
        from llm.services.teacher_service import get_teacher_service
        from llm.services.advisor_service import get_advisor_service
        
        exercise_service = get_exercise_service()
        teacher_service = get_teacher_service()
        advisor_service = get_advisor_service()
        
        return Response({
            'status': 'success',
            'services': {
                'exercise': {
                    'available': exercise_service.is_available(),
                    'name': 'Exercise Generation Service'
                },
                'teacher': {
                    'available': teacher_service.is_available(),
                    'name': 'AI Teacher Service'
                },
                'advisor': {
                    'available': advisor_service.is_available(),
                    'name': 'Learning Advisor Service'
                }
            }
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_exercises(request):
    """
    Generate AI exercises for a user
    """
    try:
        from llm.services.exercise_service import get_exercise_service
        
        user_id = str(request.user.uuid)
        num_questions = request.data.get('num_questions', 5)
        difficulty = request.data.get('difficulty', 'medium')
        topic = request.data.get('topic', '')
        
        exercise_service = get_exercise_service()
        exercises = exercise_service.generate_exercises(
            user_id=user_id,
            num_questions=num_questions,
            difficulty=difficulty,
            topic=topic
        )
        
        return Response({
            'status': 'success',
            'exercises': exercises
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_teaching_help(request):
    """
    Get AI teaching assistance
    """
    try:
        from llm.services.teacher_service import get_teacher_service
        
        question = request.data.get('question', '')
        context = request.data.get('context', '')
        
        if not question:
            return Response({
                'status': 'error',
                'message': 'Question is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        teacher_service = get_teacher_service()
        response = teacher_service.provide_teaching_help(
            question=question,
            context=context
        )
        
        return Response({
            'status': 'success',
            'response': response
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_learning_advice(request):
    """
    Get personalized learning advice
    """
    try:
        from llm.services.advisor_service import get_advisor_service
        
        user_id = str(request.user.uuid)
        current_progress = request.data.get('current_progress', {})
        goals = request.data.get('goals', [])
        
        advisor_service = get_advisor_service()
        advice = advisor_service.provide_learning_advice(
            user_id=user_id,
            current_progress=current_progress,
            goals=goals
        )
        
        return Response({
            'status': 'success',
            'advice': advice
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
