"""
Advisor Service - 教育规划顾问服务
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from functools import wraps

try:
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain not available. Using simplified AI service.")

from ..core.base_service import LLMBaseService, cache_llm_response, cache_async_llm_response
from ..core.prompts import CREATE_PLAN_PROMPT, UPDATE_PLAN_PROMPT, CHAT_AGENT_PROMPT
from ..core.models import PlanNode, ChatResponse
from .memory_service import memory_service
from .student_analyzer import student_analyzer
from apps.learning_plans.student_notes_models import StudentQuestion, TeacherNotes


def get_plan_cache_key(*args, **kwargs):
    """生成计划缓存键"""
    import hashlib
    # Skip self parameter if present
    topic = kwargs.get('topic')
    if not topic and args:
        # If args[0] is self (AdvisorService instance), use args[1]
        topic = args[1] if len(args) > 1 and hasattr(args[0], 'create_plan') else args[0]
    topic = str(topic) if topic else 'unknown'
    return f"plan_cache:{hashlib.md5(topic.encode()).hexdigest()}"


def get_chat_cache_key(*args, **kwargs):
    """生成聊天缓存键"""
    import hashlib
    # Skip self parameter if present
    message = kwargs.get('message')
    session_id = kwargs.get('session_id', 'default')
    
    if not message and args:
        # If args[0] is self (AdvisorService instance), adjust indices
        if len(args) > 0 and hasattr(args[0], 'chat_with_agent'):
            message = args[1] if len(args) > 1 else 'unknown'
            session_id = args[3] if len(args) > 3 else 'default'
        else:
            message = args[0] if args else 'unknown'
            session_id = args[2] if len(args) > 2 else 'default'
    
    message = str(message) if message else 'unknown'
    key_data = f"{message}:{session_id}"
    return f"chat_cache:{hashlib.md5(key_data.encode()).hexdigest()}"


class AdvisorService(LLMBaseService):
    """教育规划顾问服务"""
    
    @cache_llm_response(get_plan_cache_key, ttl=7200)  # 2小时缓存
    def create_plan(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        创建学习计划
        
        Args:
            topic: 学习主题
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            学习计划的 JSON 数据
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = CREATE_PLAN_PROMPT.format(topic=topic)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的计划结构
                result = [{"index": 1, "title": f"学习{topic}", "children": []}]
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_PLAN_PROMPT
            )
            result = self._execute_chain_with_fallback(chain, topic=topic)
        
        # 如果提供了会话ID，保存计划状态
        if session_id and memory_service:
            memory_service.save_plan_state(session_id, result)
            memory_service.update_conversation(
                session_id, 
                f"Create a study plan for {topic}", 
                f"Created plan with {len(result)} main sections"
            )
        
        return result
    
    async def create_plan_async(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        异步创建学习计划
        
        Args:
            topic: 学习主题
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            学习计划的 JSON 数据
        """
        # 检查缓存
        cache_key = get_plan_cache_key(topic=topic)
        from django.core.cache import cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用异步简单的OpenAI客户端
            prompt = CREATE_PLAN_PROMPT.format(topic=topic)
            response = await self.simple_chat_async(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的计划结构
                result = [{"index": 1, "title": f"学习{topic}", "children": []}]
        else:
            # 使用异步LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_PLAN_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(chain, topic=topic)
        
        # 缓存结果
        cache.set(cache_key, result, 7200)
        
        # 如果提供了会话ID，异步保存计划状态
        if session_id and memory_service:
            await memory_service.save_plan_state_async(session_id, result)
            await memory_service.update_conversation_async(
                session_id, 
                f"Create a study plan for {topic}", 
                f"Created plan with {len(result)} main sections"
            )
        
        return result
    
    def update_plan(
        self, 
        current_plan: Dict[str, Any], 
        feedback_path: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        根据反馈更新学习计划
        
        Args:
            current_plan: 当前学习计划
            feedback_path: 反馈文件路径
            session_id: 可选的会话ID
            
        Returns:
            更新的计划部分
        """
        # 读取反馈文件
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Cannot read feedback file: {e}")
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = UPDATE_PLAN_PROMPT.format(
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                result = []
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=UPDATE_PLAN_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
        
        # 如果提供了会话ID，更新记忆和计划状态
        if session_id and memory_service:
            memory_service.save_plan_state(session_id, result)
            memory_service.update_conversation(
                session_id,
                f"Update plan based on teacher feedback",
                f"Updated plan with {len(result)} changes"
            )
        
        return result
    
    async def update_plan_async(
        self, 
        current_plan: Dict[str, Any], 
        feedback_path: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        异步根据反馈更新学习计划
        
        Args:
            current_plan: 当前学习计划
            feedback_path: 反馈文件路径
            session_id: 可选的会话ID
            
        Returns:
            更新的计划部分
        """
        # 读取反馈文件（简化为同步读取）
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Cannot read feedback file: {e}")
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用异步简单的OpenAI客户端
            prompt = UPDATE_PLAN_PROMPT.format(
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
            response = await self.simple_chat_async(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                result = []
        else:
            # 使用异步LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=UPDATE_PLAN_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
        
        # 如果提供了会话ID，异步更新记忆和计划状态
        if session_id and memory_service:
            await memory_service.save_plan_state_async(session_id, result)
            await memory_service.update_conversation_async(
                session_id,
                f"Update plan based on teacher feedback",
                f"Updated plan with {len(result)} changes"
            )
        
        return result
    
    def chat_with_agent(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        与教育规划代理聊天
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含回复和计划更新的响应
        """
        # 获取对话上下文（如果有会话ID）
        context = ""
        if session_id and memory_service:
            context = memory_service.get_conversation_context(session_id)
        
        # 创建增强的提示词（包含历史上下文）
        if context:
            enhanced_message = f"Conversation context: {context}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = CHAT_AGENT_PROMPT.format(
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                result = {"reply": response, "updates": []}
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CHAT_AGENT_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
        
        # 处理 markdown 文件更新
        md_updated = False
        md_error = None
        
        # 检查是否需要更新 markdown 文件
        md_update = result.get('md_update')
        if md_update and feedback_path:
            try:
                with open(feedback_path, 'r', encoding='utf-8') as f:
                    md_text = f.read()
                
                # 替换目标段落
                target = md_update.get('target', '')
                new_content = md_update.get('new_content', '')
                updated_text = md_text.replace(target, new_content)
                
                with open(feedback_path, 'w', encoding='utf-8') as f:
                    f.write(updated_text)
                
                md_updated = True
            except Exception as e:
                md_error = str(e)
        
        # 添加 markdown 更新状态
        result['md_updated'] = md_updated
        if md_error:
            result['md_error'] = md_error
        
        # 更新对话记忆和计划状态
        if session_id and memory_service:
            memory_service.update_conversation(
                session_id,
                message,
                result.get('reply', 'No reply provided')
            )
            
            # 如果有计划更新，保存新状态
            if result.get('updates'):
                memory_service.save_plan_state(session_id, result.get('updates'))
            
        return result
    
    async def chat_with_agent_async(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        异步与教育规划代理聊天
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含回复和计划更新的响应
        """
        # 异步获取对话上下文
        context = ""
        if session_id and memory_service:
            context = await memory_service.get_conversation_context_async(session_id)
        
        # 创建增强的提示词（包含历史上下文）
        if context:
            enhanced_message = f"Conversation context: {context}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用异步简单的OpenAI客户端
            prompt = CHAT_AGENT_PROMPT.format(
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
            response = await self.simple_chat_async(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                result = {"reply": response, "updates": []}
        else:
            # 使用异步LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CHAT_AGENT_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
        
        # 异步更新记忆
        if session_id and memory_service:
            await memory_service.update_conversation_async(
                session_id,
                message,
                result.get("reply", "No response")
            )
        
        return result
    
    async def batch_create_plans_async(self, topics: List[str]) -> List[Dict[str, Any]]:
        """批量异步创建学习计划"""
        requests = [
            {
                'chain': LLMChain(llm=self.langchain_llm, prompt=CREATE_PLAN_PROMPT) if self.langchain_llm else None,
                'kwargs': {'topic': topic}
            } if self.langchain_llm else {'prompt': CREATE_PLAN_PROMPT.format(topic=topic)}
            for topic in topics
        ]
        
        results = await self.batch_process_async(requests)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append([{"index": 1, "title": f"学习{topics[i]}", "children": []}])
            else:
                try:
                    if isinstance(result, str):
                        cleaned_result = self._clean_json_content(result)
                        processed_results.append(json.loads(cleaned_result))
                    else:
                        processed_results.append(result)
                except json.JSONDecodeError:
                    processed_results.append([{"index": 1, "title": f"学习{topics[i]}", "children": []}])
        
        return processed_results

    def get_plan_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从会话中获取当前计划"""
        if memory_service:
            return memory_service.get_plan_state(session_id)
        return None
    
    def clear_session(self, session_id: str):
        """清除会话数据"""
        if memory_service:
            memory_service.clear_session(session_id)
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        from ..core.client import llm_factory
        return llm_factory.is_available()

    def create_personalized_plan(
        self, 
        topic: str, 
        user_id: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        根据学生特点创建个性化学习计划
        
        Args:
            topic: 学习主题
            user_id: 学生ID
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            个性化学习计划的 JSON 数据
        """
        try:
            # 获取学生档案和分析结果
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 构建个性化提示词
            personalized_prompt = self._build_personalized_plan_prompt(
                topic, student_profile, learning_insights
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # 使用简单的OpenAI客户端
                response = self.simple_chat(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # 降级到标准版本
                    result = self.create_plan(topic, session_id)
                    result = result if isinstance(result, list) else []
            else:
                # 使用LangChain
                from langchain.prompts import PromptTemplate
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
                
            # 添加个性化元数据
            if isinstance(result, list):
                for section in result:
                    section['personalized'] = True
                    section['adapted_for_style'] = student_profile['profile']['settings'].get('preferred_style')
                    
            # 记录顾问建议（作为教师笔记）
            self._record_advisor_recommendation(user_id, topic, result, student_profile)
            
            # 如果提供了会话ID，保存计划状态
            if session_id and memory_service:
                memory_service.save_plan_state(session_id, result)
                memory_service.update_conversation(
                    session_id, 
                    f"Create personalized study plan for {topic}",
                    f"Created personalized plan with {len(result)} main sections"
                )
            
            return result
            
        except Exception as e:
            # 发生错误时降级到标准版本
            result = self.create_plan(topic, session_id)
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
        异步根据学生特点创建个性化学习计划
        """
        try:
            # 获取学生档案和分析结果
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 构建个性化提示词
            personalized_prompt = self._build_personalized_plan_prompt(
                topic, student_profile, learning_insights
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # 使用异步简单的OpenAI客户端
                response = await self.simple_chat_async(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # 降级到标准版本
                    result = await self.create_plan_async(topic, session_id)
            else:
                # 使用异步LangChain
                from langchain.prompts import PromptTemplate
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = await self._execute_chain_with_fallback_async(chain, prompt=personalized_prompt)
            
            # 添加个性化元数据
            if isinstance(result, list):
                for section in result:
                    section['personalized'] = True
                    section['adapted_for_style'] = student_profile['profile']['settings'].get('preferred_style')
                    
            # 记录顾问建议
            self._record_advisor_recommendation(user_id, topic, result, student_profile)
            
            # 如果提供了会话ID，异步保存计划状态
            if session_id and memory_service:
                await memory_service.save_plan_state_async(session_id, result)
                await memory_service.update_conversation_async(
                    session_id, 
                    f"Create personalized study plan for {topic}",
                    f"Created personalized plan with {len(result)} main sections"
                )
            
            return result
            
        except Exception as e:
            # 发生错误时降级到标准版本
            result = await self.create_plan_async(topic, session_id)
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
        与个性化教育规划代理聊天，基于学生特点提供建议
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            user_id: 学生ID
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含个性化回复和计划更新的响应
        """
        try:
            # 获取学生档案和分析结果
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 获取对话上下文
            context = ""
            if session_id and memory_service:
                context = memory_service.get_conversation_context(session_id)
            
            # 构建个性化聊天提示词
            personalized_prompt = self._build_personalized_chat_prompt(
                message, current_plan, student_profile, learning_insights, context
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # 使用简单的OpenAI客户端
                response = self.simple_chat(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    result = {"reply": response, "updates": []}
            else:
                # 使用LangChain
                from langchain.prompts import PromptTemplate
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = self._execute_chain_with_fallback(chain, prompt=personalized_prompt)
            
            # 分析对话内容，记录重要观察
            self._analyze_and_record_conversation(user_id, message, result, student_profile)
            
            # 处理 markdown 文件更新
            md_updated = False
            md_error = None
            
            # 检查是否需要更新 markdown 文件
            md_update = result.get('md_update')
            if md_update and feedback_path:
                try:
                    with open(feedback_path, 'r', encoding='utf-8') as f:
                        md_text = f.read()
                    
                    # 替换目标段落
                    target = md_update.get('target', '')
                    new_content = md_update.get('new_content', '')
                    updated_text = md_text.replace(target, new_content)
                    
                    with open(feedback_path, 'w', encoding='utf-8') as f:
                        f.write(updated_text)
                    
                    md_updated = True
                except Exception as e:
                    md_error = str(e)
            
            # 添加个性化元数据
            result['personalized'] = True
            result['student_adaptations'] = self._generate_adaptation_summary(student_profile)
            result['md_updated'] = md_updated
            if md_error:
                result['md_error'] = md_error
            
            # 更新对话记忆和计划状态
            if session_id and memory_service:
                memory_service.update_conversation(
                    session_id,
                    message,
                    result.get('reply', 'No reply provided')
                )
                
                # 如果有计划更新，保存新状态
                if result.get('updates'):
                    memory_service.save_plan_state(session_id, result.get('updates'))
            
            return result
            
        except Exception as e:
            # 降级到标准聊天
            result = self.chat_with_agent(message, current_plan, session_id, feedback_path)
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
        异步与个性化教育规划代理聊天
        """
        try:
            # 获取学生档案和分析结果
            student_profile = student_analyzer.get_student_profile(user_id)
            learning_insights = student_analyzer.generate_learning_insights(user_id)
            
            # 异步获取对话上下文
            context = ""
            if session_id and memory_service:
                context = await memory_service.get_conversation_context_async(session_id)
            
            # 构建个性化聊天提示词
            personalized_prompt = self._build_personalized_chat_prompt(
                message, current_plan, student_profile, learning_insights, context
            )
            
            if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
                # 使用异步简单的OpenAI客户端
                response = await self.simple_chat_async(personalized_prompt)
                try:
                    cleaned_response = self._clean_json_content(response)
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    result = {"reply": response, "updates": []}
            else:
                # 使用异步LangChain
                from langchain.prompts import PromptTemplate
                personalized_template = PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                )
                chain = LLMChain(llm=self.langchain_llm, prompt=personalized_template)
                result = await self._execute_chain_with_fallback_async(chain, prompt=personalized_prompt)
            
            # 分析对话内容，记录重要观察
            self._analyze_and_record_conversation(user_id, message, result, student_profile)
            
            # 添加个性化元数据
            result['personalized'] = True
            result['student_adaptations'] = self._generate_adaptation_summary(student_profile)
            
            # 异步更新记忆
            if session_id and memory_service:
                await memory_service.update_conversation_async(
                    session_id,
                    message,
                    result.get("reply", "No response")
                )
                
                # 如果有计划更新，保存新状态
                if result.get('updates'):
                    await memory_service.save_plan_state_async(session_id, result.get('updates'))
            
            return result
            
        except Exception as e:
            # 降级到标准聊天
            result = await self.chat_with_agent_async(message, current_plan, session_id, feedback_path)
            result['personalization_error'] = str(e)
            result['personalization_applied'] = False
            return result
    
    def _build_personalized_plan_prompt(
        self, 
        topic: str, 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any]
    ) -> str:
        """构建个性化学习计划提示词"""
        
        # 基础信息
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        
        # 获取学生特征
        learning_style = settings.get('preferred_style', 'Practical')
        pace = settings.get('preferred_pace', 'normal')
        education_level = settings.get('education_level', 'undergraduate')
        attention_span = pattern.get('attention_span_minutes', 30)
        
        # 构建个性化要求
        personalization_requirements = []
        
        # 学习风格适应
        if learning_style == 'Visual':
            personalization_requirements.append("安排更多图表分析、数据可视化和思维导图相关的学习内容")
        elif learning_style == 'Practical':
            personalization_requirements.append("侧重实践操作、案例分析和项目式学习")
        elif learning_style == 'Text':
            personalization_requirements.append("安排详细的理论学习、文献阅读和概念分析")
        
        # 学习节奏适应
        if pace == 'slow':
            personalization_requirements.append("延长每个阶段的学习时间，增加复习和巩固环节")
        elif pace == 'fast':
            personalization_requirements.append("加快学习进度，增加挑战性内容和扩展阅读")
        
        # 注意力适应
        if attention_span < 20:
            personalization_requirements.append("将学习内容分解为短小的学习模块，每个模块不超过15分钟")
        elif attention_span > 60:
            personalization_requirements.append("可以安排长时间的深度学习会话和复杂项目")
        
        # 学习困难适应
        weaknesses = pattern.get('weaknesses', [])
        if 'comprehension' in weaknesses:
            personalization_requirements.append("提供更多基础概念解释和循序渐进的学习路径")
        if 'attention_difficulties' in weaknesses:
            personalization_requirements.append("使用结构化的学习计划，明确的学习目标和里程碑")
        
        # 学习优势发挥
        strengths = pattern.get('strengths', [])
        if 'logical' in strengths:
            personalization_requirements.append("安排逻辑推理和系统性思考的学习活动")
        if 'creative' in strengths:
            personalization_requirements.append("包含创新思维训练和开放性探索项目")
        
        # 问题类型偏好
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
        """记录顾问建议到数据库（作为教师笔记）"""
        
        from apps.authentication.models import User
        
        try:
            user = User.objects.get(uuid=user_id)
            
            # 生成建议摘要
            plan_summary = f"为主题'{topic}'制定了{len(plan_result)}个学习阶段的个性化计划"
            
            # 分析学生特征对计划的影响
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
            
            # 创建教师笔记记录
            TeacherNotes.objects.create(
                user=user,
                course_progress=None,  # 学习计划不一定关联特定课程
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
            # 记录失败不影响主要功能
            pass
    
    def _build_personalized_chat_prompt(
        self, 
        message: str, 
        current_plan: Dict[str, Any], 
        student_profile: Dict[str, Any], 
        learning_insights: Dict[str, Any],
        context: str = ""
    ) -> str:
        """构建个性化聊天提示词"""
        
        # 获取学生特征
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        question_analysis = student_profile['question_analysis']
        recent_performance = student_profile.get('recent_performance', {})
        
        # 学生特征摘要
        learning_style = settings.get('preferred_style', 'Practical')
        pace = settings.get('preferred_pace', 'normal')
        education_level = settings.get('education_level', 'undergraduate')
        tone = settings.get('tone', 'friendly')
        
        # 学习模式特征
        strengths = pattern.get('strengths', [])
        weaknesses = pattern.get('weaknesses', [])
        attention_span = pattern.get('attention_span_minutes', 30)
        
        # 最近表现
        weekly_summary = recent_performance.get('weekly_summary', {})
        avg_effectiveness = weekly_summary.get('avg_effectiveness', 0)
        consistency_score = weekly_summary.get('consistency_score', 0)
        
        # 构建上下文增强消息
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
        """分析对话内容并记录重要观察"""
        
        from apps.authentication.models import User
        
        try:
            user = User.objects.get(uuid=user_id)
            
            # 分析消息类型和内容
            message_analysis = self._analyze_student_message(message, student_profile)
            
            # 如果发现重要模式或需要关注的内容，记录笔记
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
            # 记录失败不影响主要功能
            pass

    def _analyze_student_message(
        self, 
        message: str, 
        student_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析学生消息，判断是否需要特别关注"""
        
        analysis = {
            'needs_attention': False,
            'message_type': 'general',
            'concern': '',
            'observation': '',
            'priority': 'low',
            'suggested_actions': []
        }
        
        message_lower = message.lower()
        
        # 检测困难和挫折表达
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
        """生成个性化适应摘要"""
        
        settings = student_profile['profile']['settings']
        pattern = student_profile['learning_pattern']
        
        adaptations = {
            'style_adaptation': '',
            'pace_adaptation': '',
            'attention_adaptation': '',
            'strength_utilization': [],
            'weakness_support': []
        }
        
        # 学习风格适应
        learning_style = settings.get('preferred_style')
        if learning_style == 'Visual':
            adaptations['style_adaptation'] = '提供了图表和视觉化内容建议'
        elif learning_style == 'Practical':
            adaptations['style_adaptation'] = '强调了实践操作和应用案例'
        elif learning_style == 'Text':
            adaptations['style_adaptation'] = '提供了详细的理论解释和文字说明'
        
        # 节奏适应
        pace = settings.get('preferred_pace')
        if pace == 'slow':
            adaptations['pace_adaptation'] = '建议延长学习时间，增加复习环节'
        elif pace == 'fast':
            adaptations['pace_adaptation'] = '建议加快进度，增加挑战内容'
        else:
            adaptations['pace_adaptation'] = '保持标准学习节奏'
        
        # 注意力适应
        attention_span = pattern.get('attention_span_minutes', 30)
        if attention_span < 20:
            adaptations['attention_adaptation'] = '建议短时间学习会话，频繁休息'
        elif attention_span > 60:
            adaptations['attention_adaptation'] = '支持长时间深度学习'
        else:
            adaptations['attention_adaptation'] = '标准时长学习会话'
        
        # 优势利用
        strengths = pattern.get('strengths', [])
        for strength in strengths:
            if strength == 'logical':
                adaptations['strength_utilization'].append('利用逻辑思维优势进行系统性学习')
            elif strength == 'creative':
                adaptations['strength_utilization'].append('发挥创造力进行探索性学习')
            elif strength == 'analytical':
                adaptations['strength_utilization'].append('运用分析能力深入理解概念')
        
        # 弱项支持
        weaknesses = pattern.get('weaknesses', [])
        for weakness in weaknesses:
            if weakness == 'comprehension':
                adaptations['weakness_support'].append('提供额外的概念解释和基础支持')
            elif weakness == 'attention_difficulties':
                adaptations['weakness_support'].append('使用结构化方法提高专注度')
            elif weakness == 'time_management':
                adaptations['weakness_support'].append('提供时间管理建议和计划支持')
        
        return adaptations

# Service instances will be created on demand
def get_advisor_service():
    """获取顾问服务实例 - 延迟初始化"""
    if not hasattr(get_advisor_service, '_instance'):
        get_advisor_service._instance = AdvisorService()
    return get_advisor_service._instance

# 向后兼容的全局变量
advisor_service = None

def _initialize_service():
    """按需初始化服务"""
    global advisor_service
    if advisor_service is None:
        try:
            advisor_service = get_advisor_service()
        except Exception as e:
            print(f"Warning: Failed to initialize advisor service: {e}")
            advisor_service = None
    return advisor_service
