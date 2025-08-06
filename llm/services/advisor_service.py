"""
Advisor Service - 教育规划顾问服务 (Refactored Coordinator)
"""
import json
import asyncio
from typing import List, Dict, Any, Optional

from ..core.base_service import LLMBaseService
from ..core.models import PlanNode, ChatResponse
from .memory_service import memory_service
from .learning_plan_creator import LearningPlanCreator, get_plan_cache_key
from .conversation_manager import ConversationManager, get_chat_cache_key
from .personalization_engine import PersonalizationEngine
from .error_handler import handle_ai_service_errors, handle_async_ai_service_errors




class AdvisorService(LLMBaseService):
    """教育规划顾问服务 - 重构后的协调器""" 
    
    def __init__(self, 
                 plan_creator: Optional[LearningPlanCreator] = None,
                 conversation_manager: Optional[ConversationManager] = None,
                 personalization_engine: Optional[PersonalizationEngine] = None):
        """Initialize AdvisorService with dependency injection"""
        super().__init__()
        
        # Use dependency injection with defaults
        self._plan_creator = plan_creator or LearningPlanCreator()
        self._conversation_manager = conversation_manager or ConversationManager()
        self._personalization_engine = personalization_engine or PersonalizationEngine()
    
    @property
    def plan_creator(self) -> LearningPlanCreator:
        """Get the learning plan creator instance"""
        return self._plan_creator
    
    @property
    def conversation_manager(self) -> ConversationManager:
        """Get the conversation manager instance"""
        return self._conversation_manager
    
    @property
    def personalization_engine(self) -> PersonalizationEngine:
        """Get the personalization engine instance"""
        return self._personalization_engine
    
    # === LEARNING PLAN CREATION METHODS (Delegated) ===
    
    @handle_ai_service_errors(fallback_result=[{"index": 1, "title": "学习计划创建失败", "children": []}])
    def create_plan(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        创建学习计划 (委托给 LearningPlanCreator)
        
        Args:
            topic: 学习主题
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            学习计划的 JSON 数据
        """
        return self._plan_creator.create_plan(topic, session_id)
    
    @handle_async_ai_service_errors(fallback_result=[{"index": 1, "title": "学习计划创建失败", "children": []}])
    async def create_plan_async(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        异步创建学习计划 (委托给 LearningPlanCreator)
        
        Args:
            topic: 学习主题
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            学习计划的 JSON 数据
        """
        return await self._plan_creator.create_plan_async(topic, session_id)
    
    @handle_ai_service_errors(fallback_result=[])
    def update_plan(
        self, 
        current_plan: Dict[str, Any], 
        feedback_path: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        根据反馈更新学习计划 (委托给 LearningPlanCreator)
        
        Args:
            current_plan: 当前学习计划
            feedback_path: 反馈文件路径
            session_id: 可选的会话ID
            
        Returns:
            更新的计划部分
        """
        return self._plan_creator.update_plan(current_plan, feedback_path, session_id)
    
    @handle_async_ai_service_errors(fallback_result=[])
    async def update_plan_async(
        self, 
        current_plan: Dict[str, Any], 
        feedback_path: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        异步根据反馈更新学习计划 (委托给 LearningPlanCreator)
        
        Args:
            current_plan: 当前学习计划
            feedback_path: 反馈文件路径
            session_id: 可选的会话ID
            
        Returns:
            更新的计划部分
        """
        return await self._plan_creator.update_plan_async(current_plan, feedback_path, session_id)

    @handle_async_ai_service_errors(fallback_result=[])
    async def batch_create_plans_async(self, topics: List[str]) -> List[Dict[str, Any]]:
        """批量异步创建学习计划 (委托给 LearningPlanCreator)"""
        return await self._plan_creator.batch_create_plans_async(topics)
    
    # === CONVERSATION MANAGEMENT METHODS (Delegated) ===
    
    @handle_ai_service_errors(fallback_result={"reply": "Sorry, I encountered an error.", "updates": []})
    def chat_with_agent(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        与教育规划代理聊天 (委托给 ConversationManager)
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含回复和计划更新的响应
        """
        return self._conversation_manager.chat_with_agent(
            message, current_plan, session_id, feedback_path
        )
    
    @handle_async_ai_service_errors(fallback_result={"reply": "Sorry, I encountered an error.", "updates": []})
    async def chat_with_agent_async(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        异步与教育规划代理聊天 (委托给 ConversationManager)
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含回复和计划更新的响应
        """
        return await self._conversation_manager.chat_with_agent_async(
            message, current_plan, session_id, feedback_path
        )
    
    # === BATCH PROCESSING METHODS ===
    
    async def batch_create_plans_async(self, topics: List[str]) -> List[Dict[str, Any]]:
        """批量异步创建学习计划 (委托给 LearningPlanCreator)"""
        return await self._plan_creator.batch_create_plans_async(topics)

        # === SESSION MANAGEMENT METHODS (Delegated) ===
    
    def get_plan_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从会话中获取当前计划 (委托给 ConversationManager)"""
        return self._conversation_manager.get_plan_from_session(session_id)
    
    def clear_session(self, session_id: str):
        """清除会话数据 (委托给 ConversationManager)"""
        return self._conversation_manager.clear_session(session_id)

        # === PERSONALIZATION METHODS (Delegated) ===
    
    @handle_ai_service_errors(fallback_result=[{"index": 1, "title": "个性化计划创建失败", "children": [], "personalization_applied": False}])
    def create_personalized_plan(
        self, 
        topic: str, 
        user_id: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        根据学生特点创建个性化学习计划 (委托给 PersonalizationEngine)
        
        Args:
            topic: 学习主题
            user_id: 学生ID
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            个性化学习计划的 JSON 数据
        """
        return self._personalization_engine.create_personalized_plan(topic, user_id, session_id)

    @handle_async_ai_service_errors(fallback_result=[{"index": 1, "title": "个性化计划创建失败", "children": [], "personalization_applied": False}])
    async def create_personalized_plan_async(
        self, 
        topic: str, 
        user_id: str,
        session_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        异步根据学生特点创建个性化学习计划 (委托给 PersonalizationEngine)
        """
        return await self._personalization_engine.create_personalized_plan_async(topic, user_id, session_id)
    
    @handle_ai_service_errors(fallback_result={"reply": "Sorry, I encountered an error.", "updates": [], "personalization_applied": False})
    def chat_with_personalized_agent(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        user_id: str,
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        与个性化教育规划代理聊天，基于学生特点提供建议 (委托给 PersonalizationEngine)
        
        Args:
            message: 用户消息
            current_plan: 当前学习计划
            user_id: 学生ID
            session_id: 可选的会话ID，用于记忆管理
            feedback_path: 可选的反馈文件路径
            
        Returns:
            包含个性化回复和计划更新的响应
        """
        return self._personalization_engine.chat_with_personalized_agent(
            message, current_plan, user_id, session_id, feedback_path
        )

    @handle_async_ai_service_errors(fallback_result={"reply": "Sorry, I encountered an error.", "updates": [], "personalization_applied": False})
    async def chat_with_personalized_agent_async(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        user_id: str,
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        异步与个性化教育规划代理聊天 (委托给 PersonalizationEngine)
        """
        return await self._personalization_engine.chat_with_personalized_agent_async(
            message, current_plan, user_id, session_id, feedback_path
        )
    
    # === UTILITY METHODS ===
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        from ..core.client import llm_factory
        return llm_factory.is_available()


# === SERVICE FACTORY AND INSTANCE MANAGEMENT ===

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
