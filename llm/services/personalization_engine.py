"""
Personalization Engine - Specialized service for handling user personalization
"""
import json
from typing import List, Dict, Any, Optional

try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..core.base_service import LLMBaseService
from .memory_service import memory_service
from .student_analyzer import student_analyzer
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes


class PersonalizationEngine(LLMBaseService):
    """Specialized service for handling user personalization and adaptation"""
    
    def create_personalized_plan(
        self, 
        topic: str, 
        user_id: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Create personalized learning plan based on student characteristics
        
        Args:
            topic: Learning topic
            user_id: Student ID
            session_id: Optional session ID for memory management
            
        Returns:
            Personalized learning plan JSON data
        """
        try:
            # Get student profile and analysis results
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # Build personalized prompt
            personalized_prompt = self._build_personalized_plan_prompt(
                topic, student_profile, learning_insights
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # Use simple OpenAI client
                response = self.simple_chat(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # Fallback to standard version
                    from .learning_plan_creator import LearningPlanCreator
                    creator = LearningPlanCreator()
                    result = creator.create_plan(topic, session_id)
                    result = result if isinstance(result, list) else []
            else:
                # Use LangChain
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
                
            # Add personalization metadata
            if isinstance(result, list):
                for section in result:
                    section['personalized'] = True
                    section['adapted_for_style'] = student_profile['profile']['settings'].get('preferred_style')
                    
            # Record advisor recommendation (as teacher notes)
            self._record_advisor_recommendation(user_id, topic, result, student_profile)
            
            # If session_id provided, save plan state
            if session_id and memory_service:
                memory_service.save_plan_state(session_id, result)
                memory_service.update_conversation(
                    session_id, 
                    f"Create personalized study plan for {topic}",
                    f"Created personalized plan with {len(result)} main sections"
                )
            
            return result
            
        except Exception as e:
            # Fallback to standard version on error
            from .learning_plan_creator import LearningPlanCreator
            creator = LearningPlanCreator()
            result = creator.create_plan(topic, session_id)
            if isinstance(result, list):
                for section in result:
                    section['personalization_error'] = str(e)
                    section['personalization_applied'] = False
            return result

    async def create_personalized_plan_async(
        self, 
        topic: str, 
        user_id: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously create personalized learning plan based on student characteristics
        """
        try:
            # Get student profile and analysis results
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # Build personalized prompt
            personalized_prompt = self._build_personalized_plan_prompt(
                topic, student_profile, learning_insights
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # Use async simple OpenAI client
                response = await self.simple_chat_async(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # Fallback to standard version
                    from .learning_plan_creator import LearningPlanCreator
                    creator = LearningPlanCreator()
                    result = await creator.create_plan_async(topic, session_id)
            else:
                # Use async LangChain
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = await self._execute_chain_with_fallback_async(chain, prompt=personalized_prompt)
            
            # Add personalization metadata
            if isinstance(result, list):
                for section in result:
                    section['personalized'] = True
                    section['adapted_for_style'] = student_profile['profile']['settings'].get('preferred_style')
                    
            # Record advisor recommendation
            self._record_advisor_recommendation(user_id, topic, result, student_profile)
            
            # If session_id provided, async save plan state
            if session_id and memory_service:
                await memory_service.save_plan_state_async(session_id, result)
                await memory_service.update_conversation_async(
                    session_id, 
                    f"Create personalized study plan for {topic}",
                    f"Created personalized plan with {len(result)} main sections"
                )
            
            return result
            
        except Exception as e:
            # Fallback to standard version on error
            from .learning_plan_creator import LearningPlanCreator
            creator = LearningPlanCreator()
            result = await creator.create_plan_async(topic, session_id)
            if isinstance(result, list):
                for section in result:
                    section['personalization_error'] = str(e)
                    section['personalization_applied'] = False
            return result
    
    def chat_with_personalized_agent(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        user_id: str,
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        Chat with personalized educational planning agent based on student characteristics
        
        Args:
            message: User message
            current_plan: Current learning plan
            user_id: Student ID
            session_id: Optional session ID for memory management
            feedback_path: Optional feedback file path
            
        Returns:
            Response containing personalized reply and plan updates
        """
        try:
            # Get student profile and analysis results
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # Get conversation context
            context = ""
            if session_id and memory_service:
                context = memory_service.get_conversation_context(session_id)
            
            # Build personalized chat prompt
            personalized_prompt = self._build_personalized_chat_prompt(
                message, current_plan, student_profile, learning_insights, context
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # Use simple OpenAI client
                response = self.simple_chat(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    result = {"reply": response, "updates": []}
            else:
                # Use LangChain
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
            
            # Analyze conversation content, record important observations
            self._analyze_and_record_conversation(user_id, message, result, student_profile)
            
            # Handle markdown file updates
            md_updated = False
            md_error = None
            
            # Check if markdown file needs updating
            md_update = result.get('md_update')
            if md_update and feedback_path:
                try:
                    with open(feedback_path, 'r', encoding='utf-8') as f:
                        md_text = f.read()
                    
                    # Replace target paragraph
                    target = md_update.get('target', '')
                    new_content = md_update.get('new_content', '')
                    updated_text = md_text.replace(target, new_content)
                    
                    with open(feedback_path, 'w', encoding='utf-8') as f:
                        f.write(updated_text)
                    
                    md_updated = True
                except Exception as e:
                    md_error = str(e)
            
            # Add personalization metadata
            result['personalized'] = True
            result['student_adaptations'] = self._generate_adaptation_summary(student_profile)
            result['md_updated'] = md_updated
            if md_error:
                result['md_error'] = md_error
            
            # Update conversation memory and plan state
            if session_id and memory_service:
                memory_service.update_conversation(
                    session_id,
                    message,
                    result.get('reply', 'No reply provided')
                )
                
                # If there are plan updates, save new state
                if result.get('updates'):
                    memory_service.save_plan_state(session_id, result.get('updates'))
            
            return result
            
        except Exception as e:
            # Fallback to standard chat
            from .conversation_manager import ConversationManager
            chat_manager = ConversationManager()
            result = chat_manager.chat_with_agent(message, current_plan, session_id, feedback_path)
            result['personalization_error'] = str(e)
            result['personalization_applied'] = False
            return result

    async def chat_with_personalized_agent_async(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        user_id: str,
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        Asynchronously chat with personalized educational planning agent
        """
        try:
            # Get student profile and analysis results
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # Asynchronously get conversation context
            context = ""
            if session_id and memory_service:
                context = await memory_service.get_conversation_context_async(session_id)
            
            # Build personalized chat prompt
            personalized_prompt = self._build_personalized_chat_prompt(
                message, current_plan, student_profile, learning_insights, context
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # Use async simple OpenAI client
                response = await self.simple_chat_async(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    result = {"reply": response, "updates": []}
            else:
                # Use async LangChain
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = await self._execute_chain_with_fallback_async(chain, prompt=personalized_prompt)
            
            # Analyze conversation content, record important observations
            self._analyze_and_record_conversation(user_id, message, result, student_profile)
            
            # Add personalization metadata
            result['personalized'] = True
            result['student_adaptations'] = self._generate_adaptation_summary(student_profile)
            
            # Async update memory
            if session_id and memory_service:
                await memory_service.update_conversation_async(
                    session_id,
                    message,
                    result.get("reply", "No response")
                )
                
                # If there are plan updates, save new state
                if result.get('updates'):
                    await memory_service.save_plan_state_async(session_id, result.get('updates'))
            
            return result
            
        except Exception as e:
            # Fallback to standard chat
            from .conversation_manager import ConversationManager
            chat_manager = ConversationManager()
            result = await chat_manager.chat_with_agent_async(message, current_plan, session_id, feedback_path)
            result['personalization_error'] = str(e)
            result['personalization_applied'] = False
            return result
    
    def _build_personalized_plan_prompt(
        self, 
        topic: str, 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any]
    ) -> str:
        """Build personalized learning plan prompt"""
        
        # Basic information
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        
        # Get student characteristics
        learning_style = settings.get('preferred_style', 'Practical')
        pace = settings.get('preferred_pace', 'normal')
        education_level = settings.get('education_level', 'undergraduate')
        attention_span = pattern.get('attention_span_minutes', 30)
        
        # Build personalization requirements
        personalization_requirements = []
        
        # Learning style adaptation
        if learning_style == 'Visual':
            personalization_requirements.append("安排更多图表分析、数据可视化和思维导图相关的学习内容")
        elif learning_style == 'Practical':
            personalization_requirements.append("侧重实践操作、案例分析和项目式学习")
        elif learning_style == 'Text':
            personalization_requirements.append("安排详细的理论学习、文献阅读和概念分析")
        
        # Learning pace adaptation
        if pace == 'slow':
            personalization_requirements.append("延长每个阶段的学习时间，增加复习和巩固环节")
        elif pace == 'fast':
            personalization_requirements.append("加快学习进度，增加挑战性内容和扩展阅读")
        
        # Attention adaptation
        if attention_span < 20:
            personalization_requirements.append("将学习内容分解为短小的学习模块，每个模块不超过15分钟")
        elif attention_span > 60:
            personalization_requirements.append("可以安排长时间的深度学习会话和复杂项目")
        
        # Learning difficulty adaptation
        weaknesses = pattern.get('weaknesses', [])
        if 'comprehension' in weaknesses:
            personalization_requirements.append("提供更多基础概念解释和循序渐进的学习路径")
        if 'attention_difficulties' in weaknesses:
            personalization_requirements.append("使用结构化的学习计划，明确的学习目标和里程碑")
        
        # Learning strengths utilization
        strengths = pattern.get('strengths', [])
        if 'logical' in strengths:
            personalization_requirements.append("安排逻辑推理和系统性思考的学习活动")
        if 'creative' in strengths:
            personalization_requirements.append("包含创新思维训练和开放性探索项目")
        
        # Question type preferences
        frequent_question_types = question_analysis.get('question_types', {})
        if 'concept' in frequent_question_types and frequent_question_types['concept'] > 2:
            personalization_requirements.append("加强概念理解和理论学习的比重")
        if 'application' in frequent_question_types and frequent_question_types['application'] > 2:
            personalization_requirements.append("增加实际应用和实践练习的内容")
        
        requirements_text = "；".join(personalization_requirements)
        
        prompt = f"""你是一位专业的个性化教育规划顾问。请根据学生的学习特点和需求制定定制化的学习计划。

学习主题：{topic}

学生特征分析：
- 学习风格：{learning_style}
- 学习节奏偏好：{pace}
- 教育水平：{education_level}
- 注意力持续时间：{attention_span}分钟
- 学习优势：{', '.join(strengths) if strengths else '待发现'}
- 需要改进的方面：{', '.join(weaknesses) if weaknesses else '暂无'}

个性化要求：
{requirements_text}

基于以上学生特征，请制定一个适合该学生的个性化学习计划，要求：

1. 学习内容要符合学生的学习风格和节奏偏好
2. 学习活动要适合学生的注意力持续时间
3. 要充分发挥学生的学习优势
4. 要针对性地改善学生的薄弱环节
5. 计划要具体可执行，包含明确的时间安排和学习目标

请返回JSON格式的学习计划，格式如下：
[
  {{
    "index": 1,
    "title": "计划标题",
    "description": "详细描述",
    "duration": "预估时间",
    "learning_objectives": ["目标1", "目标2"],
    "activities": ["活动1", "活动2"],
    "personalization_notes": "个性化调整说明",
    "children": [
      {{
        "index": 1.1,
        "title": "子项目标题",
        "description": "子项目描述",
        "duration": "时间",
        "activities": ["具体活动"]
      }}
    ]
  }}
]"""
        
        return prompt

    def _record_advisor_recommendation(
        self, 
        user_id: str, 
        topic: str, 
        plan_result: List[Dict[str, Any]], 
        student_profile: Dict[str, Any]
    ):
        """Record advisor recommendation to database (as teacher notes)"""
        
        from apps.authentication.models import User
        
        try:
            user = User.objects.get(uuid=user_id)
            
            # Generate recommendation summary
            plan_summary = f"为主题'{topic}'制定了{len(plan_result)}个学习阶段的个性化计划"
            
            # Analyze student characteristics impact on plan
            settings = student_profile['profile']['settings']
            pattern = student_profile['learning_pattern']
            
            adaptations = []
            learning_style = settings.get('preferred_style')
            if learning_style == 'Visual':
                adaptations.append("增加了视觉化学习内容")
            elif learning_style == 'Practical':
                adaptations.append("强化了实践操作环节")
            elif learning_style == 'Text':
                adaptations.append("安排了深度理论学习")
            
            pace = settings.get('preferred_pace')
            if pace == 'slow':
                adaptations.append("延长了学习周期，增加复习环节")
            elif pace == 'fast':
                adaptations.append("加快了学习进度，增加挑战内容")
            
            # Create teacher notes record
            TeacherNotes.objects.create(
                user=user,
                course_progress=None,  # Learning plan not necessarily associated with specific course
                note_type='recommendation',
                priority='medium',
                title=f"学习规划建议 - {topic}",
                content=f"{plan_summary}。个性化调整：{'; '.join(adaptations)}。",
                observations={
                    'topic': topic,
                    'plan_sections': len(plan_result),
                    'learning_style': learning_style,
                    'preferred_pace': pace,
                    'adaptations_made': adaptations
                },
                action_items=[
                    "按照个性化计划执行学习",
                    "定期检查学习进度",
                    "根据学习效果调整计划"
                ],
                tags=['学习规划', '个性化建议', topic, '顾问推荐']
            )
            
        except Exception as e:
            # Recording failure does not affect main functionality
            pass
    
    def _build_personalized_chat_prompt(
        self, 
        message: str, 
        current_plan: Dict[str, Any], 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any],
        context: str = ""
    ) -> str:
        """Build personalized chat prompt"""
        
        # Get student characteristics
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        recent_performance = student_profile.get('recent_performance', {})
        
        # Student characteristics summary
        learning_style = settings.get('preferred_style', 'Practical')
        pace = settings.get('preferred_pace', 'normal')
        education_level = settings.get('education_level', 'undergraduate')
        tone = settings.get('tone', 'friendly')
        
        # Learning pattern characteristics
        strengths = pattern.get('strengths', [])
        weaknesses = pattern.get('weaknesses', [])
        attention_span = pattern.get('attention_span_minutes', 30)
        
        # Recent performance
        weekly_summary = recent_performance.get('weekly_summary', {})
        avg_effectiveness = weekly_summary.get('avg_effectiveness', 0)
        consistency_score = weekly_summary.get('consistency_score', 0)
        
        # Build context-enhanced message
        enhanced_message = message
        if context:
            enhanced_message = f"对话历史：{context}\n\n当前消息：{message}"
        
        prompt = f"""你是一位专业的个性化教育规划顾问。请根据学生的特点和学习情况，提供个性化的建议和回复。

学生特征档案：
- 学习风格：{learning_style}
- 学习节奏偏好：{pace} 
- 教育水平：{education_level}
- 沟通语调偏好：{tone}
- 注意力持续时间：{attention_span}分钟
- 学习优势：{', '.join(strengths) if strengths else '待发现'}
- 需要改进的方面：{', '.join(weaknesses) if weaknesses else '暂无'}

学习表现分析：
- 最近学习效果评分：{avg_effectiveness}/5
- 学习一致性评分：{consistency_score}
- 问题解决率：{question_analysis.get('resolved_rate', 0)}%
- 常见问题类型：{', '.join(question_analysis.get('question_types', {}).keys())}

当前学习计划：
{json.dumps(current_plan, ensure_ascii=False, indent=2)}

学生消息：
{enhanced_message}

请根据学生的特征和学习情况，提供个性化的回复，要求：

1. 回复语调要符合学生的偏好（{tone}）
2. 建议要适合学生的学习风格（{learning_style}）和节奏（{pace}）
3. 要针对学生的优势和薄弱环节提供具体建议
4. 如果需要调整学习计划，要考虑学生的注意力特点和表现情况
5. 要鼓励学生发挥优势，同时帮助改善薄弱环节

返回JSON格式：
{{
  "reply": "个性化回复内容",
  "recommendations": ["建议1", "建议2"],
  "plan_adjustments": "计划调整建议",
  "motivation_note": "个性化激励信息",
  "updates": [计划更新部分（如有）],
  "student_insights": "对学生学习状态的观察"
}}"""
        
        return prompt

    def _analyze_and_record_conversation(
        self, 
        user_id: str, 
        message: str, 
        response: Dict[str, Any], 
        student_profile: Dict[str, Any]
    ):
        """Analyze conversation content and record important observations"""
        
        from apps.authentication.models import User
        
        try:
            user = User.objects.get(uuid=user_id)
            
            # Analyze message type and content
            message_analysis = self._analyze_student_message(message, student_profile)
            
            # If important patterns or content needing attention are discovered, record notes
            if message_analysis['needs_attention']:
                
                TeacherNotes.objects.create(
                    user=user,
                    course_progress=None,
                    note_type='interaction',
                    priority=message_analysis['priority'],
                    title=f"学习咨询对话 - {message_analysis['message_type']}",
                    content=f"学生咨询：{message[:100]}{'...' if len(message) > 100 else ''}。"
                           f"AI回复要点：{response.get('reply', '')[:100]}{'...' if len(response.get('reply', '')) > 100 else ''}。"
                           f"观察：{message_analysis['observation']}",
                    observations={
                        'message_type': message_analysis['message_type'],
                        'student_concern': message_analysis['concern'],
                        'advisor_response': response.get('reply', '')[:200],
                        'recommendations_given': response.get('recommendations', []),
                        'student_insights': response.get('student_insights', '')
                    },
                    action_items=message_analysis['suggested_actions'],
                    tags=['学习咨询', '顾问对话', message_analysis['message_type']]
                )
                
        except Exception as e:
            # Recording failure does not affect main functionality
            pass

    def _analyze_student_message(
        self, 
        message: str, 
        student_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze student message, determine if special attention is needed"""
        
        analysis = {
            'needs_attention': False,
            'message_type': 'general',
            'concern': '',
            'observation': '',
            'priority': 'low',
            'suggested_actions': []
        }
        
        message_lower = message.lower()
        
        # Detect difficulty and frustration expressions
        difficulty_keywords = ['困难', '难懂', '不明白', '听不懂', '跟不上', '太难', '很难']
        frustration_keywords = ['放弃', '不想学', '没兴趣', '没时间', '压力大', '焦虑']
        progress_keywords = ['进度', '慢', '快', '跟不上', '落后']
        motivation_keywords = ['动力', '目标', '方向', '迷茫', '不知道']
        
        if any(keyword in message_lower for keyword in difficulty_keywords):
            analysis.update({
                'needs_attention': True,
                'message_type': 'difficulty',
                'concern': '学习困难',
                'observation': '学生表达了学习困难，需要额外支持',
                'priority': 'high',
                'suggested_actions': ['提供简化的学习资源', '调整学习计划难度', '安排额外辅导']
            })
        elif any(keyword in message_lower for keyword in frustration_keywords):
            analysis.update({
                'needs_attention': True,
                'message_type': 'frustration',
                'concern': '学习挫折',
                'observation': '学生表现出学习挫折感，需要心理支持和动机激励',
                'priority': 'high',
                'suggested_actions': ['提供鼓励和支持', '重新评估学习目标', '调整学习方法']
            })
        elif any(keyword in message_lower for keyword in progress_keywords):
            analysis.update({
                'needs_attention': True,
                'message_type': 'progress_concern',
                'concern': '进度担忧',
                'observation': '学生对学习进度有担忧',
                'priority': 'medium',
                'suggested_actions': ['评估当前进度', '调整学习计划', '提供进度反馈']
            })
        elif any(keyword in message_lower for keyword in motivation_keywords):
            analysis.update({
                'needs_attention': True,
                'message_type': 'motivation',
                'concern': '动机问题',
                'observation': '学生在学习动机或方向上需要指导',
                'priority': 'medium',
                'suggested_actions': ['明确学习目标', '提供动机激励', '制定短期成就']
            })
        
        return analysis

    def _generate_adaptation_summary(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalization adaptation summary"""
        
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        
        adaptations = {
            'style_adaptation': '',
            'pace_adaptation': '',
            'attention_adaptation': '',
            'strength_utilization': [],
            'weakness_support': []
        }
        
        # Learning style adaptation
        learning_style = settings.get('preferred_style')
        if learning_style == 'Visual':
            adaptations['style_adaptation'] = '提供了图表和视觉化内容建议'
        elif learning_style == 'Practical':
            adaptations['style_adaptation'] = '强调了实践操作和应用案例'
        elif learning_style == 'Text':
            adaptations['style_adaptation'] = '提供了详细的理论解释和文字说明'
        
        # Pace adaptation
        pace = settings.get('preferred_pace')
        if pace == 'slow':
            adaptations['pace_adaptation'] = '建议延长学习时间，增加复习环节'
        elif pace == 'fast':
            adaptations['pace_adaptation'] = '建议加快进度，增加挑战内容'
        else:
            adaptations['pace_adaptation'] = '保持标准学习节奏'
        
        # Attention adaptation
        attention_span = pattern.get('attention_span_minutes', 30)
        if attention_span < 20:
            adaptations['attention_adaptation'] = '建议短时间学习会话，频繁休息'
        elif attention_span > 60:
            adaptations['attention_adaptation'] = '支持长时间深度学习'
        else:
            adaptations['attention_adaptation'] = '标准时长学习会话'
        
        # Strength utilization
        strengths = pattern.get('strengths', [])
        for strength in strengths:
            if strength == 'logical':
                adaptations['strength_utilization'].append('利用逻辑思维优势进行系统性学习')
            elif strength == 'creative':
                adaptations['strength_utilization'].append('发挥创造力进行探索性学习')
            elif strength == 'analytical':
                adaptations['strength_utilization'].append('运用分析能力深入理解概念')
        
        # Weakness support
        weaknesses = pattern.get('weaknesses', [])
        for weakness in weaknesses:
            if weakness == 'comprehension':
                adaptations['weakness_support'].append('提供额外的概念解释和基础支持')
            elif weakness == 'attention_difficulties':
                adaptations['weakness_support'].append('使用结构化方法提高专注度')
            elif weakness == 'time_management':
                adaptations['weakness_support'].append('提供时间管理建议和计划支持')
        
        return adaptations