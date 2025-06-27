"""
数据库安全和性能管理命令
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '数据库安全和性能优化工具'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=[
                'analyze_security', 'optimize_performance', 'cleanup_data',
                'warmup_cache', 'security_report', 'performance_report'
            ],
            help='要执行的操作'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='数据保留天数（用于清理操作）'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批处理大小'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(f"开始执行: {action}")
        
        if action == 'analyze_security':
            self.analyze_security()
        elif action == 'optimize_performance':
            self.optimize_performance()
        elif action == 'cleanup_data':
            self.cleanup_data(options['days'])
        elif action == 'warmup_cache':
            self.warmup_cache()
        elif action == 'security_report':
            self.security_report()
        elif action == 'performance_report':
            self.performance_report()
        
        self.stdout.write(
            self.style.SUCCESS(f"完成执行: {action}")
        )

    def analyze_security(self):
        """分析安全状况"""
        from apps.authentication.models import User, UserSession
        
        self.stdout.write("正在分析用户安全状况...")
        
        # 分析用户安全状态
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        locked_users = User.objects.filter(
            account_locked_until__gt=timezone.now()
        ).count()
        unverified_emails = User.objects.filter(
            email_verified=False,
            is_active=True
        ).count()
        weak_passwords = User.objects.filter(
            password_changed_at__isnull=True
        ).count()
        two_factor_enabled = User.objects.filter(
            two_factor_enabled=True
        ).count()
        
        # 分析会话安全
        suspicious_sessions = UserSession.objects.filter(
            is_suspicious=True,
            is_active=True
        ).count()
        
        old_sessions = UserSession.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=7),
            is_active=True
        ).count()
        
        # 输出安全报告
        self.stdout.write("\n=== 安全分析报告 ===")
        self.stdout.write(f"总用户数: {total_users}")
        self.stdout.write(f"活跃用户数: {active_users}")
        self.stdout.write(f"被锁定用户数: {locked_users}")
        self.stdout.write(f"未验证邮箱用户数: {unverified_emails}")
        self.stdout.write(f"未设密码用户数: {weak_passwords}")
        self.stdout.write(f"启用双因素认证用户数: {two_factor_enabled}")
        self.stdout.write(f"可疑会话数: {suspicious_sessions}")
        self.stdout.write(f"长期活跃会话数: {old_sessions}")
        
        # 安全建议
        if unverified_emails > 0:
            self.stdout.write(
                self.style.WARNING(f"建议: {unverified_emails} 个用户需要验证邮箱")
            )
        
        if weak_passwords > 0:
            self.stdout.write(
                self.style.WARNING(f"建议: {weak_passwords} 个用户需要强制修改密码")
            )
        
        if suspicious_sessions > 0:
            self.stdout.write(
                self.style.WARNING(f"警告: {suspicious_sessions} 个可疑会话需要处理")
            )

    def optimize_performance(self):
        """优化数据库性能"""
        self.stdout.write("正在优化数据库性能...")
        
        with connection.cursor() as cursor:
            # 更新统计信息
            self.stdout.write("更新表统计信息...")
            cursor.execute("ANALYZE;")
            
            # 清理无用数据
            self.stdout.write("清理表空间...")
            cursor.execute("VACUUM;")
            
            # 检查索引使用情况
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                ORDER BY schemaname, tablename;
            """)
            
            unused_indexes = cursor.fetchall()
            
            if unused_indexes:
                self.stdout.write("\n=== 未使用的索引 ===")
                for index in unused_indexes:
                    self.stdout.write(
                        f"表: {index[1]}, 索引: {index[2]} (从未使用)"
                    )
            
            # 检查大表
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
            
            large_tables = cursor.fetchall()
            
            self.stdout.write("\n=== 最大的表 ===")
            for table in large_tables:
                self.stdout.write(f"表: {table[1]}, 大小: {table[2]}")

    def cleanup_data(self, days):
        """清理旧数据"""
        from apps.authentication.models import UserSession
        from apps.learning_plans.models import StudySession
        
        threshold = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"清理 {days} 天前的数据...")
        
        # 清理过期会话
        expired_sessions = UserSession.objects.filter(
            last_activity__lt=threshold,
            is_active=False
        )
        session_count = expired_sessions.count()
        if session_count > 0:
            expired_sessions.delete()
            self.stdout.write(f"清理了 {session_count} 个过期会话")
        
        # 清理软删除的用户数据（保留1年）
        if days >= 365:
            from apps.authentication.models import User
            deleted_threshold = timezone.now() - timedelta(days=365)
            
            deleted_users = User.objects.filter(
                is_deleted=True,
                deleted_at__lt=deleted_threshold
            )
            user_count = deleted_users.count()
            if user_count > 0:
                deleted_users.delete()  # 硬删除
                self.stdout.write(f"永久删除了 {user_count} 个用户记录")
        
        # 清理审计日志（保留3个月）
        if days >= 90:
            # 这里可以添加审计日志清理逻辑
            pass

    def warmup_cache(self):
        """预热缓存"""
        from core.performance.cache_strategies import CacheWarmupService
        from apps.authentication.models import User
        
        self.stdout.write("开始预热缓存...")
        
        # 预热活跃用户数据
        active_users = User.objects.filter(
            is_active=True,
            last_login__gte=timezone.now() - timedelta(days=7)
        )[:100]  # 最近7天活跃的前100个用户
        
        for user in active_users:
            try:
                CacheWarmupService.warmup_user_data(user.uuid)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"用户 {user.uuid} 缓存预热失败: {str(e)}")
                )
        
        # 预热热门内容
        try:
            CacheWarmupService.warmup_popular_content()
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"热门内容预热失败: {str(e)}")
            )
        
        self.stdout.write("缓存预热完成")

    def security_report(self):
        """生成安全报告"""
        from apps.authentication.models import User, UserSession
        
        # 收集安全指标
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        
        # 登录失败统计
        failed_logins_24h = User.objects.filter(
            last_failed_login__gte=last_24h
        ).count()
        
        # 新用户注册
        new_users_24h = User.objects.filter(
            date_joined__gte=last_24h
        ).count()
        
        # 可疑活动
        suspicious_sessions = UserSession.objects.filter(
            is_suspicious=True,
            created_at__gte=last_week
        ).count()
        
        # 账户锁定
        locked_accounts = User.objects.filter(
            account_locked_until__gt=now
        ).count()
        
        self.stdout.write("\n=== 安全报告 (最近24小时) ===")
        self.stdout.write(f"失败登录次数: {failed_logins_24h}")
        self.stdout.write(f"新用户注册: {new_users_24h}")
        self.stdout.write(f"可疑会话 (最近7天): {suspicious_sessions}")
        self.stdout.write(f"当前锁定账户: {locked_accounts}")
        
        # 安全建议
        if failed_logins_24h > 100:
            self.stdout.write(
                self.style.WARNING("警告: 失败登录次数异常，可能存在暴力破解攻击")
            )
        
        if suspicious_sessions > 10:
            self.stdout.write(
                self.style.WARNING("警告: 可疑会话数量较多，建议检查")
            )

    def performance_report(self):
        """生成性能报告"""
        from core.performance.cache_strategies import CacheAnalytics
        from core.performance.optimizers import DatabaseOptimizer
        
        # 缓存统计
        cache_stats = CacheAnalytics.get_cache_stats()
        
        # 数据库统计
        db_stats = DatabaseOptimizer.get_database_stats()
        
        self.stdout.write("\n=== 性能报告 ===")
        
        if cache_stats:
            self.stdout.write(f"Redis 版本: {cache_stats.get('redis_version', 'N/A')}")
            self.stdout.write(f"内存使用: {cache_stats.get('used_memory', 'N/A')}")
            self.stdout.write(f"缓存命中率: {cache_stats.get('hit_rate', 0):.2f}%")
            self.stdout.write(f"连接客户端数: {cache_stats.get('connected_clients', 'N/A')}")
        
        self.stdout.write(f"数据库查询总数: {db_stats.get('total_queries', 'N/A')}")
        
        # 慢查询分析
        slow_queries = DatabaseOptimizer.analyze_slow_queries()
        if slow_queries:
            self.stdout.write(f"\n发现 {len(slow_queries)} 个慢查询")
            for query in slow_queries[:5]:  # 显示前5个
                self.stdout.write(f"  - {query['time']}s: {query['sql'][:100]}...")
