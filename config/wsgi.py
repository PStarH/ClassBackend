"""
WSGI 配置
"""
import os
from django.core.wsgi import get_wsgi_application

# 设置默认的 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_wsgi_application()
