"""
改进的数据库管理命令
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging
import time

from core.performance.optimizers import (
    query_profiler, connection_monitor, maintenance_scheduler,
    QueryProfiler, IndexAnalyzer, ConnectionPoolMonitor
)
from core.performance.cache_strategies import (
    adaptive_cache_manager, metrics_collector, warmup_manager
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '数据库和缓存优化管理工具'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=[
                'health-check', 'optimize', 'cleanup', 'analyze',
                'cache-stats', 'warmup', 'monitor', 'maintenance'
            ],
            help='要执行的操作'
        )
        
        parser.add_argument(
            '--tables',
            nargs='*',
            help='指定要操作的表名（用于maintenance操作）'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制执行操作'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细信息'
        )
        
        parser.add_argument(
            '--threshold',
            type=float,
            default=1.0,
            help='慢查询阈值（秒）'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(f"🚀 执行数据库优化操作: {action}")
        
        try:
            if action == 'health-check':
                self.health_check(options)
            elif action == 'optimize':
                self.optimize_database(options)
            elif action == 'cleanup':
                self.cleanup_database(options)
            elif action == 'analyze':
                self.analyze_performance(options)
            elif action == 'cache-stats':
                self.show_cache_stats(options)
            elif action == 'warmup':
                self.warmup_cache(options)
            elif action == 'monitor':
                self.monitor_system(options)
            elif action == 'maintenance':
                self.database_maintenance(options)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ 操作 '{action}' 完成")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ 操作失败: {str(e)}")
            )
            raise CommandError(f"Operation failed: {e}")

    def health_check(self, options):
        """健康检查"""
        self.stdout.write("🏥 执行系统健康检查...")
        
        # 数据库连接检查
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.stdout.write("✅ 数据库连接正常")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 数据库连接失败: {e}"))
        
        # 缓存检查
        try:
            test_key = f'health_check_{int(time.time())}'
            cache.set(test_key, 'test', 10)
            if cache.get(test_key) == 'test':
                cache.delete(test_key)
                self.stdout.write("✅ 缓存系统正常")
            else:
                self.stdout.write(self.style.WARNING("⚠️ 缓存系统异常"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 缓存系统失败: {e}"))
        
        # 连接池状态
        conn_stats = connection_monitor.get_detailed_connection_stats()
        self.stdout.write(f"📊 数据库连接统计:")
        self.stdout.write(f"  - 当前连接数: {conn_stats['current_connections']}")
        self.stdout.write(f"  - 最大连接数: {conn_stats['max_connections']}")
        
        if conn_stats['long_running_queries']:
            self.stdout.write(self.style.WARNING(
                f"⚠️ 发现 {len(conn_stats['long_running_queries'])} 个长时间运行的查询"
            ))
        
        # 缓存指标
        cache_metrics = metrics_collector.get_summary()
        self.stdout.write(f"📈 缓存指标:")
        self.stdout.write(f"  - 命中率: {cache_metrics['hit_rate']:.2%}")
        self.stdout.write(f"  - 请求/秒: {cache_metrics['requests_per_second']:.2f}")

    def optimize_database(self, options):
        """优化数据库"""
        self.stdout.write("🔧 开始数据库优化...")
        
        with connection.cursor() as cursor:
            # 更新统计信息
            self.stdout.write("📊 更新表统计信息...")
            cursor.execute("ANALYZE;")
            
            # 清理表空间
            self.stdout.write("🧹 清理表空间...")
            cursor.execute("VACUUM;")
            
            # 索引分析
            self.stdout.write("🔍 分析索引使用情况...")
            missing_indexes = IndexAnalyzer.analyze_missing_indexes()
            unused_indexes = IndexAnalyzer.analyze_unused_indexes()
            
            if missing_indexes:
                self.stdout.write("💡 建议创建的索引:")
                for suggestion in missing_indexes[:5]:  # 显示前5个
                    self.stdout.write(f"  - {suggestion['suggestion']}")
            
            if unused_indexes:
                self.stdout.write("🗑️ 可能需要删除的索引:")
                for suggestion in unused_indexes[:5]:  # 显示前5个
                    self.stdout.write(f"  - {suggestion['suggestion']}")

    def cleanup_database(self, options):
        """清理数据库"""
        self.stdout.write("🧹 开始数据库清理...")
        
        # 清理过期会话
        from apps.authentication.models import UserSession
        
        threshold = timezone.now() - timedelta(days=30)
        expired_sessions = UserSession.objects.filter(
            last_activity__lt=threshold
        )
        
        count = expired_sessions.count()
        if count > 0:
            if options['force'] or self.confirm_action(f"删除 {count} 个过期会话"):
                expired_sessions.delete()
                self.stdout.write(f"✅ 已删除 {count} 个过期会话")
        
        # 清理缓存中的过期项
        self.stdout.write("🧹 清理过期缓存...")
        try:
            # 这里可以添加Redis特定的清理逻辑
            cache.clear()
            self.stdout.write("✅ 缓存清理完成")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️ 缓存清理失败: {e}"))

    def analyze_performance(self, options):
        """性能分析"""
        self.stdout.write("📊 开始性能分析...")
        
        threshold = options.get('threshold', 1.0)
        
        # 慢查询分析
        slow_queries = query_profiler.get_slow_queries()
        if slow_queries:
            self.stdout.write(f"🐌 发现 {len(slow_queries)} 个慢查询:")
            for query in slow_queries[:5]:
                self.stdout.write(
                    f"  - {query.execution_time:.2f}s: {query.sql[:100]}..."
                )
        
        # 查询统计
        query_stats = query_profiler.get_query_statistics()
        self.stdout.write("📈 查询统计:")
        self.stdout.write(f"  - 总查询数: {query_stats['total_queries']}")
        self.stdout.write(f"  - 慢查询数: {query_stats['slow_queries']}")
        self.stdout.write(f"  - 慢查询比例: {query_stats['slow_query_percentage']:.2f}%")
        self.stdout.write(f"  - 平均执行时间: {query_stats['avg_execution_time']:.3f}s")
        
        # 表大小分析
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """)
            
            self.stdout.write("📦 最大的表:")
            for row in cursor.fetchall():
                self.stdout.write(f"  - {row[1]}: {row[2]}")

    def show_cache_stats(self, options):
        """显示缓存统计"""
        self.stdout.write("📊 缓存统计信息:")
        
        # 基本指标
        metrics = metrics_collector.get_summary()
        self.stdout.write(f"📈 基本指标:")
        for key, value in metrics.items():
            if isinstance(value, float):
                self.stdout.write(f"  - {key}: {value:.3f}")
            else:
                self.stdout.write(f"  - {key}: {value}")
        
        # 自适应缓存统计
        self.stdout.write(f"🎯 自适应缓存:")
        self.stdout.write(f"  - 跟踪的键数量: {len(adaptive_cache_manager.access_stats)}")
        
        # 显示访问最频繁的键
        top_keys = adaptive_cache_manager.access_stats.most_common(5)
        if top_keys:
            self.stdout.write("🔥 访问最频繁的键:")
            for key, count in top_keys:
                hit_rate = adaptive_cache_manager.calculate_hit_rate(key)
                self.stdout.write(f"  - {key[:50]}: {count} 次访问, {hit_rate:.2%} 命中率")

    def warmup_cache(self, options):
        """缓存预热"""
        self.stdout.write("🔥 开始缓存预热...")
        
        # 执行所有预热策略
        warmup_manager.execute_warmup()
        
        self.stdout.write("✅ 缓存预热完成")

    def monitor_system(self, options):
        """系统监控"""
        self.stdout.write("👁️ 启动系统监控...")
        
        try:
            while True:
                # 连接状态
                conn_stats = connection_monitor.get_detailed_connection_stats()
                
                # 缓存指标
                cache_metrics = metrics_collector.get_summary()
                
                # 显示实时状态
                self.stdout.write(f"\r📊 连接: {conn_stats['current_connections']}, "
                               f"缓存命中率: {cache_metrics['hit_rate']:.2%}, "
                               f"RPS: {cache_metrics['requests_per_second']:.1f}", 
                               ending='')
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            self.stdout.write("\n🛑 监控已停止")

    def database_maintenance(self, options):
        """数据库维护"""
        self.stdout.write("🔧 执行数据库维护...")
        
        tables = options.get('tables', [])
        force = options.get('force', False)
        
        if not tables:
            # 获取所有用户表
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """)
                tables = [row[0] for row in cursor.fetchall()]
        
        self.stdout.write(f"🎯 处理 {len(tables)} 个表...")
        
        for table in tables:
            self.stdout.write(f"🔧 维护表: {table}")
            
            operations = maintenance_scheduler.perform_maintenance(table, force)
            
            if operations:
                self.stdout.write(f"  ✅ 执行了: {', '.join(operations)}")
            else:
                self.stdout.write(f"  ℹ️ 无需维护")

    def confirm_action(self, message):
        """确认操作"""
        response = input(f"{message}? (y/N): ").lower().strip()
        return response in ['y', 'yes']
