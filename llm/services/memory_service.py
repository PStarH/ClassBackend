"""
Memory Service - 管理对话历史和计划状态
"""
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_openai import OpenAI as LangChainOpenAI

from ..core.client import llm_factory


class MemoryService:
    """记忆管理服务"""
    
    def __init__(self):
        from ..core.config import LLMConfig
        self.llm = LangChainOpenAI(
            api_key=LLMConfig.API_KEY,
            base_url=LLMConfig.BASE_URL,
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE
        )
        
        # 对话记忆存储：session_id -> memory
        self.conversation_memories: Dict[str, ConversationBufferMemory] = {}
        self.summary_memories: Dict[str, ConversationSummaryMemory] = {}
        
        # 计划状态存储：session_id -> plan
        self.plan_states: Dict[str, Dict[str, Any]] = {}
    
    def get_conversation_memory(self, session_id: str) -> ConversationBufferMemory:
        """获取对话缓冲记忆"""
        if session_id not in self.conversation_memories:
            self.conversation_memories[session_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
        return self.conversation_memories[session_id]
    
    def get_summary_memory(self, session_id: str) -> ConversationSummaryMemory:
        """获取对话摘要记忆"""
        if session_id not in self.summary_memories:
            self.summary_memories[session_id] = ConversationSummaryMemory(
                llm=self.llm,
                memory_key="chat_summary",
                return_messages=True
            )
        return self.summary_memories[session_id]
    
    def save_plan_state(self, session_id: str, plan: Dict[str, Any]):
        """保存计划状态"""
        self.plan_states[session_id] = plan
    
    def get_plan_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取计划状态"""
        return self.plan_states.get(session_id)
    
    def update_conversation(self, session_id: str, user_input: str, ai_output: str):
        """更新对话记忆"""
        buffer_memory = self.get_conversation_memory(session_id)
        summary_memory = self.get_summary_memory(session_id)
        
        # 更新缓冲记忆
        buffer_memory.save_context(
            {"input": user_input}, 
            {"output": ai_output}
        )
        
        # 更新摘要记忆
        summary_memory.save_context(
            {"input": user_input}, 
            {"output": ai_output}
        )
    
    def get_conversation_context(self, session_id: str) -> str:
        """获取对话上下文"""
        summary_memory = self.get_summary_memory(session_id)
        return summary_memory.buffer
    
    def clear_session(self, session_id: str):
        """清除会话数据"""
        if session_id in self.conversation_memories:
            del self.conversation_memories[session_id]
        if session_id in self.summary_memories:
            del self.summary_memories[session_id]
        if session_id in self.plan_states:
            del self.plan_states[session_id]


# 全局记忆服务实例
memory_service = MemoryService()
