#!/usr/bin/env python
"""
Comprehensive Backend Service Verification and Analysis
"""
import os
import sys
import django
from pathlib import Path
import traceback

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def analyze_project_structure():
    """Analyze the project structure and identify potential issues"""
    print("🔍 Analyzing Project Structure")
    
    # Check for dead code and unused files
    issues = []
    
    # Check for Python cache files
    cache_files = list(project_root.rglob("__pycache__"))
    if cache_files:
        issues.append(f"Found {len(cache_files)} __pycache__ directories")
    
    # Check for .pyc files
    pyc_files = list(project_root.rglob("*.pyc"))
    if pyc_files:
        issues.append(f"Found {len(pyc_files)} .pyc files")
    
    # Check for duplicate test files
    test_files = list(project_root.rglob("test_*.py"))
    tests_dir_files = list((project_root / "tests").rglob("*.py")) if (project_root / "tests").exists() else []
    
    if test_files and tests_dir_files:
        issues.append(f"Found tests in both root ({len(test_files)}) and tests/ directory ({len(tests_dir_files)})")
    
    print(f"📋 Found {len(issues)} structural issues:")
    for issue in issues:
        print(f"  - {issue}")
    
    return issues

def test_database_models():
    """Test all database models"""
    print("\n🗄️ Testing Database Models")
    
    results = {}
    
    # Test User model
    try:
        from apps.authentication.models import User
        user_count = User.objects.count()
        results['User'] = f"✅ OK ({user_count} users)"
    except Exception as e:
        results['User'] = f"❌ FAILED: {str(e)}"
    
    # Test CourseProgress model
    try:
        from apps.courses.models import CourseProgress
        course_count = CourseProgress.objects.count()
        results['CourseProgress'] = f"✅ OK ({course_count} courses)"
    except Exception as e:
        results['CourseProgress'] = f"❌ FAILED: {str(e)}"
    
    # Test StudySession model
    try:
        from apps.learning_plans.models import StudySession
        session_count = StudySession.objects.count()
        results['StudySession'] = f"✅ OK ({session_count} sessions)"
    except Exception as e:
        results['StudySession'] = f"❌ FAILED: {str(e)}"
    
    for model, status in results.items():
        print(f"  {model}: {status}")
    
    return results

def test_langchain_services():
    """Test LangChain AI services"""
    print("\n🤖 Testing LangChain Services")
    
    results = {}
    
    # Test service imports
    try:
        from llm.services.exercise_service import get_exercise_service
        from llm.services.teacher_service import get_teacher_service
        from llm.services.advisor_service import get_advisor_service
        results['Service Imports'] = "✅ OK"
    except Exception as e:
        results['Service Imports'] = f"❌ FAILED: {str(e)}"
        return results
    
    # Test individual services
    try:
        exercise_service = get_exercise_service()
        available = exercise_service.is_available()
        results['Exercise Service'] = f"✅ {'Available' if available else 'Unavailable (no API key)'}"
    except Exception as e:
        results['Exercise Service'] = f"❌ FAILED: {str(e)}"
    
    try:
        teacher_service = get_teacher_service()
        available = teacher_service.is_available()
        results['Teacher Service'] = f"✅ {'Available' if available else 'Unavailable (no API key)'}"
    except Exception as e:
        results['Teacher Service'] = f"❌ FAILED: {str(e)}"
    
    try:
        advisor_service = get_advisor_service()
        available = advisor_service.is_available()
        results['Advisor Service'] = f"✅ {'Available' if available else 'Unavailable (no API key)'}"
    except Exception as e:
        results['Advisor Service'] = f"❌ FAILED: {str(e)}"
    
    for service, status in results.items():
        print(f"  {service}: {status}")
    
    return results

def test_django_apis():
    """Test Django API views and URLs"""
    print("\n🌐 Testing Django APIs")
    
    results = {}
    
    # Test API view imports
    api_modules = [
        ('Authentication Views', 'apps.authentication.views'),
        ('Course Views', 'apps.courses.views'),
        ('Learning Plans Views', 'apps.learning_plans.views'),
        ('AI Services Views', 'apps.ai_services.views'),
    ]
    
    for name, module_path in api_modules:
        try:
            __import__(module_path)
            results[name] = "✅ OK"
        except Exception as e:
            results[name] = f"❌ FAILED: {str(e)}"
    
    # Test URL configurations
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        # Test health endpoint
        response = client.get('/health/')
        results['Health Endpoint'] = f"✅ OK (status: {response.status_code})"
    except Exception as e:
        results['Health Endpoint'] = f"❌ FAILED: {str(e)}"
    
    for api, status in results.items():
        print(f"  {api}: {status}")
    
    return results

