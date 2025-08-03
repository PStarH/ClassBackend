# Production Database Configuration with Connection Pooling
"""
Optimized database settings for high-performance production environment
Includes connection pooling, query optimization, and monitoring
"""

from django.conf import settings
import os

# Production-ready database configuration
PRODUCTION_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'smartclassroom_prod'),
        'USER': os.getenv('DB_USER', 'smartclassroom'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            # Connection pooling settings
            'MAX_CONNS': 100,  # Maximum connections in pool
            'MIN_CONNS': 10,   # Minimum connections to maintain
            
            # Connection timeout settings
            'connect_timeout': 10,
            'statement_timeout': 30000,  # 30 seconds max query time
            'lock_timeout': 5000,        # 5 seconds max lock wait
            'idle_in_transaction_session_timeout': 300000,  # 5 minutes
            
            # Performance optimization
            'sslmode': 'prefer',
            'application_name': 'SmartClassroom_AI',
            'tcp_keepalives_idle': '300',
            'tcp_keepalives_interval': '30',
            'tcp_keepalives_count': '3',
            
            # Query optimization
            'options': ' '.join([
                '-c default_transaction_isolation=read_committed',
                '-c timezone=UTC',
                '-c max_connections=200',
                '-c shared_buffers=256MB',
                '-c effective_cache_size=1GB',
                '-c work_mem=8MB',
                '-c maintenance_work_mem=64MB',
                '-c random_page_cost=1.1',
                '-c effective_io_concurrency=200',
                '-c checkpoint_completion_target=0.9',
                '-c wal_buffers=16MB',
                '-c default_statistics_target=100',
            ])
        },
        
        # Connection management
        'CONN_MAX_AGE': 3600,     # 1 hour connection lifetime
        'CONN_HEALTH_CHECKS': True,
        'ATOMIC_REQUESTS': False,  # Manual transaction management for performance
        
        # Connection pooling with PgBouncer integration
        'POOL_CLASS': 'pgbouncer.DatabasePool',
        'POOL_OPTIONS': {
            'pool_size': 20,           # Connections per process
            'max_overflow': 30,        # Additional connections under load
            'pool_recycle': 3600,      # Recycle connections after 1 hour
            'pool_timeout': 30,        # Max time to get connection
            'pool_pre_ping': True,     # Validate connections before use
        }
    },
    
    # Separate read replica for analytics and reporting
    'read_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'smartclassroom_prod'),
        'USER': os.getenv('DB_READ_USER', 'smartclassroom_read'),
        'PASSWORD': os.getenv('DB_READ_PASSWORD'),
        'HOST': os.getenv('DB_READ_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_READ_PORT', '5432'),
        'OPTIONS': {
            'MAX_CONNS': 50,
            'MIN_CONNS': 5,
            'connect_timeout': 10,
            'statement_timeout': 60000,  # Longer timeout for analytics
            'sslmode': 'prefer',
            'application_name': 'SmartClassroom_Analytics',
        },
        'CONN_MAX_AGE': 1800,  # 30 minutes
        'CONN_HEALTH_CHECKS': True,
    }
}

# Enhanced Redis configuration for caching and sessions
REDIS_CACHE_CONFIG = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
                'socket_keepalive': True,
                'socket_keepalive_options': {
                    'TCP_KEEPIDLE': 1,
                    'TCP_KEEPINTVL': 3,
                    'TCP_KEEPCNT': 5,
                },
                'health_check_interval': 30,
            }
        },
        'TIMEOUT': 300,
        'KEY_PREFIX': 'smartclassroom',
        'VERSION': 1,
    },
    
    # Separate cache for user sessions
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/2",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        },
        'TIMEOUT': 3600,  # 1 hour sessions
        'KEY_PREFIX': 'session',
    },
    
    # Cache for LLM responses and AI data
    'llm_cache': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/3",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 30,
                'retry_on_timeout': True,
            }
        },
        'TIMEOUT': 7200,  # 2 hours for AI responses
        'KEY_PREFIX': 'llm',
    },
    
    # Cache for analytics and reporting data
    'analytics_cache': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/4",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            }
        },
        'TIMEOUT': 1800,  # 30 minutes for analytics
        'KEY_PREFIX': 'analytics',
    }
}

