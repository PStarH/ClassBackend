"""
LLM Client Factory - 集中管理 OpenAI 客户端
"""
from openai import OpenAI
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
        if self._client is None:
            self._client = OpenAI(
                api_key=LLMConfig.API_KEY,
                base_url=LLMConfig.BASE_URL
            )
        return self._client
    
    def get_model_name(self):
        """获取模型名称"""
        return LLMConfig.MODEL_NAME


# 全局实例
llm_factory = LLMClientFactory()
