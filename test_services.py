#!/usr/bin/env python
"""
测试服务可用性的脚本
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_llm_services():
    """测试LLM服务"""
    print("=== LLM Services Test ===")
    
    try:
        from llm.core.client import llm_factory
        print(f"✓ LLM Client available: {llm_factory.is_available()}")
        
        if llm_factory.is_available():
            print(f"✓ Model name: {llm_factory.get_model_name()}")
        else:
            print("✗ LLM Client not available - check API configuration")
            
    except Exception as e:
        print(f"✗ LLM Client error: {e}")
    
    try:
        from llm.services.exercise_service import exercise_service
        print(f"✓ Exercise Service available: {exercise_service.is_available()}")
        
    except Exception as e:
        print(f"✗ Exercise Service error: {e}")

def test_database_models():
    """测试数据库模型"""
    print("\n=== Database Models Test ===")
    
    try:
        from apps.authentication.models import User, UserSettings
        print(f"✓ User model loaded")
        print(f"✓ User count: {User.objects.count()}")
        
        from apps.courses.models import CourseContent, CourseProgress
        print(f"✓ Course models loaded")
        print(f"✓ CourseContent count: {CourseContent.objects.count()}")
        print(f"✓ CourseProgress count: {CourseProgress.objects.count()}")
        
        from apps.learning_plans.models import StudySession
        print(f"✓ StudySession model loaded")
        print(f"✓ StudySession count: {StudySession.objects.count()}")
        
    except Exception as e:
        print(f"✗ Database model error: {e}")

def test_api_endpoints():
    """测试API端点配置"""
    print("\n=== API Endpoints Test ===")
    
    try:
        from django.urls import resolve, reverse
        from django.test import Client
        
        # 测试主要端点是否可以解析
        endpoints = [
            '/api/v1/',
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/courses/',
            '/api/v1/learning-plans/',
            '/api/v1/ai/exercise/status/',
        ]
        
        for endpoint in endpoints:
            try:
                resolve(endpoint)
                print(f"✓ Endpoint {endpoint} - OK")
            except Exception as e:
                print(f"✗ Endpoint {endpoint} - Error: {e}")
                
    except Exception as e:
        print(f"✗ API endpoints test error: {e}")

def test_cache_and_services():
    """测试缓存和服务"""
    print("\n=== Cache and Services Test ===")
    
    try:
        from django.core.cache import cache
        
        # 测试缓存
        test_key = "test_key"
        test_value = "test_value"
        cache.set(test_key, test_value, 30)
        cached_value = cache.get(test_key)
        
        if cached_value == test_value:
            print("✓ Cache system working")
        else:
            print("✗ Cache system not working")
            
        cache.delete(test_key)
        
    except Exception as e:
        print(f"✗ Cache test error: {e}")

def test_configuration():
    """测试配置"""
    print("\n=== Configuration Test ===")
    
    try:
        from django.conf import settings
        
        print(f"✓ DEBUG mode: {settings.DEBUG}")
        print(f"✓ Database: {settings.DATABASES['default']['ENGINE']}")
        print(f"✓ Installed apps count: {len(settings.INSTALLED_APPS)}")
        
        # 检查重要的配置
        if hasattr(settings, 'DEEPSEEK_API_KEY'):
            print(f"✓ DEEPSEEK_API_KEY configured: {bool(settings.DEEPSEEK_API_KEY)}")
        else:
            print("✗ DEEPSEEK_API_KEY not found in settings")
            
    except Exception as e:
        print(f"✗ Configuration test error: {e}")

if __name__ == "__main__":
    print("Backend System Health Check")
    print("=" * 40)
    
    test_configuration()
    test_database_models()
    test_cache_and_services()
    test_llm_services()
    test_api_endpoints()
    
    print("\n" + "=" * 40)
    print("Health check completed!")
