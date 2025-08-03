"""
增强的异步LangChain服务
包含超时处理、高级缓存、Celery集成和错误恢复
基于建议的最佳实践实现
"""
import asyncio
import logging
import time
import hashlib
from typing import Any, Dict, Optional, List, Union, Callable
from functools import wraps
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from decouple import config

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

try:
    from langchain.chains import LLMChain
    from langchain_openai import OpenAI as LangChainOpenAI
    from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
    from langchain.callbacks import AsyncCallbackHandler
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .unified_service import BaseLLMService, LLMServiceError, CacheManager

logger = logging.getLogger(__name__)

# 配置常量
DEFAULT_TIMEOUT = config('LLM_DEFAULT_TIMEOUT', default=30, cast=int)
BATCH_SIZE = config('LLM_BATCH_SIZE', default=5, cast=int)
MAX_RETRIES = config('LLM_MAX_RETRIES', default=3, cast=int)
CACHE_TTL = config('LLM_CACHE_TTL', default=3600, cast=int)


class TimeoutError(LLMServiceError):
    """超时错误"""
    pass


class RateLimitError(LLMServiceError):
    """速率限制错误"""
    pass


class AsyncCallbackMonitor(AsyncCallbackHandler):
    """异步回调监控器 - 用于LangChain性能监控"""
    
    def __init__(self):
        self.start_time = None
        self.tokens_used = 0
        self.call_count = 0
    
    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """LLM开始时的回调"""
        self.start_time = time.time()
        self.call_count += 1
        logger.debug(f"LLM调用开始 #{self.call_count}: {len(prompts)} prompts")
    
    async def on_llm_end(self, response, **kwargs) -> None:
        """LLM结束时的回调"""
        if self.start_time:
            duration = time.time() - self.start_time
            logger.info(f"LLM调用完成，耗时: {duration:.2f}s")
            
            # 记录性能指标
            self._record_performance_metrics(duration)
    
    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """LLM错误时的回调"""
        logger.error(f"LLM调用失败: {error}")
    
    def _record_performance_metrics(self, duration: float):
        """记录性能指标"""
        try:
            # 使用缓存记录性能数据
            metrics_key = f"llm_metrics:{timezone.now().strftime('%Y%m%d')}"
            metrics = cache.get(metrics_key, {'total_calls': 0, 'total_time': 0, 'avg_time': 0})
            
            metrics['total_calls'] += 1
            metrics['total_time'] += duration
            metrics['avg_time'] = metrics['total_time'] / metrics['total_calls']
            
            cache.set(metrics_key, metrics, 86400)  # 缓存一天
            
            # 慢查询警告
            if duration > config('LLM_SLOW_QUERY_THRESHOLD', default=5.0, cast=float):
                logger.warning(f"检测到慢LLM调用: {duration:.2f}s")
                
        except Exception as e:
            logger.error(f"性能指标记录失败: {e}")


class AdvancedCacheManager(CacheManager):
    """高级缓存管理器 - 支持层级缓存和智能失效"""
    
    def __init__(self, cache_prefix: str = "llm_advanced", default_ttl: int = 3600):
        super().__init__(cache_prefix, default_ttl)
        self.hit_count = 0
        self.miss_count = 0
    
    def generate_smart_cache_key(self, prompt: str, model: str, user_id: Optional[str] = None) -> str:
        """生成智能缓存键 - 考虑用户、模型和内容"""
        # 对长提示词进行摘要
        if len(prompt) > 500:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        else:
            prompt_hash = prompt
        
        key_components = [self.cache_prefix, model, prompt_hash]
        if user_id:
            key_components.append(f"user_{user_id}")
        
        return ":".join(key_components)
    
    def get_with_stats(self, key: str) -> Optional[Any]:
        """获取缓存并记录统计"""
        result = self.get(key)
        if result is not None:
            self.hit_count += 1
            logger.debug(f"缓存命中: {key}")
        else:
            self.miss_count += 1
            logger.debug(f"缓存未命中: {key}")
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'total_requests': total
        }
    
    def invalidate_pattern(self, pattern: str) -> int:
        """根据模式失效缓存"""
        try:
            # 注意：这需要Redis支持，Django默认缓存不支持模式删除
            if hasattr(cache, 'delete_pattern'):
                return cache.delete_pattern(f"{self.cache_prefix}:{pattern}*")
            else:
                logger.warning("当前缓存后端不支持模式删除")
                return 0
        except Exception as e:
            logger.error(f"缓存模式删除失败: {e}")
            return 0


