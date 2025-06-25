"""
LLM Base Service - 提供通用的 LLM 调用服务
"""
import json
import re
from typing import Any, Dict, Optional, Type
from langchain.chains import LLMChain
from langchain_openai import OpenAI as LangChainOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from .client import llm_factory
from .models import PlanNode, OutlineSection, SectionDetail, ChatResponse


class LLMBaseService:
    """LLM 基础服务类"""
    
    def __init__(self):
        from .config import LLMConfig
        self.client = llm_factory.get_client()
        self.model_name = llm_factory.get_model_name()
        # 为 LangChain 创建 LLM 实例
        self.langchain_llm = LangChainOpenAI(
            api_key=LLMConfig.API_KEY,
            base_url=LLMConfig.BASE_URL,
            model=LLMConfig.MODEL_NAME,
            temperature=LLMConfig.TEMPERATURE
        )
    
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
    
    def _execute_chain_with_fallback(self, chain: LLMChain, **kwargs) -> Dict[str, Any]:
        """执行 LangChain 并提供回退机制"""
        try:
            # 使用 LangChain 执行
            result = chain.run(**kwargs)
            cleaned_result = self._clean_json_content(result)
            return json.loads(cleaned_result)
        except Exception as e:
            # 回退到原始 OpenAI 客户端
            print(f"LangChain execution failed: {e}, falling back to OpenAI client")
            return self._fallback_to_openai(chain, **kwargs)
    
    def _fallback_to_openai(self, chain: LLMChain, **kwargs) -> Dict[str, Any]:
        """回退到原始 OpenAI 客户端"""
        # 格式化提示词
        formatted_prompt = chain.prompt.format(**kwargs)
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": formatted_prompt}
            ],
            stream=False
        )
        
        content = response.choices[0].message.content
        cleaned_content = self._clean_json_content(content)
        return json.loads(cleaned_content)
    
    def _execute_with_parser(
        self, 
        chain: LLMChain, 
        parser: PydanticOutputParser,
        **kwargs
    ) -> BaseModel:
        """使用 Pydantic 解析器执行链"""
        try:
            result = chain.run(**kwargs)
            return parser.parse(result)
        except Exception:
            # 回退机制
            raw_result = self._execute_chain_with_fallback(chain, **kwargs)
            # 尝试直接从字典创建模型
            model_class = parser.get_output_schema()
            return model_class(**raw_result)
