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
    
    # 性能优化配置
    REQUEST_TIMEOUT = config('LLM_REQUEST_TIMEOUT', default=30, cast=int)
    MAX_RETRIES = config('LLM_MAX_RETRIES', default=3, cast=int)
    RETRY_DELAY = config('LLM_RETRY_DELAY', default=1.0, cast=float)
    
    # 并发控制配置
    MAX_CONCURRENT_REQUESTS = config('LLM_MAX_CONCURRENT_REQUESTS', default=10, cast=int)
    RATE_LIMIT_PER_MINUTE = config('LLM_RATE_LIMIT_PER_MINUTE', default=60, cast=int)
    
    # 质量控制配置
    ENABLE_RESPONSE_VALIDATION = config('LLM_ENABLE_RESPONSE_VALIDATION', default=True, cast=bool)
    MIN_RESPONSE_LENGTH = config('LLM_MIN_RESPONSE_LENGTH', default=10, cast=int)
    MAX_RESPONSE_LENGTH = config('LLM_MAX_RESPONSE_LENGTH', default=4000, cast=int)
    
    # 监控配置
    ENABLE_METRICS = config('LLM_ENABLE_METRICS', default=True, cast=bool)
    METRICS_RETENTION_DAYS = config('LLM_METRICS_RETENTION_DAYS', default=7, cast=int)
    
    # 回退策略配置
    ENABLE_FALLBACK = config('LLM_ENABLE_FALLBACK', default=True, cast=bool)
    FALLBACK_MODEL = config('LLM_FALLBACK_MODEL', default='deepseek-chat')
    
    # 安全配置
    ENABLE_CONTENT_FILTERING = config('LLM_ENABLE_CONTENT_FILTERING', default=True, cast=bool)
    MAX_INPUT_LENGTH = config('LLM_MAX_INPUT_LENGTH', default=2000, cast=int)
    
    @classmethod
    def validate_config(cls):
        """验证配置是否完整"""
        if not cls.API_KEY:
            # 只发出警告，不抛出异常，让应用正常启动
            print("Warning: DEEPSEEK_API_KEY is not set. AI services will be disabled.")
            return False
        if not cls.BASE_URL:
            raise ValueError("BASE_URL is required")
        return True


# 验证配置（非阻塞式）
try:
    LLMConfig.validate_config()
except Exception as e:
    print(f"LLM Config validation warning: {e}")
