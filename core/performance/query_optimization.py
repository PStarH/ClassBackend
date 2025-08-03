"""
查询优化工具和中间件
包含查询分析、N+1检测、自动优化等功能
基于建议的最佳实践实现
"""
import time
import logging
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, Counter
from contextvars import ContextVar
from functools import wraps

from django.db import connection, connections
from django.db.models import QuerySet, Prefetch
from django.db.models.query import ModelIterable
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination, CursorPagination

logger = logging.getLogger(__name__)

# 上下文变量用于追踪查询
query_context: ContextVar[Dict] = ContextVar('query_context', default={})

# 查询性能配置
SLOW_QUERY_THRESHOLD = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)  # 1秒
N_PLUS_ONE_THRESHOLD = 10  # N+1查询检测阈值
ENABLE_QUERY_OPTIMIZATION = getattr(settings, 'ENABLE_QUERY_OPTIMIZATION', True)


class QueryAnalyzer:
    """查询分析器"""
    
    def __init__(self):
        self.queries = []
        self.start_time = None
        self.similar_queries = defaultdict(list)
    
    def start_analysis(self):
        """开始查询分析"""
        self.start_time = time.time()
        self.queries = []
        self.similar_queries.clear()
    
    def add_query(self, query_info: Dict[str, Any]):
        """添加查询信息"""
        query_info['timestamp'] = time.time()
        self.queries.append(query_info)
        
        # 分组相似查询
        sql_template = self._normalize_sql(query_info['sql'])
        self.similar_queries[sql_template].append(query_info)
    
    def _normalize_sql(self, sql: str) -> str:
        """标准化SQL语句，用于检测相似查询"""
        import re
        
        # 移除参数值，保留结构
        sql = re.sub(r"'[^']*'", "'?'", sql)  # 字符串参数
        sql = re.sub(r'\b\d+\b', '?', sql)    # 数字参数
        sql = re.sub(r'\s+', ' ', sql)        # 多余空格
        
        return sql.strip().lower()
    
    def detect_n_plus_one(self) -> List[Dict[str, Any]]:
        """检测N+1查询问题"""
        issues = []
        
        for sql_template, query_list in self.similar_queries.items():
            if len(query_list) > N_PLUS_ONE_THRESHOLD:
                total_time = sum(q['time'] for q in query_list)
                
                issues.append({
                    'type': 'n_plus_one',
                    'sql_template': sql_template,
                    'count': len(query_list),
                    'total_time': total_time,
                    'avg_time': total_time / len(query_list),
                    'queries': query_list[:5],  # 只保留前5个示例
                    'suggestion': self._suggest_optimization(sql_template)
                })
        
        return issues
    
    def detect_slow_queries(self) -> List[Dict[str, Any]]:
        """检测慢查询"""
        slow_queries = []
        
        for query in self.queries:
            if query['time'] > SLOW_QUERY_THRESHOLD:
                slow_queries.append({
                    'type': 'slow_query',
                    'sql': query['sql'],
                    'time': query['time'],
                    'suggestion': self._suggest_slow_query_optimization(query['sql'])
                })
        
        return slow_queries
    
    def _suggest_optimization(self, sql_template: str) -> str:
        """建议查询优化方案"""
        if 'select' in sql_template and 'join' not in sql_template:
            if 'where' in sql_template and 'id' in sql_template:
                return "Consider using select_related() or prefetch_related() to reduce multiple queries"
            elif 'foreign key' in sql_template:
                return "Use select_related() for forward ForeignKey relationships"
        
        return "Consider query optimization techniques like prefetching or caching"
    
    def _suggest_slow_query_optimization(self, sql: str) -> str:
        """建议慢查询优化方案"""
        suggestions = []
        
        if 'ORDER BY' in sql.upper() and 'LIMIT' not in sql.upper():
            suggestions.append("Add LIMIT clause to reduce result set")
        
        if 'LIKE' in sql.upper():
            suggestions.append("Consider using full-text search or database-specific search features")
        
        if sql.count('JOIN') > 3:
            suggestions.append("Consider breaking complex joins into multiple queries")
        
        if not suggestions:
            suggestions.append("Review indexes and query structure")
        
        return "; ".join(suggestions)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        if not self.start_time:
            return {}
        
        total_time = time.time() - self.start_time
        total_queries = len(self.queries)
        total_query_time = sum(q['time'] for q in self.queries)
        
        n_plus_one_issues = self.detect_n_plus_one()
        slow_queries = self.detect_slow_queries()
        
        return {
            'total_time': total_time,
            'total_queries': total_queries,
            'total_query_time': total_query_time,
            'avg_query_time': total_query_time / total_queries if total_queries > 0 else 0,
            'n_plus_one_issues': len(n_plus_one_issues),
            'slow_queries': len(slow_queries),
            'issues': n_plus_one_issues + slow_queries,
            'query_efficiency': (total_time - total_query_time) / total_time if total_time > 0 else 1
        }


