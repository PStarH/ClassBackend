"""
开发环境配置
"""
from .base import *

# 开发环境特定配置
DEBUG = True

# 开发环境数据库（可以使用 SQLite 进行快速开发）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='education_platform_dev'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
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
    }
}
