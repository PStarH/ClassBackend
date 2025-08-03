"""
高级数据库配置 - PostgreSQL连接池优化、索引管理和性能调优
基于建议的最佳实践实现
"""
from decouple import config
import logging

logger = logging.getLogger(__name__)

# PostgreSQL 连接池配置 (PgBouncer类似的Django配置)
DATABASE_POOL_SETTINGS = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='education_platform'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            # SSL 配置
            'sslmode': config('DB_SSL_MODE', default='prefer'),
            'sslcert': config('DB_SSL_CERT', default=''),
            'sslkey': config('DB_SSL_KEY', default=''),
            'sslrootcert': config('DB_SSL_ROOT_CERT', default=''),
            
            # 连接超时设置
            'connect_timeout': config('DB_CONNECT_TIMEOUT', default=10, cast=int),
            'statement_timeout': config('DB_STATEMENT_TIMEOUT', default=30000, cast=int),  # 30秒
            'lock_timeout': config('DB_LOCK_TIMEOUT', default=5000, cast=int),  # 5秒，避免长事务锁表
            
            # 事务隔离级别 - 避免长事务
            'options': '-c default_transaction_isolation=read_committed -c statement_timeout=30s -c lock_timeout=5s',
            
            # PostgreSQL 性能参数
            'init_command': """
                SET synchronous_commit = off;
                SET wal_buffers = '16MB';
                SET checkpoint_completion_target = 0.7;
                SET effective_cache_size = '1GB';
                SET shared_buffers = '256MB';
                SET work_mem = '4MB';
                SET maintenance_work_mem = '64MB';
                SET random_page_cost = 1.1;
                SET effective_io_concurrency = 200;
            """,
        },
        
        # Django 连接池设置
        'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=600, cast=int),  # 10分钟连接保持
        'CONN_HEALTH_CHECKS': True,
        'ATOMIC_REQUESTS': config('DB_ATOMIC_REQUESTS', default=False, cast=bool),  # 避免长事务，手动控制
        
        # 连接池参数
        'CONNECTION_POOL_SIZE': config('DB_POOL_SIZE', default=20, cast=int),
        'CONNECTION_POOL_MAX_OVERFLOW': config('DB_POOL_MAX_OVERFLOW', default=10, cast=int),
        'CONNECTION_POOL_TIMEOUT': config('DB_POOL_TIMEOUT', default=30, cast=int),
        'CONNECTION_POOL_RECYCLE': config('DB_POOL_RECYCLE', default=3600, cast=int),  # 1小时回收连接
    }
}

# 读写分离配置 (如果使用主从复制)
DATABASE_ROUTER_SETTINGS = {
    'default': DATABASE_POOL_SETTINGS['default'],
    'replica': {
        **DATABASE_POOL_SETTINGS['default'],
        'HOST': config('DB_REPLICA_HOST', default=DATABASE_POOL_SETTINGS['default']['HOST']),
        'OPTIONS': {
            **DATABASE_POOL_SETTINGS['default']['OPTIONS'],
            'options': '-c default_transaction_isolation=read_committed -c transaction_read_only=on',
        }
    }
}

