"""
开发环境配置
"""
from .base import *

# 开发环境特定配置
DEBUG = True

# 开发环境允许的主机
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 开发环境允许所有来源的 CORS 请求
CORS_ALLOW_ALL_ORIGINS = True

# 开发环境日志级别
LOGGING['loggers']['apps']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# 开发工具（可选）
try:
    import django_extensions
    INSTALLED_APPS += ['django_extensions']
except ImportError:
    pass

# Email 后端（开发环境使用控制台）
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 缓存（开发环境使用内存缓存）
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
