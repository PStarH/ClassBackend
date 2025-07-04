"""
Teacher Service - 教师课程服务
"""
import json
from typing import List, Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone

try:
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..core.base_service import LLMBaseService
from ..core.prompts import CREATE_OUTLINE_PROMPT, SECTION_DETAIL_PROMPT
from ..core.models import OutlineSection, SectionDetail
from .student_analyzer import student_analyzer
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes


class TeacherService(LLMBaseService):
    """教师课程服务"""
    
    def create_outline(self, topic: str) -> List[Dict[str, Any]]:
        """
        生成课程大纲
        Args:
            topic: 课程主题
            
        Returns:
            课程大纲的 JSON 数据
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = CREATE_OUTLINE_PROMPT.format(topic=topic)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的大纲结构
                result = [{"index": "1", "title": f"{topic} - 基础概念"}]
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_OUTLINE_PROMPT
            )
            result = self._execute_chain_with_fallback(chain, topic=topic)
        
        return result
    
    def generate_section_detail(self, index: str, title: str) -> Dict[str, Any]:
        """
        生成章节详细内容
        
        Args:
            index: 章节索引
            title: 章节标题
            
        Returns:
            章节详细内容的 JSON 数据
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = SECTION_DETAIL_PROMPT.format(index=index, title=title)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的内容结构
                result = {
                    "index": index,
                    "title": title,
                    "content": f"这是关于{title}的详细内容。",
                    "graphs": {}
                }
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=SECTION_DETAIL_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                index=index,
                title=title
            )
        
        return result
    
    def generate_personalized_section_detail(
        self, 
        index: str, 
        title: str, 
        user_id: str,
        course_progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据学生数据生成个性化章节详细内容
        
        Args:
            index: 章节索引
            title: 章节标题
            user_id: 学生ID
            course_progress_id: 课程进度ID (可选)
            
        Returns:
            个性化章节详细内容的 JSON 数据
        """
        try:
            # 获取学生档案
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 构建个性化提示词
            personalized_prompt = self._build_personalized_prompt(
                index, title, student_profile, learning_insights
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                response = self.simple_chat(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # 降级到标准版本
                    result = self.generate_section_detail(index, title)
                    result['personalization_note'] = "个性化处理失败，使用标准内容"
            else:
                from langchain.prompts import PromptTemplate
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(
                    llm=self.langchain_llm,
                    prompt=personalized_template
                )
                result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
            
            # 添加个性化元数据
            result['personalization_applied'] = True
            result['student_profile_used'] = {
                'learning_style': student_profile['profile']['settings'].get('preferred_style'),
                'pace': student_profile['profile']['settings'].get('preferred_pace'),
                'education_level': student_profile['profile']['settings'].get('education_level'),
            }
            result['adaptation_notes'] = self._generate_adaptation_notes(student_profile, learning_insights)
            
            return result
            
        except Exception as e:
            # 发生错误时降级到标准版本
            result = self.generate_section_detail(index, title)
            result['personalization_error'] = str(e)
            result['personalization_applied'] = False
            return result
    
    def _build_personalized_prompt(
        self, 
        index: str, 
        title: str, 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any]
    ) -> str:
        """构建个性化提示词"""
        
        # 获取学生特征
        settings = student_profile['profile']['settings']
        learning_stats = student_profile['learning_stats']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        
        # 构建学生特征描述
        student_characteristics = []
        
        # 学习风格
        learning_style = settings.get('preferred_style', 'Practical')
        if learning_style == 'Visual':
            student_characteristics.append("偏好视觉学习，需要图表、图像和视觉示例")
        elif learning_style == 'Text':
            student_characteristics.append("偏好文本学习，适合详细的文字说明和理论阐述")
        elif learning_style == 'Practical':
            student_characteristics.append("偏好实践学习，需要实际操作和案例演示")
        
        # 学习节奏
        pace = settings.get('preferred_pace', 'Moderate')
        if pace == 'Very Detailed':
            student_characteristics.append("需要非常详细的解释和循序渐进的教学")
        elif pace == 'Fast':
            student_characteristics.append("学习节奏较快，可以接受较多信息密度")
        elif pace == 'Ultra Fast':
            student_characteristics.append("学习节奏很快，适合简洁高效的内容组织")
        
        # 教育背景
        education_level = settings.get('education_level', 'undergraduate')
        if education_level in ['graduate', 'phd']:
            student_characteristics.append("具有高等教育背景，可以理解复杂概念")
        elif education_level == 'high_school':
            student_characteristics.append("需要更基础的解释和更多的背景知识")
        
        # 学习模式分析
        if 'attention_difficulties' in pattern.get('weaknesses', []):
            student_characteristics.append("注意力容易分散，需要结构化和要点明确的内容")
        
        if 'good_focus' in pattern.get('strengths', []):
            student_characteristics.append("专注度良好，可以处理较长的学习内容")
        
        # 常见问题类型
        frequent_types = question_analysis.get('question_types', {})
        if 'concept' in frequent_types and frequent_types['concept'] > 0:
            student_characteristics.append("经常对概念理解有疑问，需要清晰的概念解释")
        if 'application' in frequent_types and frequent_types['application'] > 0:
            student_characteristics.append("经常对应用实践有疑问，需要更多实际例子")
        
        # 学习建议
        recommendations = learning_insights.get('recommendations', [])
        adaptation_notes = []
        for rec in recommendations:
            if "番茄工作法" in rec:
                adaptation_notes.append("内容应该分段组织，便于分批学习")
            elif "缩短单次学习时长" in rec:
                adaptation_notes.append("内容应该简洁精炼，重点突出")
        
        characteristics_text = "； ".join(student_characteristics)
        adaptation_text = "； ".join(adaptation_notes) if adaptation_notes else "无特殊调整需求"
        
        personalized_prompt = f"""你是一位专业的个性化教学内容生成专家。请为章节"{title}"（索引：{index}）生成详细的教学内容。

学生特征分析：
{characteristics_text}

内容调整建议：
{adaptation_text}

请生成符合该学生特点的章节详细内容，要求：
1. 根据学生的学习风格调整内容呈现方式
2. 根据学习节奏调整内容详细程度
3. 根据教育背景调整语言难度和概念深度
4. 根据常见问题类型重点强化相关内容
5. 考虑学生的注意力特点组织内容结构

返回格式（仅返回JSON，不要包含任何其他文字）：
{{
    "index": "{index}",
    "title": "{title}",
    "content": "详细的教学内容，根据学生特点个性化调整",
    "key_points": ["要点1", "要点2", "要点3"],
    "examples": ["示例1", "示例2"],
    "practice_suggestions": ["练习建议1", "练习建议2"],
    "common_pitfalls": ["常见错误1", "常见错误2"],
    "additional_resources": ["资源1", "资源2"],
    "graphs": {{
        "概念图": "DOT格式的图表定义"
    }},
    "personalization_notes": "个性化调整说明"
}}"""
        
        return personalized_prompt
    
    def _generate_adaptation_notes(
        self, 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any]
    ) -> List[str]:
        """生成适应性调整说明"""
        notes = []
        
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        
        # 基于学习风格的调整
        style = settings.get('preferred_style')
        if style == 'Visual':
            notes.append("增加了视觉元素和图表说明")
        elif style == 'Practical':
            notes.append("强化了实践案例和操作指导")
        elif style == 'Text':
            notes.append("提供了详细的文字解释和理论分析")
        
        # 基于学习困难的调整
        weaknesses = pattern.get('weaknesses', [])
        if 'attention_difficulties' in weaknesses:
            notes.append("采用分段式结构，便于分批学习")
        if 'comprehension' in weaknesses:
            notes.append("简化了语言表达，增加了基础概念解释")
        
        # 基于学习优势的调整
        strengths = pattern.get('strengths', [])
        if 'logical' in strengths:
            notes.append("强化了逻辑推理和系统性思考")
        if 'creative' in strengths:
            notes.append("增加了创新思维和扩展应用")
        
        return notes
    
    def answer_student_question(
        self, 
        question_text: str, 
        user_id: str, 
        context: Optional[str] = None,
        course_progress_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        回答学生问题并记录
        
        Args:
            question_text: 问题内容
            user_id: 学生ID
            context: 问题上下文
            course_progress_id: 相关课程进度ID
            
        Returns:
            回答结果和问题记录信息
        """
        try:
            # 获取学生档案用于个性化回答
            student_profile = student_analyzer.get_student_profile(user_id)
            
            # 构建个性化回答提示词
            answer_prompt = self._build_answer_prompt(question_text, context, student_profile)
            
            # 生成回答
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                response = self.simple_chat(answer_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    answer_data = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    answer_data = {
                        "answer": response,
                        "explanation": "详细解释",
                        "examples": [],
                        "related_concepts": [],
                        "follow_up_suggestions": []
                    }
            else:
                from langchain.prompts import PromptTemplate
                answer_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=answer_template)
                answer_data = self._execute_chain_with_fallback(chain, prompt=answer_prompt)
            
            # 分析问题类型和难度
            question_analysis = self._analyze_question(question_text, student_profile)
            
            # 记录问题到数据库
            question_record = self._record_student_question(
                user_id, question_text, context, answer_data, 
                question_analysis, course_progress_id
            )
            
            # 生成教师观察笔记
            self._generate_teacher_observation(user_id, question_text, question_analysis, course_progress_id)
            
            return {
                'success': True,
                'answer': answer_data,
                'question_record_id': str(question_record.id),
                'question_analysis': question_analysis,
                'personalization_applied': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'answer': {
                    "answer": "抱歉，处理您的问题时出现了错误。请稍后重试或联系教师。",
                    "explanation": "",
                    "examples": [],
                    "related_concepts": [],
                    "follow_up_suggestions": []
                }
            }
    
    def _build_answer_prompt(
        self, 
        question_text: str, 
        context: Optional[str], 
        student_profile: Dict[str, Any]
    ) -> str:
        """构建个性化回答提示词"""
        
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        
        # 获取学生特征
        learning_style = settings.get('preferred_style', 'Practical')
        tone = settings.get('tone', 'friendly')
        education_level = settings.get('education_level', 'undergraduate')
        
        # 构建语调描述
        tone_description = {
            'friendly': '友好亲切',
            'professional': '专业严谨',
            'encouraging': '鼓励支持',
            'casual': '轻松随意',
            'formal': '正式规范'
        }.get(tone, '友好亲切')
        
        # 构建风格描述
        style_description = {
            'Visual': '使用图表、图像等视觉化方式辅助解释',
            'Text': '提供详细的文字说明和理论分析',
            'Practical': '重点提供实际案例和操作指导'
        }.get(learning_style, '结合理论和实践')
        
        context_text = f"\n问题上下文：{context}" if context else ""
        
        prompt = f"""你是一位专业的个性化教学助手。请回答学生的问题，并根据学生特点调整回答方式。

学生问题：{question_text}{context_text}

学生特征：
- 偏好学习风格：{learning_style} ({style_description})
- 偏好语调：{tone} ({tone_description})
- 教育水平：{education_level}
- 注意力持续时间：{pattern.get('attention_span_minutes', 30)}分钟

请根据学生特点提供个性化回答，要求：
1. 语调符合学生偏好
2. 解释方式适合学生的学习风格
3. 内容深度匹配学生的教育背景
4. 如果学生注意力持续时间较短，请简化回答结构

返回格式（仅返回JSON）：
{{
    "answer": "简洁明确的答案",
    "explanation": "详细解释，根据学生特点调整",
    "examples": ["相关例子1", "相关例子2"],
    "related_concepts": ["相关概念1", "相关概念2"],
    "follow_up_suggestions": ["后续学习建议1", "后续学习建议2"],
    "difficulty_level": "basic/intermediate/advanced",
    "estimated_reading_time": "预估阅读时间(分钟)"
}}"""
        
        return prompt
    
    def _analyze_question(self, question_text: str, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """分析问题类型和难度"""
        
        # 简单的关键词分析来确定问题类型
        question_lower = question_text.lower()
        
        question_type = 'general'
        if any(word in question_lower for word in ['什么是', '定义', '概念', '含义']):
            question_type = 'concept'
        elif any(word in question_lower for word in ['怎么做', '如何', '步骤', '方法', '实现']):
            question_type = 'application'
        elif any(word in question_lower for word in ['为什么', '原理', '原因', '机制']):
            question_type = 'theory'
        elif any(word in question_lower for word in ['错误', '报错', '问题', '不工作', '失败']):
            question_type = 'technical'
        
        # 基于问题长度和复杂度估计难度
        difficulty_level = 'basic'
        if len(question_text) > 100 or '复杂' in question_text or '深入' in question_text:
            difficulty_level = 'advanced'
        elif len(question_text) > 50 or any(word in question_lower for word in ['详细', '具体', '进一步']):
            difficulty_level = 'intermediate'
        
        return {
            'question_type': question_type,
            'difficulty_level': difficulty_level,
            'question_length': len(question_text),
            'estimated_complexity': 'high' if len(question_text.split()) > 20 else 'medium' if len(question_text.split()) > 10 else 'low'
        }
    
    def _record_student_question(
        self, 
        user_id: str, 
        question_text: str, 
        context: Optional[str], 
        answer_data: Dict[str, Any],
        question_analysis: Dict[str, Any],
        course_progress_id: Optional[str]
    ) -> StudentQuestion:
        """记录学生问题到数据库"""
        
        from apps.authentication.models import User
        from apps.courses.models import CourseProgress
        
        user = User.objects.get(uuid=user_id)
        course_progress = None
        if course_progress_id:
            try:
                course_progress = CourseProgress.objects.get(course_uuid=course_progress_id)
            except CourseProgress.DoesNotExist:
                pass
        
        # 生成标签
        tags = [question_analysis['question_type'], question_analysis['difficulty_level']]
        if course_progress:
            tags.append(course_progress.subject_name)
        
        question_record = StudentQuestion.objects.create(
            user=user,
            course_progress=course_progress,
            question_text=question_text,
            question_type=question_analysis['question_type'],
            difficulty_level=question_analysis['difficulty_level'],
            context=context or '',
            ai_response=json.dumps(answer_data, ensure_ascii=False),
            is_resolved=True,  # AI已回答，标记为已解决
            tags=tags
        )
        
        return question_record
    
    def _generate_teacher_observation(
        self, 
        user_id: str, 
        question_text: str, 
        question_analysis: Dict[str, Any],
        course_progress_id: Optional[str]
    ):
        """生成教师观察笔记"""
        
        from apps.authentication.models import User
        from apps.courses.models import CourseProgress
        
        try:
            user = User.objects.get(uuid=user_id)
            course_progress = None
            if course_progress_id:
                try:
                    course_progress = CourseProgress.objects.get(course_uuid=course_progress_id)
                except CourseProgress.DoesNotExist:
                    pass
            
            # 分析是否需要创建观察笔记
            recent_questions = StudentQuestion.objects.filter(
                user=user,
                question_type=question_analysis['question_type'],
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # 如果同类型问题较多，生成观察笔记
            if recent_questions >= 3:
                priority = 'high' if recent_questions >= 5 else 'medium'
                
                TeacherNotes.objects.create(
                    user=user,
                    course_progress=course_progress,
                    note_type='difficulty',
                    priority=priority,
                    title=f"频繁{question_analysis['question_type']}类型问题",
                    content=f"学生在最近7天内提出了{recent_questions}个{question_analysis['question_type']}类型的问题，"
                           f"最新问题：{question_text[:100]}{'...' if len(question_text) > 100 else ''}。"
                           f"建议关注该领域的理解情况。",
                    observations={
                        'question_frequency': recent_questions,
                        'question_type': question_analysis['question_type'],
                        'difficulty_level': question_analysis['difficulty_level'],
                        'time_period': '7天'
                    },
                    action_items=[
                        f"加强{question_analysis['question_type']}类型内容的教学",
                        "提供更多相关练习和例子",
                        "考虑调整教学方法"
                    ],
                    tags=['频繁提问', question_analysis['question_type'], '需要关注']
                )
        
        except Exception as e:
            # 记录失败不影响主要功能
            pass
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        from ..core.client import llm_factory
        return llm_factory.is_available()


# 全局服务实例
try:
    teacher_service = TeacherService()
except Exception as e:
    print(f"Warning: Failed to initialize teacher service: {e}")
    teacher_service = None