class CircuitBreaker:
    """熔断器 - 防止级联失败"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
                logger.info("熔断器进入半开状态")
            else:
                raise LLMServiceError("熔断器开启状态，调用被拒绝")
        
        try:
            result = func(*args, **kwargs)
            
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("熔断器恢复正常状态")
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
            
            raise e


class EnhancedAsyncLLMService(BaseLLMService):
    """增强的异步LLM服务"""
    
    def __init__(self):
        super().__init__()
        self.advanced_cache = AdvancedCacheManager()
        self.circuit_breaker = CircuitBreaker()
        self.executor = ThreadPoolExecutor(max_workers=config('LLM_THREAD_POOL_SIZE', default=10, cast=int))
        self.callback_monitor = AsyncCallbackMonitor() if LANGCHAIN_AVAILABLE else None
        
        # 初始化内存管理
        self.conversation_memory = {}
        self.memory_cleanup_interval = config('MEMORY_CLEANUP_INTERVAL', default=3600, cast=int)
        self.last_memory_cleanup = time.time()
    
    def get_service_name(self) -> str:
        return "enhanced_async_llm"
    
    @asynccontextmanager
    async def timeout_context(self, timeout: int = DEFAULT_TIMEOUT):
        """超时上下文管理器"""
        try:
            yield
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM请求超时 ({timeout}s)")
        except FutureTimeoutError:
            raise TimeoutError(f"LLM请求超时 ({timeout}s)")
    
    async def safe_completion_with_timeout(
        self,
        prompt: str,
        timeout: int = DEFAULT_TIMEOUT,
        use_cache: bool = True,
        user_id: Optional[str] = None
    ) -> str:
        """带超时和安全保护的完成"""
        # 智能缓存键
        cache_key = self.advanced_cache.generate_smart_cache_key(
            prompt, self.model_name, user_id
        )
        
        if use_cache:
            cached_result = self.advanced_cache.get_with_stats(cache_key)
            if cached_result:
                return cached_result
        
        async with self.timeout_context(timeout):
            try:
                # 使用熔断器保护
                result = await asyncio.wait_for(
                    self._execute_with_circuit_breaker(prompt),
                    timeout=timeout
                )
                
                if use_cache:
                    self.advanced_cache.set(cache_key, result, CACHE_TTL)
                
                return result
                
            except asyncio.TimeoutError:
                raise TimeoutError(f"LLM请求超时: {timeout}s")
            except Exception as e:
                logger.error(f"LLM请求失败: {e}")
                raise LLMServiceError(f"Completion failed: {e}")
    
    async def _execute_with_circuit_breaker(self, prompt: str) -> str:
        """通过熔断器执行请求"""
        def sync_completion():
            return self.circuit_breaker.call(self.simple_completion, prompt, False)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, sync_completion)
    
    async def batch_completion_with_rate_limit(
        self,
        requests: List[Dict[str, Any]],
        batch_size: int = BATCH_SIZE,
        rate_limit_delay: float = 1.0,
        timeout: int = DEFAULT_TIMEOUT,
        use_cache: bool = True
    ) -> List[Any]:
        """带速率限制的批量处理"""
        results = []
        total_batches = (len(requests) + batch_size - 1) // batch_size
        
        logger.info(f"开始批量处理: {len(requests)} 请求, {total_batches} 批次")
        
        for i, batch_start in enumerate(range(0, len(requests), batch_size)):
            batch_end = min(batch_start + batch_size, len(requests))
            batch = requests[batch_start:batch_end]
            
            logger.debug(f"处理批次 {i+1}/{total_batches}: {len(batch)} 请求")
            
            # 创建异步任务
            tasks = []
            for request in batch:
                prompt = request.get('prompt', '')
                user_id = request.get('user_id')
                
                task = self.safe_completion_with_timeout(
                    prompt, timeout, use_cache, user_id
                )
                tasks.append(task)
            
            # 执行批次
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
                
                # 速率限制延迟
                if i < total_batches - 1:  # 最后一批不需要延迟
                    await asyncio.sleep(rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"批次 {i+1} 执行失败: {e}")
                # 为失败的批次添加错误结果
                batch_results = [LLMServiceError(f"Batch {i+1} failed: {e}")] * len(batch)
                results.extend(batch_results)
        
        logger.info(f"批量处理完成: {len(results)} 结果")
        return results
    
    def get_conversation_memory(self, conversation_id: str) -> ConversationBufferMemory:
        """获取或创建对话内存"""
        if conversation_id not in self.conversation_memory:
            if LANGCHAIN_AVAILABLE:
                self.conversation_memory[conversation_id] = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            else:
                # 简单的内存实现
                self.conversation_memory[conversation_id] = {
                    'messages': [],
                    'created_at': time.time()
                }
        
        return self.conversation_memory[conversation_id]
    
    def cleanup_old_memory(self):
        """清理旧的内存数据"""
        current_time = time.time()
        
        if current_time - self.last_memory_cleanup < self.memory_cleanup_interval:
            return
        
        expired_conversations = []
        max_age = config('CONVERSATION_MEMORY_MAX_AGE', default=86400, cast=int)  # 24小时
        
        for conv_id, memory in self.conversation_memory.items():
            if hasattr(memory, 'created_at'):
                if current_time - memory.created_at > max_age:
                    expired_conversations.append(conv_id)
            elif isinstance(memory, dict) and 'created_at' in memory:
                if current_time - memory['created_at'] > max_age:
                    expired_conversations.append(conv_id)
        
        for conv_id in expired_conversations:
            del self.conversation_memory[conv_id]
            logger.debug(f"清理过期对话内存: {conv_id}")
        
        self.last_memory_cleanup = current_time
        logger.info(f"内存清理完成，删除 {len(expired_conversations)} 个过期对话")
    
    async def conversation_completion(
        self,
        prompt: str,
        conversation_id: str,
        timeout: int = DEFAULT_TIMEOUT,
        use_cache: bool = False,  # 对话通常不缓存
        user_id: Optional[str] = None
    ) -> str:
        """对话式完成"""
        memory = self.get_conversation_memory(conversation_id)
        
        # 构建包含历史的提示词
        if LANGCHAIN_AVAILABLE and hasattr(memory, 'chat_memory'):
            history = memory.chat_memory.messages
            context_prompt = self._build_context_prompt(prompt, history)
        elif isinstance(memory, dict):
            history = memory.get('messages', [])
            context_prompt = self._build_simple_context_prompt(prompt, history)
        else:
            context_prompt = prompt
        
        # 执行完成
        result = await self.safe_completion_with_timeout(
            context_prompt, timeout, use_cache, user_id
        )
        
        # 更新内存
        self._update_conversation_memory(memory, prompt, result)
        
        # 定期清理内存
        self.cleanup_old_memory()
        
        return result
    
    def _build_context_prompt(self, prompt: str, history) -> str:
        """构建包含上下文的提示词"""
        context_lines = ["对话历史:"]
        
        for message in history[-10:]:  # 只保留最近10条消息
            if hasattr(message, 'content'):
                role = getattr(message, 'type', 'unknown')
                content = message.content
                context_lines.append(f"{role}: {content}")
        
        context_lines.append(f"\n当前问题: {prompt}")
        return "\n".join(context_lines)
    
    def _build_simple_context_prompt(self, prompt: str, history: List[Dict]) -> str:
        """构建简单上下文提示词"""
        context_lines = ["对话历史:"]
        
        for message in history[-10:]:
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            context_lines.append(f"{role}: {content}")
        
        context_lines.append(f"\n当前问题: {prompt}")
        return "\n".join(context_lines)
    
    def _update_conversation_memory(self, memory, user_input: str, ai_response: str):
        """更新对话内存"""
        if LANGCHAIN_AVAILABLE and hasattr(memory, 'chat_memory'):
            memory.chat_memory.add_user_message(user_input)
            memory.chat_memory.add_ai_message(ai_response)
        elif isinstance(memory, dict):
            memory['messages'].extend([
                {'role': 'user', 'content': user_input},
                {'role': 'assistant', 'content': ai_response}
            ])
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_stats = self.advanced_cache.get_cache_stats()
        
        stats = {
            'cache_stats': cache_stats,
            'circuit_breaker_state': self.circuit_breaker.state,
            'circuit_breaker_failures': self.circuit_breaker.failure_count,
            'active_conversations': len(self.conversation_memory),
            'service_name': self.get_service_name(),
            'langchain_available': LANGCHAIN_AVAILABLE,
        }
        
        # 添加回调监控统计
        if self.callback_monitor:
            stats['callback_stats'] = {
                'total_calls': self.callback_monitor.call_count,
            }
        
        return stats
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        # 清理资源
        self.executor.shutdown(wait=False)


# Celery任务集成
if CELERY_AVAILABLE:
    @shared_task(bind=True, max_retries=MAX_RETRIES)
    def async_llm_completion_task(self, prompt: str, user_id: Optional[str] = None):
        """Celery异步LLM完成任务"""
        try:
            service = EnhancedAsyncLLMService()
            
            # 由于Celery任务是同步的，我们需要运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    service.safe_completion_with_timeout(prompt, use_cache=True, user_id=user_id)
                )
                return {'status': 'success', 'result': result}
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Celery LLM任务失败: {e}")
            
            # 重试逻辑
            if self.request.retries < MAX_RETRIES:
                retry_delay = 2 ** self.request.retries  # 指数退避
                logger.info(f"任务重试 #{self.request.retries + 1}，延迟 {retry_delay}s")
                raise self.retry(countdown=retry_delay, exc=e)
            
            return {'status': 'error', 'error': str(e)}
    
    @shared_task
    def batch_llm_completion_task(requests: List[Dict[str, Any]]):
        """Celery批量LLM完成任务"""
        try:
            service = EnhancedAsyncLLMService()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(
                    service.batch_completion_with_rate_limit(requests)
                )
                return {'status': 'success', 'results': results}
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Celery批量LLM任务失败: {e}")
            return {'status': 'error', 'error': str(e)}


# 导出主要组件
__all__ = [
    'EnhancedAsyncLLMService',
    'AdvancedCacheManager', 
    'CircuitBreaker',
    'AsyncCallbackMonitor',
    'TimeoutError',
    'RateLimitError',
]

# 如果Celery可用，导出任务
if CELERY_AVAILABLE:
    __all__.extend([
        'async_llm_completion_task',
        'batch_llm_completion_task'
    ])