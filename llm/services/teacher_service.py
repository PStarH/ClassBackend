"""
Teacher Service - 教师课程服务
"""
from typing import List, Dict, Any
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser

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


# 全局服务实例
teacher_service = TeacherService()
