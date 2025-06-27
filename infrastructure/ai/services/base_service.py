"""
AI 基础服务 - 提供通用的 LLM 调用功能
"""
import json
import logging
from typing import Any, Dict, Type, Union
from langchain.chains import LLMChain
from langchain_openai import OpenAI as LangChainOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from ..clients.llm_factory import llm_client_factory

logger = logging.getLogger(__name__)


class AIBaseService:
    """AI 基础服务类"""
    
    def __init__(self):
        self.client = llm_client_factory.get_deepseek_client()
        self.model_name = llm_client_factory.get_default_model_name()
        
        # 为 LangChain 创建 LLM 实例
        self.langchain_llm = LangChainOpenAI(
            api_key=self.client.api_key,
            base_url=self.client.base_url,
            model=self.model_name,
            temperature=0.1
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
    
    def _execute_chain_safely(self, chain: LLMChain, **kwargs) -> Dict[str, Any]:
        """
        安全执行 LangChain 并提供回退机制
        
        Args:
            chain: LangChain 链
            **kwargs: 链的输入参数
            
        Returns:
            解析后的 JSON 数据
            
        Raises:
            ValueError: 当无法解析 JSON 时
        """
        try:
            # 使用 LangChain 执行
            result = chain.run(**kwargs)
            cleaned_result = self._clean_json_content(result)
            return json.loads(cleaned_result)
        except Exception as e:
            logger.warning(f"LangChain execution failed: {e}, falling back to OpenAI client")
            return self._fallback_to_openai(chain, **kwargs)
    
    def _fallback_to_openai(self, chain: LLMChain, **kwargs) -> Dict[str, Any]:
        """
        回退到原始 OpenAI 客户端
        
        Args:
            chain: LangChain 链
            **kwargs: 链的输入参数
            
        Returns:
            解析后的 JSON 数据
        """
        try:
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
        except Exception as e:
            logger.error(f"Fallback to OpenAI also failed: {e}")
            raise ValueError(f"Failed to get valid response from AI: {e}")
    
    def _execute_with_pydantic_parser(
        self, 
        chain: LLMChain, 
        parser: PydanticOutputParser,
        **kwargs
    ) -> BaseModel:
        """
        使用 Pydantic 解析器执行链
        
        Args:
            chain: LangChain 链
            parser: Pydantic 输出解析器
            **kwargs: 链的输入参数
            
        Returns:
            解析后的 Pydantic 模型实例
        """
        try:
            result = chain.run(**kwargs)
            return parser.parse(result)
        except Exception as e:
            logger.warning(f"Pydantic parsing failed: {e}, trying raw JSON approach")
            # 回退机制：直接从字典创建模型
            raw_result = self._execute_chain_safely(chain, **kwargs)
            model_class = parser.get_output_schema()
            return model_class(**raw_result)
    
    def _create_simple_completion(
        self, 
        prompt: str, 
        response_format: str = "json"
    ) -> Union[str, Dict[str, Any]]:
        """
        创建简单的文本补全
        
        Args:
            prompt: 提示词
            response_format: 响应格式，'json' 或 'text'
            
        Returns:
            AI 响应
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )
            
            content = response.choices[0].message.content
            
            if response_format == "json":
                cleaned_content = self._clean_json_content(content)
                return json.loads(cleaned_content)
            else:
                return content
                
        except Exception as e:
            logger.error(f"Simple completion failed: {e}")
            raise ValueError(f"Failed to get AI completion: {e}")
    
    def _validate_response_structure(
        self, 
        response: Dict[str, Any], 
        required_fields: list
    ) -> bool:
        """
        验证响应结构
        
        Args:
            response: AI 响应
            required_fields: 必需字段列表
            
        Returns:
            是否有效
        """
        for field in required_fields:
            if field not in response:
                logger.warning(f"Missing required field: {field}")
                return False
        return True
