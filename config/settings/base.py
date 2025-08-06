"""
基础配置 - 所有环境通用的配置
"""
import os
from pathlib import Path
from decouple import config

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 安全配置
# SECURITY WARNING: SECRET_KEY must be set in environment variables
# Generate a new key using: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY = config('SECRET_KEY')  # No default - force environment variable
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# 应用配置
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'drf_spectacular',
    # 'django_celery_beat',        # Temporarily disabled for basic setup
    # 'django_celery_results',     # Temporarily disabled for basic setup
]

LOCAL_APPS = [
    'core',
    'apps.authentication',  # 用户管理 (users, user_settings)
    'apps.courses',         # 课程管理 (course_progress, course_content)
    'apps.learning_plans',  # 学习记录 (study_sessions) - 已有实现
    'apps.ai_services',     # AI服务 (大模型/AI服务) - 已恢复
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# 中间件配置 - 增强版安全
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.security.middleware.SecurityHeadersMiddleware',  # 安全头中间件
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.HealthCheckMiddleware',  # 健康检查中间件
    'core.monitoring.middleware.PerformanceMonitoringMiddleware',  # 性能监控中间件
    'core.middleware.enhanced_rate_limit.EnhancedRateLimitMiddleware',  # 增强限流中间件
    'core.security.input_validation.InputValidationMiddleware',  # 输入验证中间件
    'core.performance.query_optimization.QueryOptimizationMiddleware',  # 查询优化中间件
    'core.security.middleware.AuditLogMiddleware',  # 审计日志中间件
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.authentication.enhanced_jwt.JWTTokenRefreshMiddleware',  # JWT自动刷新中间件
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.CacheResponseMiddleware',  # 响应缓存中间件
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URL 配置
ROOT_URLCONF = 'config.urls'

# 模板配置
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI 配置
WSGI_APPLICATION = 'config.wsgi.application'

# 数据库配置 - 使用优化的配置
# 注意：确保PostgreSQL数据库使用UTF-8编码创建
# CREATE DATABASE education_platform ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8';

# 导入优化的数据库配置
from core.performance.advanced_database_config import get_database_config

# 根据环境获取数据库配置
DATABASES = get_database_config('development')

# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    # 注释掉自定义密码验证器，因为它不兼容Django的密码验证器格式
    # {
    #     'NAME': 'core.security.validators.DataSecurityValidator.validate_password_strength',
    # },
]

# 国际化配置
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 静态文件配置
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Django REST Framework 配置 - 增强版
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 'apps.authentication.enhanced_jwt.EnhancedJWTAuthentication',  # Temporarily disabled
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',  # Using simple pagination
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        # 'django_filters.rest_framework.DjangoFilterBackend',  # Temporarily disabled
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'ai_api': '10/minute',  # AI API专用限流
        'login': '5/minute',    # 登录API限流
    },
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
    
    # 性能优化设置
    'DEFAULT_METADATA_CLASS': None,  # 禁用元数据以提高性能
    'NUM_PROXIES': config('DRF_NUM_PROXIES', default=0, cast=int),
    
    # 缓存配置
    'DEFAULT_CACHE_TIMEOUT': config('DRF_CACHE_TIMEOUT', default=300, cast=int),
    'DEFAULT_CACHE_KEY_PREFIX': 'drf_cache',
}

# drf-spectacular 配置 (OpenAPI/Swagger)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Smart Classroom AI Platform API',
    'DESCRIPTION': 'AI-powered education platform with personalized learning and intelligent recommendations',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]',
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tagsSorter': 'alpha',
        'operationsSorter': 'alpha',
    },
    'SWAGGER_UI_FAVICON_HREF': '/static/favicon.ico',
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': True,
        'hideHostname': True,
        'noAutoAuth': False,
    },
    'SERVERS': [
        {'url': 'http://localhost:8000', 'description': 'Development server'},
        {'url': 'https://api.yourplatform.com', 'description': 'Production server'},
    ],
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'Courses', 'description': 'Course management and content'},
        {'name': 'Learning Plans', 'description': 'Personalized learning plans and progress'},
        {'name': 'AI Services', 'description': 'AI-powered educational services'},
        {'name': 'Analytics', 'description': 'Learning analytics and insights'},
    ],
    'PREPROCESSING_HOOKS': [
        'core.api.preprocessing.remove_sensitive_fields',
    ],
    'POSTPROCESSING_HOOKS': [
        'core.api.postprocessing.add_security_headers',
    ],
}