class QueryOptimizationMiddleware:
    """查询优化中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if not ENABLE_QUERY_OPTIMIZATION:
            return self.get_response(request)
        
        # 初始化查询分析器
        analyzer = QueryAnalyzer()
        analyzer.start_analysis()
        
        # 设置上下文
        query_context.set({'analyzer': analyzer, 'request': request})
        
        # 监控查询
        with QueryMonitor(analyzer):
            response = self.get_response(request)
        
        # 分析结果
        summary = analyzer.get_summary()
        
        # 记录性能问题
        if summary.get('n_plus_one_issues', 0) > 0 or summary.get('slow_queries', 0) > 0:
            self._log_performance_issues(request, summary)
        
        # 添加调试头
        if settings.DEBUG:
            response['X-Query-Count'] = str(summary.get('total_queries', 0))
            response['X-Query-Time'] = f"{summary.get('total_query_time', 0):.3f}s"
        
        return response
    
    def _log_performance_issues(self, request, summary: Dict[str, Any]):
        """记录性能问题"""
        logger.warning(
            f"Query performance issues detected for {request.path}: "
            f"N+1 issues: {summary.get('n_plus_one_issues', 0)}, "
            f"Slow queries: {summary.get('slow_queries', 0)}, "
            f"Total queries: {summary.get('total_queries', 0)}"
        )
        
        # 缓存问题报告
        issues_key = f"query_issues:{timezone.now().strftime('%Y%m%d')}"
        issues = cache.get(issues_key, [])
        issues.append({
            'path': request.path,
            'method': request.method,
            'summary': summary,
            'timestamp': timezone.now().isoformat()
        })
        cache.set(issues_key, issues, 86400)  # 24小时


class QueryMonitor:
    """查询监控器 - 上下文管理器"""
    
    def __init__(self, analyzer: QueryAnalyzer):
        self.analyzer = analyzer
        self.original_execute = None
        self.original_executemany = None
    
    def __enter__(self):
        # 替换数据库执行方法
        self.original_execute = connection.cursor().execute
        self.original_executemany = connection.cursor().executemany
        
        def monitored_execute(cursor, sql, params=None):
            start_time = time.time()
            result = self.original_execute(sql, params)
            end_time = time.time()
            
            self.analyzer.add_query({
                'sql': sql,
                'params': params,
                'time': end_time - start_time
            })
            
            return result
        
        def monitored_executemany(cursor, sql, param_list):
            start_time = time.time()
            result = self.original_executemany(sql, param_list)
            end_time = time.time()
            
            self.analyzer.add_query({
                'sql': sql,
                'params': param_list,
                'time': end_time - start_time,
                'batch': True
            })
            
            return result
        
        # 应用监控
        for conn in connections.all():
            cursor = conn.cursor()
            cursor.execute = lambda sql, params=None: monitored_execute(cursor, sql, params)
            cursor.executemany = lambda sql, param_list: monitored_executemany(cursor, sql, param_list)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始方法
        for conn in connections.all():
            cursor = conn.cursor()
            cursor.execute = self.original_execute
            cursor.executemany = self.original_executemany


class OptimizedQuerySet(QuerySet):
    """优化的QuerySet"""
    
    def smart_prefetch(self, *relations):
        """智能预取相关对象"""
        optimized_relations = []
        
        for relation in relations:
            if isinstance(relation, str):
                # 分析关系类型并选择最佳策略
                if self._is_forward_relation(relation):
                    optimized_relations.append(relation)  # select_related
                else:
                    # 使用prefetch_related with queryset optimization
                    optimized_queryset = self._get_optimized_queryset_for_relation(relation)
                    if optimized_queryset:
                        optimized_relations.append(
                            Prefetch(relation, queryset=optimized_queryset)
                        )
                    else:
                        optimized_relations.append(relation)
        
        return self.prefetch_related(*optimized_relations)
    
    def _is_forward_relation(self, relation: str) -> bool:
        """检查是否是正向关系（适合select_related）"""
        try:
            field_names = relation.split('__')
            current_model = self.model
            
            for field_name in field_names:
                field = current_model._meta.get_field(field_name)
                if hasattr(field, 'related_model'):
                    if hasattr(field, 'many_to_many') and field.many_to_many:
                        return False  # ManyToMany关系
                    if hasattr(field, 'one_to_many') and field.one_to_many:
                        return False  # 反向ForeignKey关系
                    current_model = field.related_model
                else:
                    return False
            
            return True
        except:
            return False
    
    def _get_optimized_queryset_for_relation(self, relation: str) -> Optional[QuerySet]:
        """为关系获取优化的queryset"""
        try:
            # 根据关系类型返回优化的queryset
            field_names = relation.split('__')
            current_model = self.model
            
            for field_name in field_names[:-1]:
                field = current_model._meta.get_field(field_name)
                current_model = field.related_model
            
            final_field = current_model._meta.get_field(field_names[-1])
            related_model = final_field.related_model
            
            # 返回只选择必要字段的queryset
            essential_fields = self._get_essential_fields(related_model)
            return related_model.objects.only(*essential_fields)
            
        except:
            return None
    
    def _get_essential_fields(self, model) -> List[str]:
        """获取模型的关键字段"""
        essential_fields = ['id']
        
        # 添加常用字段
        for field in model._meta.fields:
            if field.name in ['name', 'title', 'slug', 'created_at', 'updated_at']:
                essential_fields.append(field.name)
        
        return essential_fields


class CursorBasedPagination(CursorPagination):
    """基于游标的分页器 - 性能更好"""
    
    page_size = 20
    max_page_size = 100
    cursor_query_param = 'cursor'
    page_size_query_param = 'page_size'
    ordering = '-created_at'  # 默认排序
    
    def get_paginated_response_schema(self, schema):
        """自定义分页响应schema"""
        return {
            'type': 'object',
            'properties': {
                'next': {'type': 'string', 'nullable': True},
                'previous': {'type': 'string', 'nullable': True},
                'results': schema,
                'count': {'type': 'integer'},
                'page_info': {
                    'type': 'object',
                    'properties': {
                        'has_next_page': {'type': 'boolean'},
                        'has_previous_page': {'type': 'boolean'},
                        'start_cursor': {'type': 'string', 'nullable': True},
                        'end_cursor': {'type': 'string', 'nullable': True},
                    }
                }
            }
        }


def optimize_queryset(func):
    """查询优化装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 检查是否有优化建议
        context = query_context.get({})
        analyzer = context.get('analyzer')
        
        if analyzer:
            # 在函数执行前记录查询数量
            initial_query_count = len(analyzer.queries)
        
        result = func(*args, **kwargs)
        
        if analyzer:
            # 检查是否产生了过多查询
            new_queries = len(analyzer.queries) - initial_query_count
            if new_queries > 10:  # 阈值
                logger.warning(
                    f"Function {func.__name__} generated {new_queries} database queries. "
                    "Consider using select_related() or prefetch_related()"
                )
        
        return result
    
    return wrapper


