"""
数据库性能优化工具 - 增强版
"""
import time
import logging
from functools import wraps
from typing import Dict, List, Any, Optional
from django.db import connection, transaction
from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryProfile:
    """查询性能分析结果"""
    sql: str
    execution_time: float
    rows_examined: int
    rows_sent: int
    timestamp: float
    is_slow: bool = False


class QueryProfiler:
    """查询性能分析器"""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_stats = defaultdict(list)
        self.enabled = getattr(settings, 'ENABLE_QUERY_PROFILING', False)
    
    def profile_query(self, sql: str) -> QueryProfile:
        """分析单个查询"""
        if not self.enabled:
            return None
        
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"EXPLAIN ANALYZE {sql}")
                explain_result = cursor.fetchall()
            
            execution_time = time.time() - start_time
            
            # 解析EXPLAIN ANALYZE结果
            rows_examined = 0
            rows_sent = 0
            
            for row in explain_result:
                line = str(row[0])
                if 'rows=' in line:
                    # 简单的行数提取，实际可能需要更复杂的解析
                    import re
                    matches = re.findall(r'rows=(\d+)', line)
                    if matches:
                        rows_examined += int(matches[0])
            
            profile = QueryProfile(
                sql=sql,
                execution_time=execution_time,
                rows_examined=rows_examined,
                rows_sent=rows_sent,
                timestamp=time.time(),
                is_slow=execution_time > self.slow_query_threshold
            )
            
            # 记录到统计中
            self.query_stats[sql].append(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"查询分析失败: {e}")
            return None
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryProfile]:
        """获取慢查询列表"""
        slow_queries = []
        
        for sql, profiles in self.query_stats.items():
            for profile in profiles:
                if profile.is_slow:
                    slow_queries.append(profile)
        
        # 按执行时间排序
        slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
        return slow_queries[:limit]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        total_queries = sum(len(profiles) for profiles in self.query_stats.values())
        slow_queries = sum(
            1 for profiles in self.query_stats.values()
            for profile in profiles if profile.is_slow
        )
        
        avg_execution_time = 0
        if total_queries > 0:
            total_time = sum(
                profile.execution_time 
                for profiles in self.query_stats.values()
                for profile in profiles
            )
            avg_execution_time = total_time / total_queries
        
        return {
            'total_queries': total_queries,
            'slow_queries': slow_queries,
            'slow_query_percentage': (slow_queries / total_queries * 100) if total_queries > 0 else 0,
            'avg_execution_time': avg_execution_time,
            'unique_queries': len(self.query_stats)
        }


class IndexAnalyzer:
    """索引分析器"""
    
    @staticmethod
    def analyze_missing_indexes() -> List[Dict[str, Any]]:
        """分析缺失的索引"""
        suggestions = []
        
        with connection.cursor() as cursor:
            # 查找可能需要索引的查询
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation,
                    most_common_vals
                FROM pg_stats 
                WHERE schemaname = 'public' 
                AND n_distinct > 100
                AND correlation < 0.1
                ORDER BY n_distinct DESC;
            """)
            
            stats = cursor.fetchall()
            
            for stat in stats:
                suggestions.append({
                    'table': stat[1],
                    'column': stat[2],
                    'distinct_values': stat[3],
                    'correlation': stat[4],
                    'suggestion': f"考虑在 {stat[1]}.{stat[2]} 上创建索引"
                })
        
        return suggestions
    
    @staticmethod
    def analyze_unused_indexes() -> List[Dict[str, Any]]:
        """分析未使用的索引"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE idx_scan < 10  -- 扫描次数很少
                ORDER BY idx_scan ASC;
            """)
            
            return [
                {
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'reads': row[3],
                    'fetches': row[4],
                    'scans': row[5],
                    'suggestion': f"索引 {row[2]} 使用频率很低，考虑删除"
                }
                for row in cursor.fetchall()
            ]


class ConnectionPoolMonitor:
    """连接池监控器"""
    
    @staticmethod
    def get_detailed_connection_stats() -> Dict[str, Any]:
        """获取详细的连接统计"""
        with connection.cursor() as cursor:
            # 获取当前连接状态
            cursor.execute("""
                SELECT 
                    state,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (now() - state_change))) as avg_duration
                FROM pg_stat_activity 
                WHERE datname = current_database()
                GROUP BY state;
            """)
            
            connection_states = {row[0]: {'count': row[1], 'avg_duration': row[2]} 
                               for row in cursor.fetchall()}
            
            # 获取慢查询
            cursor.execute("""
                SELECT 
                    pid,
                    state,
                    query_start,
                    state_change,
                    EXTRACT(EPOCH FROM (now() - query_start)) as duration,
                    LEFT(query, 100) as query_preview
                FROM pg_stat_activity 
                WHERE datname = current_database()
                AND state = 'active'
                AND query_start < now() - interval '10 seconds'
                ORDER BY query_start;
            """)
            
            long_running_queries = [
                {
                    'pid': row[0],
                    'duration': row[4],
                    'query_preview': row[5]
                }
                for row in cursor.fetchall()
            ]
            
            return {
                'connection_states': connection_states,
                'long_running_queries': long_running_queries,
                'max_connections': ConnectionPoolMonitor._get_max_connections(),
                'current_connections': sum(state['count'] for state in connection_states.values())
            }
    
    @staticmethod
    def _get_max_connections() -> int:
        """获取最大连接数配置"""
        with connection.cursor() as cursor:
            cursor.execute("SHOW max_connections;")
            return int(cursor.fetchone()[0])
    
    @staticmethod
    def kill_idle_connections(idle_threshold_minutes: int = 30):
        """终止空闲连接"""
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity 
                WHERE datname = current_database()
                AND state = 'idle'
                AND state_change < now() - interval '{idle_threshold_minutes} minutes';
            """)
            
            killed_count = cursor.rowcount
            logger.info(f"终止了 {killed_count} 个空闲连接")
            return killed_count


