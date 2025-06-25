"""
Advisor Service - 教育规划顾问服务
"""
import json
from typing import List, Dict, Any, Optional
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser

from ..core.base_service import LLMBaseService
from ..core.prompts import CREATE_PLAN_PROMPT, UPDATE_PLAN_PROMPT, CHAT_AGENT_PROMPT
from ..core.models import PlanNode, ChatResponse
from .memory_service import memory_service


class AdvisorService(LLMBaseService):
    """教育规划顾问服务"""
    
    def create_plan(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        创建学习计划
        
        Args:
            topic: 学习主题
            session_id: 可选的会话ID，用于记忆管理
            
        Returns:
            学习计划的 JSON 数据
        """
        chain = LLMChain(
            llm=self.langchain_llm,
            prompt=CREATE_PLAN_PROMPT
        )
        
        result = self._execute_chain_with_fallback(chain, topic=topic)
        
        # 如果提供了会话ID，保存计划状态
        if session_id:
            memory_service.save_plan_state(session_id, result)
            memory_service.update_conversation(
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
        if session_id:
            memory_service.save_plan_state(session_id, result)
            memory_service.update_conversation(
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
        if session_id:
            context = memory_service.get_conversation_context(session_id)
        
        # 创建增强的提示词（包含历史上下文）
        enhanced_prompt = CHAT_AGENT_PROMPT
        if context:
            enhanced_message = f"Conversation context: {context}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        chain = LLMChain(
            llm=self.langchain_llm,
            prompt=enhanced_prompt
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
        if session_id:
            memory_service.update_conversation(
                session_id,
                message,
                result.get('reply', 'No reply provided')
            )
            
            # 如果有计划更新，保存新状态
            if result.get('updates'):
                memory_service.save_plan_state(session_id, result.get('updates'))
            
        return result
    
    def get_plan_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从会话中获取当前计划"""
        return memory_service.get_plan_state(session_id)
    
    def clear_session(self, session_id: str):
        """清除会话数据"""
        memory_service.clear_session(session_id)


# 全局服务实例
advisor_service = AdvisorService()
