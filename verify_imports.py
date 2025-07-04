"""
验证advisor服务导入
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

try:
    from llm.services.advisor_service import advisor_service
    print("✓ Advisor服务导入成功")
    print(f"  - 服务实例: {advisor_service is not None}")
    
    # 检查新增的个性化方法
    has_personalized_plan = hasattr(advisor_service, 'create_personalized_plan')
    has_personalized_chat = hasattr(advisor_service, 'chat_with_personalized_agent')
    print(f"  - 个性化方法: {'存在' if has_personalized_plan and has_personalized_chat else '缺失'}")
    
except Exception as e:
    print(f"✗ Advisor服务导入失败: {e}")

try:
    from llm.services.teacher_service import teacher_service
    print("✓ Teacher服务导入成功")
    
    # 检查新增的个性化方法
    has_personalized_section = hasattr(teacher_service, 'generate_personalized_section_detail')
    has_answer_question = hasattr(teacher_service, 'answer_student_question')
    print(f"  - 个性化方法: {'存在' if has_personalized_section and has_answer_question else '缺失'}")
    
except Exception as e:
    print(f"✗ Teacher服务导入失败: {e}")

try:
    from llm.services.exercise_service import exercise_service
    print("✓ Exercise服务导入成功")
    
    # 检查个性化功能
    has_personalized_exercises = hasattr(exercise_service, '_generate_personalized_exercises')
    print(f"  - 个性化方法: {'存在' if has_personalized_exercises else '缺失'}")
    
except Exception as e:
    print(f"✗ Exercise服务导入失败: {e}")

try:
    from llm.services.student_analyzer import student_analyzer
    print("✓ 学生分析器导入成功")
    
    # 检查分析方法
    has_profile = hasattr(student_analyzer, 'get_student_profile')
    has_insights = hasattr(student_analyzer, 'generate_learning_insights')
    print(f"  - 分析方法: {'存在' if has_profile and has_insights else '缺失'}")
    
except Exception as e:
    print(f"✗ 学生分析器导入失败: {e}")

print("\\n=== 导入验证完成 ===")