class TableMaintenanceScheduler:
    """表维护调度器"""
    
    def __init__(self):
        self.maintenance_history = {}
    
    def should_vacuum(self, table_name: str) -> bool:
        """检查表是否需要清理"""
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    n_dead_tup,
                    n_live_tup,
                    (n_dead_tup::float / GREATEST(n_live_tup, 1)) as dead_ratio
                FROM pg_stat_user_tables 
                WHERE relname = %s;
            """, [table_name])
            
            result = cursor.fetchone()
            if not result:
                return False
            
            dead_tuples, live_tuples, dead_ratio = result
            
            # 如果死元组比例超过20%，建议清理
            return dead_ratio > 0.2 or dead_tuples > 10000
    
    def should_analyze(self, table_name: str) -> bool:
        """检查表是否需要分析"""
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    last_analyze,
                    last_autoanalyze,
                    n_mod_since_analyze
                FROM pg_stat_user_tables 
                WHERE relname = %s;
            """, [table_name])
            
            result = cursor.fetchone()
            if not result:
                return False
            
            last_analyze, last_autoanalyze, n_mod_since_analyze = result
            
            # 如果修改的行数超过1000或者7天没有分析，建议分析
            import datetime
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            
            return (n_mod_since_analyze > 1000 or 
                   (last_analyze and last_analyze < seven_days_ago) or
                   (last_autoanalyze and last_autoanalyze < seven_days_ago))
    
    def perform_maintenance(self, table_name: str, force: bool = False):
        """执行表维护"""
        maintenance_performed = []
        
        if force or self.should_vacuum(table_name):
            with connection.cursor() as cursor:
                cursor.execute(f"VACUUM {table_name};")
                maintenance_performed.append('VACUUM')
                logger.info(f"对表 {table_name} 执行了 VACUUM")
        
        if force or self.should_analyze(table_name):
            with connection.cursor() as cursor:
                cursor.execute(f"ANALYZE {table_name};")
                maintenance_performed.append('ANALYZE')
                logger.info(f"对表 {table_name} 执行了 ANALYZE")
        
        if maintenance_performed:
            self.maintenance_history[table_name] = {
                'timestamp': time.time(),
                'operations': maintenance_performed
            }
        
        return maintenance_performed


# 全局实例
query_profiler = QueryProfiler()
connection_monitor = ConnectionPoolMonitor()
maintenance_scheduler = TableMaintenanceScheduler()


class DatabaseOptimizer:
    """数据库性能优化器"""
    
    @staticmethod
    def analyze_slow_queries(threshold_seconds=1.0):
        """分析慢查询"""
        queries = connection.queries
        slow_queries = []
        
        for query in queries:
            if float(query.get('time', 0)) > threshold_seconds:
                slow_queries.append({
                    'sql': query['sql'],
                    'time': query['time'],
                    'params': query.get('params', [])
                })
        
        if slow_queries:
            logger.warning(f"发现 {len(slow_queries)} 个慢查询")
            for query in slow_queries:
                logger.warning(f"慢查询 ({query['time']}s): {query['sql']}")
        
        return slow_queries
    
    @staticmethod
    def optimize_queryset(queryset):
        """优化查询集"""
        if isinstance(queryset, QuerySet):
            # 自动添加 select_related 和 prefetch_related
            model = queryset.model
            
            # 获取外键字段
            foreign_keys = []
            many_to_many = []
            
            for field in model._meta.get_fields():
                if field.is_relation:
                    if field.many_to_one or field.one_to_one:
                        foreign_keys.append(field.name)
                    elif field.many_to_many or field.one_to_many:
                        many_to_many.append(field.name)
            
            # 应用优化
            if foreign_keys:
                queryset = queryset.select_related(*foreign_keys[:5])  # 限制数量避免过度优化
            
            if many_to_many:
                queryset = queryset.prefetch_related(*many_to_many[:3])
        
        return queryset
    
    @staticmethod
    def get_database_stats():
        """获取数据库统计信息"""
        with connection.cursor() as cursor:
            # 获取表大小统计
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE schemaname = 'public'
                ORDER BY tablename, attname;
            """)
            
            stats = cursor.fetchall()
            
            # 获取索引使用情况
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes
                ORDER BY idx_tup_read DESC;
            """)
            
            index_stats = cursor.fetchall()
            
            return {
                'table_stats': stats,
                'index_stats': index_stats,
                'total_queries': len(connection.queries)
            }


