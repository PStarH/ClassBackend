"""
测试环境配置
"""
from .base import *

# 测试环境配置
DEBUG = True

# 测试数据库（使用内存 SQLite）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# 测试环境不需要密码验证
AUTH_PASSWORD_VALIDATORS = []

# 测试环境缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# 测试环境 Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# 禁用迁移以加速测试
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# 测试时使用简单的密码哈希
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# 静态文件测试配置
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
