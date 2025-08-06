"""
Learning Plan Creator - Specialized service for creating and updating learning plans
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

from ..core.base_service import LLMBaseService, cache_llm_response
from ..core.prompts import CREATE_PLAN_PROMPT, UPDATE_PLAN_PROMPT
from .memory_service import memory_service


def get_plan_cache_key(*args, **kwargs):
    """Generate plan cache key"""
    import hashlib
    # Skip self parameter if present
    topic = kwargs.get('topic')
    if not topic and args:
        # If args[0] is self, use args[1]
        topic = args[1] if len(args) > 1 and hasattr(args[0], 'create_plan') else args[0]
    topic = str(topic) if topic else 'unknown'
    return f"plan_cache:{hashlib.md5(topic.encode()).hexdigest()}"


class LearningPlanCreator(LLMBaseService):
    """Specialized service for creating and updating learning plans"""
    
    @cache_llm_response(get_plan_cache_key, ttl=7200)  # 2 hour cache
    def create_plan(self, topic: str, session_id: str = None) -> List[Dict[str, Any]]:
        """
        Create a learning plan
        
        Args:
            topic: Learning topic
            session_id: Optional session ID for memory management
            
        Returns:
            Learning plan JSON data
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use simple OpenAI client
            prompt = CREATE_PLAN_PROMPT.format(topic=topic)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If parsing fails, return simple plan structure
                result = [{"index": 1, "title": f"学习{topic}", "children": []}]
        else:
            # Use LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_PLAN_PROMPT
            )
            result = self._execute_chain_with_fallback(chain, topic=topic)
        
        # If session_id provided, save plan state
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
        Asynchronously create a learning plan
        
        Args:
            topic: Learning topic
            session_id: Optional session ID for memory management
            
        Returns:
            Learning plan JSON data
        """
        # Check cache
        cache_key = get_plan_cache_key(topic=topic)
        from django.core.cache import cache
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
            
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use async simple OpenAI client
            prompt = CREATE_PLAN_PROMPT.format(topic=topic)
            response = await self.simple_chat_async(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # If parsing fails, return simple plan structure
                result = [{"index": 1, "title": f"学习{topic}", "children": []}]
        else:
            # Use async LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_PLAN_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(chain, topic=topic)
        
        # Cache result
        cache.set(cache_key, result, 7200)
        
        # If session_id provided, asynchronously save plan state
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
        Update learning plan based on feedback
        
        Args:
            current_plan: Current learning plan
            feedback_path: Feedback file path
            session_id: Optional session ID
            
        Returns:
            Updated plan sections
        """
        # Read feedback file
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Cannot read feedback file: {e}")
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use simple OpenAI client
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
            # Use LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=UPDATE_PLAN_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
        
        # If session_id provided, update memory and plan state
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
        Asynchronously update learning plan based on feedback
        
        Args:
            current_plan: Current learning plan
            feedback_path: Feedback file path
            session_id: Optional session ID
            
        Returns:
            Updated plan sections
        """
        # Read feedback file (simplified to sync read)
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback = f.read()
        except Exception as e:
            raise FileNotFoundError(f"Cannot read feedback file: {e}")
        
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # Use async simple OpenAI client
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
            # Use async LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=UPDATE_PLAN_PROMPT
            )
            result = await self._execute_chain_with_fallback_async(
                chain,
                current_plan=json.dumps(current_plan, ensure_ascii=False),
                feedback=feedback
            )
        
        # If session_id provided, async update memory and plan state
        if session_id and memory_service:
            await memory_service.save_plan_state_async(session_id, result)
            await memory_service.update_conversation_async(
                session_id,
                f"Update plan based on teacher feedback",
                f"Updated plan with {len(result)} changes"
            )
        
        return result

    async def batch_create_plans_async(self, topics: List[str]) -> List[Dict[str, Any]]:
        """Batch create learning plans asynchronously"""
        requests = [
            {
                'chain': LLMChain(llm=self.langchain_llm, prompt=CREATE_PLAN_PROMPT) if self.langchain_llm else None,
                'kwargs': {'topic': topic}
            } if self.langchain_llm else {'prompt': CREATE_PLAN_PROMPT.format(topic=topic)}
            for topic in topics
        ]
        
        results = await self.batch_process_async(requests)
        
        # Process results
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