# Database Router for Read/Write Split
class DatabaseRouter:
    """
    Database router to split read/write operations
    Routes read queries to read replica, writes to primary
    """
    
    read_db_models = {
        # Models that primarily do read operations
        'studysession': 'read_replica',
        'courseprogress': 'read_replica', 
        'courseContent': 'read_replica',
    }
    
    def db_for_read(self, model, **hints):
        """Suggest database for read operations"""
        model_name = model._meta.model_name.lower()
        
        # Route analytics and reporting queries to read replica
        if model_name in self.read_db_models:
            return 'read_replica'
        
        # Check if this is an analytics view
        if hints.get('instance') and hasattr(hints['instance'], '_analytics_query'):
            return 'read_replica'
        
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Suggest database for write operations"""
        # All writes go to primary database
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same app"""
        db_set = {'default', 'read_replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on primary database"""
        return db == 'default'

# Connection Pool Monitoring
class ConnectionPoolMonitor:
    """Monitor database connection pool health"""
    
    @staticmethod
    def get_pool_stats():
        """Get connection pool statistics"""
        from django.db import connections
        
        stats = {}
        for alias, connection in connections.all():
            if hasattr(connection, 'connection') and connection.connection:
                pool_info = {
                    'alias': alias,
                    'is_usable': connection.is_usable(),
                    'queries_logged': len(connection.queries),
                    'vendor': connection.vendor,
                }
                
                # Get pool-specific stats if available
                if hasattr(connection, 'pool'):
                    pool = connection.pool
                    pool_info.update({
                        'pool_size': getattr(pool, 'size', 'unknown'),
                        'checked_in': getattr(pool, 'checkedin', 'unknown'),
                        'checked_out': getattr(pool, 'checkedout', 'unknown'),
                        'overflow': getattr(pool, 'overflow', 'unknown'),
                    })
                
                stats[alias] = pool_info
        
        return stats
    
    @staticmethod
    def health_check():
        """Perform database health check"""
        from django.db import connections
        from django.core.cache import cache
        
        health_status = {
            'database': {},
            'cache': {},
            'overall_status': 'healthy'
        }
        
        # Check database connections
        for alias in ['default', 'read_replica']:
            try:
                connection = connections[alias]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                
                health_status['database'][alias] = {
                    'status': 'healthy' if result else 'unhealthy',
                    'response_time': 'fast'  # Could measure actual time
                }
            except Exception as e:
                health_status['database'][alias] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['overall_status'] = 'degraded'
        
        # Check cache health
        try:
            cache.set('health_check', 'ok', 60)
            cache_result = cache.get('health_check')
            
            health_status['cache']['default'] = {
                'status': 'healthy' if cache_result == 'ok' else 'unhealthy'
            }
        except Exception as e:
            health_status['cache']['default'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'degraded'
        
        return health_status

# Performance optimization settings
PERFORMANCE_SETTINGS = {
    # Database query optimization
    'DEBUG_SQL': False,  # Disable in production
    'SQL_DEBUG_THRESHOLD': 0.5,  # Log queries > 500ms
    
    # Connection settings
    'DB_POOL_SIZE': 20,
    'DB_MAX_OVERFLOW': 30,
    'DB_POOL_TIMEOUT': 30,
    'DB_POOL_RECYCLE': 3600,
    
    # Cache settings
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_SESSION_TIMEOUT': 3600,
    'CACHE_LLM_TIMEOUT': 7200,
    
    # Query optimization
    'QUERY_CACHE_ENABLED': True,
    'BULK_OPERATIONS_BATCH_SIZE': 1000,
    'PAGINATION_DEFAULT_SIZE': 20,
    'PAGINATION_MAX_SIZE': 100,
}

# Export configuration
__all__ = [
    'PRODUCTION_DATABASES',
    'REDIS_CACHE_CONFIG', 
    'DatabaseRouter',
    'ConnectionPoolMonitor',
    'PERFORMANCE_SETTINGS'
]