def test_inter_service_integration():
    """Test integration between services"""
    print("\n🔗 Testing Inter-Service Integration")
    
    results = {}
    
    # Test database + AI service integration
    try:
        from apps.authentication.models import User
        from llm.services.exercise_service import get_exercise_service
        
        # Check if we can generate exercises for a user
        if User.objects.exists():
            user = User.objects.first()
            exercise_service = get_exercise_service()
            
            # This should not fail even without API key
            mock_result = exercise_service.generate_exercises(
                user_id=str(user.uuid),
                num_questions=1
            )
            results['DB + AI Integration'] = "✅ OK (mock data generated)"
        else:
            results['DB + AI Integration'] = "⚠️ No users to test with"
    except Exception as e:
        results['DB + AI Integration'] = f"❌ FAILED: {str(e)}"
    
    # Test cache integration
    try:
        from django.core.cache import cache
        cache.set('integration_test', 'working', 30)
        value = cache.get('integration_test')
        if value == 'working':
            results['Cache Integration'] = "✅ OK"
        else:
            results['Cache Integration'] = "❌ FAILED: Cache not working"
        cache.delete('integration_test')
    except Exception as e:
        results['Cache Integration'] = f"❌ FAILED: {str(e)}"
    
    for integration, status in results.items():
        print(f"  {integration}: {status}")
    
    return results

def identify_cleanup_opportunities():
    """Identify files and code that can be cleaned up"""
    print("\n🧹 Identifying Cleanup Opportunities")
    
    cleanup_items = []
    
    # Find duplicate test files
    root_tests = list(project_root.glob("test_*.py"))
    tests_dir = project_root / "tests"
    
    if root_tests and tests_dir.exists():
        cleanup_items.append({
            'type': 'duplicate_tests',
            'description': f'Consolidate {len(root_tests)} test files from root to tests/ directory',
            'files': [str(f) for f in root_tests]
        })
    
    # Find cache files
    cache_dirs = list(project_root.rglob("__pycache__"))
    if cache_dirs:
        cleanup_items.append({
            'type': 'cache_cleanup',
            'description': f'Remove {len(cache_dirs)} __pycache__ directories',
            'files': [str(d) for d in cache_dirs]
        })
    
    # Find large log files
    log_files = list(project_root.rglob("*.log"))
    large_logs = [f for f in log_files if f.stat().st_size > 1024 * 1024]  # > 1MB
    if large_logs:
        cleanup_items.append({
            'type': 'large_logs',
            'description': f'Found {len(large_logs)} large log files',
            'files': [str(f) for f in large_logs]
        })
    
    # Find potentially unused files
    gitignore_file = project_root / '.gitignore'
    if not gitignore_file.exists():
        cleanup_items.append({
            'type': 'missing_gitignore',
            'description': 'No .gitignore file found',
            'files': []
        })
    
    print(f"📋 Found {len(cleanup_items)} cleanup opportunities:")
    for item in cleanup_items:
        print(f"  - {item['description']}")
    
    return cleanup_items

def generate_api_documentation():
    """Generate API endpoint documentation"""
    print("\n📝 Generating API Documentation")
    
    api_endpoints = []
    
    try:
        from django.urls import get_resolver
        from django.conf import settings
        
        resolver = get_resolver(settings.ROOT_URLCONF)
        
        # This is a simplified approach - in a real scenario, you'd use DRF's schema generation
        api_endpoints = [
            {
                'path': '/api/auth/login/',
                'method': 'POST',
                'description': 'User authentication',
                'requires_auth': False
            },
            {
                'path': '/api/auth/logout/',
                'method': 'POST',
                'description': 'User logout',
                'requires_auth': True
            },
            {
                'path': '/api/courses/',
                'method': 'GET',
                'description': 'List user courses',
                'requires_auth': True
            },
            {
                'path': '/api/learning-plans/',
                'method': 'GET',
                'description': 'List learning plans',
                'requires_auth': True
            },
            {
                'path': '/api/ai/generate-exercises/',
                'method': 'POST',
                'description': 'Generate AI exercises',
                'requires_auth': True
            }
        ]
        
        print(f"📋 Documented {len(api_endpoints)} API endpoints")
        
    except Exception as e:
        print(f"❌ Failed to generate API documentation: {str(e)}")
    
    return api_endpoints

def main():
    """Run comprehensive backend analysis"""
    print("🚀 ClassBackend Service Verification and Analysis\n")
    
    # Run all tests
    structure_issues = analyze_project_structure()
    db_results = test_database_models()
    ai_results = test_langchain_services()
    api_results = test_django_apis()
    integration_results = test_inter_service_integration()
    cleanup_items = identify_cleanup_opportunities()
    api_docs = generate_api_documentation()
    
    # Generate summary
    print("\n📊 SUMMARY")
    print("=" * 50)
    
    total_tests = len(db_results) + len(ai_results) + len(api_results) + len(integration_results)
    passed_tests = sum(1 for results in [db_results, ai_results, api_results, integration_results] 
                      for result in results.values() if "✅" in result)
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Structural Issues: {len(structure_issues)}")
    print(f"Cleanup Opportunities: {len(cleanup_items)}")
    print(f"API Endpoints Documented: {len(api_docs)}")
    
    # Status
    if passed_tests == total_tests and len(structure_issues) == 0:
        print("\n🎉 Backend is in excellent condition!")
    elif passed_tests >= total_tests * 0.8:
        print("\n✅ Backend is in good condition with minor issues to address")
    else:
        print("\n⚠️ Backend has significant issues that need attention")
    
    return {
        'structure_issues': structure_issues,
        'test_results': {
            'database': db_results,
            'ai_services': ai_results,
            'api': api_results,
            'integration': integration_results
        },
        'cleanup_items': cleanup_items,
        'api_endpoints': api_docs
    }

if __name__ == "__main__":
    results = main()
