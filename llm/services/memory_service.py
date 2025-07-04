"""
Memory Service - 管理对话历史和计划状态 (升级版)
"""
import asyncio
import threading
import time
from collections import OrderedDict
from typing import Dict, List, Any, Optional
from django.core.cache import cache

try:
    # 使用新的 LangChain Memory API (兼容 0.3.x)
    from langchain_community.chat_message_histories import ChatMessageHistory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langchain_openai import OpenAI as LangChainOpenAI
    LANGCHAIN_AVAILABLE = True
    
    class ModernConversationMemory:
        """现代化的对话记忆实现"""
        def __init__(self, memory_key="chat_history", return_messages=True):
            self.memory_key = memory_key
            self.return_messages = return_messages
            self.chat_history = ChatMessageHistory()
            self.last_access = time.time()
        
        def save_context(self, inputs, outputs):
            """保存对话上下文"""
            # 添加用户消息
            if isinstance(inputs, dict):
                user_input = inputs.get('input', str(inputs))
            else:
                user_input = str(inputs)
            self.chat_history.add_user_message(user_input)
            
            # 添加AI响应
            if isinstance(outputs, dict):
                ai_output = outputs.get('output', str(outputs))
            else:
                ai_output = str(outputs)
            self.chat_history.add_ai_message(ai_output)
            
            self.last_access = time.time()
            
            # 限制消息数量
            if len(self.chat_history.messages) > 100:
                # 保留最近50条消息
                self.chat_history.messages = self.chat_history.messages[-50:]
        
        @property
        def messages(self):
            """获取消息列表 (兼容旧API)"""
            return [
                {
                    "input" if isinstance(msg, HumanMessage) else "output": msg.content,
                    "type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "timestamp": time.time()
                }
                for msg in self.chat_history.messages
            ]
    
    class ModernSummaryMemory:
        """现代化的摘要记忆实现"""
        def __init__(self, llm=None, memory_key="chat_summary", return_messages=True, max_token_limit=2000):
            self.llm = llm
            self.memory_key = memory_key
            self.return_messages = return_messages
            self.max_token_limit = max_token_limit
            self.chat_history = ChatMessageHistory()
            self.summary = ""
            self.last_access = time.time()
        
        def save_context(self, inputs, outputs):
            """保存并可能摘要化上下文"""
            # 保存到历史
            if isinstance(inputs, dict):
                user_input = inputs.get('input', str(inputs))
            else:
                user_input = str(inputs)
            self.chat_history.add_user_message(user_input)
            
            if isinstance(outputs, dict):
                ai_output = outputs.get('output', str(outputs))
            else:
                ai_output = str(outputs)
            self.chat_history.add_ai_message(ai_output)
            
            self.last_access = time.time()
            
            # 检查是否需要摘要
            total_content = self.summary + " ".join([msg.content for msg in self.chat_history.messages])
            if len(total_content) > self.max_token_limit:
                self._create_summary()
        
        def _create_summary(self):
            """创建对话摘要"""
            if not self.chat_history.messages:
                return
            
            # 简化的摘要逻辑
            recent_messages = self.chat_history.messages[-10:]  # 最近10条消息
            
            summary_content = []
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    summary_content.append(f"用户: {msg.content[:100]}...")
                else:
                    summary_content.append(f"助手: {msg.content[:100]}...")
            
            self.summary = " | ".join(summary_content)
            
            # 清理旧消息，只保留最近几条
            self.chat_history.messages = self.chat_history.messages[-5:]
        
        @property
        def buffer(self):
            """获取摘要缓冲区"""
            return self.summary + " | " + " | ".join([msg.content for msg in self.chat_history.messages[-3:]])

except ImportError:
    LANGCHAIN_AVAILABLE = False
    # 保持原有的简单实现作为后备
    class ModernConversationMemory:
        def __init__(self, memory_key="chat_history", return_messages=True):
            self.memory_key = memory_key
            self.return_messages = return_messages
            self.messages = []
            self.last_access = time.time()
        
        def save_context(self, inputs, outputs):
            self.messages.append({"input": inputs, "output": outputs})
            self.last_access = time.time()
            if len(self.messages) > 50:
                self.messages = self.messages[-50:]
    
    class ModernSummaryMemory:
        def __init__(self, llm=None, memory_key="chat_summary", return_messages=True):
            self.llm = llm
            self.memory_key = memory_key
            self.return_messages = return_messages
            self.buffer = ""
            self.last_access = time.time()
        
        def save_context(self, inputs, outputs):
            new_content = f"User: {inputs['input'] if isinstance(inputs, dict) else inputs}, AI: {outputs['output'] if isinstance(outputs, dict) else outputs}; "
            self.buffer += new_content
            self.last_access = time.time()
            if len(self.buffer) > 2000:
                self.buffer = self.buffer[-2000:]

from ..core.client import llm_factory


