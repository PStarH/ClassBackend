"""
LLM Base Service - 提供通用的 LLM 调用服务
"""
import json
import re
from typing import Any, Dict, Optional, Type

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


class LLMBaseService:
    """LLM 基础服务类"""
    
    def __init__(self):
        if not llm_factory.is_available():
            raise RuntimeError("LLM client is not available")
            
        from .config import LLMConfig
        self.client = llm_factory.get_client()
        self.model_name = llm_factory.get_model_name()
        
        # 为 LangChain 创建 LLM 实例（如果可用）
        if LANGCHAIN_AVAILABLE:
            self.langchain_llm = LangChainOpenAI(
                api_key=LLMConfig.API_KEY,
                base_url=LLMConfig.BASE_URL,
                model=LLMConfig.MODEL_NAME,
                temperature=LLMConfig.TEMPERATURE
            )
        else:
            self.langchain_llm = None
    
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
        if not LANGCHAIN_AVAILABLE or not self.langchain_llm:
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
