"""
LLM Configuration - 统一的配置管理
"""
import os
from decouple import config

# DeepSeek 配置
DEEPSEEK_CONFIG = {
    'api_key': config('DEEPSEEK_API_KEY', default=''),
    'base_url': config('DEEPSEEK_BASE_URL', default='https://api.deepseek.com')
}


class LLMConfig:
    """LLM 配置类"""
    
    # OpenAI/DeepSeek 配置
    API_KEY = DEEPSEEK_CONFIG.get('api_key', '')
    BASE_URL = DEEPSEEK_CONFIG.get('base_url', 'https://api.deepseek.com')
    MODEL_NAME = config('LLM_MODEL_NAME', default='deepseek-chat')
    
    # LangChain 配置
    TEMPERATURE = config('LLM_TEMPERATURE', default=0.1, cast=float)
    MAX_TOKENS = config('LLM_MAX_TOKENS', default=2000, cast=int)
    
    # 缓存配置
    ENABLE_CACHE = config('LLM_ENABLE_CACHE', default=True, cast=bool)
    CACHE_TTL = config('LLM_CACHE_TTL', default=3600, cast=int)  # 1小时
    
    # 记忆管理配置
    MAX_MEMORY_SIZE = config('LLM_MAX_MEMORY_SIZE', default=50, cast=int)
    ENABLE_SUMMARY_MEMORY = config('LLM_ENABLE_SUMMARY_MEMORY', default=True, cast=bool)
    
    # 文件路径配置
    FEEDBACK_FILES_PATH = config('FEEDBACK_FILES_PATH', default='/tmp/feedback/')
    
    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        if not cls.API_KEY:
            raise ValueError("API_KEY is required")
        if not cls.BASE_URL:
            raise ValueError("BASE_URL is required")
        return True


# 验证配置
LLMConfig.validate_config()
