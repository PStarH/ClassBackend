"""
数据库优化管理命令
应用索引优化、连接池配置和性能调优
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.conf import settings
import logging
import time

from core.performance.advanced_database_config import (
    create_indexes_sql,
    optimize_database_settings,
    DatabaseHealthChecker,
    INDEX_OPTIMIZATION_CONFIG
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize database with indexes, connection pool and performance tuning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create optimized indexes for high frequency queries',
        )
        parser.add_argument(
            '--optimize-settings',
            action='store_true',
            help='Apply PostgreSQL performance settings',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run database health checks',
        )
        parser.add_argument(
            '--analyze-tables',
            action='store_true',
            help='Update table statistics for query optimizer',
        )
        parser.add_argument(
            '--vacuum-analyze',
            action='store_true',
            help='Run VACUUM ANALYZE on all tables',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without executing',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting database optimization...')
        )

        if options['health_check']:
            self.run_health_checks()

        if options['create_indexes']:
            self.create_optimized_indexes(dry_run=options['dry_run'])

        if options['optimize_settings']:
            self.apply_performance_settings(dry_run=options['dry_run'])

        if options['analyze_tables']:
            self.analyze_tables(dry_run=options['dry_run'])

        if options['vacuum_analyze']:
            self.vacuum_analyze_tables(dry_run=options['dry_run'])

        self.stdout.write(
            self.style.SUCCESS('✅ Database optimization completed!')
        )

    def run_health_checks(self):
        """运行数据库健康检查"""
        self.stdout.write(
            self.style.WARNING('📊 Running database health checks...')
        )

        # 连接池检查
        pool_status = DatabaseHealthChecker.check_connection_pool()
        if pool_status['status'] == 'ok':
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Connection pool: {pool_status['active_connections']}/{pool_status['max_connections']} "
                    f"({pool_status['usage_ratio']:.1%})"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Connection pool issue: {pool_status.get('error', 'High usage')}"
                )
            )

        # 慢查询检查
        slow_queries = DatabaseHealthChecker.check_slow_queries()
        if slow_queries['status'] == 'ok':
            self.stdout.write(
                self.style.SUCCESS("✅ No slow queries detected")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Found {len(slow_queries.get('slow_queries', []))} slow queries"
                )
            )

        # 数据库大小检查
        self.check_database_size()

        # 索引使用情况检查
        self.check_index_usage()

    def check_database_size(self):
        """检查数据库大小"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        pg_size_pretty(pg_database_size(current_database())) as db_size,
                        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections
                """)
                result = cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"💾 Database size: {result[0]}, Active connections: {result[1]}"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Size check failed: {e}")
            )

    def check_index_usage(self):
        """检查索引使用情况"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes 
                    WHERE idx_tup_read = 0 OR idx_tup_fetch = 0
                    ORDER BY schemaname, tablename;
                """)
                unused_indexes = cursor.fetchall()
                
                if unused_indexes:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Found {len(unused_indexes)} potentially unused indexes"
                        )
                    )
                    for idx in unused_indexes:
                        self.stdout.write(f"  - {idx[0]}.{idx[1]}.{idx[2]}")
                else:
                    self.stdout.write(
                        self.style.SUCCESS("✅ All indexes are being used")
                    )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Index usage check failed: {e}")
            )

    def create_optimized_indexes(self, dry_run=False):
        """创建优化索引"""
        self.stdout.write(
            self.style.WARNING('🔧 Creating optimized indexes...')
        )

        sql_statements = create_indexes_sql()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("📋 DRY RUN - Would execute the following SQL:")
            )
            for sql in sql_statements:
                self.stdout.write(f"  {sql}")
            return

        success_count = 0
        total_count = len(sql_statements)

        for sql in sql_statements:
            try:
                start_time = time.time()
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                
                execution_time = time.time() - start_time
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Index created in {execution_time:.2f}s: {sql[:80]}..."
                    )
                )
                success_count += 1
                
            except Exception as e:
                if "already exists" in str(e):
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Index already exists: {sql[:80]}...")
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Failed to create index: {e}")
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Index creation summary: {success_count}/{total_count} successful"
            )
        )

    def apply_performance_settings(self, dry_run=False):
        """应用性能设置"""
        self.stdout.write(
            self.style.WARNING('⚙️  Applying performance settings...')
        )

        settings_dict = optimize_database_settings()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("📋 DRY RUN - Would apply the following settings:")
            )
            for key, value in settings_dict.items():
                self.stdout.write(f"  {key} = {value}")
            return

        # 注意：这些设置需要数据库管理员权限，通常在postgresql.conf中配置
        self.stdout.write(
            self.style.WARNING(
                "⚠️  Performance settings require database admin privileges.\n"
                "   Please apply these settings in postgresql.conf:"
            )
        )
        
        for key, value in settings_dict.items():
            self.stdout.write(f"  {key} = {value}")

        # 应用一些可以在会话级别设置的参数
        session_settings = [
            "SET statement_timeout = '30s'",
            "SET lock_timeout = '5s'", 
            "SET idle_in_transaction_session_timeout = '10min'",
        ]

        for setting in session_settings:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(setting)
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Applied: {setting}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to apply {setting}: {e}")
                )

    def analyze_tables(self, dry_run=False):
        """更新表统计信息"""
        self.stdout.write(
            self.style.WARNING('📈 Updating table statistics...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("📋 DRY RUN - Would run ANALYZE on all tables")
            )
            return

        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("ANALYZE;")
            
            execution_time = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ ANALYZE completed in {execution_time:.2f}s"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ ANALYZE failed: {e}")
            )

    def vacuum_analyze_tables(self, dry_run=False):
        """运行VACUUM ANALYZE"""
        self.stdout.write(
            self.style.WARNING('🧹 Running VACUUM ANALYZE...')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("📋 DRY RUN - Would run VACUUM ANALYZE")
            )
            return

        # 获取所有用户表
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, tablename 
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY schemaname, tablename;
                """)
                tables = cursor.fetchall()

            for schema, table in tables:
                try:
                    start_time = time.time()
                    with connection.cursor() as cursor:
                        # 使用非阻塞的VACUUM
                        cursor.execute(f'VACUUM (ANALYZE, VERBOSE) "{schema}"."{table}";')
                    
                    execution_time = time.time() - start_time
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ VACUUM ANALYZE {schema}.{table} completed in {execution_time:.2f}s"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"❌ VACUUM ANALYZE {schema}.{table} failed: {e}")
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to get table list: {e}")
            )

    def generate_optimization_report(self):
        """生成优化报告"""
        self.stdout.write(
            self.style.SUCCESS('\n📊 Database Optimization Report')
        )
        self.stdout.write('=' * 50)
        
        # 连接配置
        self.stdout.write(f"🔗 Connection Max Age: {getattr(settings, 'DATABASES', {}).get('default', {}).get('CONN_MAX_AGE', 'Not set')}")
        self.stdout.write(f"🔒 Atomic Requests: {getattr(settings, 'DATABASES', {}).get('default', {}).get('ATOMIC_REQUESTS', 'Not set')}")
        
        # 缓存配置
        cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'Not configured')
        self.stdout.write(f"💾 Cache Backend: {cache_backend}")
        
        # 索引统计
        total_indexes = (
            len(INDEX_OPTIMIZATION_CONFIG['HIGH_FREQUENCY_INDEXES']) +
            len(INDEX_OPTIMIZATION_CONFIG['COMPOSITE_INDEXES']) +
            len(INDEX_OPTIMIZATION_CONFIG['PARTIAL_INDEXES'])
        )
        self.stdout.write(f"📈 Optimized Indexes: {total_indexes}")
        
        self.stdout.write('=' * 50)