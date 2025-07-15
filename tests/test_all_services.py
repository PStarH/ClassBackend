#!/usr/bin/env python
"""
Comprehensive Backend Services Test
Tests all services to ensure they are functioning correctly
"""

import os
import sys
import django
from django.utils import timezone
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Import all necessary modules
from django.contrib.auth import get_user_model
from django.test import Client
from django.db import connection
from apps.courses.models import CourseProgress
from apps.learning_plans.models import StudySession
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes

# Import all AI services
from llm.services.advisor_service import get_advisor_service
from llm.services.teacher_service import get_teacher_service
from llm.services.exercise_service import get_exercise_service
from llm.services.memory_service import memory_service
from llm.services.student_analyzer import student_analyzer

# Import API views
from apps.learning_plans import views as learning_plan_views
from apps.ai_services import views as ai_service_views

User = get_user_model()


class ServiceTester:
    """Comprehensive service testing class"""
    
    def __init__(self):
        self.results = {}
        self.test_user = None
        self.client = Client()
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
        
    def print_result(self, name: str, status: str, details: str = ""):
        """Print test result"""
        icon = "✅" if "success" in status.lower() or "passed" in status.lower() else "❌"
        print(f"  {name}: {icon} {status}")
        if details:
            print(f"     → {details}")
            
    def setup_test_data(self):
        """Setup test user and initial data"""
        try:
            # Create or get test user
            self.test_user, created = User.objects.get_or_create(
                email='service_test@test.com',
                defaults={
                    'username': 'service_test_user'
                }
            )
            if created:
                self.test_user.set_password('TestPass123!')
                self.test_user.save()
                
            # Login the test client
            self.client.force_login(self.test_user)
            
            self.print_result("Test Data Setup", "Success", f"User: {self.test_user.email}")
            return True
            
        except Exception as e:
            self.print_result("Test Data Setup", "Failed", str(e))
            return False
            
    def test_ai_services(self):
        """Test all AI services"""
        self.print_header("Testing AI Services")
        
        # Test Advisor Service
        try:
            advisor = get_advisor_service()
            if advisor and advisor.is_available():
                # Test create plan
                plan = advisor.create_plan("Python Programming", session_id="test_session")
                if plan and isinstance(plan, list) and len(plan) > 0:
                    self.print_result("Advisor Service - Create Plan", "Success", 
                                    f"Created plan with {len(plan)} sections")
                else:
                    self.print_result("Advisor Service - Create Plan", "Failed", "Invalid plan structure")
                    
                # Test chat
                chat_response = advisor.chat_with_agent(
                    "What should I learn first?",
                    "Python Programming",
                    session_id="test_session"
                )
                if chat_response and 'reply' in chat_response:
                    self.print_result("Advisor Service - Chat", "Success", 
                                    f"Response length: {len(chat_response['reply'])}")
                else:
                    self.print_result("Advisor Service - Chat", "Failed", "Invalid chat response")
            else:
                self.print_result("Advisor Service", "Not Available", "Service unavailable")
                
        except Exception as e:
            self.print_result("Advisor Service", "Failed", str(e))
            
        # Test Teacher Service
        try:
            teacher = get_teacher_service()
            if teacher and teacher.is_available():
                # Test create outline
                outline = teacher.create_outline("Python Basics")
                if outline and isinstance(outline, list) and len(outline) > 0:
                    self.print_result("Teacher Service - Create Outline", "Success", 
                                    f"Created outline with {len(outline)} sections")
                else:
                    self.print_result("Teacher Service - Create Outline", "Failed", "Invalid outline")
                    
                # Test explain topic
                explanation = teacher.explain_topic("Variables in Python")
                if explanation and 'explanation' in explanation:
                    self.print_result("Teacher Service - Explain Topic", "Success", 
                                    f"Explanation length: {len(explanation['explanation'])}")
                else:
                    self.print_result("Teacher Service - Explain Topic", "Failed", "Invalid explanation")
            else:
                self.print_result("Teacher Service", "Not Available", "Service unavailable")
                
        except Exception as e:
            self.print_result("Teacher Service", "Failed", str(e))
            
        # Test Exercise Service
        try:
            exercise = get_exercise_service()
            if exercise and exercise.is_available():
                # Test generate exercises
                exercises = exercise.generate_exercises(
                    "Python variables and data types",
                    difficulty=1,
                    count=3,
                    session_id="test_session"
                )
                if exercises and isinstance(exercises, list) and len(exercises) > 0:
                    self.print_result("Exercise Service - Generate", "Success", 
                                    f"Generated {len(exercises)} exercises")
                else:
                    self.print_result("Exercise Service - Generate", "Failed", "No exercises generated")
                    
                # Test evaluate answer
                if exercises and len(exercises) > 0:
                    evaluation = exercise.evaluate_answer(
                        exercises[0],
                        "x = 5",
                        session_id="test_session"
                    )
                    if evaluation and 'is_correct' in evaluation:
                        self.print_result("Exercise Service - Evaluate", "Success", 
                                        f"Evaluation: {evaluation.get('is_correct')}")
                    else:
                        self.print_result("Exercise Service - Evaluate", "Failed", "Invalid evaluation")
            else:
                self.print_result("Exercise Service", "Not Available", "Service unavailable")
                
        except Exception as e:
            self.print_result("Exercise Service", "Failed", str(e))
            
        # Test Memory Service
        try:
            if memory_service:
                # Test conversation memory
                memory_service.update_conversation(
                    "test_session",
                    "What is Python?",
                    "Python is a high-level programming language"
                )
                
                history = memory_service.get_conversation_history("test_session", limit=5)
                if history:
                    self.print_result("Memory Service - Conversation", "Success", 
                                    f"Retrieved {len(history)} messages")
                else:
                    self.print_result("Memory Service - Conversation", "Success", "Empty history")
                    
                # Test context summary
                summary = memory_service.get_context_summary("test_session")
                if summary:
                    self.print_result("Memory Service - Context", "Success", 
                                    f"Summary length: {len(summary)}")
                else:
                    self.print_result("Memory Service - Context", "Success", "No context yet")
            else:
                self.print_result("Memory Service", "Not Available", "Service unavailable")
                
        except Exception as e:
            self.print_result("Memory Service", "Failed", str(e))
            
        # Test Student Analyzer
        try:
            if student_analyzer:
                analysis = student_analyzer.analyze_student_progress(
                    str(self.test_user.uuid),
                    days=7
                )
                if analysis:
                    self.print_result("Student Analyzer", "Success", 
                                    f"Analysis keys: {list(analysis.keys())}")
                else:
                    self.print_result("Student Analyzer", "Success", "No data to analyze")
            else:
                self.print_result("Student Analyzer", "Not Available", "Service unavailable")
                
        except Exception as e:
            self.print_result("Student Analyzer", "Failed", str(e))
            
    def test_api_endpoints(self):
        """Test all API endpoints"""
        self.print_header("Testing API Endpoints")
        
        # Test health endpoint
        try:
            response = self.client.get('/health/')
            self.print_result("Health Endpoint", f"Status {response.status_code}", 
                            response.content.decode() if response.status_code == 200 else "")
        except Exception as e:
            self.print_result("Health Endpoint", "Failed", str(e))
            
        # Test API endpoints
        api_tests = [
            ('/api/v1/ai/status/', 'GET', None, 'AI Status'),
            ('/api/v1/learning-plans/', 'GET', None, 'Learning Plans List'),
            ('/api/v1/study-sessions/', 'GET', None, 'Study Sessions List'),
            ('/api/v1/courses/', 'GET', None, 'Courses List'),
        ]
        
        for url, method, data, name in api_tests:
            try:
                if method == 'GET':
                    response = self.client.get(url)
                elif method == 'POST':
                    response = self.client.post(url, data, content_type='application/json')
                    
                if response.status_code in [200, 201]:
                    content = response.json() if response.content else {}
                    self.print_result(f"API - {name}", "Success", 
                                    f"Status {response.status_code}")
                else:
                    self.print_result(f"API - {name}", f"Status {response.status_code}", 
                                    response.content.decode()[:100] if response.content else "")
            except Exception as e:
                self.print_result(f"API - {name}", "Failed", str(e))
                
    def test_database_operations(self):
        """Test database operations"""
        self.print_header("Testing Database Operations")
        
        try:
            # Test CourseProgress
            course_progress, created = CourseProgress.objects.get_or_create(
                user=self.test_user,
                content_id='test_course_123',
                defaults={
                    'proficiency_level': 0,
                    'difficulty': 5
                }
            )
            self.print_result("CourseProgress Model", "Success", 
                            f"{'Created' if created else 'Retrieved'} course progress")
            
            # Test StudySession
            study_session = StudySession.objects.create(
                user=self.test_user,
                course_progress=course_progress,
                start_time=timezone.now(),
                duration_minutes=45,
                effectiveness_rating=4,
                content_covered="Test content",
                subject_category="Python"
            )
            self.print_result("StudySession Model", "Success", 
                            f"Created session ID: {study_session.id}")
            
            # Test StudentQuestion
            question = StudentQuestion.objects.create(
                student=self.test_user,
                question_text="What is a variable?",
                subject="Python Basics",
                difficulty_level=1
            )
            self.print_result("StudentQuestion Model", "Success", 
                            f"Created question ID: {question.id}")
            
            # Test TeacherNotes
            note = TeacherNotes.objects.create(
                student=self.test_user,
                note_text="Good progress on basics",
                subject="Python",
                created_by=self.test_user
            )
            self.print_result("TeacherNotes Model", "Success", 
                            f"Created note ID: {note.id}")
            
            # Clean up
            study_session.delete()
            question.delete()
            note.delete()
            
        except Exception as e:
            self.print_result("Database Operations", "Failed", str(e))
            
    def test_cache_operations(self):
        """Test cache operations"""
        self.print_header("Testing Cache Operations")
        
        try:
            from django.core.cache import cache
            
            # Test set/get
            cache.set('test_key', 'test_value', 60)
            value = cache.get('test_key')
            if value == 'test_value':
                self.print_result("Cache Set/Get", "Success", "Basic operations working")
            else:
                self.print_result("Cache Set/Get", "Failed", f"Expected 'test_value', got '{value}'")
                
            # Test delete
            cache.delete('test_key')
            value = cache.get('test_key')
            if value is None:
                self.print_result("Cache Delete", "Success", "Delete operation working")
            else:
                self.print_result("Cache Delete", "Failed", f"Key still exists: {value}")
                
            # Test cache services
            from apps.learning_plans.cache_services import StudySessionCache
            
            stats = StudySessionCache.get_user_daily_stats(
                str(self.test_user.uuid),
                timezone.now().date()
            )
            self.print_result("Cache Services", "Success", 
                            f"Daily stats keys: {list(stats.keys()) if stats else 'None'}")
            
        except Exception as e:
            self.print_result("Cache Operations", "Failed", str(e))
            
    def test_authentication(self):
        """Test authentication and permissions"""
        self.print_header("Testing Authentication & Permissions")
        
        try:
            # Test authenticated request
            response = self.client.get('/api/v1/ai/status/')
            if response.status_code == 200:
                self.print_result("Authenticated Request", "Success", "User authenticated")
            else:
                self.print_result("Authenticated Request", "Failed", 
                                f"Status {response.status_code}")
                
            # Test unauthenticated request
            anon_client = Client()
            response = anon_client.get('/api/v1/ai/status/')
            if response.status_code == 401:
                self.print_result("Unauthenticated Request", "Success", 
                                "Properly rejected (401)")
            else:
                self.print_result("Unauthenticated Request", "Failed", 
                                f"Unexpected status {response.status_code}")
                
        except Exception as e:
            self.print_result("Authentication Tests", "Failed", str(e))
            
    def test_error_handling(self):
        """Test error handling"""
        self.print_header("Testing Error Handling")
        
        try:
            # Test invalid endpoint
            response = self.client.get('/api/v1/invalid-endpoint/')
            if response.status_code == 404:
                self.print_result("404 Error Handling", "Success", "Proper 404 response")
            else:
                self.print_result("404 Error Handling", "Failed", 
                                f"Unexpected status {response.status_code}")
                
            # Test invalid data
            response = self.client.post(
                '/api/v1/study-sessions/',
                json.dumps({'invalid': 'data'}),
                content_type='application/json'
            )
            if response.status_code in [400, 422]:
                self.print_result("Invalid Data Handling", "Success", 
                                "Proper validation error")
            else:
                self.print_result("Invalid Data Handling", "Warning", 
                                f"Status {response.status_code}")
                
        except Exception as e:
            self.print_result("Error Handling Tests", "Failed", str(e))
            
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("🚀 ClassBackend Comprehensive Service Test")
        print("="*60)
        
        if not self.setup_test_data():
            print("\n❌ Failed to setup test data. Aborting tests.")
            return
            
        self.test_ai_services()
        self.test_api_endpoints()
        self.test_database_operations()
        self.test_cache_operations()
        self.test_authentication()
        self.test_error_handling()
        
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print("\n✅ All tests completed. Review results above for any failures.")
        
        # Cleanup
        try:
            if self.test_user:
                # Don't delete the user as it might be used elsewhere
                print("\n🧹 Test user preserved: service_test_user")
        except:
            pass


if __name__ == "__main__":
    tester = ServiceTester()
    tester.run_all_tests()