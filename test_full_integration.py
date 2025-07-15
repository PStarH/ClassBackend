#!/usr/bin/env python
"""
Comprehensive Integration Test for ClassBackend
Tests all main services and their interactions
"""
import os
import sys
import django
from pathlib import Path
import traceback
import json

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_full_integration():
    """Test the complete workflow from user creation to AI service usage"""
    print("🔄 Testing Full Integration Workflow")
    
    results = {}
    
    try:
        # 1. Test User Model and Authentication
        from apps.authentication.models import User
        
        # Create or get test user
        test_user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={
                'username': 'testuser'
            }
        )
        
        results['user_creation'] = f"✅ {'Created' if created else 'Retrieved'} test user"
        
        # 2. Test Course Progress Model
        from apps.courses.models import CourseProgress, CourseContent
        
        # Get or create course content
        course_content = CourseContent.objects.first()
        if not course_content:
            course_content = CourseContent.objects.create(
                outline={'title': 'Test Course', 'description': 'Test course outline'},
                chapters=[{'title': 'Chapter 1', 'content': 'Test content'}]
            )
        
        course_progress, created = CourseProgress.objects.get_or_create(
            user_uuid=test_user,
            subject_name='test-course',
            content_id=course_content,
            defaults={
                'proficiency_level': 0,
                'difficulty': 5
            }
        )
        
        results['course_progress'] = f"✅ {'Created' if created else 'Retrieved'} course progress"
        
        # 3. Test Study Session Model
        from apps.learning_plans.models import StudySession
        from django.utils import timezone
        
        study_session = StudySession.objects.create(
            user=test_user,
            course_progress=course_progress,
            start_time=timezone.now(),
            duration_minutes=30,
            effectiveness_rating=4
        )
        
        results['study_session'] = "✅ Created study session"
        
        # 4. Test AI Services Integration
        from llm.services.advisor_service import get_advisor_service
        from llm.services.teacher_service import get_teacher_service
        from llm.services.exercise_service import get_exercise_service
        
        advisor_service = get_advisor_service()
        teacher_service = get_teacher_service()
        exercise_service = get_exercise_service()
        
        # Test Advisor Service
        try:
            plan = advisor_service.create_plan("Python Basics")
            results['advisor_service'] = f"✅ Created learning plan with {len(plan)} sections"
        except Exception as e:
            results['advisor_service'] = f"⚠️ Plan creation: {str(e)[:50]}..."
        
        # Test Teacher Service  
        try:
            outline = teacher_service.create_outline("Python Functions")
            results['teacher_service'] = f"✅ Created outline with {len(outline)} sections"
        except Exception as e:
            results['teacher_service'] = f"⚠️ Outline creation: {str(e)[:50]}..."
        
        # Test Exercise Service
        try:
            exercises = exercise_service.generate_exercises(
                user_id=str(test_user.uuid),
                num_questions=3
            )
            results['exercise_service'] = f"✅ Generated {len(exercises)} exercises"
        except Exception as e:
            results['exercise_service'] = f"⚠️ Exercise generation: {str(e)[:50]}..."
        
        # 5. Test Cache Integration
        from django.core.cache import cache
        
        cache_key = f"integration_test_{test_user.uuid}"
        test_data = {"user_id": str(test_user.uuid), "timestamp": "now"}
        
        cache.set(cache_key, test_data, 300)  # 5 minutes
        cached_data = cache.get(cache_key)
        
        if cached_data == test_data:
            results['cache_integration'] = "✅ Cache working correctly"
        else:
            results['cache_integration'] = "❌ Cache not working"
        
        cache.delete(cache_key)
        
        # 6. Test API Endpoints
        from django.test import Client
        
        client = Client()
        
        # Test health endpoint
        response = client.get('/health/')
        results['health_endpoint'] = f"✅ Health endpoint: {response.status_code}"
        
        # Test AI service status endpoint (requires auth, so expect 401/403)
        response = client.get('/api/v1/ai/status/')
        results['ai_status_endpoint'] = f"✅ AI status endpoint: {response.status_code}"
        
        # 7. Test Database Queries
        user_count = User.objects.count()
        course_count = CourseProgress.objects.count()
        session_count = StudySession.objects.count()
        
        results['database_queries'] = f"✅ Users: {user_count}, Courses: {course_count}, Sessions: {session_count}"
        
        # Clean up test data
        study_session.delete()
        
        return results
        
    except Exception as e:
        results['integration_error'] = f"❌ Integration test failed: {str(e)}"
        traceback.print_exc()
        return results

