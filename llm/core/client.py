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
            # 准备基础参数
            base_params = {
                'api_key': LLMConfig.API_KEY
            }
            
            # 只在有值时添加可选参数
            if LLMConfig.BASE_URL:
                base_params['base_url'] = LLMConfig.BASE_URL
                
            try:
                self._client = OpenAI(**base_params)
            except (TypeError, ValueError) as e:
                # 兼容性处理：只使用必需参数
                print(f"Warning: OpenAI client initialization with full params failed: {e}")
                try:
                    self._client = OpenAI(api_key=LLMConfig.API_KEY)
                except Exception as e2:
                    print(f"Error: Even minimal OpenAI client initialization failed: {e2}")
                    raise
        return self._client
    
    def get_async_client(self):
        """获取异步 OpenAI 客户端实例"""
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package is not available")
        
        if not LLMConfig.API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
            
        if self._async_client is None:
            # 准备基础参数
            base_params = {
                'api_key': LLMConfig.API_KEY
            }
            
            # 只在有值时添加可选参数
            if LLMConfig.BASE_URL:
                base_params['base_url'] = LLMConfig.BASE_URL
                
            try:
                self._async_client = AsyncOpenAI(**base_params)
            except (TypeError, ValueError) as e:
                # 兼容性处理：只使用必需参数
                print(f"Warning: AsyncOpenAI client initialization with full params failed: {e}")
                try:
                    self._async_client = AsyncOpenAI(api_key=LLMConfig.API_KEY)
                except Exception as e2:
                    print(f"Error: Even minimal AsyncOpenAI client initialization failed: {e2}")
                    raise
        return self._async_client

    def get_model_name(self):
        """获取模型名称"""
        return LLMConfig.MODEL_NAME
    
    def is_available(self):
        """检查AI服务是否可用"""
        return OPENAI_AVAILABLE and bool(LLMConfig.API_KEY)


# 全局实例
llm_factory = LLMClientFactory()
