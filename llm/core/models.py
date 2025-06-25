"""
Pydantic Models - 结构化输出模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PlanNode(BaseModel):
    """学习计划节点"""
    index: float = Field(description="节点索引")
    title: str = Field(description="节点标题")
    children: List['PlanNode'] = Field(default_factory=list, description="子节点")


class OutlineSection(BaseModel):
    """课程大纲部分"""
    index: str = Field(description="章节索引")
    title: str = Field(description="章节标题")


class SectionDetail(BaseModel):
    """章节详细内容"""
    index: str = Field(description="章节索引")
    title: str = Field(description="章节标题")
    content: str = Field(description="详细内容，包含图表占位符")
    graphs: Dict[str, str] = Field(default_factory=dict, description="图表定义")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str = Field(description="回复内容")
    updates: List[PlanNode] = Field(default_factory=list, description="计划更新部分")


class PlanUpdateResponse(BaseModel):
    """计划更新响应"""
    updates: List[PlanNode] = Field(description="需要更新的计划节点")


# 让 PlanNode 支持递归引用
PlanNode.model_rebuild()
