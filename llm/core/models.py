"""
Pydantic Models - 结构化输出模型
"""
from typing import List, Dict, Any, Optional

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    # 简单的模型基类实现
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        def dict(self):
            return {k: v for k, v in self.__dict__.items()}
    
    def Field(**kwargs):
        return None


class PlanNode(BaseModel):
    """学习计划节点"""
    if PYDANTIC_AVAILABLE:
        index: float = Field(default=0.0, description="节点索引")
        title: str = Field(default="", description="节点标题")
        children: List['PlanNode'] = Field(default_factory=list, description="子节点")
    else:
        def __init__(self, index=0.0, title="", children=None, **kwargs):
            self.index = index
            self.title = title
            self.children = children or []
            super().__init__(**kwargs)


class OutlineSection(BaseModel):
    """课程大纲部分"""
    if PYDANTIC_AVAILABLE:
        index: str = Field(default="", description="大纲索引")
        title: str = Field(default="", description="大纲标题")
    else:
        def __init__(self, index="", title="", **kwargs):
            self.index = index
            self.title = title
            super().__init__(**kwargs)


class SectionDetail(BaseModel):
    """章节详细内容"""
    if PYDANTIC_AVAILABLE:
        index: str = Field(default="", description="章节索引")
        title: str = Field(default="", description="章节标题")
        content: str = Field(default="", description="章节内容")
        graphs: Dict[str, Any] = Field(default_factory=dict, description="图表信息")
    else:
        def __init__(self, index="", title="", content="", graphs=None, **kwargs):
            self.index = index
            self.title = title
            self.content = content
            self.graphs = graphs or {}
            super().__init__(**kwargs)


class ChatResponse(BaseModel):
    """聊天响应"""
    if PYDANTIC_AVAILABLE:
        reply: str = Field(default="", description="回复内容")
        updates: List[Any] = Field(default_factory=list, description="更新内容")
    else:
        def __init__(self, reply="", updates=None, **kwargs):
            self.reply = reply
            self.updates = updates or []
            super().__init__(**kwargs)


class PlanUpdateResponse(BaseModel):
    """计划更新响应"""
    if PYDANTIC_AVAILABLE:
        updates: List[Any] = Field(default_factory=list, description="更新列表")
    else:
        def __init__(self, updates=None, **kwargs):
            self.updates = updates or []
            super().__init__(**kwargs)


class ExerciseOption(BaseModel):
    """练习题选项"""
    if PYDANTIC_AVAILABLE:
        id: str = Field(default="", description="选项ID")
        text: str = Field(default="", description="选项内容")
    else:
        def __init__(self, id="", text="", **kwargs):
            self.id = id
            self.text = text
            super().__init__(**kwargs)


class Exercise(BaseModel):
    """单个练习题"""
    if PYDANTIC_AVAILABLE:
        id: str = Field(default="", description="题目ID")
        question: str = Field(default="", description="题目内容")
        type: str = Field(default="multiple_choice", description="题目类型")
        options: List[ExerciseOption] = Field(default_factory=list, description="选项列表")
        correct_answer: str = Field(default="", description="正确答案")
        explanation: str = Field(default="", description="答案解析")
        difficulty: int = Field(default=5, description="难度等级")
        points: int = Field(default=10, description="分值")
    else:
        def __init__(self, id="", question="", type="multiple_choice", options=None, 
                     correct_answer="", explanation="", difficulty=5, points=10, **kwargs):
            self.id = id
            self.question = question
            self.type = type
            self.options = options or []
            self.correct_answer = correct_answer
            self.explanation = explanation
            self.difficulty = difficulty
            self.points = points
            super().__init__(**kwargs)


class ExerciseResponse(BaseModel):
    """练习题响应"""
    if PYDANTIC_AVAILABLE:
        exercises: List[Exercise] = Field(default_factory=list, description="练习题列表")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    else:
        def __init__(self, exercises=None, metadata=None, **kwargs):
            self.exercises = exercises or []
            self.metadata = metadata or {}
            super().__init__(**kwargs)