class OptimizedLRUCache:
    """优化的LRU缓存，支持过期时间和内存清理"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            
            # 检查是否过期
            if time.time() - self._timestamps[key] > self.ttl:
                self.remove(key)
                return None
            
            # 移动到末尾（最近使用）
            value = self._cache.pop(key)
            self._cache[key] = value
            return value
    
    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.pop(key)
            elif len(self._cache) >= self.max_size:
                # 移除最久未使用的项
                oldest_key = next(iter(self._cache))
                self.remove(oldest_key)
            
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def remove(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def clear_expired(self) -> int:
        """清理过期项，返回清理的数量"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self._timestamps.items()
                if current_time - timestamp > self.ttl
            ]
            
            for key in expired_keys:
                self.remove(key)
            
            return len(expired_keys)
    
    def size(self) -> int:
        return len(self._cache)

from ..core.client import llm_factory


class MemoryService:
    """记忆管理服务 - 优化版本"""
    
    def __init__(self):
        self.llm = None
        
        if LANGCHAIN_AVAILABLE and llm_factory.is_available():
            try:
                from ..core.config import LLMConfig
                self.llm = LangChainOpenAI(
                    api_key=LLMConfig.API_KEY,
                    base_url=LLMConfig.BASE_URL,
                    model=LLMConfig.MODEL_NAME,
                    temperature=LLMConfig.TEMPERATURE
                )
            except Exception as e:
                print(f"Warning: Failed to initialize LangChain LLM: {e}")
        
        # 使用优化的LRU缓存替代普通字典
        self.conversation_memories = OptimizedLRUCache(max_size=200, ttl=7200)  # 2小时TTL
        self.summary_memories = OptimizedLRUCache(max_size=200, ttl=7200)
        self.plan_states = OptimizedLRUCache(max_size=100, ttl=14400)  # 4小时TTL
        
        # 异步任务队列
        self._async_tasks = []
        self._processing_lock = asyncio.Lock()
        
        # 内存使用监控
        self._memory_warning_threshold = 150  # 当缓存项超过150时发出警告
        
        # 启动清理任务
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        def cleanup_task():
            while True:
                try:
                    total_cleared = 0
                    total_cleared += self.conversation_memories.clear_expired()
                    total_cleared += self.summary_memories.clear_expired()
                    total_cleared += self.plan_states.clear_expired()
                    
                    # 内存压力检查
                    total_items = (self.conversation_memories.size() + 
                                 self.summary_memories.size() + 
                                 self.plan_states.size())
                    
                    if total_items > self._memory_warning_threshold:
                        print(f"Memory warning: {total_items} items in cache")
                        # 强制清理一些最老的项
                        self._force_cleanup()
                    
                    if total_cleared > 0:
                        print(f"Cleaned up {total_cleared} expired memory items")
                    
                    time.sleep(300)  # 每5分钟运行一次
                except Exception as e:
                    print(f"Memory cleanup task error: {e}")
                    time.sleep(60)  # 发生错误时等待1分钟再重试
        
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
    
    def _force_cleanup(self):
        """强制清理内存，保留最近使用的项"""
        # 强制清理最老的30%项目
        max_items = self._memory_warning_threshold
        
        if self.conversation_memories.size() > max_items:
            items_to_remove = self.conversation_memories.size() - int(max_items * 0.7)
            for _ in range(items_to_remove):
                if self.conversation_memories._cache:
                    oldest_key = next(iter(self.conversation_memories._cache))
                    self.conversation_memories.remove(oldest_key)
        
        if self.summary_memories.size() > max_items:
            items_to_remove = self.summary_memories.size() - int(max_items * 0.7)
            for _ in range(items_to_remove):
                if self.summary_memories._cache:
                    oldest_key = next(iter(self.summary_memories._cache))
                    self.summary_memories.remove(oldest_key)
    
    async def get_conversation_memory_async(self, session_id: str):
        """异步获取对话记忆"""
        async with self._processing_lock:
            memory = self.conversation_memories.get(session_id)
            if memory is None:
                memory = ModernConversationMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
                self.conversation_memories.put(session_id, memory)
            return memory
    
    async def get_summary_memory_async(self, session_id: str):
        """异步获取摘要记忆"""
        async with self._processing_lock:
            memory = self.summary_memories.get(session_id)
            if memory is None:
                memory = ModernSummaryMemory(
                    llm=self.llm,
                    memory_key="chat_summary",
                    return_messages=True
                )
                self.summary_memories.put(session_id, memory)
            return memory
    
    async def save_conversation_async(self, session_id: str, user_input: str, ai_response: str):
        """异步保存对话"""
        async with self._processing_lock:
            # 批量保存到buffer memory
            buffer_memory = await self.get_conversation_memory_async(session_id)
            buffer_memory.save_context(
                {"input": user_input},
                {"output": ai_response}
            )
            
            # 异步保存到summary memory
            summary_memory = await self.get_summary_memory_async(session_id)
            summary_memory.save_context(
                {"input": user_input},
                {"output": ai_response}
            )
            
            # 异步保存到Django缓存
            cache_key = f"conversation_history_{session_id}"
            cache.set(cache_key, {
                "user_input": user_input,
                "ai_response": ai_response,
                "timestamp": time.time()
            }, timeout=7200)
    
    async def batch_save_conversations_async(self, conversations: List[Dict]):
        """批量异步保存对话"""
        tasks = []
        for conv in conversations:
            task = self.save_conversation_async(
                conv['session_id'],
                conv['user_input'],
                conv['ai_response']
            )
            tasks.append(task)
        
        # 批量执行，限制并发数
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            
            # 在批次之间添加小延迟
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.1)
    
    async def get_plan_state_async(self, plan_id: str) -> Dict[str, Any]:
        """异步获取计划状态"""
        async with self._processing_lock:
            plan_state = self.plan_states.get(plan_id)
            if plan_state is None:
                plan_state = {
                    "current_step": 0,
                    "completed_steps": [],
                    "context": {},
                    "last_updated": time.time()
                }
                self.plan_states.put(plan_id, plan_state)
            return plan_state
    
    async def update_plan_state_async(self, plan_id: str, updates: Dict[str, Any]):
        """异步更新计划状态"""
        async with self._processing_lock:
            plan_state = await self.get_plan_state_async(plan_id)
            plan_state.update(updates)
            plan_state["last_updated"] = time.time()
            self.plan_states.put(plan_id, plan_state)
    
    def save_plan_state(self, session_id: str, plan: Dict[str, Any]):
        """保存计划状态"""
        self.plan_states.put(session_id, plan)
        
        # 同时保存到Django缓存作为持久化备份
        cache_key = f"plan_state:{session_id}"
        cache.set(cache_key, plan, 14400)  # 4小时
    
    def get_plan_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取计划状态"""
        # 首先从内存缓存获取
        plan = self.plan_states.get(session_id)
        if plan is None:
            # 从Django缓存恢复
            cache_key = f"plan_state:{session_id}"
            plan = cache.get(cache_key)
            if plan:
                self.plan_states.put(session_id, plan)
        return plan
    
    async def update_conversation_async(self, session_id: str, user_input: str, ai_output: str):
        """异步更新对话记忆"""
        try:
            # 在线程池中执行内存操作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._update_conversation_sync, 
                session_id, user_input, ai_output
            )
        except Exception as e:
            print(f"Warning: Failed to update conversation memory: {e}")
    
    def _update_conversation_sync(self, session_id: str, user_input: str, ai_output: str):
        """同步更新对话记忆的内部方法"""
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
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取对话历史记录"""
        try:
            memory = self.get_conversation_memory(session_id)
            if hasattr(memory, 'messages'):
                return memory.messages
            return []
        except Exception as e:
            print(f"Warning: Failed to get conversation history: {e}")
            return []
    
    def get_conversation_memory(self, session_id: str):
        """获取对话记忆对象"""
        memory = self.conversation_memories.get(session_id)
        if memory is None:
            memory = ModernConversationMemory(memory_key="chat_history", return_messages=True)
            self.conversation_memories.put(session_id, memory)
        return memory
    
    def get_summary_memory(self, session_id: str):
        """获取摘要记忆对象"""
        memory = self.summary_memories.get(session_id)
        if memory is None:
            memory = ModernSummaryMemory(llm=self.llm, memory_key="chat_summary", return_messages=True)
            self.summary_memories.put(session_id, memory)
        return memory
    
    def update_conversation(self, session_id: str, user_input: str, ai_output: str):
        """更新对话记忆"""
        self._update_conversation_sync(session_id, user_input, ai_output)
    
    def get_conversation_context(self, session_id: str) -> str:
        """获取对话上下文"""
        try:
            summary_memory = self.get_summary_memory(session_id)
            return summary_memory.buffer
        except Exception as e:
            print(f"Warning: Failed to get conversation context: {e}")
            return ""
    
    async def get_conversation_context_async(self, session_id: str) -> str:
        """异步获取对话上下文"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_conversation_context, 
            session_id
        )
    
    def clear_session(self, session_id: str):
        """清除会话数据"""
        self.conversation_memories.remove(session_id)
        self.summary_memories.remove(session_id)
        self.plan_states.remove(session_id)
    
    async def clear_session_async(self, session_id: str):
        """异步清除会话数据"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.clear_session, session_id)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存使用统计"""
        return {
            "conversation_memories": self.conversation_memories.size(),
            "summary_memories": self.summary_memories.size(),
            "plan_states": self.plan_states.size(),
            "total_items": (self.conversation_memories.size() + 
                          self.summary_memories.size() + 
                          self.plan_states.size()),
            "warning_threshold": self._memory_warning_threshold
        }
    
    def force_cleanup(self) -> Dict[str, int]:
        """强制清理过期项"""
        stats = {
            "conversation_cleared": self.conversation_memories.clear_expired(),
            "summary_cleared": self.summary_memories.clear_expired(),
            "plan_cleared": self.plan_states.clear_expired()
        }
        stats["total_cleared"] = sum(stats.values())
        return stats


# 全局记忆服务实例
try:
    memory_service = MemoryService()
except Exception as e:
    print(f"Warning: Failed to initialize memory service: {e}")
    memory_service = None
