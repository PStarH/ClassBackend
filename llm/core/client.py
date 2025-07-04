"""
LLM Client Factory - 集中管理 OpenAI 客户端
"""
try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not available. AI services will be disabled.")

from .config import LLMConfig


class LLMClientFactory:
    """单例工厂模式管理 LLM 客户端"""
    _instance = None
    _client = None
    _async_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self):
        """获取 OpenAI 客户端实例"""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package is not available")
        
        if not LLMConfig.API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
            
        if self._client is None:
            # Use module-level OpenAI API to avoid client init issues
            import openai as openai_module
            # Configure OpenAI credentials and base URL
            openai_module.api_key = LLMConfig.API_KEY
            try:
                setattr(openai_module, 'base_url', LLMConfig.BASE_URL)
            except Exception:
                pass
            self._client = openai_module
        return self._client
    
    def get_async_client(self):
        """获取异步 OpenAI 客户端实例"""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package is not available")
        
        if not LLMConfig.API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
            
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=LLMConfig.API_KEY,
                base_url=LLMConfig.BASE_URL
            )
        return self._async_client

    def get_model_name(self):
        """获取模型名称"""
        return LLMConfig.MODEL_NAME
    
    def is_available(self):
        """检查AI服务是否可用"""
        return OPENAI_AVAILABLE and bool(LLMConfig.API_KEY)


# 全局实例
llm_factory = LLMClientFactory()
