"""
课程管理相关的数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CourseSection(BaseModel):
    """课程章节"""
    index: str = Field(description="章节索引")
    title: str = Field(description="章节标题")


class CourseOutline(BaseModel):
    """课程大纲"""
    topic: str = Field(description="课程主题")
    sections: List[CourseSection] = Field(description="章节列表")
    total_sections: int = Field(description="总章节数")


class SectionDetailRequest(BaseModel):
    """章节详情请求"""
    index: str = Field(description="章节索引")
    title: str = Field(description="章节标题")
    course_context: Optional[str] = Field(None, description="课程上下文")


class GraphDefinition(BaseModel):
    """图表定义"""
    graph_id: str = Field(description="图表ID")
    dot_definition: str = Field(description="DOT语言图表定义")
    description: str = Field(description="图表描述")


class SectionDetail(BaseModel):
    """章节详细内容"""
    index: str = Field(description="章节索引")
    title: str = Field(description="章节标题")
    content: str = Field(description="详细内容，包含图表占位符")
    graphs: Dict[str, str] = Field(default_factory=dict, description="图表定义映射")
    estimated_duration: Optional[int] = Field(None, description="预估学习时长（分钟）")
    learning_objectives: List[str] = Field(default_factory=list, description="学习目标")
    prerequisites: List[str] = Field(default_factory=list, description="前置要求")


class CourseCreationRequest(BaseModel):
    """课程创建请求"""
    topic: str = Field(description="课程主题")
    target_audience: str = Field(default="初学者", description="目标受众")
    difficulty_level: str = Field(default="入门", description="难度级别")
    duration_hours: Optional[int] = Field(None, description="总时长（小时）")


class CourseCreationResponse(BaseModel):
    """课程创建响应"""
    outline: CourseOutline = Field(description="课程大纲")
    creation_status: str = Field(description="创建状态")
    estimated_total_duration: int = Field(description="预估总时长（分钟）")
