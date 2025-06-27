"""
数据库性能优化工具
"""
import time
import logging
from functools import wraps
from django.db import connection, transaction
from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


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
