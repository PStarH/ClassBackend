"""
LLM 客户端工厂 - 集中管理 AI 模型客户端
"""
from openai import OpenAI
from django.conf import settings
from typing import Optional


class LLMClientFactory:
    """单例工厂模式管理 LLM 客户端"""
    _instance: Optional['LLMClientFactory'] = None
    _deepseek_client: Optional[OpenAI] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_deepseek_client(self) -> OpenAI:
        """获取 DeepSeek 客户端实例"""
        if self._deepseek_client is None:
            self._deepseek_client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
        return self._deepseek_client
    
    def get_default_model_name(self) -> str:
        """获取默认模型名称"""
        return settings.DEEPSEEK_MODEL
    
    def reset_clients(self):
        """重置所有客户端（主要用于测试）"""
        self._deepseek_client = None


# 全局工厂实例
llm_client_factory = LLMClientFactory()