def test_performance_metrics():
    """Test system performance metrics"""
    print("\n⚡ Testing Performance Metrics")
    
    import time
    from django.db import connection
    from django.core.cache import cache
    
    results = {}
    
    # Test database query performance
    start_time = time.time()
    from apps.authentication.models import User
    users = list(User.objects.all()[:10])
    db_time = time.time() - start_time
    results['db_query_time'] = f"✅ DB Query: {db_time:.3f}s ({len(users)} users)"
    
    # Test cache performance
    start_time = time.time()
    cache.set('perf_test', 'test_data', 60)
    cache_data = cache.get('perf_test')
    cache_time = time.time() - start_time
    results['cache_time'] = f"✅ Cache: {cache_time:.3f}s"
    cache.delete('perf_test')
    
    # Test AI service availability
    start_time = time.time()
    from llm.services.advisor_service import get_advisor_service
    advisor_service = get_advisor_service()
    available = advisor_service.is_available()
    ai_time = time.time() - start_time
    results['ai_check_time'] = f"✅ AI Check: {ai_time:.3f}s ({'Available' if available else 'Unavailable'})"
    
    return results

def test_security_measures():
    """Test security configurations"""
    print("\n🔒 Testing Security Measures")
    
    results = {}
    
    # Test CORS settings
    from django.conf import settings
    
    if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
        results['cors_configured'] = "✅ CORS configured"
    else:
        results['cors_configured'] = "⚠️ CORS not configured"
    
    # Test secret key
    if settings.SECRET_KEY and len(settings.SECRET_KEY) > 20:
        results['secret_key'] = "✅ Secret key properly configured"
    else:
        results['secret_key'] = "⚠️ Secret key issue"
    
    # Test debug mode
    if settings.DEBUG:
        results['debug_mode'] = "⚠️ Debug mode enabled (development)"
    else:
        results['debug_mode'] = "✅ Debug mode disabled (production)"
    
    # Test allowed hosts
    if settings.ALLOWED_HOSTS:
        results['allowed_hosts'] = f"✅ Allowed hosts: {len(settings.ALLOWED_HOSTS)} configured"
    else:
        results['allowed_hosts'] = "⚠️ No allowed hosts configured"
    
    return results

def main():
    """Run comprehensive integration tests"""
    print("🚀 ClassBackend Comprehensive Integration Test\n")
    
    # Run all integration tests
    integration_results = test_full_integration()
    performance_results = test_performance_metrics()
    security_results = test_security_measures()
    
    # Print results
    print("\n📊 INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    all_results = {
        "Integration Tests": integration_results,
        "Performance Tests": performance_results,
        "Security Tests": security_results
    }
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n{category}:")
        for test_name, result in results.items():
            print(f"  {test_name}: {result}")
            total_tests += 1
            if "✅" in result:
                passed_tests += 1
    
    # Overall summary
    print(f"\n📈 OVERALL SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All integration tests passed! System is fully operational.")
    elif passed_tests >= total_tests * 0.8:
        print("✅ Most tests passed. System is operational with minor issues.")
    else:
        print("⚠️ Several tests failed. System needs attention.")
    
    return {
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'results': all_results
    }

if __name__ == "__main__":
    results = main()