def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_queries = len(connection.queries)
            
            execution_time = end_time - start_time
            query_count = end_queries - start_queries
            
            # 记录性能指标
            if execution_time > 1.0 or query_count > 10:
                logger.warning(
                    f"性能警告 - 函数: {func.__name__}, "
                    f"执行时间: {execution_time:.2f}s, "
                    f"查询次数: {query_count}"
                )
    
    return wrapper


class QueryCache:
    """查询缓存"""
    
    @staticmethod
    def cache_queryset(cache_key, queryset, timeout=300):
        """缓存查询结果"""
        try:
            # 执行查询并缓存结果
            results = list(queryset)
            cache.set(cache_key, results, timeout)
            return results
        except Exception as e:
            logger.error(f"查询缓存失败: {str(e)}")
            return list(queryset)
    
    @staticmethod
    def get_cached_queryset(cache_key):
        """获取缓存的查询结果"""
        return cache.get(cache_key)
    
    @staticmethod
    def invalidate_cache(pattern):
        """失效缓存"""
        try:
            cache.delete_many(cache.keys(pattern))
        except Exception as e:
            logger.error(f"缓存失效失败: {str(e)}")


class BatchProcessor:
    """批处理器"""
    
    @staticmethod
    def bulk_create_optimized(model, objects, batch_size=1000):
        """优化的批量创建"""
        created_objects = []
        
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    created_batch = model.objects.bulk_create(
                        batch,
                        ignore_conflicts=True
                    )
                    created_objects.extend(created_batch)
            except Exception as e:
                logger.error(f"批量创建失败 (批次 {i//batch_size + 1}): {str(e)}")
        
        return created_objects
    
    @staticmethod
    def bulk_update_optimized(model, objects, fields, batch_size=1000):
        """优化的批量更新"""
        updated_count = 0
        
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    updated_count += model.objects.bulk_update(
                        batch,
                        fields,
                        batch_size=batch_size
                    )
            except Exception as e:
                logger.error(f"批量更新失败 (批次 {i//batch_size + 1}): {str(e)}")
        
        return updated_count


class DatabaseConnectionPool:
    """数据库连接池管理"""
    
    @staticmethod
    def get_connection_stats():
        """获取连接池状态"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    state_change
                FROM pg_stat_activity 
                WHERE datname = current_database()
                ORDER BY query_start DESC;
            """)
            
            connections = cursor.fetchall()
            
            active_count = sum(1 for conn in connections if conn[4] == 'active')
            idle_count = sum(1 for conn in connections if conn[4] == 'idle')
            
            return {
                'total': len(connections),
                'active': active_count,
                'idle': idle_count,
                'connections': connections
            }
    
    @staticmethod
    def close_idle_connections():
        """关闭空闲连接"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                AND state = 'idle'
                AND state_change < now() - interval '1 hour';
            """)
            
            terminated = cursor.rowcount
            logger.info(f"关闭了 {terminated} 个空闲连接")
            return terminated


# 缓存失效信号处理
@receiver([post_save, post_delete])
def invalidate_related_cache(sender, **kwargs):
    """自动失效相关缓存"""
    model_name = sender.__name__.lower()
    
    # 失效模型相关的缓存
    cache_patterns = [
        f"api_response:*:{model_name}:*",
        f"queryset:{model_name}:*",
        f"count:{model_name}:*"
    ]
    
    for pattern in cache_patterns:
        try:
            QueryCache.invalidate_cache(pattern)
        except Exception as e:
            logger.error(f"缓存失效失败 {pattern}: {str(e)}")


class DatabaseMaintenanceService:
    """数据库维护服务"""
    
    @staticmethod
    def analyze_table_statistics():
        """分析表统计信息"""
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE;")
            logger.info("数据库统计信息更新完成")
    
    @staticmethod
    def vacuum_tables():
        """清理表空间"""
        with connection.cursor() as cursor:
            cursor.execute("VACUUM;")
            logger.info("数据库清理完成")
    
    @staticmethod
    def reindex_tables():
        """重建索引"""
        with connection.cursor() as cursor:
            cursor.execute("REINDEX DATABASE %s;" % settings.DATABASES['default']['NAME'])
            logger.info("索引重建完成")
    
    @staticmethod
    def get_table_sizes():
        """获取表大小"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
            """)
            
            return cursor.fetchall()
    
    @staticmethod
    def cleanup_old_sessions(days=30):
        """清理旧会话"""
        from django.utils import timezone
        from datetime import timedelta
        from apps.authentication.models import UserSession
        
        threshold = timezone.now() - timedelta(days=days)
        deleted_count, _ = UserSession.objects.filter(
            last_activity__lt=threshold
        ).delete()
        
        logger.info(f"清理了 {deleted_count} 个旧会话记录")
        return deleted_count
