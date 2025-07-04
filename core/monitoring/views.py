"""
性能监控API视图
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from core.monitoring.performance import performance_monitor
import json


@api_view(['GET'])
@permission_classes([IsAdminUser])
def performance_dashboard(request):
    """性能监控仪表板"""
    try:
        dashboard_data = performance_monitor.get_dashboard_data()
        return Response(dashboard_data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_summary(request):
    """获取指标摘要"""
    hours = int(request.GET.get('hours', 1))
    
    try:
        summary = performance_monitor.collector.get_metrics_summary(hours=hours)
        return Response(summary, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def slow_operations(request):
    """获取慢操作"""
    threshold_ms = float(request.GET.get('threshold_ms', 1000))
    limit = int(request.GET.get('limit', 10))
    
    try:
        slow_ops = performance_monitor.collector.get_slow_operations(
            threshold_ms=threshold_ms, 
            limit=limit
        )
        return Response({'slow_operations': slow_ops}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def cost_analysis(request):
    """获取成本分析"""
    hours = int(request.GET.get('hours', 24))
    
    try:
        analysis = performance_monitor.get_cost_analysis(hours=hours)
        return Response(analysis, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def database_stats(request):
    """获取数据库统计"""
    try:
        stats = performance_monitor.db_monitor.get_connection_stats()
        return Response(stats, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@cache_page(60 * 5)  # 缓存5分钟
def system_health(request):
    """系统健康检查 - 公开接口"""
    try:
        health = performance_monitor._assess_system_health()
        
        # 简化的健康状态，不暴露敏感信息
        public_health = {
            'status': health['overall'],
            'timestamp': performance_monitor.collector.metrics[-1].timestamp if performance_monitor.collector.metrics else 0,
            'services': {
                'database': health['database'],
                'cache': health['cache'],
                'llm': health['llm']
            }
        }
        
        return JsonResponse(public_health)
    except Exception as e:
        return JsonResponse(
            {'status': 'error', 'message': 'Health check failed'}, 
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_metrics(request):
    """清空指标数据"""
    try:
        performance_monitor.collector.metrics.clear()
        performance_monitor.cache_monitor.hit_count = 0
        performance_monitor.cache_monitor.miss_count = 0
        performance_monitor.db_monitor.query_count = 0
        
        return Response(
            {'message': 'Metrics cleared successfully'}, 
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def export_metrics(request):
    """导出指标数据"""
    hours = int(request.GET.get('hours', 24))
    format_type = request.GET.get('format', 'json')
    
    try:
        summary = performance_monitor.collector.get_metrics_summary(hours=hours)
        slow_ops = performance_monitor.collector.get_slow_operations()
        cost_analysis = performance_monitor.get_cost_analysis(hours=hours)
        
        export_data = {
            'export_timestamp': performance_monitor.collector.metrics[-1].timestamp if performance_monitor.collector.metrics else 0,
            'time_period_hours': hours,
            'metrics_summary': summary,
            'slow_operations': slow_ops,
            'cost_analysis': cost_analysis
        }
        
        if format_type == 'json':
            response = JsonResponse(export_data)
            response['Content-Disposition'] = f'attachment; filename="metrics_export_{hours}h.json"'
            return response
        else:
            return Response(
                {'error': 'Unsupported format. Use format=json'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
