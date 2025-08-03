"""
Enhanced Humanized AI Teacher Service - 人性化 AI 教师服务
提供个性化、情感化的教学体验
"""
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone

try:
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferWindowMemory
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..core.base_service import LLMBaseService
from .student_analyzer import student_analyzer
from apps.authentication.models import User
from apps.learning_plans.models import StudySession


class HumanizedTeacherService(LLMBaseService):
    """人性化AI教师服务"""
    
    def __init__(self):
        super().__init__()
        self.personality_traits = {
            'supportive': ['encouraging', 'patient', 'understanding'],
            'enthusiastic': ['energetic', 'passionate', 'motivating'],
            'wise': ['knowledgeable', 'insightful', 'thoughtful'],
            'friendly': ['warm', 'approachable', 'caring']
        }
        
        self.emotional_responses = {
            'frustrated': {
                'opening': [
                    "I can see you're finding this challenging - that's completely normal! 😊",
                    "Hey, take a deep breath! Every expert was once a beginner. 💪",
                    "I understand this can be tough. Let's break it down together! 🤝"
                ],
                'encouragement': [
                    "You're doing better than you think!",
                    "Every mistake is a step closer to mastery.",
                    "I believe in your ability to figure this out!"
                ]
            },
            'excited': {
                'opening': [
                    "I love your enthusiasm! 🚀 Let's channel that energy!",
                    "Your excitement is contagious! 🌟 Let's dive deeper!",
                    "Amazing energy! 🔥 You're going to love what comes next!"
                ],
                'reinforcement': [
                    "Keep that momentum going!",
                    "Your passion for learning shows!",
                    "This is exactly the right attitude!"
                ]
            },
            'confused': {
                'opening': [
                    "Great question! Let me explain this differently. 🤔",
                    "I can clarify that for you! Sometimes these concepts take time. 💡",
                    "No worries! Let's approach this from another angle. 🎯"
                ],
                'clarification': [
                    "Think of it this way...",
                    "A simple analogy might help...",
                    "Let me show you with an example..."
                ]
            },
            'confident': {
                'opening': [
                    "You're absolutely on the right track! 💪",
                    "Excellent thinking! 🎯 You've got this!",
                    "Your understanding is solid! 🌟 Let's build on it!"
                ],
                'advancement': [
                    "Ready for the next challenge?",
                    "Let's take this to the next level!",
                    "Time for something more advanced!"
                ]
            }
        }
        
        self.learning_style_adaptations = {
            'visual': {
                'approach': 'diagrams, charts, and visual examples',
                'language': 'picture this', 'imagine', 'visualize', 'see'
            },
            'auditory': {
                'approach': 'verbal explanations and discussions',
                'language': 'listen to this', 'sounds like', 'tell me about'
            },
            'kinesthetic': {
                'approach': 'hands-on practice and real examples',
                'language': 'try this', 'hands-on', 'practice', 'do'
            },
            'reading': {
                'approach': 'detailed written explanations',
                'language': 'read through this', 'note that', 'observe'
            }
        }

    async def generate_personalized_response(
        self, 
        user_id: str, 
        question: str, 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """生成个性化的教师回应"""
        
        try:
            # 获取用户档案
            user_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 分析用户情绪状态
            emotional_state = self._analyze_user_emotion(question, context)
            
            # 获取学习风格
            learning_style = user_profile['profile']['settings'].get('preferred_style', 'practical')
            
            # 检查学习历史和困难点
            difficulty_areas = self._identify_difficulty_areas(user_id, question)
            
            # 构建个性化提示词
            personalized_prompt = self._build_personalized_teaching_prompt(
                question=question,
                user_profile=user_profile,
                emotional_state=emotional_state,
                learning_style=learning_style,
                difficulty_areas=difficulty_areas,
                context=context
            )
            
            # 生成AI回应
            ai_response = await self._generate_ai_response(personalized_prompt)
            
            # 添加人性化元素
            humanized_response = self._add_personality_elements(
                response=ai_response,
                emotional_state=emotional_state,
                learning_style=learning_style,
                user_profile=user_profile
            )
            
            # 生成后续建议
            next_steps = self._generate_next_steps(question, user_profile, difficulty_areas)
            
            # 记录交互
            await self._log_interaction(user_id, question, humanized_response)
            
            return {
                'success': True,
                'response': humanized_response,
                'emotional_tone': emotional_state,
                'learning_style_adapted': learning_style,
                'next_steps': next_steps,
                'personalization_applied': True,
                'teaching_strategy': self._get_teaching_strategy(emotional_state, learning_style),
                'encouragement_level': self._calculate_encouragement_need(user_profile, emotional_state)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'fallback_response': self._generate_fallback_response(question)
            }

    def _analyze_user_emotion(self, question: str, context: Optional[Dict] = None) -> str:
        """分析用户情绪状态"""
        
        # 关键词情绪检测
        frustrated_keywords = ['difficult', 'hard', 'confused', 'stuck', 'help', 'don\'t understand', 'error']
        excited_keywords = ['awesome', 'great', 'love', 'excited', 'amazing', 'cool', 'wow']
        confident_keywords = ['got it', 'understand', 'easy', 'clear', 'make sense', 'ready']
        confused_keywords = ['what', 'how', 'why', 'explain', 'clarify', 'mean']
        
        question_lower = question.lower()
        
        # 检查上下文中的情绪指示
        if context and 'recent_performance' in context:
            recent_perf = context['recent_performance']
            if recent_perf.get('success_rate', 0) < 0.3:
                return 'frustrated'
            elif recent_perf.get('success_rate', 0) > 0.8:
                return 'confident'
        
        # 基于关键词分析
        if any(keyword in question_lower for keyword in frustrated_keywords):
            return 'frustrated'
        elif any(keyword in question_lower for keyword in excited_keywords):
            return 'excited'
        elif any(keyword in question_lower for keyword in confident_keywords):
            return 'confident'
        elif any(keyword in question_lower for keyword in confused_keywords):
            return 'confused'
        
        return 'neutral'

    def _identify_difficulty_areas(self, user_id: str, question: str) -> List[str]:
        """识别用户的学习困难领域"""
        
        try:
            # 获取最近的学习会话
            recent_sessions = StudySession.objects.filter(
                user__uuid=user_id
            ).order_by('-start_time')[:10]
            
            difficulty_areas = []
            
            # 分析会话内容寻找模式
            for session in recent_sessions:
                if session.effectiveness_rating and session.effectiveness_rating < 3:
                    if session.content_covered:
                        # 简单的关键词提取
                        content = session.content_covered.lower()
                        if 'loop' in content or 'iteration' in content:
                            difficulty_areas.append('loops')
                        if 'function' in content or 'method' in content:
                            difficulty_areas.append('functions')
                        if 'class' in content or 'object' in content:
                            difficulty_areas.append('oop')
                        if 'variable' in content or 'assignment' in content:
                            difficulty_areas.append('variables')
            
            # 去重
            return list(set(difficulty_areas))
            
        except Exception:
            return []

    def _build_personalized_teaching_prompt(
        self, 
        question: str, 
        user_profile: Dict,
        emotional_state: str,
        learning_style: str,
        difficulty_areas: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """构建个性化教学提示词"""
        
        # 获取用户设置
        settings = user_profile['profile']['settings']
        user_name = settings.get('name', 'Student')
        education_level = settings.get('education_level', 'undergraduate')
        tone_preference = settings.get('tone', 'friendly')
        
        # 获取学习模式
        pattern = user_profile['learning_pattern']
        attention_span = pattern.get('attention_span_minutes', 30)
        weaknesses = pattern.get('weaknesses', [])
        
        # 构建情绪适应指导
        emotional_guidance = self._get_emotional_guidance(emotional_state)
        
        # 构建学习风格适应
        style_adaptation = self.learning_style_adaptations.get(learning_style.lower(), {})
        
        # 构建困难领域支持
        difficulty_support = ""
        if difficulty_areas:
            difficulty_support = f"Note: {user_name} has previously struggled with {', '.join(difficulty_areas)}. Provide extra support in these areas."
        
        prompt = f"""You are an empathetic, highly skilled AI teacher named 'Alex'. You're having a conversation with {user_name}, a {education_level} student.

STUDENT CONTEXT:
- Name: {user_name}
- Education Level: {education_level}
- Learning Style: {learning_style}
- Preferred Tone: {tone_preference}
- Attention Span: {attention_span} minutes
- Current Emotional State: {emotional_state}
- Learning Difficulties: {weaknesses}
{difficulty_support}

EMOTIONAL ADAPTATION:
{emotional_guidance}

LEARNING STYLE ADAPTATION:
Teaching approach: Focus on {style_adaptation.get('approach', 'clear explanations')}
Use language like: {', '.join(style_adaptation.get('language', ['explain', 'show']))}

TEACHING GUIDELINES:
1. Always start with appropriate emotional support based on their state
2. Adapt your explanation complexity to their education level
3. Use their preferred learning style approach
4. Keep explanations focused (they have {attention_span} min attention span)
5. Be encouraging and supportive, especially if they're struggling
6. Provide practical examples and next steps
7. Use emojis appropriately to maintain engagement
8. If they seem frustrated, break concepts into smaller pieces
9. If they're confident, challenge them appropriately

STUDENT'S QUESTION: "{question}"

Respond as Alex the AI teacher, providing a helpful, personalized, and emotionally appropriate response. Be warm, encouraging, and adapt your teaching style to help them succeed."""

        return prompt

    def _get_emotional_guidance(self, emotional_state: str) -> str:
        """获取情绪适应指导"""
        
        guidance_map = {
            'frustrated': """
- Start with validation and encouragement
- Break down complex concepts into smaller steps
- Use patience and reassurance
- Offer alternative explanations if they don't understand
- Remind them that struggling is part of learning
""",
            'excited': """
- Match their energy and enthusiasm
- Build on their excitement with engaging content
- Challenge them appropriately to maintain engagement
- Use their motivation to introduce more advanced concepts
""",
            'confused': """
- Provide clear, step-by-step explanations
- Use analogies and examples they can relate to
- Check for understanding before moving forward
- Offer multiple ways to understand the same concept
""",
            'confident': """
- Acknowledge their competence
- Provide appropriately challenging material
- Encourage them to help others or take on projects
- Build on their confidence to explore advanced topics
""",
            'neutral': """
- Maintain engaging and clear communication
- Assess their understanding as you go
- Adapt based on their responses
- Provide encouragement to keep them motivated
"""
        }
        
        return guidance_map.get(emotional_state, guidance_map['neutral'])

    async def _generate_ai_response(self, prompt: str) -> str:
        """生成AI回应"""
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            return self.simple_chat(prompt)
        else:
            # 使用LangChain与记忆功能
            from langchain.prompts import PromptTemplate
            
            template = PromptTemplate(
                input_variables=["prompt"],
                template="{prompt}"
            )
            
            chain = LLMChain(llm=self.langchain_llm, prompt=template)
            return self._execute_chain_with_fallback(chain, prompt=prompt)

    def _add_personality_elements(
        self, 
        response: str, 
        emotional_state: str, 
        learning_style: str,
        user_profile: Dict
    ) -> str:
        """添加个性化元素到回应中"""
        
        # 获取适当的开场白
        if emotional_state in self.emotional_responses:
            emotional_responses = self.emotional_responses[emotional_state]
            if 'opening' in emotional_responses and not any(opener.split()[0].lower() in response.lower() for opener in emotional_responses['opening']):
                # 如果回应没有包含情绪适应的开场，添加一个
                opening = random.choice(emotional_responses['opening'])
                response = f"{opening}\n\n{response}"
        
        # 根据学习风格调整语言
        style_language = self.learning_style_adaptations.get(learning_style.lower(), {}).get('language', [])
        
        # 添加个性化结尾
        settings = user_profile['profile']['settings']
        name = settings.get('name', 'there')
        
        encouraging_endings = [
            f"You've got this, {name}! 💪",
            f"Keep up the great work, {name}! 🌟",
            f"I'm here to help whenever you need, {name}! 🤝",
            f"Happy coding, {name}! 🚀"
        ]
        
        if emotional_state == 'frustrated':
            encouraging_endings = [
                f"Take it one step at a time, {name}. You're doing great! 😊",
                f"Remember, every expert was once a beginner, {name}! 💪",
                f"I believe in you, {name}! Let's tackle this together! 🤝"
            ]
        
        # 随机添加鼓励结尾（30%概率）
        if random.random() < 0.3:
            response += f"\n\n{random.choice(encouraging_endings)}"
        
        return response

    def _generate_next_steps(self, question: str, user_profile: Dict, difficulty_areas: List[str]) -> List[str]:
        """生成后续学习建议"""
        
        next_steps = []
        
        # 基于困难领域的建议
        if 'loops' in difficulty_areas:
            next_steps.append("Practice more loop exercises to strengthen your understanding")
        if 'functions' in difficulty_areas:
            next_steps.append("Try creating simple functions with different parameters")
        if 'oop' in difficulty_areas:
            next_steps.append("Work through object-oriented programming examples step by step")
        
        # 基于学习模式的建议
        pattern = user_profile['learning_pattern']
        if pattern.get('attention_span_minutes', 30) < 20:
            next_steps.append("Take short 10-15 minute study sessions for better retention")
        
        # 通用建议
        general_suggestions = [
            "Try explaining the concept to someone else (rubber duck debugging)",
            "Practice with similar problems to reinforce your understanding",
            "Create a simple project that uses what you've learned",
            "Review the fundamentals if you're still feeling uncertain"
        ]
        
        # 添加1-2个通用建议
        next_steps.extend(random.sample(general_suggestions, min(2, len(general_suggestions))))
        
        return next_steps[:4]  # 限制为最多4个建议

    def _get_teaching_strategy(self, emotional_state: str, learning_style: str) -> str:
        """获取教学策略描述"""
        
        strategy_map = {
            ('frustrated', 'visual'): "Breaking down concepts with diagrams and step-by-step visual guides",
            ('frustrated', 'auditory'): "Providing clear verbal explanations with patience and encouragement",
            ('frustrated', 'kinesthetic'): "Offering hands-on practice with simple, achievable tasks",
            ('excited', 'visual'): "Using engaging diagrams and visual challenges",
            ('excited', 'auditory'): "Interactive discussions and verbal problem-solving",
            ('excited', 'kinesthetic'): "Hands-on projects and practical applications",
            ('confident', 'visual'): "Advanced visual concepts and complex diagrams",
            ('confident', 'auditory'): "In-depth discussions and advanced explanations",
            ('confident', 'kinesthetic'): "Challenging projects and real-world applications"
        }
        
        return strategy_map.get((emotional_state, learning_style.lower()), 
                              "Adaptive teaching based on student needs")

    def _calculate_encouragement_need(self, user_profile: Dict, emotional_state: str) -> str:
        """计算鼓励需求等级"""
        
        recent_performance = user_profile.get('recent_performance', {})
        avg_effectiveness = recent_performance.get('weekly_summary', {}).get('avg_effectiveness', 3)
        
        if emotional_state == 'frustrated' or avg_effectiveness < 2.5:
            return "high"
        elif emotional_state == 'confident' and avg_effectiveness > 4:
            return "low"
        else:
            return "medium"

    async def _log_interaction(self, user_id: str, question: str, response: str):
        """记录交互日志"""
        
        try:
            # 这里可以添加数据库记录逻辑
            # 记录用户问题、AI回应、时间戳等
            pass
        except Exception:
            # 记录失败不应影响主要功能
            pass

    def _generate_fallback_response(self, question: str) -> str:
        """生成后备回应"""
        
        return f"""I understand you're asking about: "{question}"

While I'm experiencing some technical difficulties, I want to help you! Here are some general tips:

1. Break down complex problems into smaller parts
2. Look for patterns and examples in documentation
3. Practice with simple cases first
4. Don't hesitate to ask for help when needed

I'm here to support your learning journey! 🌟 Please try asking your question again, and I'll do my best to provide a helpful response."""


# 创建全局服务实例
def get_humanized_teacher_service():
    """获取人性化教师服务实例"""
    global _humanized_teacher_instance
    if not hasattr(get_humanized_teacher_service, '_instance'):
        get_humanized_teacher_service._instance = HumanizedTeacherService()
    return get_humanized_teacher_service._instance


# 向后兼容
humanized_teacher = None

def _initialize_humanized_teacher():
    """初始化人性化教师服务"""
    global humanized_teacher
    if humanized_teacher is None:
        humanized_teacher = get_humanized_teacher_service()
    return humanized_teacher