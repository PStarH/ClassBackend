"""
Conversation Manager - Specialized service for handling chat interactions
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

from ..core.base_service import LLMBaseService
from ..core.prompts import CHAT_AGENT_PROMPT
from .memory_service import memory_service


def get_chat_cache_key(*args, **kwargs):
    """Generate chat cache key"""
    import hashlib
    # Skip self parameter if present
    message = kwargs.get('message')
    session_id = kwargs.get('session_id', 'default')
    
    if not message and args:
        # If args[0] is self, adjust indices
        if len(args) > 0 and hasattr(args[0], 'chat_with_agent'):
            message = args[1] if len(args) > 1 else 'unknown'
            session_id = args[3] if len(args) > 3 else 'default'
        else:
            message = args[0] if args else 'unknown'
            session_id = args[2] if len(args) > 2 else 'default'
    
    message = str(message) if message else 'unknown'
    key_data = f"{message}:{session_id}"
    return f"chat_cache:{hashlib.md5(key_data.encode()).hexdigest()}"


class ConversationManager(LLMBaseService):
    """Specialized service for handling chat interactions and conversations"""
    
    def chat_with_agent(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        Chat with the educational planning agent
        
        Args:
            message: User message
            current_plan: Current learning plan
            session_id: Optional session ID for memory management
            feedback_path: Optional feedback file path
            
        Returns:
            Response containing reply and plan updates
        """
        # Get conversation context (if session_id exists)
        context = ""
        if session_id and memory_service:
            context = memory_service.get_conversation_context(session_id)
        
        # Create enhanced prompt (with historical context)
        if context:
            enhanced_message = f"Conversation context: {context}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use simple OpenAI client
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
            # Use LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CHAT_AGENT_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
        
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
        
        # Add markdown update status
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
    
    async def chat_with_agent_async(
        self, 
        message: str, 
        current_plan: Dict[str, Any],
        session_id: str = None,
        feedback_path: str = None
    ) -> Dict[str, Any]:
        """
        Asynchronously chat with the educational planning agent
        
        Args:
            message: User message
            current_plan: Current learning plan
            session_id: Optional session ID for memory management
            feedback_path: Optional feedback file path
            
        Returns:
            Response containing reply and plan updates
        """
        # Asynchronously get conversation context
        context = ""
        if session_id and memory_service:
            context = await memory_service.get_conversation_context_async(session_id)
        
        # Create enhanced prompt (with historical context)
        if context:
            enhanced_message = f"Conversation context: {context}\n\nCurrent message: {message}"
        else:
            enhanced_message = message
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use async simple OpenAI client
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
            # Use async LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CHAT_AGENT_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                message=enhanced_message
            )
        
        # Async update memory
        if session_id and memory_service:
            await memory_service.update_conversation_async(
                session_id,
                message,
                result.get("reply", "No response")
            )
        
        return result
    
    def get_plan_from_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current plan from session"""
        if memory_service:
            return memory_service.get_plan_state(session_id)
        return None
    
    def clear_session(self, session_id: str):
        """Clear session data"""
        if memory_service:
            memory_service.clear_session(session_id)
    
    def get_conversation_history(self, session_id: str) -> str:
        """Get conversation history for a session"""
        if memory_service:
            return memory_service.get_conversation_context(session_id)
        return ""
    
    async def get_conversation_history_async(self, session_id: str) -> str:
        """Asynchronously get conversation history for a session"""
        if memory_service:
            return await memory_service.get_conversation_context_async(session_id)
        return ""
    
    def update_conversation_memory(
        self,
        session_id: str,
        user_message: str,
        agent_reply: str
    ):
        """Update conversation memory with new exchange"""
        if session_id and memory_service:
            memory_service.update_conversation(session_id, user_message, agent_reply)
    
    async def update_conversation_memory_async(
        self,
        session_id: str,
        user_message: str,
        agent_reply: str
    ):
        """Asynchronously update conversation memory with new exchange"""
        if session_id and memory_service:
            await memory_service.update_conversation_async(session_id, user_message, agent_reply)