# CORS 配置
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True

# AI 服务配置
DEEPSEEK_API_KEY = config('DEEPSEEK_API_KEY', default='')
DEEPSEEK_BASE_URL = config('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')
DEEPSEEK_MODEL = config('DEEPSEEK_MODEL', default='deepseek-chat')

# 邮件配置
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # 开发环境默认使用控制台

# Redis 和缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'education_platform_default',
        'TIMEOUT': 300,  # 5分钟默认超时
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'education_platform_sessions',
        'TIMEOUT': 28800,  # 8小时
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    },
    'api_cache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'education_platform_api',
        'TIMEOUT': 600,  # 10分钟
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    },
    'user_cache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'education_platform_user',
        'TIMEOUT': 1800,  # 30分钟
        'OPTIONS': {
            'MAX_ENTRIES': 500,
            'CULL_FREQUENCY': 3,
        }
    },
    'llm_cache': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'education_platform_llm',
        'TIMEOUT': 3600,  # 1小时
        'OPTIONS': {
            'MAX_ENTRIES': 200,
            'CULL_FREQUENCY': 3,
        }
    }
}

# Session 配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 28800  # 8小时
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# API 配置
API_RATE_LIMIT = config('API_RATE_LIMIT', default=100, cast=int)  # 每分钟请求数
API_RATE_LIMIT_PERIOD = config('API_RATE_LIMIT_PERIOD', default=60, cast=int)  # 速率限制时间窗口
API_BURST_RATE_LIMIT = config('API_BURST_RATE_LIMIT', default=20, cast=int)  # 突发限制
API_CACHE_TIMEOUT = config('API_CACHE_TIMEOUT', default=300, cast=int)  # API 缓存超时时间

