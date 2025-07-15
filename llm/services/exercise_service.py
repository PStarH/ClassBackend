"""
Exercise Service - 练习题生成服务
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

try:
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..core.base_service import LLMBaseService
from ..core.prompts import EXERCISE_PROMPT
from ..core.models import ExerciseResponse
from .student_analyzer import student_analyzer
from apps.courses.models import CourseProgress
from apps.learning_plans.models import StudySession
from apps.authentication.models import User


class ExerciseService(LLMBaseService):
    """练习题生成服务"""
    
    def generate_exercises(
        self, 
        user_id: str,
        course_progress_id: str = None,
        study_session_id: str = None,
        num_questions: int = None
    ) -> Dict[str, Any]:
        """
        根据用户学习情况生成个性化练习题
        
        Args:
            user_id: 用户ID
            course_progress_id: 课程进度ID (可选)
            study_session_id: 学习会话ID (可选)
            num_questions: 题目数量 (可选，会根据学习情况自动调整)
            
        Returns:
            包含练习题的 JSON 数据
        """
        try:
            # 获取学生档案进行个性化调整
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 获取用户学习数据
            user_data = self._get_user_learning_data(user_id, course_progress_id, study_session_id)
            
            # 基于学生档案调整用户数据
            user_data = self._personalize_user_data(user_data, student_profile, learning_insights)
            
            # 自动调整题目数量
            if num_questions is None:
                num_questions = self._calculate_personalized_question_count(user_data, student_profile)
            
            # 生成个性化练习题
            exercises = self._generate_personalized_exercises(user_data, num_questions, student_profile)
            
            return {
                'success': True,
                'exercises': exercises,
                'metadata': {
                    'user_id': user_id,
                    'course_progress_id': course_progress_id,
                    'study_session_id': study_session_id,
                    'num_questions': num_questions,
                    'difficulty_level': user_data.get('difficulty_level', 'medium'),
                    'proficiency_level': user_data.get('proficiency_level', 0),
                    'personalization_applied': True,
                    'learning_style': student_profile['profile']['settings'].get('preferred_style', 'Practical'),
                    'generated_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'exercises': []
            }
    
    def _personalize_user_data(
        self, 
        user_data: Dict[str, Any], 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """基于学生档案个性化调整用户数据"""
        
        # 获取学生特征
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        
        # 根据学习风格调整练习重点
        learning_style = settings.get('preferred_style', 'Practical')
        if learning_style == 'Visual':
            user_data['exercise_focus'] = 'visual_interpretation'
        elif learning_style == 'Practical':
            user_data['exercise_focus'] = 'application_practice'
        elif learning_style == 'Text':
            user_data['exercise_focus'] = 'concept_understanding'
        
        # 根据常见问题类型调整练习内容
        frequent_question_types = question_analysis.get('question_types', {})
        if 'concept' in frequent_question_types and frequent_question_types['concept'] > 2:
            user_data['needs_concept_reinforcement'] = True
        if 'application' in frequent_question_types and frequent_question_types['application'] > 2:
            user_data['needs_application_practice'] = True
        
        # 根据注意力持续时间调整题目复杂度
        attention_span = pattern.get('attention_span_minutes', 30)
        if attention_span < 20:
            user_data['prefer_short_questions'] = True
        elif attention_span > 60:
            user_data['can_handle_complex_questions'] = True
        
        # 根据学习困难调整难度
        weaknesses = pattern.get('weaknesses', [])
        if 'comprehension' in weaknesses:
            user_data['needs_simplified_language'] = True
        if 'attention_difficulties' in weaknesses:
            user_data['needs_structured_questions'] = True
        
        return user_data
    
    def _calculate_personalized_question_count(
        self, 
        user_data: Dict[str, Any], 
        student_profile: Dict[str, Any]
    ) -> int:
        """根据学生特征计算个性化题目数量"""
        
        # 基础计算
        base_count = self._calculate_question_count(user_data)
        
        # 根据注意力持续时间调整
        attention_span = student_profile['learning_pattern'].get('attention_span_minutes', 30)
        if attention_span < 20:
            base_count = max(3, base_count - 2)  # 减少题目数量
        elif attention_span > 60:
            base_count = min(12, base_count + 2)  # 增加题目数量
        
        # 根据学习效果调整
        recent_performance = student_profile.get('recent_performance', {})
        weekly_summary = recent_performance.get('weekly_summary', {})
        
        if weekly_summary.get('avg_effectiveness', 0) >= 4:
            base_count += 1  # 学习效果好，可以增加题目
        elif weekly_summary.get('avg_effectiveness', 0) <= 2:
            base_count = max(3, base_count - 1)  # 学习效果不佳，减少题目
        
        return base_count
    
    def _generate_personalized_exercises(
        self, 
        user_data: Dict[str, Any], 
        num_questions: int, 
        student_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成个性化练习题"""
        
        # 构建个性化提示词
        personalized_prompt = self._build_personalized_exercise_prompt(
            user_data, num_questions, student_profile
        )
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            response = self.simple_chat(personalized_prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
                if isinstance(result, dict) and 'exercises' in result:
                    exercises = result['exercises']
                elif isinstance(result, list):
                    exercises = result
                else:
                    exercises = self._generate_fallback_exercises(user_data, num_questions)
            except json.JSONDecodeError:
                exercises = self._generate_fallback_exercises(user_data, num_questions)
        else:
            # 使用LangChain
            from langchain.prompts import PromptTemplate
            personalized_template = PromptTemplate(
                input_variables=["prompt"],
                template="{prompt}"
            )
            chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
            result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
            
            if isinstance(result, dict) and 'exercises' in result:
                exercises = result['exercises']
            elif isinstance(result, list):
                exercises = result
            else:
                exercises = self._generate_fallback_exercises(user_data, num_questions)
        
        # 验证和标准化练习题格式
        validated_exercises = self.validate_exercise_format(exercises)
        
        # 添加个性化标记
        for exercise in validated_exercises:
            exercise['personalized'] = True
            exercise['adapted_for_style'] = student_profile['profile']['settings'].get('preferred_style', 'Practical')
        
        return validated_exercises
    
    def _build_personalized_exercise_prompt(
        self, 
        user_data: Dict[str, Any], 
        num_questions: int, 
        student_profile: Dict[str, Any]
    ) -> str:
        """构建个性化练习题生成提示词"""
        
        # 基础信息
        content_covered = "; ".join(user_data.get('content_covered', []))[:500]
        if not content_covered:
            content_covered = f"{user_data.get('subject_name', '通用')}的基础知识"
        
        difficulty_level = self._get_difficulty_description(user_data.get('difficulty', 5))
        proficiency_desc = self._get_proficiency_description(user_data.get('proficiency_level', 0))
        
        # 个性化调整信息
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        
        learning_style = settings.get('preferred_style', 'Practical')
        education_level = settings.get('education_level', 'undergraduate')
        tone = settings.get('tone', 'friendly')
        
        # 构建个性化要求
        personalization_requirements = []
        
        # 学习风格适应
        if learning_style == 'Visual':
            personalization_requirements.append("题目应该包含图表描述、数据分析等视觉化元素")
        elif learning_style == 'Practical':
            personalization_requirements.append("题目应该侧重实际应用场景和操作步骤")
        elif learning_style == 'Text':
            personalization_requirements.append("题目应该侧重概念理解和理论分析")
        
        # 教育水平适应
        if education_level in ['graduate', 'phd']:
            personalization_requirements.append("可以使用更专业的术语和复杂的概念")
        elif education_level == 'high_school':
            personalization_requirements.append("使用简单易懂的语言，避免过于专业的术语")
        
        # 注意力适应
        attention_span = pattern.get('attention_span_minutes', 30)
        if attention_span < 20:
            personalization_requirements.append("题目表述要简洁明了，避免冗长的描述")
        elif attention_span > 60:
            personalization_requirements.append("可以设计稍微复杂的情境题，包含更多细节")
        
        # 学习困难适应
        weaknesses = pattern.get('weaknesses', [])
        if 'comprehension' in weaknesses:
            personalization_requirements.append("语言要简单清晰，提供额外的解释说明")
        if 'attention_difficulties' in weaknesses:
            personalization_requirements.append("题目结构要清晰，重点信息要突出")
        
        # 特殊需求
        if user_data.get('needs_concept_reinforcement'):
            personalization_requirements.append("增加概念理解类题目的比重")
        if user_data.get('needs_application_practice'):
            personalization_requirements.append("增加应用实践类题目的比重")
        
        requirements_text = "；".join(personalization_requirements)
        
        prompt = f"""你是一位专业的个性化练习题生成专家。请根据学生的学习情况和个人特点生成定制化的练习题。

学生学习情况：
- 学科：{user_data.get('subject_name', '通用')}
- 已学内容：{content_covered}
- 难度等级：{difficulty_level}
- 熟练程度：{proficiency_desc}
- 每周学习时长：{user_data.get('learning_hour_week', 0)}小时

学生个人特点：
- 学习风格：{learning_style}
- 教育水平：{education_level}
- 偏好语调：{tone}
- 注意力持续时间：{attention_span}分钟

个性化要求：
{requirements_text}

请生成 {num_questions} 道个性化练习题，要求：
1. 题目必须基于已学内容，不能出现学生未学过的知识点
2. 难度要与学生的熟练程度和课程难度相匹配
3. 题目风格要符合学生的学习偏好和特点
4. 题目类型主要为选择题，每题4个选项（A、B、C、D）
5. 提供正确答案和个性化的详细解析
6. 解析要符合学生的理解水平和语言偏好

返回格式要求（仅返回JSON，不要包含任何其他文字或格式）：
{{
    "exercises": [
        {{
            "id": "q_1",
            "question": "个性化的题目内容",
            "type": "multiple_choice",
            "options": [
                {{"id": "A", "text": "选项A"}},
                {{"id": "B", "text": "选项B"}},
                {{"id": "C", "text": "选项C"}},
                {{"id": "D", "text": "选项D"}}
            ],
            "correct_answer": "A",
            "explanation": "根据学生特点定制的详细解析",
            "difficulty": 1-10,
            "points": 10,
            "personalization_notes": "说明本题的个性化调整"
        }}
    ]
}}"""
        
        return prompt
    
    def _get_user_learning_data(
        self, 
        user_id: str, 
        course_progress_id: str = None,
        study_session_id: str = None
    ) -> Dict[str, Any]:
        """获取用户学习数据"""
        try:
            user = User.objects.get(uuid=user_id)
            data = {
                'user_email': user.email,
                'proficiency_level': 0,
                'difficulty': 5,
                'subject_name': '通用',
                'content_covered': [],
                'learning_hour_week': 0,
                'learning_hour_total': 0,
                'feedback': {},
                'recent_sessions': []
            }
            
            # 获取课程进度数据
            if course_progress_id:
                try:
                    course_progress = CourseProgress.objects.get(course_uuid=course_progress_id)
                    data.update({
                        'proficiency_level': course_progress.proficiency_level,
                        'difficulty': course_progress.difficulty,
                        'subject_name': course_progress.subject_name,
                        'learning_hour_week': course_progress.learning_hour_week,
                        'learning_hour_total': course_progress.learning_hour_total,
                        'feedback': course_progress.feedback,
                        'user_experience': course_progress.user_experience
                    })
                except CourseProgress.DoesNotExist:
                    pass
            
            # 获取学习会话数据
            if study_session_id:
                try:
                    study_session = StudySession.objects.get(id=study_session_id)
                    data['content_covered'].append(study_session.content_covered)
                    data['session_duration'] = study_session.duration_minutes
                    data['effectiveness_rating'] = study_session.effectiveness_rating
                except StudySession.DoesNotExist:
                    pass
            
            # 获取最近的学习会话
            recent_sessions = StudySession.objects.filter(
                user=user
            ).order_by('-start_time')[:5]
            
            for session in recent_sessions:
                if session.content_covered:
                    data['content_covered'].append(session.content_covered)
                data['recent_sessions'].append({
                    'content': session.content_covered,
                    'duration': session.duration_minutes,
                    'effectiveness': session.effectiveness_rating,
                    'date': session.start_time.isoformat() if session.start_time else None
                })
            
            return data
            
        except User.DoesNotExist:
            raise ValueError(f"User with ID {user_id} not found")
    
    def _calculate_question_count(self, user_data: Dict[str, Any]) -> int:
        """根据学习情况自动计算题目数量"""
        base_count = 5  # 基础题目数量
        
        # 根据学习时长调整
        learning_hour_week = user_data.get('learning_hour_week', 0)
        if learning_hour_week > 10:
            base_count += 3  # 学习积极性高，增加题目
        elif learning_hour_week > 5:
            base_count += 1
        elif learning_hour_week < 2:
            base_count -= 1  # 学习时间少，减少题目
        
        # 根据熟练度调整
        proficiency_level = user_data.get('proficiency_level', 0)
        if proficiency_level > 75:
            base_count += 2  # 熟练度高，增加题目
        elif proficiency_level < 25:
            base_count -= 1  # 熟练度低，减少题目
        
        # 根据难度调整
        difficulty = user_data.get('difficulty', 5)
        if difficulty > 7:
            base_count -= 1  # 难度高，减少题目
        elif difficulty < 3:
            base_count += 1  # 难度低，增加题目
        
        # 确保题目数量在合理范围内
        return max(3, min(base_count, 10))
    
    def _generate_exercises_with_ai(self, user_data: Dict[str, Any], num_questions: int) -> List[Dict[str, Any]]:
        """使用AI生成练习题"""
        # 准备提示词参数
        content_covered = "; ".join(user_data.get('content_covered', []))[:500]  # 限制长度
        if not content_covered:
            content_covered = f"{user_data.get('subject_name', '通用')}的基础知识"
        
        difficulty_level = self._get_difficulty_description(user_data.get('difficulty', 5))
        proficiency_desc = self._get_proficiency_description(user_data.get('proficiency_level', 0))
        
        # 构建提示词
        prompt_params = {
            'subject_name': user_data.get('subject_name', '通用'),
            'content_covered': content_covered,
            'difficulty_level': difficulty_level,
            'proficiency_level': proficiency_desc,
            'num_questions': num_questions,
            'learning_hour_week': user_data.get('learning_hour_week', 0),
            'feedback': json.dumps(user_data.get('feedback', {}), ensure_ascii=False)
        }
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = EXERCISE_PROMPT.format(**prompt_params)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
                if isinstance(result, dict) and 'exercises' in result:
                    return result['exercises']
                elif isinstance(result, list):
                    return result
                else:
                    return self._generate_fallback_exercises(user_data, num_questions)
            except json.JSONDecodeError:
                return self._generate_fallback_exercises(user_data, num_questions)
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=EXERCISE_PROMPT
            )
            result = self._execute_chain_with_fallback(chain, **prompt_params)
            if isinstance(result, dict) and 'exercises' in result:
                return result['exercises']
            elif isinstance(result, list):
                return result
            else:
                return self._generate_fallback_exercises(user_data, num_questions)
    
    def _get_difficulty_description(self, difficulty: int) -> str:
        """获取难度描述"""
        if difficulty <= 2:
            return "极易"
        elif difficulty <= 4:
            return "简单"
        elif difficulty <= 6:
            return "中等"
        elif difficulty <= 8:
            return "困难"
        else:
            return "极难"
    
    def _get_proficiency_description(self, proficiency: int) -> str:
        """获取熟练度描述"""
        if proficiency <= 20:
            return "初学者"
        elif proficiency <= 40:
            return "基础"
        elif proficiency <= 60:
            return "中级"
        elif proficiency <= 80:
            return "高级"
        else:
            return "专家"
    
    def _generate_fallback_exercises(self, user_data: Dict[str, Any], num_questions: int) -> List[Dict[str, Any]]:
        """生成后备练习题"""
        subject = user_data.get('subject_name', '通用')
        exercises = []
        
        for i in range(num_questions):
            exercise = {
                "id": f"q_{i+1}",
                "question": f"关于{subject}的问题 {i+1}：请选择正确答案",
                "type": "multiple_choice",
                "options": [
                    {"id": "A", "text": "选项A"},
                    {"id": "B", "text": "选项B"},
                    {"id": "C", "text": "选项C"},
                    {"id": "D", "text": "选项D"}
                ],
                "correct_answer": "A",
                "explanation": "这是一个示例题目，请联系系统管理员更新AI服务配置。",
                "difficulty": user_data.get('difficulty', 5),
                "points": 10
            }
            exercises.append(exercise)
        
        return exercises
    
    def validate_exercise_format(self, exercises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """验证和标准化练习题格式"""
        validated_exercises = []
        
        for i, exercise in enumerate(exercises):
            validated_exercise = {
                "id": exercise.get("id", f"q_{i+1}"),
                "question": exercise.get("question", f"问题 {i+1}"),
                "type": exercise.get("type", "multiple_choice"),
                "options": exercise.get("options", []),
                "correct_answer": exercise.get("correct_answer", "A"),
                "explanation": exercise.get("explanation", ""),
                "difficulty": exercise.get("difficulty", 5),
                "points": exercise.get("points", 10)
            }
            
            # 验证选择题格式
            if validated_exercise["type"] == "multiple_choice":
                if not validated_exercise["options"]:
                    validated_exercise["options"] = [
                        {"id": "A", "text": "选项A"},
                        {"id": "B", "text": "选项B"},
                        {"id": "C", "text": "选项C"},
                        {"id": "D", "text": "选项D"}
                    ]
            
            validated_exercises.append(validated_exercise)
        
        return validated_exercises


# 创建全局服务实例
# Service instances will be created on demand
def get_exercise_service():
    """获取练习服务实例 - 延迟初始化"""
    global _exercise_service_instance
    if not hasattr(get_exercise_service, '_instance'):
        get_exercise_service._instance = ExerciseService()
    return get_exercise_service._instance

# 向后兼容的全局变量
exercise_service = None

def _initialize_service():
    """按需初始化服务"""
    global exercise_service
    if exercise_service is None:
        exercise_service = get_exercise_service()
    return exercise_service
