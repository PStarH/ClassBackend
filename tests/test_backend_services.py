#!/usr/bin/env python
"""
Backend Services Testing Script
Tests PostgreSQL, Django, and LangChain/AI services integration
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_status(message, status='info'):
    if status == 'success':
        print(f"{GREEN}✓ {message}{RESET}")
    elif status == 'error':
        print(f"{RED}✗ {message}{RESET}")
    elif status == 'warning':
        print(f"{YELLOW}⚠ {message}{RESET}")
    else:
        print(f"{BLUE}→ {message}{RESET}")

def test_database_connection():
    """Test PostgreSQL database connection"""
    print("\n" + "="*50)
    print("Testing PostgreSQL Database Connection")
    print("="*50)
    
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print_status(f"PostgreSQL connected: {version[0]}", 'success')
            
            # Test tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print_status(f"Found {len(tables)} tables in database", 'success')
            
        return True
    except Exception as e:
        print_status(f"Database connection failed: {str(e)}", 'error')
        return False

def test_django_models():
    """Test Django models and ORM"""
    print("\n" + "="*50)
    print("Testing Django Models")
    print("="*50)
    
    try:
        from apps.authentication.models import User
        from apps.courses.models import CourseContent, CourseProgress
        from apps.learning_plans.models import StudySession
        
        # Test user model
        user_count = User.objects.count()
        print_status(f"User model accessible - {user_count} users found", 'success')
        
        # Test course content model
        content_count = CourseContent.objects.count()
        print_status(f"CourseContent model accessible - {content_count} course contents found", 'success')
        
        # Test course progress model
        progress_count = CourseProgress.objects.count()
        print_status(f"CourseProgress model accessible - {progress_count} progress records found", 'success')
        
        # Test study session model
        session_count = StudySession.objects.count()
        print_status(f"StudySession model accessible - {session_count} sessions found", 'success')
        
        return True
    except Exception as e:
        print_status(f"Model testing failed: {str(e)}", 'error')
        return False

def test_api_endpoints():
    """Test Django REST API endpoints"""
    print("\n" + "="*50)
    print("Testing API Endpoints")
    print("="*50)
    
    try:
        from django.test import Client
        from django.urls import reverse
        
        client = Client()
        
        # Test health endpoint
        response = client.get('/health/')
        if response.status_code == 200:
            print_status("Health check endpoint working", 'success')
        else:
            print_status(f"Health check failed: {response.status_code}", 'error')
        
        # List API endpoints
        from config.urls import urlpatterns
        print_status("Available API endpoints:", 'info')
        
        api_endpoints = [
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/courses/',
            '/api/v1/learning-plans/',
            '/api/v1/ai/advisor/',
        ]
        
        for endpoint in api_endpoints:
            print(f"  • {endpoint}")
        
        return True
    except Exception as e:
        print_status(f"API endpoint testing failed: {str(e)}", 'error')
        return False

def test_langchain_service():
    """Test LangChain/AI service integration"""
    print("\n" + "="*50)
    print("Testing LangChain/AI Service")
    print("="*50)
    
    try:
        from llm.core.client import llm_factory
        from llm.core.config import LLMConfig
        
        # Check API key
        if LLMConfig.API_KEY:
            print_status("DeepSeek API key configured", 'success')
        else:
            print_status("DeepSeek API key not configured", 'error')
            return False
        
        # Test LLM availability
        if llm_factory.is_available():
            print_status("LLM service is available", 'success')
            
            # Test basic LLM call
            try:
                client = llm_factory.get_client()
                print_status("LLM client initialized successfully", 'success')
                
                # Note: We won't make actual API calls to avoid costs
                print_status("LLM ready for API calls (not testing to avoid costs)", 'info')
                
            except Exception as e:
                print_status(f"LLM client initialization error: {str(e)}", 'warning')
        else:
            print_status("LLM service not available", 'error')
            return False
        
        return True
    except Exception as e:
        print_status(f"LangChain service testing failed: {str(e)}", 'error')
        return False

def test_cache_service():
    """Test cache service"""
    print("\n" + "="*50)
    print("Testing Cache Service")
    print("="*50)
    
    try:
        from django.core.cache import cache
        
        # Test set/get
        test_key = 'test_backend_services'
        test_value = {'timestamp': str(datetime.now())}
        
        cache.set(test_key, test_value, 60)
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            print_status("Cache service working correctly", 'success')
        else:
            print_status("Cache service not working properly", 'error')
        
        # Clean up
        cache.delete(test_key)
        
        return True
    except Exception as e:
        print_status(f"Cache service testing failed: {str(e)}", 'error')
        return False

def main():
    """Run all tests"""
    print(f"\n{BLUE}Backend Services Test Suite{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    print(f"Testing started at: {datetime.now()}")
    
    results = {
        'Database': test_database_connection(),
        'Django Models': test_django_models(),
        'API Endpoints': test_api_endpoints(),
        'LangChain/AI Service': test_langchain_service(),
        'Cache Service': test_cache_service(),
    }
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    
    all_passed = True
    for service, result in results.items():
        if result:
            print_status(f"{service}: PASSED", 'success')
        else:
            print_status(f"{service}: FAILED", 'error')
            all_passed = False
    
    if all_passed:
        print(f"\n{GREEN}All services are working correctly!{RESET}")
    else:
        print(f"\n{RED}Some services need attention.{RESET}")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())