class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def optimize_list_view_queryset(queryset: QuerySet, request=None) -> QuerySet:
        """优化列表视图的queryset"""
        # 自动添加select_related for ForeignKey fields
        select_related_fields = []
        prefetch_related_fields = []
        
        for field in queryset.model._meta.fields:
            if hasattr(field, 'related_model') and field.related_model:
                if not hasattr(field, 'many_to_many') or not field.many_to_many:
                    select_related_fields.append(field.name)
        
        # 自动添加prefetch_related for reverse relations
        for field in queryset.model._meta.related_objects:
            if hasattr(field, 'get_accessor_name'):
                prefetch_related_fields.append(field.get_accessor_name())
        
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields[:5])  # 限制数量
        
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields[:3])  # 限制数量
        
        return queryset
    
    @staticmethod
    def optimize_detail_view_queryset(queryset: QuerySet, request=None) -> QuerySet:
        """优化详情视图的queryset"""
        # 为详情视图预取所有相关数据
        select_related_fields = []
        prefetch_related_fields = []
        
        # 获取所有ForeignKey字段
        for field in queryset.model._meta.fields:
            if hasattr(field, 'related_model') and field.related_model:
                select_related_fields.append(field.name)
        
        # 获取所有反向关系
        for field in queryset.model._meta.related_objects:
            if hasattr(field, 'get_accessor_name'):
                prefetch_related_fields.append(field.get_accessor_name())
        
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)
        
        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)
        
        return queryset


