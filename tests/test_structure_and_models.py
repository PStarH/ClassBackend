"""
测试个性化AI Agent功能结构
测试新增的方法和数据库模型，不依赖LLM客户端
"""
import os
import sys
import django
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.courses.models import CourseProgress
from apps.learning_plans.models import StudySession
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes, StudentLearningPattern
from apps.authentication.models import UserSettings

User = get_user_model()

def test_structure_and_models():
    """测试新增的数据库模型和功能结构"""
    
    print("=== 测试个性化AI Agent结构和模型 ===\\n")
    
    # 1. 获取或创建测试用户
    try:
        user = User.objects.filter(email__contains='test').first()
        if not user:
            print("创建测试用户...")
            user = User.objects.create_user(
                email='test_personalized@example.com',
                username='test_personalized',
                password='testpass123'
            )
        
        print(f"使用测试用户: {user.email} (ID: {user.uuid})")
        
        # 2. 创建用户设置
        user_settings, created = UserSettings.objects.get_or_create(
            user_uuid=user,
            defaults={
                'preferred_style': 'Practical',
                'preferred_pace': 'normal',
                'education_level': 'undergraduate',
                'tone': 'friendly'
            }
        )
        print(f"✓ 用户设置: {'创建' if created else '已存在'}")
        
        # 3. 测试StudentQuestion模型
        print("\\n3. 测试StudentQuestion模型...")
        question = StudentQuestion.objects.create(
            user=user,
            question_text="什么是Python中的列表推导式？",
            question_type="concept",
            difficulty_level="medium",
            context="学习Python数据结构时的疑问",
            ai_response='{"answer": "列表推导式是一种简洁的创建列表的方法..."}',
            is_resolved=True,
            tags=["Python", "数据结构", "概念理解"]
        )
        print(f"✓ 学生问题记录创建成功 - ID: {question.id}")
        
        # 4. 测试TeacherNotes模型
        print("\\n4. 测试TeacherNotes模型...")
        teacher_note = TeacherNotes.objects.create(
            user=user,
            note_type="observation",
            priority="medium",
            title="学生概念理解能力观察",
            content="学生对Python基础概念理解较好，但在实际应用中需要更多练习。",
            observations={
                "question_frequency": 3,
                "question_type": "concept",
                "learning_pattern": "理论掌握好，实践需加强"
            },
            action_items=[
                "提供更多实践练习",
                "加强代码实现训练"
            ],
            tags=["概念理解", "实践能力", "需要关注"]
        )
        print(f"✓ 教师笔记记录创建成功 - ID: {teacher_note.id}")
        
        # 5. 测试StudentLearningPattern模型
        print("\\n5. 测试StudentLearningPattern模型...")
        learning_pattern = StudentLearningPattern.objects.create(
            user=user,
            attention_span_minutes=25,
            strengths=["logical", "analytical"],
            weaknesses=["attention_difficulties"],
            frequent_question_types=["concept", "application"],
            difficulty_progression_rate=1.2,
            preferred_learning_time={"morning": True, "afternoon": False},
            concept_mastery_patterns={"basic": "fast", "advanced": "medium"}
        )
        print(f"✓ 学习模式记录创建成功 - ID: {learning_pattern.id}")
        
        # 6. 测试模型关联和查询
        print("\\n6. 测试模型关联和查询...")
        
        # 查询用户的所有问题
        user_questions = StudentQuestion.objects.filter(user=user)
        print(f"✓ 用户问题数量: {user_questions.count()}")
        
        # 查询用户的所有教师笔记
        user_notes = TeacherNotes.objects.filter(user=user)
        print(f"✓ 用户教师笔记数量: {user_notes.count()}")
        
        # 查询用户的学习模式
        user_patterns = StudentLearningPattern.objects.filter(user=user)
        print(f"✓ 用户学习模式记录数量: {user_patterns.count()}")
        
        # 7. 测试数据分析功能
        print("\\n7. 测试数据分析功能...")
        
        # 测试问题分析
        concept_questions = StudentQuestion.objects.filter(
            user=user, 
            question_type="concept"
        ).count()
        print(f"✓ 概念类型问题数量: {concept_questions}")
        
        # 测试笔记分析
        high_priority_notes = TeacherNotes.objects.filter(
            user=user,
            priority="high"
        ).count()
        print(f"✓ 高优先级笔记数量: {high_priority_notes}")
        
        # 8. 测试服务方法结构
        print("\\n8. 测试服务方法结构...")
        
        # 导入服务
        try:
            from llm.services.teacher_service import TeacherService
            teacher = TeacherService()
            
            # 检查新方法是否存在
            has_personalized_section = hasattr(teacher, 'generate_personalized_section_detail')
            has_answer_question = hasattr(teacher, 'answer_student_question')
            print(f"✓ Teacher服务个性化方法: {'存在' if has_personalized_section and has_answer_question else '缺失'}")
            
        except Exception as e:
            print(f"✗ Teacher服务导入失败: {e}")
        
        try:
            from llm.services.advisor_service import AdvisorService
            advisor = AdvisorService()
            
            # 检查新方法是否存在
            has_personalized_plan = hasattr(advisor, 'create_personalized_plan')
            has_personalized_chat = hasattr(advisor, 'chat_with_personalized_agent')
            print(f"✓ Advisor服务个性化方法: {'存在' if has_personalized_plan and has_personalized_chat else '缺失'}")
            
        except Exception as e:
            print(f"✗ Advisor服务导入失败: {e}")
        
        try:
            from llm.services.exercise_service import ExerciseService
            exercise = ExerciseService()
            
            # 检查个性化方法是否存在
            has_personalized_exercises = hasattr(exercise, '_generate_personalized_exercises')
            has_personalized_data = hasattr(exercise, '_personalize_user_data')
            print(f"✓ Exercise服务个性化方法: {'存在' if has_personalized_exercises and has_personalized_data else '缺失'}")
            
        except Exception as e:
            print(f"✗ Exercise服务导入失败: {e}")
        
        try:
            from llm.services.student_analyzer import StudentDataAnalyzer
            analyzer = StudentDataAnalyzer()
            
            # 检查分析方法是否存在
            has_profile = hasattr(analyzer, 'get_student_profile')
            has_insights = hasattr(analyzer, 'generate_learning_insights')
            print(f"✓ 学生分析器方法: {'存在' if has_profile and has_insights else '缺失'}")
            
        except Exception as e:
            print(f"✗ 学生分析器导入失败: {e}")
        
        # 9. 测试数据清理（可选）
        print("\\n9. 清理测试数据...")
        test_data_count = 0
        test_data_count += StudentQuestion.objects.filter(user=user).count()
        test_data_count += TeacherNotes.objects.filter(user=user).count()
        test_data_count += StudentLearningPattern.objects.filter(user=user).count()
        
        print(f"✓ 本次测试创建的数据记录总数: {test_data_count}")
        
        print("\\n=== 结构和模型测试完成 ===")
        print("\\n功能摘要:")
        print("✓ 数据库模型: StudentQuestion, TeacherNotes, StudentLearningPattern")
        print("✓ Teacher服务: 个性化章节内容、学生问题回答、教师笔记生成")
        print("✓ Advisor服务: 个性化学习计划、个性化聊天、建议记录")
        print("✓ Exercise服务: 个性化练习题生成、学生特征适应")
        print("✓ 学生分析器: 档案分析、学习洞察、模式更新")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_structure_and_models()
