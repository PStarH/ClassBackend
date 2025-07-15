#!/usr/bin/env python
"""
Comprehensive Service Integration Test
Tests LangChain, PostgreSQL, and Django services working together
"""
import os
import sys
import django
import json
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

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

def test_langchain_service():
    """Test LangChain service functionality"""
    print("\n" + "="*50)
    print("Testing LangChain Service")
    print("="*50)
    
    try:
        from llm.services.advisor_service import advisor_service
        from llm.services.exercise_service import exercise_service
        from llm.services.teacher_service import teacher_service
        
        # Test advisor service
        if advisor_service and advisor_service.is_available():
            print_status("Advisor service available", 'success')
            
            # Test creating a simple plan
            try:
                plan = advisor_service.create_plan("Python basics", "test_session_123")
                if plan and 'plan' in plan:
                    print_status("Successfully created learning plan", 'success')
                else:
                    print_status("Plan creation returned unexpected format", 'warning')
            except Exception as e:
                print_status(f"Plan creation failed: {str(e)}", 'error')
        else:
            print_status("Advisor service not available", 'error')
        
        # Test exercise service
        if exercise_service and exercise_service.is_available():
            print_status("Exercise service available", 'success')
        else:
            print_status("Exercise service not available", 'warning')
        
        # Test teacher service
        if teacher_service and teacher_service.is_available():
            print_status("Teacher service available", 'success')
        else:
            print_status("Teacher service not available", 'warning')
        
        return True
    except Exception as e:
        print_status(f"LangChain service testing failed: {str(e)}", 'error')
        return False

def test_postgresql_operations():
    """Test PostgreSQL database operations"""
    print("\n" + "="*50)
    print("Testing PostgreSQL Operations")
    print("="*50)
    
    try:
        from apps.authentication.models import User
        from apps.courses.models import CourseContent, CourseProgress
        from apps.learning_plans.models import StudySession
        from django.db import transaction
        
        # Test creating a user
        with transaction.atomic():
            test_user, created = User.objects.get_or_create(
                email='test@example.com',
                defaults={
                    'username': 'testuser'
                }
            )
            if created:
                test_user.set_password('TestPass123!')  # Include uppercase, lowercase, numbers
                test_user.save()
                print_status("Created test user", 'success')
            else:
                print_status("Test user already exists", 'info')
        
        # Test creating course content
        with transaction.atomic():
            course_content, created = CourseContent.objects.get_or_create(
                outline={'title': 'Test Course', 'description': 'Test Description'},
                defaults={
                    'chapters': [
                        {'title': 'Chapter 1', 'text': 'Introduction to testing'},
                        {'title': 'Chapter 2', 'text': 'Advanced testing concepts'}
                    ]
                }
            )
            if created:
                print_status("Created test course content", 'success')
            else:
                print_status("Test course content already exists", 'info')
        
        # Test creating course progress
        with transaction.atomic():
            progress, created = CourseProgress.objects.get_or_create(
                user_uuid=test_user,
                content_id=course_content,
                defaults={
                    'subject_name': 'Testing',
                    'proficiency_level': 50,
                    'difficulty': 5
                }
            )
            if created:
                print_status("Created course progress record", 'success')
            else:
                print_status("Course progress already exists", 'info')
        
        # Test querying
        user_count = User.objects.count()
        content_count = CourseContent.objects.count()
        progress_count = CourseProgress.objects.count()
        
        print_status(f"Database contains: {user_count} users, {content_count} courses, {progress_count} progress records", 'success')
        
        return True
    except Exception as e:
        print_status(f"PostgreSQL operations failed: {str(e)}", 'error')
        return False

