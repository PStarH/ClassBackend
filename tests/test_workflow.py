#!/usr/bin/env python
"""
API 功能测试脚本
"""
import os
import sys
import django
import json
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.authentication.models import UserSettings
from apps.courses.models import CourseContent, CourseProgress
from apps.learning_plans.models import StudySession

User = get_user_model()

def test_user_workflow():
    """测试完整的用户工作流程"""
    print("=== Testing Complete User Workflow ===")
    
    client = Client()
    
    # 1. 用户注册
    print("\n1. Testing User Registration...")
    register_data = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'SecurePass123!'
    }
    
    response = client.post('/api/v1/auth/register/', register_data, content_type='application/json')
    print(f"Registration response: {response.status_code}")
    if response.status_code == 201:
        print("✓ User registration successful")
        user_data = response.json()
        user_id = user_data['data']['uuid']
        print(f"✓ User ID: {user_id}")
    else:
        print(f"✗ Registration failed: {response.json()}")
        return False
    
    # 2. 用户登录
    print("\n2. Testing User Login...")
    login_data = {
        'email': 'test@example.com',
        'password': 'SecurePass123!'
    }
    
    response = client.post('/api/v1/auth/login/', login_data, content_type='application/json')
    print(f"Login response: {response.status_code}")
    if response.status_code == 200:
        print("✓ User login successful")
        login_response = response.json()
        # 在实际应用中，这里会有token等认证信息
    else:
        print(f"✗ Login failed: {response.json()}")
        return False
    
    # 3. 创建用户设置
    print("\n3. Testing User Settings...")
    try:
        user = User.objects.get(email='test@example.com')
        settings, created = UserSettings.objects.get_or_create(
            user_uuid=user,
            defaults={
                'preferred_pace': 'Moderate',
                'preferred_style': 'Practical',
                'tone': 'friendly',
                'skills': ['Python', 'Django']
            }
        )
        if created:
            print("✓ User settings created")
        else:
            print("✓ User settings already exist")
    except Exception as e:
        print(f"✗ User settings error: {e}")
        return False
    
    # 4. 创建课程内容
    print("\n4. Testing Course Content...")
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
    except Exception as e:
        print(f"✗ Course content creation error: {e}")
        return False
    
    # 5. 创建课程进度
    print("\n5. Testing Course Progress...")
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
        print(f"✗ Course progress creation error: {e}")
        return False
    
    # 6. 创建学习会话
    print("\n6. Testing Study Session...")
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
        print(f"✗ Study session creation error: {e}")
        return False
    
    # 7. 测试练习题生成
    print("\n7. Testing Exercise Generation...")
    try:
        exercise_data = {
            'user_id': str(user.uuid),
            'course_progress_id': str(course_progress.course_uuid),
            'study_session_id': str(study_session.id),
            'num_questions': 3
        }
        
        response = client.post('/api/v1/ai/exercise/generate/', exercise_data, content_type='application/json')
        print(f"Exercise generation response: {response.status_code}")
        
        if response.status_code == 200:
            exercises_response = response.json()
            if exercises_response.get('success'):
                print("✓ Exercise generation successful")
                exercises = exercises_response.get('exercises', [])
                print(f"✓ Generated {len(exercises)} exercises")
                
                # 显示第一个练习题的示例
                if exercises:
                    first_exercise = exercises[0]
                    print(f"✓ Sample exercise: {first_exercise.get('question', 'N/A')[:50]}...")
            else:
                print(f"✗ Exercise generation failed: {exercises_response}")
        else:
            print(f"✗ Exercise generation request failed: {response.status_code}")
            if hasattr(response, 'json'):
                print(f"   Error details: {response.json()}")
    except Exception as e:
        print(f"✗ Exercise generation error: {e}")
    
    # 8. 测试其他API端点
    print("\n8. Testing Other API Endpoints...")
    
    # 测试用户信息获取（需要认证）
    try:
        # 模拟登录状态（在实际应用中会使用Token认证）
        client.force_login(user)
        response = client.get('/api/v1/auth/user/')
        print(f"User detail response: {response.status_code}")
        if response.status_code == 200:
            print("✓ User detail retrieval successful")
    except Exception as e:
        print(f"User detail test error: {e}")
    
    # 测试练习题服务状态
    try:
        response = client.get('/api/v1/ai/exercise/status/')
        print(f"Exercise service status response: {response.status_code}")
        if response.status_code == 200:
            status_data = response.json()
            print(f"✓ Exercise service status: {status_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"Exercise service status test error: {e}")
    
    return True

def cleanup_test_data():
    """清理测试数据"""
    print("\n=== Cleaning up test data ===")
    try:
        User.objects.filter(email='test@example.com').delete()
        print("✓ Test data cleaned up")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == "__main__":
    print("Backend API Workflow Test")
    print("=" * 50)
    
    try:
        success = test_user_workflow()
        if success:
            print("\n" + "=" * 50)
            print("✓ All tests completed successfully!")
        else:
            print("\n" + "=" * 50)
            print("✗ Some tests failed")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        cleanup_test_data()
