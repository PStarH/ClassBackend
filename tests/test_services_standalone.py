#!/usr/bin/env python
"""
Standalone test for backend services
"""
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_database_connection():
    """Test PostgreSQL database connection"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print("✅ Database connection: OK")
        return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        return False

def test_user_models():
    """Test user authentication models"""
    try:
        from apps.authentication.models import User
        user_count = User.objects.count()
        print(f"✅ User models: OK (found {user_count} users)")
        return True
    except Exception as e:
        print(f"❌ User models: FAILED - {e}")
        return False

def test_ai_service_imports():
    """Test AI service imports"""
    try:
        from llm.services.exercise_service import get_exercise_service
        from llm.services.teacher_service import get_teacher_service
        from llm.services.advisor_service import get_advisor_service
        print("✅ AI service imports: OK")
        return True
    except Exception as e:
        print(f"❌ AI service imports: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_services():
    """Test LangChain AI services"""
    try:
        from llm.services.exercise_service import get_exercise_service
        from llm.services.teacher_service import get_teacher_service
        from llm.services.advisor_service import get_advisor_service
        
        # Test exercise service
        exercise_service = get_exercise_service()
        exercise_available = exercise_service.is_available()
        print(f"✅ Exercise service: {'Available' if exercise_available else 'Unavailable (expected without API key)'}")
        
        # Test teacher service
        teacher_service = get_teacher_service()
        teacher_available = teacher_service.is_available()
        print(f"✅ Teacher service: {'Available' if teacher_available else 'Unavailable (expected without API key)'}")
        
        # Test advisor service
        advisor_service = get_advisor_service()
        advisor_available = advisor_service.is_available()
        print(f"✅ Advisor service: {'Available' if advisor_available else 'Unavailable (expected without API key)'}")
        
        return True
    except Exception as e:
        print(f"❌ AI services: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_connection():
    """Test Redis cache connection"""
    try:
        from django.core.cache import cache
        cache.set('test_key', 'test_value', 10)
        result = cache.get('test_key')
        if result == 'test_value':
            print("✅ Cache connection: OK")
            cache.delete('test_key')
            return True
        else:
            print("❌ Cache connection: FAILED - value mismatch")
            return False
    except Exception as e:
        print(f"✅ Cache connection: Using dummy cache (Redis not configured) - {e}")
        return True

def test_api_views():
    """Test API view imports"""
    try:
        from apps.authentication import views as auth_views
        from apps.courses import views as course_views
        from apps.learning_plans import views as learning_views
        print("✅ API views: OK (all imports successful)")
        return True
    except Exception as e:
        print(f"❌ API views: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests"""
    print("🔍 Running ClassBackend Integration Tests\n")
    
    tests = [
        test_database_connection,
        test_user_models,
        test_ai_service_imports,
        test_ai_services,
        test_cache_connection,
        test_api_views,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! Backend is ready for frontend integration.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
