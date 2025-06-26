"""
生产环境配置
"""
from .base import *

# 生产环境安全配置
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# 生产环境数据库
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# 安全设置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_TZ = True

# Session 安全
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True

# 静态文件处理
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# 日志配置（生产环境）
LOGGING['handlers']['file']['filename'] = '/var/log/education_platform/django.log'
LOGGING['loggers']['apps']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'

# Email 配置（生产环境）
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# 缓存配置（生产环境使用 Redis）
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
                'socket_keepalive': True,
                'socket_keepalive_options': {},
                'health_check_interval': 30,
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
            'MASTER_CACHE': config('REDIS_MASTER_CACHE', default='redis-master'),
        },
        'KEY_PREFIX': 'education_platform_prod',
        'TIMEOUT': 300,
        'VERSION': 1,
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_SESSIONS_URL', default=config('REDIS_URL')),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 30,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'sessions_prod',
        'TIMEOUT': 86400,
    },
    'api_cache': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_API_CACHE_URL', default=config('REDIS_URL')),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 40,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'api_prod',
        'TIMEOUT': 600,
    }
}

# 生产环境 API 配置
API_RATE_LIMIT = config('API_RATE_LIMIT', default=200, cast=int)
API_RATE_LIMIT_PERIOD = config('API_RATE_LIMIT_PERIOD', default=60, cast=int)
API_CACHE_TIMEOUT = config('API_CACHE_TIMEOUT', default=600, cast=int)
