"""
统一的LLM服务 - 整合重复代码，提供更清晰的架构
"""
import json
import asyncio
import logging
from typing import Any, Dict, Optional, Type, Union, List
from functools import wraps
from abc import ABC, abstractmethod

from django.core.cache import cache
from django.conf import settings

try:
    from langchain.chains import LLMChain
    from langchain_openai import OpenAI as LangChainOpenAI
    from langchain.output_parsers import PydanticOutputParser
    from langchain.memory import ConversationBufferMemory
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from .client import llm_factory
from .config import LLMConfig

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM服务异常"""
    pass


class ResponseValidator:
    """响应验证器"""
    
    @staticmethod
    def validate_json_response(response: str) -> Dict[str, Any]:
        """验证并清理JSON响应"""
        try:
            cleaned = ResponseValidator.clean_json_content(response)
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise LLMServiceError(f"Invalid JSON response: {e}")
    
    @staticmethod
    def clean_json_content(content: str) -> str:
        """清理AI返回的内容，移除markdown格式"""
        content = content.strip()
        
        # 移除markdown代码块
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        return content.strip()
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> bool:
        """验证必需字段"""
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.warning(f"缺少必需字段: {missing_fields}")
            return False
        return True


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_prefix: str = "llm", default_ttl: int = 3600):
        self.cache_prefix = cache_prefix
        self.default_ttl = default_ttl
    
    def generate_cache_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{':'.join(str(arg) for arg in args)}:{json.dumps(kwargs, sort_keys=True)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{self.cache_prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            return cache.get(key)
        except Exception as e:
            logger.error(f"缓存读取失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            ttl = ttl or self.default_ttl
            cache.set(key, value, ttl)
            return True
        except Exception as e:
            logger.error(f"缓存设置失败: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"缓存删除失败: {e}")
            return False


class BaseLLMService(ABC):
    """LLM服务基类"""
    
    def __init__(self):
        if not llm_factory.is_available():
            raise LLMServiceError("LLM client is not available")
        
        self.client = llm_factory.get_client()
        self.model_name = llm_factory.get_model_name()
        self.cache_manager = CacheManager()
        self.validator = ResponseValidator()
        
        # LangChain支持
        if LANGCHAIN_AVAILABLE:
            self.langchain_llm = LangChainOpenAI(
                api_key=LLMConfig.API_KEY,
                base_url=LLMConfig.BASE_URL,
                model=LLMConfig.MODEL_NAME,
                temperature=LLMConfig.TEMPERATURE
            )
        else:
            self.langchain_llm = None
            logger.warning("LangChain不可用，将使用基础OpenAI客户端")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return llm_factory.is_available()
    
    @abstractmethod
    def get_service_name(self) -> str:
        """获取服务名称"""
        pass
    
    def simple_completion(self, prompt: str, use_cache: bool = True) -> str:
        """简单的文本完成"""
        if use_cache:
            cache_key = self.cache_manager.generate_cache_key("simple", prompt)
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            
            result = response.choices[0].message.content
            
            if use_cache:
                self.cache_manager.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"简单完成请求失败: {e}")
            raise LLMServiceError(f"Completion failed: {e}")
    
    def structured_completion(
        self, 
        prompt: str, 
        response_schema: Optional[Type[BaseModel]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """结构化完成，返回JSON格式"""
        if use_cache:
            cache_key = self.cache_manager.generate_cache_key("structured", prompt, str(response_schema))
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
        
        try:
            # 添加JSON格式要求到提示词
            json_prompt = f"{prompt}\n\n请以JSON格式返回响应。"
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": json_prompt}],
                stream=False
            )
            
            content = response.choices[0].message.content
            result = self.validator.validate_json_response(content)
            
            # 如果提供了模式，验证响应
            if response_schema and PYDANTIC_AVAILABLE:
                try:
                    response_schema(**result)
                except Exception as e:
                    logger.warning(f"响应模式验证失败: {e}")
            
            if use_cache:
                self.cache_manager.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"结构化完成请求失败: {e}")
            raise LLMServiceError(f"Structured completion failed: {e}")
    
    def chain_completion(
        self, 
        chain: 'LLMChain', 
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """使用LangChain执行完成"""
        if not LANGCHAIN_AVAILABLE or not self.langchain_llm:
            # 回退到基础实现
            return self._fallback_completion(chain, **kwargs)
        
        if use_cache:
            cache_key = self.cache_manager.generate_cache_key("chain", str(chain), **kwargs)
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
        
        try:
            result = chain.run(**kwargs)
            
            # 如果结果是字符串，尝试解析为JSON
            if isinstance(result, str):
                result = self.validator.validate_json_response(result)
            
            if use_cache:
                self.cache_manager.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"LangChain执行失败: {e}，回退到基础实现")
            return self._fallback_completion(chain, **kwargs)
    
    def _fallback_completion(self, chain: 'LLMChain', **kwargs) -> Dict[str, Any]:
        """回退到基础OpenAI实现"""
        try:
            # 格式化提示词
            if hasattr(chain, 'prompt') and hasattr(chain.prompt, 'format'):
                formatted_prompt = chain.prompt.format(**kwargs)
            else:
                formatted_prompt = f"根据以下参数生成响应: {kwargs}"
            
            return self.structured_completion(formatted_prompt, use_cache=False)
            
        except Exception as e:
            logger.error(f"回退实现也失败: {e}")
            raise LLMServiceError(f"All completion methods failed: {e}")
    
    async def async_completion(self, prompt: str, use_cache: bool = True) -> str:
        """异步完成"""
        if use_cache:
            cache_key = self.cache_manager.generate_cache_key("async", prompt)
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                return cached_result
        
        try:
            # 使用线程池执行同步调用
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.simple_completion,
                prompt,
                False  # 不在内部使用缓存，避免重复
            )
            
            if use_cache:
                self.cache_manager.set(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"异步完成失败: {e}")
            raise LLMServiceError(f"Async completion failed: {e}")
    
    async def batch_completion(
        self, 
        requests: List[Dict[str, Any]], 
        batch_size: int = 5,
        use_cache: bool = True
    ) -> List[Any]:
        """批量异步处理"""
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # 创建异步任务
            tasks = []
            for request in batch:
                if 'prompt' in request:
                    task = self.async_completion(request['prompt'], use_cache)
                elif 'chain' in request:
                    # 暂时使用同步方法，未来可以改进
                    task = asyncio.create_task(
                        asyncio.to_thread(
                            self.chain_completion,
                            request['chain'],
                            use_cache,
                            **request.get('kwargs', {})
                        )
                    )
                else:
                    continue
                
                tasks.append(task)
            
            # 等待批次完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # 批次间延迟
            if i + batch_size < len(requests):
                await asyncio.sleep(0.1)
        
        return results


def cache_llm_response(cache_key_func, ttl: int = 3600):
    """LLM响应缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            
            # 尝试获取缓存
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                logger.debug(f"缓存设置: {cache_key}")
                return result
            except Exception as e:
                logger.error(f"函数执行失败: {e}")
                raise
        
        return wrapper
    return decorator


def async_cache_llm_response(cache_key_func, ttl: int = 3600):
    """异步LLM响应缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            
            # 尝试获取缓存
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行异步函数
            try:
                result = await func(*args, **kwargs)
                cache.set(cache_key, result, ttl)
                logger.debug(f"缓存设置: {cache_key}")
                return result
            except Exception as e:
                logger.error(f"异步函数执行失败: {e}")
                raise
        
        return wrapper
    return decorator
