"""
LLM Client Factory - 集中管理 OpenAI 客户端
"""
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI package not available. AI services will be disabled.")

from .config import LLMConfig


class LLMClientFactory:
    """单例工厂模式管理 LLM 客户端"""
    _instance = None
    _client = None
    
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
            self._client = OpenAI(
                api_key=LLMConfig.API_KEY,
                base_url=LLMConfig.BASE_URL
            )
        return self._client
    
    def get_model_name(self):
        """获取模型名称"""
        return LLMConfig.MODEL_NAME
    
    def is_available(self):
        """检查AI服务是否可用"""
        return OPENAI_AVAILABLE and bool(LLMConfig.API_KEY)


# 全局实例
llm_factory = LLMClientFactory()
