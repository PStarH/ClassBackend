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
    def __init__(self, index=0.0, title="", children=None, **kwargs):
        self.index = index
        self.title = title
        self.children = children or []
        super().__init__(**kwargs)


class OutlineSection(BaseModel):
    """课程大纲部分"""
    def __init__(self, index="", title="", **kwargs):
        self.index = index
        self.title = title
        super().__init__(**kwargs)


class SectionDetail(BaseModel):
    """章节详细内容"""
    def __init__(self, index="", title="", content="", graphs=None, **kwargs):
        self.index = index
        self.title = title
        self.content = content
        self.graphs = graphs or {}
        super().__init__(**kwargs)


class ChatResponse(BaseModel):
    """聊天响应"""
    def __init__(self, reply="", updates=None, **kwargs):
        self.reply = reply
        self.updates = updates or []
        super().__init__(**kwargs)


class PlanUpdateResponse(BaseModel):
    """计划更新响应"""
    def __init__(self, updates=None, **kwargs):
        self.updates = updates or []
        super().__init__(**kwargs)
