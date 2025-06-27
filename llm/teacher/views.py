from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view

from ..services.teacher_service import teacher_service


@api_view(['POST'])
def create_outline(request):
    """
    生成课程大纲。
    请求参数应包含 'topic'。
    响应：包含 'index' 和 'title' 的 JSON 数组。
    """
    topic = request.data.get('topic')
    if not topic:
        return JsonResponse(
            {'error': 'Missing topic in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        outline = teacher_service.create_outline(topic)
        return JsonResponse(outline, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to create outline', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def generate_section_detail(request):
    """
    生成单个章节的详细文本和 DOT 图表。
    请求参数应包含 'index' 和 'title'。
    响应：包含以下字段的 JSON 对象：
      - 'index', 'title'
      - 'content': 包含 '[graph_ID]' 标记的详细文本，用于标记图表渲染位置
      - 'graphs': 以 graph_ID 为键、DOT 定义字符串为值的对象
    """
    index = request.data.get('index')
    title = request.data.get('title')
    if index is None or title is None:
        return JsonResponse(
            {'error': 'Missing index or title in request'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        detail = teacher_service.generate_section_detail(str(index), title)
        return JsonResponse(detail, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': 'Failed to generate section detail', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