# Redis 全局配置
DJANGO_REDIS_IGNORE_EXCEPTIONS = True
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 10*1024*1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 10,
            'formatter': 'security',
        },
        'performance_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'performance.log',
            'maxBytes': 10*1024*1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['performance_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# 监控和性能配置
ENABLE_PERFORMANCE_MONITORING = config('ENABLE_PERFORMANCE_MONITORING', default=True, cast=bool)
SLOW_QUERY_THRESHOLD = config('SLOW_QUERY_THRESHOLD', default=1.0, cast=float)
CACHE_ANALYTICS_ENABLED = config('CACHE_ANALYTICS_ENABLED', default=True, cast=bool)

# 数据保护配置
DATA_ENCRYPTION_ENABLED = config('DATA_ENCRYPTION_ENABLED', default=False, cast=bool)
SENSITIVE_DATA_MASKING = config('SENSITIVE_DATA_MASKING', default=True, cast=bool)
AUDIT_LOG_ENABLED = config('AUDIT_LOG_ENABLED', default=True, cast=bool)

# 自定义用户模型
AUTH_USER_MODEL = 'authentication.User'

# Celery异步任务配置
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')

# Celery基础设置
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_EXPIRES = config('CELERY_RESULT_EXPIRES', default=3600, cast=int)

# LLM任务专用配置
LLM_ASYNC_ENABLED = config('LLM_ASYNC_ENABLED', default=True, cast=bool)
LLM_TASK_TIMEOUT = config('LLM_TASK_TIMEOUT', default=60, cast=int)
LLM_BATCH_SIZE = config('LLM_BATCH_SIZE', default=5, cast=int)
LLM_RATE_LIMIT = config('LLM_RATE_LIMIT', default='10/m')

# 任务重试配置
CELERY_TASK_DEFAULT_RETRY_DELAY = config('CELERY_TASK_RETRY_DELAY', default=60, cast=int)
CELERY_TASK_MAX_RETRIES = config('CELERY_TASK_MAX_RETRIES', default=3, cast=int)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# JWT增强配置
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_LIFETIME = config('JWT_ACCESS_TOKEN_LIFETIME', default=900, cast=int)  # 15分钟
JWT_REFRESH_TOKEN_LIFETIME = config('JWT_REFRESH_TOKEN_LIFETIME', default=604800, cast=int)  # 7天

# 限流增强配置
RATE_LIMIT_ENABLED = config('RATE_LIMIT_ENABLED', default=True, cast=bool)
RATE_LIMIT_USE_CACHE = config('RATE_LIMIT_USE_CACHE', default=True, cast=bool)
RATE_LIMIT_CACHE_PREFIX = config('RATE_LIMIT_CACHE_PREFIX', default='rate_limit')

# 查询优化配置
ENABLE_QUERY_OPTIMIZATION = config('ENABLE_QUERY_OPTIMIZATION', default=True, cast=bool)
SLOW_QUERY_THRESHOLD = config('SLOW_QUERY_THRESHOLD', default=1.0, cast=float)
N_PLUS_ONE_DETECTION_THRESHOLD = config('N_PLUS_ONE_THRESHOLD', default=10, cast=int)

# API性能配置
API_REQUEST_TIMEOUT = config('API_REQUEST_TIMEOUT', default=30, cast=int)
API_MAX_CONCURRENT_REQUESTS = config('API_MAX_CONCURRENT_REQUESTS', default=100, cast=int)
API_RESPONSE_COMPRESSION = config('API_RESPONSE_COMPRESSION', default=True, cast=bool)

# 数据库连接优化
DATABASE_CONNECTION_HEALTH_CHECKS = config('DB_HEALTH_CHECKS', default=True, cast=bool)
DATABASE_CONN_MAX_AGE = config('DB_CONN_MAX_AGE', default=600, cast=int)
DATABASE_AUTOCOMMIT = config('DB_AUTOCOMMIT', default=True, cast=bool)

# 安全监控配置
SECURITY_MONITOR_ENABLED = config('SECURITY_MONITOR_ENABLED', default=True, cast=bool)
SECURITY_ALERT_THRESHOLD = config('SECURITY_ALERT_THRESHOLD', default=10, cast=int)
SECURITY_TIME_WINDOW = config('SECURITY_TIME_WINDOW', default=300, cast=int)
MAX_FAILED_LOGIN_ATTEMPTS = config('MAX_FAILED_LOGIN_ATTEMPTS', default=5, cast=int)
IP_BLACKLIST_DURATION = config('IP_BLACKLIST_DURATION', default=3600, cast=int)

# 安全验证配置
SECURITY_SKIP_PATHS = config('SECURITY_SKIP_PATHS', default='/health/,/metrics/,/static/,/media/', cast=lambda v: v.split(','))
SECURITY_STRICT_PATHS = config('SECURITY_STRICT_PATHS', default='/api/auth/,/api/ai/,/admin/', cast=lambda v: v.split(','))
SECURITY_LOG_TO_DB = config('SECURITY_LOG_TO_DB', default=True, cast=bool)

# 文件上传安全
MAX_UPLOAD_SIZE = config('MAX_UPLOAD_SIZE', default=104857600, cast=int)  # 100MB
ALLOWED_FILE_TYPES = config('ALLOWED_FILE_TYPES', default='image/jpeg,image/png,image/gif,text/plain,application/pdf,application/json', cast=lambda v: v.split(','))

# 告警配置
SECURITY_ALERT_EMAILS = config('SECURITY_ALERT_EMAILS', default='', cast=lambda v: v.split(',') if v else [])
SLACK_WEBHOOK_URL = config('SLACK_WEBHOOK_URL', default='')
SECURITY_WEBHOOK_URL = config('SECURITY_WEBHOOK_URL', default='')

# Sentry错误监控 (可选)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
            ),
            CeleryIntegration(
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
        ],
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.1, cast=float),
        send_default_pii=False,
        environment=BUILD_ENV,
        release=config('APP_VERSION', default='1.0.0'),
    )
