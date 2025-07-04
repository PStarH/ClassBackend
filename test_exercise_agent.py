#!/usr/bin/env python
"""
测试练习题生成服务
"""
import os
import sys
import django
import json
from datetime import datetime

# 设置Django环境
sys.path.append('/Users/sampan/Documents/GitHub/ClassBackend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.authentication.models import User
from apps.courses.models import CourseProgress, CourseContent
from apps.learning_plans.models import StudySession
from llm.services.exercise_service import exercise_service


def test_exercise_generation():
    """测试练习题生成功能"""
    print("=== 练习题生成服务测试 ===\n")
    
    # 1. 检查服务状态
    print("1. 检查服务状态:")
    if exercise_service.is_available():
        print("✅ 练习题生成服务可用")
    else:
        print("❌ 练习题生成服务不可用")
        return
    
    # 2. 创建测试用户（如果不存在）
    print("\n2. 准备测试数据:")
    test_email = "test_exercise@example.com"
    try:
        user = User.objects.get(email=test_email)
        print(f"✅ 使用现有测试用户: {user.email}")
    except User.DoesNotExist:
        user = User.objects.create_user(
            email=test_email,
            username="test_exercise_user",
            password="Testpass123!"
        )
        print(f"✅ 创建测试用户: {user.email}")
    
    # 3. 创建课程内容和进度
    course_content = CourseContent.objects.create(
        outline={"title": "Python编程基础", "chapters": 5},
        chapters=[
            {"title": "Python基础语法", "text": "Python是一种解释型、面向对象的编程语言..."},
            {"title": "数据类型和变量", "text": "Python支持多种数据类型，包括数字、字符串、列表..."}
        ]
    )
    
    course_progress = CourseProgress.objects.create(
        user_uuid=user,
        subject_name="Python编程",
        content_id=course_content,
        proficiency_level=60,  # 中级水平
        learning_hour_week=8,   # 每周8小时
        learning_hour_total=40, # 累计40小时
        difficulty=6,           # 中等偏难
        user_experience="有一些编程基础，学过Java",
        feedback={"learning_style": "实践导向", "prefer_examples": True}
    )
    
    # 4. 创建学习会话
    study_session = StudySession.objects.create(
        user=user,
        course_progress=course_progress,
        start_time=datetime.now(),
        duration_minutes=60,
        content_covered="Python基础语法：变量定义、数据类型、条件语句、循环结构",
        effectiveness_rating=4,
        subject_category="编程语言",
        learning_environment="home"
    )
    
    print(f"✅ 创建课程进度: {course_progress.subject_name}")
    print(f"✅ 创建学习会话: {study_session.content_covered[:50]}...")
    
    # 5. 测试练习题生成
    print("\n3. 生成练习题:")
    try:
        result = exercise_service.generate_exercises(
            user_id=str(user.uuid),
            course_progress_id=str(course_progress.course_uuid),
            study_session_id=str(study_session.id)
        )
        
        if result.get('success'):
            exercises = result['exercises']
            metadata = result['metadata']
            
            print(f"✅ 成功生成 {len(exercises)} 道练习题")
            print(f"📊 元数据: 难度等级={metadata.get('difficulty_level')}, 熟练度={metadata.get('proficiency_level')}")
            
            # 显示前2道题
            for i, exercise in enumerate(exercises[:2]):
                print(f"\n--- 题目 {i+1} ---")
                print(f"问题: {exercise['question']}")
                print("选项:")
                for option in exercise['options']:
                    print(f"  {option['id']}: {option['text']}")
                print(f"正确答案: {exercise['correct_answer']}")
                print(f"难度: {exercise['difficulty']}/10")
                print(f"解析: {exercise['explanation']}")
        else:
            print(f"❌ 生成失败: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 6. 测试基于内容的练习题生成
    print("\n4. 测试基于指定内容的练习题生成:")
    try:
        user_data = {
            'subject_name': 'Python编程',
            'content_covered': ['Python变量和数据类型', 'if语句和循环'],
            'difficulty': 5,
            'proficiency_level': 50,
            'learning_hour_week': 6,
            'learning_hour_total': 30,
            'feedback': {'prefer_practical': True}
        }
        
        exercises = exercise_service._generate_exercises_with_ai(user_data, 3)
        validated_exercises = exercise_service.validate_exercise_format(exercises)
        
        print(f"✅ 基于指定内容生成 {len(validated_exercises)} 道练习题")
        
        # 显示第一道题
        if validated_exercises:
            ex = validated_exercises[0]
            print(f"\n--- 示例题目 ---")
            print(f"问题: {ex['question']}")
            print("选项:")
            for option in ex['options']:
                print(f"  {option['id']}: {option['text']}")
            print(f"正确答案: {ex['correct_answer']}")
            
    except Exception as e:
        print(f"❌ 基于内容生成测试失败: {str(e)}")
    
    # 7. 清理测试数据
    print("\n5. 清理测试数据:")
    try:
        study_session.delete()
        course_progress.delete()
        course_content.delete()
        # user.delete()  # 保留用户以便后续测试
        print("✅ 测试数据清理完成")
    except Exception as e:
        print(f"⚠️ 清理数据时出现问题: {str(e)}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_exercise_generation()
