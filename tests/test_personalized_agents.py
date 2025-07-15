"""
测试个性化AI Agent功能
包括teacher、advisor、exercise三个服务的个性化能力和学生笔记功能
"""
import os
import sys
import django

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.courses.models import CourseProgress
from apps.learning_plans.models import StudySession
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes, StudentLearningPattern
from llm.services.teacher_service import teacher_service
from llm.services.advisor_service import advisor_service
from llm.services.exercise_service import exercise_service
from llm.services.student_analyzer import student_analyzer

User = get_user_model()

def test_personalized_ai_agents():
    """测试个性化AI代理功能"""
    
    print("=== 测试个性化AI Agent功能 ===\n")
    
    # 1. 获取或创建测试用户
    try:
        user = User.objects.filter(email__contains='test').first()
        if not user:
            print("未找到测试用户，请确保数据库中有测试数据")
            return
        
        user_id = str(user.uuid)
        print(f"使用测试用户: {user.email} (ID: {user_id})")
        
        # 2. 测试学生数据分析器
        print("\\n2. 测试学生数据分析器...")
        try:
            student_profile = student_analyzer.get_student_profile(user_id)
            print(f"✓ 学生档案获取成功")
            print(f"  - 学习风格: {student_profile['profile']['settings'].get('preferred_style', 'N/A')}")
            print(f"  - 学习节奏: {student_profile['profile']['settings'].get('preferred_pace', 'N/A')}")
            
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            print(f"✓ 学习洞察生成成功")
            print(f"  - 建议数量: {len(learning_insights.get('recommendations', []))}")
        except Exception as e:
            print(f"✗ 学生分析器测试失败: {e}")
        
        # 3. 测试Teacher个性化功能
        print("\\n3. 测试Teacher个性化功能...")
        if teacher_service:
            try:
                # 测试个性化章节内容生成
                section_result = teacher_service.generate_personalized_section_detail(
                    index="1.1",
                    title="Python基础语法",
                    user_id=user_id
                )
                if section_result.get('personalization_applied'):
                    print("✓ 个性化章节内容生成成功")
                    print(f"  - 个性化应用: {section_result.get('personalization_applied')}")
                    print(f"  - 适应的学习风格: {section_result.get('student_profile_used', {}).get('learning_style', 'N/A')}")
                else:
                    print("✗ 个性化章节内容生成失败")
                
                # 测试学生问题回答功能
                question_result = teacher_service.answer_student_question(
                    question_text="什么是Python变量？",
                    user_id=user_id,
                    context="学习Python基础语法时遇到的问题"
                )
                if question_result.get('success'):
                    print("✓ 学生问题回答成功")
                    print(f"  - 问题记录ID: {question_result.get('question_record_id')}")
                    print(f"  - 个性化应用: {question_result.get('personalization_applied')}")
                else:
                    print(f"✗ 学生问题回答失败: {question_result.get('error')}")
                    
            except Exception as e:
                print(f"✗ Teacher服务测试失败: {e}")
        else:
            print("✗ Teacher服务未初始化")
        
        # 4. 测试Advisor个性化功能
        print("\\n4. 测试Advisor个性化功能...")
        if advisor_service:
            try:
                # 测试个性化学习计划创建
                plan_result = advisor_service.create_personalized_plan(
                    topic="Python编程入门",
                    user_id=user_id
                )
                if isinstance(plan_result, list) and len(plan_result) > 0:
                    print("✓ 个性化学习计划创建成功")
                    print(f"  - 计划阶段数: {len(plan_result)}")
                    print(f"  - 个性化标记: {plan_result[0].get('personalized', False) if plan_result else 'N/A'}")
                else:
                    print("✗ 个性化学习计划创建失败")
                
                # 测试个性化聊天功能
                chat_result = advisor_service.chat_with_personalized_agent(
                    message="我觉得学习进度有点慢，怎么办？",
                    current_plan={"sections": []},
                    user_id=user_id
                )
                if chat_result.get('personalized'):
                    print("✓ 个性化聊天功能成功")
                    print(f"  - 回复长度: {len(chat_result.get('reply', ''))}")
                    print(f"  - 学生适应摘要: {bool(chat_result.get('student_adaptations'))}")
                else:
                    print("✗ 个性化聊天功能失败")
                    
            except Exception as e:
                print(f"✗ Advisor服务测试失败: {e}")
        else:
            print("✗ Advisor服务未初始化")
        
        # 5. 测试Exercise个性化功能
        print("\\n5. 测试Exercise个性化功能...")
        if exercise_service:
            try:
                # 测试个性化练习题生成
                exercise_result = exercise_service.generate_exercises(
                    user_id=user_id,
                    num_questions=3
                )
                if exercise_result.get('success'):
                    exercises = exercise_result.get('exercises', [])
                    print("✓ 个性化练习题生成成功")
                    print(f"  - 练习题数量: {len(exercises)}")
                    print(f"  - 个性化应用: {exercise_result.get('metadata', {}).get('personalization_applied', False)}")
                    print(f"  - 适应的学习风格: {exercise_result.get('metadata', {}).get('learning_style', 'N/A')}")
                else:
                    print(f"✗ 个性化练习题生成失败: {exercise_result.get('error')}")
                    
            except Exception as e:
                print(f"✗ Exercise服务测试失败: {e}")
        else:
            print("✗ Exercise服务未初始化")
        
        # 6. 测试数据库记录
        print("\\n6. 测试数据库记录...")
        try:
            # 检查学生问题记录
            question_count = StudentQuestion.objects.filter(user=user).count()
            print(f"✓ 学生问题记录: {question_count}条")
            
            # 检查教师笔记记录
            notes_count = TeacherNotes.objects.filter(user=user).count()
            print(f"✓ 教师笔记记录: {notes_count}条")
            
            # 检查学习模式记录
            pattern_count = StudentLearningPattern.objects.filter(user=user).count()
            print(f"✓ 学习模式记录: {pattern_count}条")
            
            # 显示最近的记录
            recent_question = StudentQuestion.objects.filter(user=user).order_by('-created_at').first()
            if recent_question:
                print(f"  - 最近问题: {recent_question.question_text[:50]}...")
            
            recent_note = TeacherNotes.objects.filter(user=user).order_by('-created_at').first()
            if recent_note:
                print(f"  - 最近笔记: {recent_note.title}")
                
        except Exception as e:
            print(f"✗ 数据库记录检查失败: {e}")
        
        print("\\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_personalized_ai_agents()