# 索引优化配置
INDEX_OPTIMIZATION_CONFIG = {
    # 高频查询字段索引
    'HIGH_FREQUENCY_INDEXES': [
        # 用户相关
        ('authentication_user', ['email'], {'unique': True}),
        ('authentication_user', ['username'], {'unique': True}),
        ('authentication_user', ['is_active', 'date_joined']),
        
        # 课程相关
        ('courses_course', ['title']),
        ('courses_course', ['created_at', 'is_active']),
        ('courses_course', ['category', 'difficulty_level']),
        
        # 学习计划相关 - 避免N+1查询
        ('learning_plans_learningplan', ['user_id', 'status']),
        ('learning_plans_learningplan', ['created_at', 'updated_at']),
        ('learning_plans_studysession', ['learning_plan_id', 'session_date']),
        
        # AI服务相关
        ('ai_services_aiinteraction', ['user_id', 'created_at']),
        ('ai_services_aiinteraction', ['interaction_type', 'status']),
    ],
    
    # 复合索引优化查询性能
    'COMPOSITE_INDEXES': [
        # 用户活动分析
        ('authentication_user', ['is_active', 'last_login', 'date_joined']),
        
        # 课程进度查询
        ('courses_courseprogress', ['user_id', 'course_id', 'status']),
        ('courses_courseprogress', ['course_id', 'completion_percentage', 'updated_at']),
        
        # 学习分析查询
        ('learning_plans_studysession', ['user_id', 'session_date', 'duration']),
        ('learning_plans_studysession', ['learning_plan_id', 'status', 'session_date']),
        
        # AI交互分析
        ('ai_services_aiinteraction', ['user_id', 'interaction_type', 'created_at']),
    ],
    
    # 局部索引 (条件索引)
    'PARTIAL_INDEXES': [
        # 只索引活跃用户
        ('authentication_user', ['last_login'], {'condition': 'is_active = true'}),
        
        # 只索引进行中的学习计划
        ('learning_plans_learningplan', ['user_id', 'updated_at'], {'condition': "status = 'in_progress'"}),
        
        # 只索引最近的AI交互
        ('ai_services_aiinteraction', ['user_id', 'created_at'], 
         {'condition': "created_at > (NOW() - INTERVAL '30 days')"}),
    ],
    
    # 全文搜索索引
    'FULLTEXT_INDEXES': [
        ('courses_course', ['title', 'description'], {'language': 'chinese'}),
        ('courses_coursecontent', ['content'], {'language': 'chinese'}),
    ]
}

# 数据库维护配置
DATABASE_MAINTENANCE_CONFIG = {
    # 自动清理配置
    'AUTO_VACUUM_SETTINGS': {
        'autovacuum': 'on',
        'autovacuum_vacuum_scale_factor': 0.1,
        'autovacuum_analyze_scale_factor': 0.05,
        'autovacuum_vacuum_cost_delay': '10ms',
        'autovacuum_vacuum_cost_limit': 200,
    },
    
    # 统计信息更新
    'STATISTICS_TARGET': 100,
    
    # 检查点配置
    'CHECKPOINT_SETTINGS': {
        'checkpoint_timeout': '5min',
        'checkpoint_completion_target': 0.7,
        'wal_buffers': '16MB',
        'checkpoint_segments': 32,
    }
}

# 监控查询配置
SLOW_QUERY_MONITORING = {
    'ENABLED': config('SLOW_QUERY_MONITORING', default=True, cast=bool),
    'THRESHOLD': config('SLOW_QUERY_THRESHOLD', default=1.0, cast=float),  # 1秒
    'LOG_LEVEL': 'WARNING',
    'INCLUDE_EXPLAIN': config('SLOW_QUERY_EXPLAIN', default=False, cast=bool),
}

# 缓存失效策略
DATABASE_CACHE_INVALIDATION = {
    'STRATEGIES': {
        'user_data': {
            'tables': ['authentication_user', 'authentication_userprofile'],
            'cache_keys': ['user_profile_{user_id}', 'user_permissions_{user_id}'],
            'ttl': 1800,  # 30分钟
        },
        'course_data': {
            'tables': ['courses_course', 'courses_coursecontent'],
            'cache_keys': ['course_{course_id}', 'course_content_{course_id}'],
            'ttl': 3600,  # 1小时
        },
        'learning_progress': {
            'tables': ['learning_plans_learningplan', 'learning_plans_studysession'],
            'cache_keys': ['learning_plan_{plan_id}', 'user_progress_{user_id}'],
            'ttl': 600,  # 10分钟
        }
    }
}

def get_database_config(environment='development'):
    """
    根据环境获取数据库配置
    """
    if environment == 'production':
        config = DATABASE_ROUTER_SETTINGS.copy()
        # 生产环境使用更严格的设置
        config['default']['CONN_MAX_AGE'] = 300  # 5分钟
        config['default']['OPTIONS']['statement_timeout'] = 10000  # 10秒
        return config
    elif environment == 'testing':
        config = DATABASE_POOL_SETTINGS.copy()
        # 测试环境快速连接
        config['default']['CONN_MAX_AGE'] = 0
        config['default']['OPTIONS']['connect_timeout'] = 5
        return config
    else:
        return DATABASE_POOL_SETTINGS