# 性能监控工具
class QueryPerformanceMonitor:
    """查询性能监控器"""
    
    @staticmethod
    def get_daily_stats() -> Dict[str, Any]:
        """获取每日统计"""
        today = timezone.now().strftime('%Y%m%d')
        issues_key = f"query_issues:{today}"
        issues = cache.get(issues_key, [])
        
        total_issues = len(issues)
        n_plus_one_count = sum(1 for issue in issues if issue.get('summary', {}).get('n_plus_one_issues', 0) > 0)
        slow_query_count = sum(1 for issue in issues if issue.get('summary', {}).get('slow_queries', 0) > 0)
        
        # 统计最常见的问题路径
        path_counter = Counter(issue.get('path', 'unknown') for issue in issues)
        
        return {
            'date': today,
            'total_issues': total_issues,
            'n_plus_one_count': n_plus_one_count,
            'slow_query_count': slow_query_count,
            'top_problematic_paths': path_counter.most_common(10)
        }
    
    @staticmethod
    def generate_optimization_report() -> Dict[str, Any]:
        """生成优化报告"""
        stats = QueryPerformanceMonitor.get_daily_stats()
        
        recommendations = []
        
        if stats['n_plus_one_count'] > 0:
            recommendations.append({
                'type': 'n_plus_one',
                'priority': 'high',
                'description': f"Detected {stats['n_plus_one_count']} N+1 query issues",
                'solution': "Use select_related() and prefetch_related() to optimize database queries"
            })
        
        if stats['slow_query_count'] > 0:
            recommendations.append({
                'type': 'slow_queries',
                'priority': 'medium',
                'description': f"Detected {stats['slow_query_count']} slow queries",
                'solution': "Review query indexes and consider query optimization"
            })
        
        return {
            'stats': stats,
            'recommendations': recommendations,
            'generated_at': timezone.now().isoformat()
        }


# 导出主要组件
__all__ = [
    'QueryOptimizationMiddleware',
    'QueryAnalyzer',
    'OptimizedQuerySet',
    'CursorBasedPagination',
    'QueryOptimizer',
    'QueryPerformanceMonitor',
    'optimize_queryset',
]