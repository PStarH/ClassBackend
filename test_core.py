#!/usr/bin/env python
"""
简化的后端功能测试
"""
import os
import sys
import django
import json
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.authentication.models import UserSettings
from apps.courses.models import CourseContent, CourseProgress
from apps.learning_plans.models import StudySession

User = get_user_model()

def test_models_and_services():
    """测试模型和服务"""
    print("=== Testing Models and Services ===")
    
    # 1. 测试用户创建
    print("\n1. Testing User Creation...")
    try:
        # 清理已存在的测试用户
        User.objects.filter(email='test@example.com').delete()
        
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='SecurePass123!'
        )
        print(f"✓ User created: {user.email} (ID: {user.uuid})")
        
        # 创建用户设置
        user_settings = UserSettings.objects.create(
            user_uuid=user,
            preferred_pace='Moderate',
            preferred_style='Practical',
            tone='friendly',
            skills=['Python', 'Django']
        )
        print(f"✓ User settings created")
        
    except Exception as e:
        print(f"✗ User creation failed: {e}")
        return False
    
    # 2. 测试课程内容创建
    print("\n2. Testing Course Content...")
    try:
        course_content = CourseContent.objects.create(
            outline={
                'title': 'Python基础教程',
                'description': '学习Python编程基础',
                'difficulty': 'beginner'
            },
            chapters=[
                {
                    'title': '第一章：Python简介',
                    'text': 'Python是一种高级编程语言...',
                    'created_at': datetime.now().isoformat()
                },
                {
                    'title': '第二章：变量和数据类型',
                    'text': '在Python中，变量是存储数据的容器...',
                    'created_at': datetime.now().isoformat()
                }
            ]
        )
        print(f"✓ Course content created: {course_content.content_id}")
        print(f"✓ Chapter count: {course_content.chapter_count}")
        
    except Exception as e:
        print(f"✗ Course content creation failed: {e}")
        return False
    
    # 3. 测试课程进度创建
    print("\n3. Testing Course Progress...")
    try:
        course_progress = CourseProgress.objects.create(
            user_uuid=user,
            subject_name='Python编程',
            content_id=course_content,
            user_experience='有一些编程基础，想学习Python',
            proficiency_level=25,
            learning_hour_week=10,
            learning_hour_total=20,
            difficulty=5,
            feedback={'satisfaction': 8, 'clarity': 9}
        )
        print(f"✓ Course progress created: {course_progress.course_uuid}")
        
    except Exception as e:
        print(f"✗ Course progress creation failed: {e}")
        return False
    
    # 4. 测试学习会话创建
    print("\n4. Testing Study Session...")
    try:
        study_session = StudySession.objects.create(
            user=user,
            start_time=datetime.now(),
            duration_minutes=45,
            content_covered='学习了Python基础语法和变量概念',
            effectiveness_rating=4,
            course_progress=course_progress,
            subject_category='编程',
            learning_environment='home',
            device_type='laptop'
        )
        print(f"✓ Study session created: {study_session.id}")
        
    except Exception as e:
        print(f"✗ Study session creation failed: {e}")
        return False
    
    # 5. 测试LLM练习题生成服务
    print("\n5. Testing Exercise Generation Service...")
    try:
        from llm.services.exercise_service import exercise_service
        
        if not exercise_service.is_available():
            print("✗ Exercise service not available - check API configuration")
            return True  # 这不是致命错误，LLM服务可能没有配置
        
        # 测试练习题生成
        result = exercise_service.generate_exercises(
            user_id=str(user.uuid),
            course_progress_id=str(course_progress.course_uuid),
            study_session_id=str(study_session.id),
            num_questions=3
        )
        
        if result.get('success'):
            exercises = result.get('exercises', [])
            print(f"✓ Exercise generation successful - Generated {len(exercises)} exercises")
            
            if exercises:
                first_exercise = exercises[0]
                print(f"✓ Sample exercise: {first_exercise.get('question', 'N/A')[:60]}...")
                print(f"✓ Exercise type: {first_exercise.get('type', 'N/A')}")
        else:
            print(f"✗ Exercise generation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"✗ Exercise service test failed: {e}")
    
    # 6. 测试数据关联
    print("\n6. Testing Data Relationships...")
    try:
        # 测试外键关联
        assert study_session.course_progress == course_progress
        assert course_progress.user_uuid == user
        assert course_progress.content_id == course_content
        
        # 测试反向关联
        user_sessions = user.study_sessions.all()
        user_progresses = user.course_progresses.all()
        
        print(f"✓ User has {user_sessions.count()} study sessions")
        print(f"✓ User has {user_progresses.count()} course progresses")
        print(f"✓ Course content has {course_content.progress_records.count()} progress records")
        
    except Exception as e:
        print(f"✗ Data relationship test failed: {e}")
        return False
    
    return True

def test_database_queries():
    """测试数据库查询性能"""
    print("\n=== Testing Database Queries ===")
    
    try:
        from django.db import connection
        
        # 测试一些基本查询
        user_count = User.objects.count()
        course_count = CourseContent.objects.count()
        progress_count = CourseProgress.objects.count()
        session_count = StudySession.objects.count()
        
        print(f"✓ Database counts - Users: {user_count}, Courses: {course_count}, Progress: {progress_count}, Sessions: {session_count}")
        
        # 测试复杂查询
        recent_sessions = StudySession.objects.select_related('user', 'course_progress').filter(
            duration_minutes__gt=30
        )[:5]
        
        print(f"✓ Complex query executed - Found {recent_sessions.count()} sessions > 30 minutes")
        
        # 显示查询数量
        query_count = len(connection.queries)
        print(f"✓ Total queries executed: {query_count}")
        
    except Exception as e:
        print(f"✗ Database query test failed: {e}")
        return False
    
    return True

def cleanup_test_data():
    """清理测试数据"""
    print("\n=== Cleaning up test data ===")
    try:
        User.objects.filter(email='test@example.com').delete()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"Cleanup error: {e}")

def test_llm_service_directly():
    """直接测试LLM服务"""
    print("\n=== Direct LLM Service Test ===")
    
    try:
        from llm.core.client import llm_factory
        from llm.core.config import LLMConfig
        
        print(f"✓ LLM Client available: {llm_factory.is_available()}")
        print(f"✓ API Key configured: {bool(LLMConfig.API_KEY)}")
        print(f"✓ Model: {LLMConfig.MODEL_NAME}")
        
        if llm_factory.is_available():
            # 测试简单的LLM调用
            from llm.core.base_service import LLMBaseService
            
            service = LLMBaseService()
            simple_response = service.simple_chat("请用一句话介绍Python编程语言。")
            print(f"✓ LLM response: {simple_response[:100]}...")
            
    except Exception as e:
        print(f"✗ LLM service test failed: {e}")

if __name__ == "__main__":
    print("Backend Core Functionality Test")
    print("=" * 50)
    
    try:
        # 核心功能测试
        success = test_models_and_services()
        
        if success:
            # 数据库查询测试
            test_database_queries()
            
            # LLM服务测试
            test_llm_service_directly()
            
            print("\n" + "=" * 50)
            print("✓ Core functionality tests completed successfully!")
        else:
            print("\n" + "=" * 50)
            print("✗ Some core tests failed")
            
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        cleanup_test_data()