def create_indexes_sql():
    """
    生成创建索引的SQL语句
    """
    sql_statements = []
    
    # 普通索引
    for table, columns, options in INDEX_OPTIMIZATION_CONFIG['HIGH_FREQUENCY_INDEXES']:
        unique = 'UNIQUE ' if options.get('unique', False) else ''
        index_name = f"idx_{table}_{'_'.join(columns)}"
        sql = f"CREATE {unique}INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)});"
        sql_statements.append(sql)
    
    # 复合索引
    for table, columns, options in INDEX_OPTIMIZATION_CONFIG['COMPOSITE_INDEXES']:
        index_name = f"idx_{table}_composite_{'_'.join(columns[:2])}"
        sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)});"
        sql_statements.append(sql)
    
    # 局部索引
    for table, columns, options in INDEX_OPTIMIZATION_CONFIG['PARTIAL_INDEXES']:
        condition = options.get('condition', '')
        index_name = f"idx_{table}_partial_{'_'.join(columns)}"
        sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table} ({', '.join(columns)}) WHERE {condition};"
        sql_statements.append(sql)
    
    return sql_statements

def optimize_database_settings():
    """
    返回PostgreSQL优化设置
    """
    return {
        # 内存设置
        'shared_buffers': '256MB',  # 系统内存的25%
        'effective_cache_size': '1GB',  # 系统内存的75%
        'work_mem': '4MB',  # 每个查询操作的内存
        'maintenance_work_mem': '64MB',  # 维护操作内存
        
        # 检查点设置
        'checkpoint_completion_target': 0.7,
        'wal_buffers': '16MB',
        'checkpoint_timeout': '5min',
        
        # 查询规划器
        'random_page_cost': 1.1,  # SSD优化
        'effective_io_concurrency': 200,  # SSD并发
        
        # 连接设置
        'max_connections': 100,
        'superuser_reserved_connections': 3,
        
        # 日志设置
        'log_min_duration_statement': 1000,  # 记录慢查询
        'log_checkpoints': 'on',
        'log_connections': 'on',
        'log_disconnections': 'on',
        'log_lock_waits': 'on',
        
        # 自动清理
        'autovacuum': 'on',
        'autovacuum_vacuum_scale_factor': 0.1,
        'autovacuum_analyze_scale_factor': 0.05,
    }

class DatabaseHealthChecker:
    """数据库健康检查器"""
    
    @staticmethod
    def check_connection_pool():
        """检查连接池状态"""
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                active_connections = cursor.fetchone()[0]
                
                cursor.execute("SELECT setting::int FROM pg_settings WHERE name = 'max_connections';")
                max_connections = cursor.fetchone()[0]
                
                usage_ratio = active_connections / max_connections
                if usage_ratio > 0.8:
                    logger.warning(f"High connection usage: {usage_ratio:.2%}")
                
                return {
                    'active_connections': active_connections,
                    'max_connections': max_connections,
                    'usage_ratio': usage_ratio,
                    'status': 'warning' if usage_ratio > 0.8 else 'ok'
                }
        except Exception as e:
            logger.error(f"Connection pool check failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def check_slow_queries():
        """检查慢查询"""
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT query, mean_time, calls, total_time
                    FROM pg_stat_statements 
                    WHERE mean_time > 1000 
                    ORDER BY mean_time DESC 
                    LIMIT 10;
                """)
                slow_queries = cursor.fetchall()
                return {
                    'slow_queries': slow_queries,
                    'status': 'warning' if slow_queries else 'ok'
                }
        except Exception as e:
            logger.error(f"Slow query check failed: {e}")
            return {'status': 'error', 'error': str(e)}

# 导出配置
__all__ = [
    'DATABASE_POOL_SETTINGS',
    'DATABASE_ROUTER_SETTINGS', 
    'INDEX_OPTIMIZATION_CONFIG',
    'DATABASE_MAINTENANCE_CONFIG',
    'SLOW_QUERY_MONITORING',
    'DATABASE_CACHE_INVALIDATION',
    'get_database_config',
    'create_indexes_sql',
    'optimize_database_settings',
    'DatabaseHealthChecker'
]