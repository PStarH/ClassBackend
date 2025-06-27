"""
Teacher Service - 教师课程服务
"""
import json
from typing import List, Dict, Any

try:
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from ..core.base_service import LLMBaseService
from ..core.prompts import CREATE_OUTLINE_PROMPT, SECTION_DETAIL_PROMPT
from ..core.models import OutlineSection, SectionDetail


class TeacherService(LLMBaseService):
    """教师课程服务"""
    
    def create_outline(self, topic: str) -> List[Dict[str, Any]]:
        """
        生成课程大纲
        
        Args:
            topic: 课程主题
            
        Returns:
            课程大纲的 JSON 数据
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = CREATE_OUTLINE_PROMPT.format(topic=topic)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的大纲结构
                result = [{"index": "1", "title": f"{topic} - 基础概念"}]
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=CREATE_OUTLINE_PROMPT
            )
            result = self._execute_chain_with_fallback(chain, topic=topic)
        
        return result
    
    def generate_section_detail(self, index: str, title: str) -> Dict[str, Any]:
        """
        生成章节详细内容
        
        Args:
            index: 章节索引
            title: 章节标题
            
        Returns:
            章节详细内容的 JSON 数据
        """
        if not self.langchain_llm or not LANGCHAIN_AVAILABLE:
            # 使用简单的OpenAI客户端
            prompt = SECTION_DETAIL_PROMPT.format(index=index, title=title)
            response = self.simple_chat(prompt)
            try:
                cleaned_response = self._clean_json_content(response)
                result = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # 如果解析失败，返回简单的内容结构
                result = {
                    "index": index,
                    "title": title,
                    "content": f"这是关于{title}的详细内容。",
                    "graphs": {}
                }
        else:
            # 使用LangChain
            chain = LLMChain(
                llm=self.langchain_llm,
                prompt=SECTION_DETAIL_PROMPT
            )
            result = self._execute_chain_with_fallback(
                chain,
                index=index,
                title=title
            )
        
        return result
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        from ..core.client import llm_factory
        return llm_factory.is_available()


# 全局服务实例
try:
    teacher_service = TeacherService()
except Exception as e:
    print(f"Warning: Failed to initialize teacher service: {e}")
    teacher_service = None