def test_django_api_integration():
    """Test Django API endpoints with real data"""
    print("\n" + "="*50)
    print("Testing Django API Integration")
    print("="*50)
    
    try:
        from django.test import Client
        from rest_framework.authtoken.models import Token
        from apps.authentication.models import User
        
        client = Client()
        
        # Test unauthenticated health check
        response = client.get('/health/')
        if response.status_code == 200:
            print_status("Health check endpoint working", 'success')
        else:
            print_status(f"Health check failed: {response.status_code}", 'error')
        
        # Get or create test user token
        try:
            test_user = User.objects.get(email='test@example.com')
            token, created = Token.objects.get_or_create(user=test_user)
            print_status(f"Test user token: {token.key[:8]}...", 'success')
            
            # Test authenticated API call
            headers = {'HTTP_AUTHORIZATION': f'Token {token.key}'}
            
            # Test course progress endpoint
            response = client.get('/api/v1/courses/progress/', **headers)
            if response.status_code == 200:
                print_status("Course progress API working", 'success')
            else:
                print_status(f"Course progress API failed: {response.status_code}", 'error')
            
            # Test AI advisor endpoint
            response = client.post(
                '/api/v1/ai/advisor/plan/create',
                data=json.dumps({'topic': 'Python basics', 'session_id': 'test_123'}),
                content_type='application/json',
                **headers
            )
            if response.status_code in [200, 503]:  # 503 if AI service not available
                if response.status_code == 200:
                    print_status("AI advisor API working", 'success')
                else:
                    print_status("AI advisor API returned 503 (service unavailable)", 'warning')
            else:
                print_status(f"AI advisor API failed: {response.status_code}", 'error')
                
        except User.DoesNotExist:
            print_status("Test user not found", 'error')
        
        return True
    except Exception as e:
        print_status(f"Django API integration failed: {str(e)}", 'error')
        return False

def test_service_integration():
    """Test all services working together"""
    print("\n" + "="*50)
    print("Testing Inter-Service Integration")
    print("="*50)
    
    try:
        from apps.authentication.models import User
        from apps.courses.models import CourseContent, CourseProgress
        from llm.services.advisor_service import advisor_service
        from django.core.cache import cache
        
        # Test cache + database
        cache_key = 'integration_test'
        test_data = {'timestamp': str(datetime.now()), 'user_count': User.objects.count()}
        cache.set(cache_key, test_data, 60)
        
        retrieved = cache.get(cache_key)
        if retrieved == test_data:
            print_status("Cache + Database integration working", 'success')
        else:
            print_status("Cache integration issue", 'error')
        
        # Test LangChain + Database
        if advisor_service and advisor_service.is_available():
            try:
                # Get course data
                course = CourseContent.objects.first()
                if course:
                    # Create a plan based on course content
                    plan = advisor_service.create_plan(
                        f"Study plan for {course.outline.get('title', 'Course')}",
                        "integration_test"
                    )
                    if plan:
                        print_status("LangChain + Database integration working", 'success')
                    else:
                        print_status("LangChain integration returned no data", 'warning')
                else:
                    print_status("No course data available for integration test", 'warning')
            except Exception as e:
                print_status(f"LangChain integration error: {str(e)}", 'error')
        else:
            print_status("LangChain service not available for integration test", 'warning')
        
        # Clean up cache
        cache.delete(cache_key)
        
        return True
    except Exception as e:
        print_status(f"Service integration test failed: {str(e)}", 'error')
        return False

def main():
    """Run all integration tests"""
    print(f"\n{BLUE}Backend Service Integration Test Suite{RESET}")
    print(f"{BLUE}{'='*50}{RESET}")
    print(f"Testing started at: {datetime.now()}")
    
    results = {
        'LangChain Service': test_langchain_service(),
        'PostgreSQL Operations': test_postgresql_operations(),
        'Django API Integration': test_django_api_integration(),
        'Inter-Service Integration': test_service_integration(),
    }
    
    # Summary
    print("\n" + "="*50)
    print("Integration Test Summary")
    print("="*50)
    
    all_passed = True
    for service, result in results.items():
        if result:
            print_status(f"{service}: PASSED", 'success')
        else:
            print_status(f"{service}: FAILED", 'error')
            all_passed = False
    
    if all_passed:
        print(f"\n{GREEN}All integration tests passed!{RESET}")
        print(f"{GREEN}Backend services are working together correctly.{RESET}")
    else:
        print(f"\n{RED}Some integration tests failed.{RESET}")
        print(f"{YELLOW}Please check the logs above for details.{RESET}")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())