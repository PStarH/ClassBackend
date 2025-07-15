"""
LLM Base Service - 提供通用的 LLM 调用服务
"""
import json
import re
import asyncio
import concurrent.futures
from typing import Any, Dict, Optional, Type, Coroutine
from functools import wraps
from django.core.cache import cache

try:
    from langchain.chains import LLMChain
    from langchain_openai import OpenAI as LangChainOpenAI
    from langchain.output_parsers import PydanticOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain packages not available. Some AI features will be limited.")

try:
    from pydantic import BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("Warning: Pydantic not available. AI response parsing will be limited.")


from .client import llm_factory


def cache_llm_response(cache_key_func, ttl=3600):
    """缓存LLM响应的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def cache_async_llm_response(cache_key_func, ttl=3600):
    """缓存异步LLM响应的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


class LLMBaseService:
    """LLM 基础服务类"""
    
    def __init__(self):
        # 延迟初始化，避免在模块加载时创建客户端
        self.client = None
        self.model_name = None
        self.langchain_llm = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """确保服务已初始化"""
        if self._initialized:
            return
            
        if not llm_factory.is_available():
            print("Warning: LLM client is not available")
            return
            
        try:
            from .config import LLMConfig
            self.client = llm_factory.get_client()
            self.model_name = llm_factory.get_model_name()
            
            # 为 LangChain 创建 LLM 实例（如果可用），若初始化失败则回退
            if LANGCHAIN_AVAILABLE:
                try:
                    # 尝试使用最新的 LangChain OpenAI 初始化方式
                    self.langchain_llm = LangChainOpenAI(
                        api_key=LLMConfig.API_KEY,
                        base_url=LLMConfig.BASE_URL,
                        model_name=LLMConfig.MODEL_NAME,
                        temperature=LLMConfig.TEMPERATURE
                    )
                except (TypeError, AttributeError) as e:
                    try:
                        # 回退到基础参数初始化
                        self.langchain_llm = LangChainOpenAI(
                            openai_api_key=LLMConfig.API_KEY,
                            model_name=LLMConfig.MODEL_NAME,
                            temperature=LLMConfig.TEMPERATURE
                        )
                    except Exception as e2:
                        # 最终回退：只使用必需参数
                        print(f"Warning: LangChain initialization failed with standard params: {e2}")
                        try:
                            self.langchain_llm = LangChainOpenAI(
                                openai_api_key=LLMConfig.API_KEY
                            )
                        except Exception as e3:
                            print(f"Warning: Failed to initialize LangChain LLM completely: {e3}")
                            self.langchain_llm = None
            else:
                self.langchain_llm = None
                
            self._initialized = True
        except Exception as e:
            print(f"Warning: Failed to initialize LLM service: {e}")
    
    def _get_pydantic_parser(self, pydantic_object: Type[BaseModel]):
        """获取Pydantic解析器"""
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic is not available for parsing.")
        return PydanticOutputParser(pydantic_object=pydantic_object)

    def _execute_chain_with_fallback(
        self, 
        chain: 'LLMChain',
        **kwargs: Any
    ) -> Any:
        """
        执行LLMChain，并在失败时提供回退机制
        """
        try:
            response = chain.invoke(kwargs)
            # 如果有输出解析器，LangChain会处理解析
            if chain.output_parser:
                return response['text']
            
            # 对于没有解析器的原始输出，手动加载
            if isinstance(response, str):
                return json.loads(self._clean_json_content(response))
            elif isinstance(response, dict) and 'text' in response:
                return json.loads(self._clean_json_content(response['text']))
            return response

        except Exception as e:
            print(f"Error executing LLMChain: {e}")
            # 根据 kwargs 构建一个简单的回退响应
            fallback_data = {"error": str(e)}
            fallback_data.update(kwargs)
            return fallback_data

    def _clean_json_content(self, content: str) -> str:
        """清理 AI 返回的内容，移除 markdown 格式"""
        content = content.strip()
        
        # 移除 markdown 代码块
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        return content.strip()
    
    def simple_chat(self, prompt: str) -> str:
        """简单的聊天接口，不依赖LangChain"""
        self._ensure_initialized()
        if not self.client:
            return "AI服务暂时不可用"
            
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        
        return response.choices[0].message.content
    
    def _execute_chain_with_fallback(self, chain, **kwargs) -> Dict[str, Any]:
        """执行 LangChain 并提供回退机制"""
        self._ensure_initialized()
        
        if not LANGCHAIN_AVAILABLE or not self.langchain_llm or not self.client:
            return self._fallback_to_openai(chain, **kwargs)
            
        try:
            # 使用 LangChain 执行
            result = chain.run(**kwargs)
            cleaned_result = self._clean_json_content(result)
            return json.loads(cleaned_result)
        except Exception as e:
            # 回退到原始 OpenAI 客户端
            print(f"LangChain execution failed: {e}, falling back to OpenAI client")
            return self._fallback_to_openai(chain, **kwargs)
    
    def _fallback_to_openai(self, chain, **kwargs) -> Dict[str, Any]:
        """回退到原始 OpenAI 客户端"""
        if not self.client:
            return {"error": "AI服务暂时不可用"}
            
        # 简单的提示词格式化
        if hasattr(chain, 'prompt') and hasattr(chain.prompt, 'format'):
            formatted_prompt = chain.prompt.format(**kwargs)
        else:
            # 如果没有LangChain，构建简单的提示词
            formatted_prompt = f"根据以下参数生成响应: {kwargs}"
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": formatted_prompt}
            ],
            stream=False
        )
        
        content = response.choices[0].message.content
        cleaned_content = self._clean_json_content(content)
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            # 如果不是JSON，返回简单的响应结构
            return {"reply": content}
    
    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """生成缓存键"""
        import hashlib
        key_data = f"{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return f"llm_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def simple_chat_async(self, prompt: str) -> str:
        """异步简单的聊天接口，不依赖LangChain"""
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            response = await loop.run_in_executor(
                executor,
                lambda: self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
            )
        return response.choices[0].message.content
    
    async def _execute_chain_with_fallback_async(self, chain, **kwargs) -> Dict[str, Any]:
        """异步执行 LangChain 并提供回退机制"""
        if not LANGCHAIN_AVAILABLE or not self.langchain_llm:
            return await self._fallback_to_openai_async(chain, **kwargs)
            
        try:
            # 使用线程池执行 LangChain
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: chain.run(**kwargs)
                )
            cleaned_result = self._clean_json_content(result)
            return json.loads(cleaned_result)
        except Exception as e:
            # 回退到原始 OpenAI 客户端
            print(f"LangChain execution failed: {e}, falling back to OpenAI client")
            return await self._fallback_to_openai_async(chain, **kwargs)
    
    async def _fallback_to_openai_async(self, chain, **kwargs) -> Dict[str, Any]:
        """异步回退到原始 OpenAI 客户端"""
        # 简单的提示词格式化
        if hasattr(chain, 'prompt') and hasattr(chain.prompt, 'format'):
            formatted_prompt = chain.prompt.format(**kwargs)
        else:
            # 如果没有LangChain，构建简单的提示词
            formatted_prompt = f"根据以下参数生成响应: {kwargs}"
        
        content = await self.simple_chat_async(formatted_prompt)
        cleaned_content = self._clean_json_content(content)
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            # 如果不是JSON，返回简单的响应结构
            return {"reply": content}
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.client is not None and llm_factory.is_available()
        
    
    # 批处理异步方法
    async def batch_process_async(self, requests: list, batch_size: int = 5) -> list:
        """批量异步处理多个请求"""
        results = []
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            batch_tasks = []
            
            for request in batch:
                if isinstance(request, dict):
                    if 'chain' in request:
                        task = self._execute_chain_with_fallback_async(
                            request['chain'], **request.get('kwargs', {})
                        )
                    else:
                        task = self.simple_chat_async(request.get('prompt', ''))
                else:
                    task = self.simple_chat_async(str(request))
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # 在批次之间添加小延迟，避免API限制
            if i + batch_size < len(requests):
                await asyncio.sleep(0.1)
        
        return results
