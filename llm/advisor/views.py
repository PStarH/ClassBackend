from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view

from ..services.advisor_service import advisor_service


@api_view(['POST'])
def create_plan(request):
    """创建学习计划"""
    topic = request.data.get('topic')
    session_id = request.data.get('session_id')  # 可选的会话ID
    
    if not topic:
        return JsonResponse(
            {'error': 'Missing topic in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        plan = advisor_service.create_plan(topic, session_id)
        return JsonResponse(plan, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to create plan', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def update_plan(request):
    """根据反馈更新学习计划"""
    feedback_path = request.data.get('feedback_md_path')
    current_plan = request.data.get('plan')
    session_id = request.data.get('session_id')  # 可选的会话ID
    
    if not feedback_path or not current_plan:
        return JsonResponse(
            {'error': 'Missing feedback_md_path or plan in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        updates = advisor_service.update_plan(current_plan, feedback_path, session_id)
        return JsonResponse(updates, safe=False)
    except FileNotFoundError as e:
        return JsonResponse(
            {'error': 'Cannot read feedback file', 'details': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to update plan', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def chat_agent(request):
    """与教育规划代理聊天"""
    message = request.data.get('message')
    current_plan = request.data.get('plan')
    session_id = request.data.get('session_id')  # 可选的会话ID
    feedback_path = request.data.get('feedback_md_path')  # 可选参数
    
    if not message or not current_plan:
        return JsonResponse(
            {'error': 'Missing message or plan in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        result = advisor_service.chat_with_agent(message, current_plan, session_id, feedback_path)
        return JsonResponse(result, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to chat with agent', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_plan_from_session(request):
    """从会话中获取当前计划"""
    session_id = request.GET.get('session_id')
    
    if not session_id:
        return JsonResponse(
            {'error': 'Missing session_id parameter'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        plan = advisor_service.get_plan_from_session(session_id)
        if plan is None:
            return JsonResponse(
                {'error': 'No plan found for this session'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        return JsonResponse(plan, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to get plan from session', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def clear_session(request):
    """清除会话数据"""
    session_id = request.data.get('session_id')
    
    if not session_id:
        return JsonResponse(
            {'error': 'Missing session_id in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        advisor_service.clear_session(session_id)
        return JsonResponse({'message': 'Session cleared successfully'})
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to clear session', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

