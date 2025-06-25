"""
学习计划相关的数据模型
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LearningPlanNode(BaseModel):
    """学习计划节点"""
    index: float = Field(description="节点索引，支持嵌套编号如 1.1, 1.2")
    title: str = Field(description="节点标题")
    children: List['LearningPlanNode'] = Field(default_factory=list, description="子节点列表")
    
    class Config:
        json_encoders = {
            float: lambda v: v if v % 1 != 0 else int(v)  # 整数显示为整数
        }


class LearningPlanResponse(BaseModel):
    """学习计划响应"""
    plan: List[LearningPlanNode] = Field(description="学习计划树")
    total_nodes: int = Field(description="总节点数")
    max_depth: int = Field(description="最大深度")


class PlanUpdateRequest(BaseModel):
    """计划更新请求"""
    current_plan: Dict[str, Any] = Field(description="当前学习计划")
    feedback_content: str = Field(description="反馈内容")
    feedback_source: str = Field(default="teacher", description="反馈来源")


class PlanUpdateResponse(BaseModel):
    """计划更新响应"""
    updates: List[LearningPlanNode] = Field(description="需要更新的计划节点")
    change_summary: str = Field(description="变更摘要")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(description="用户消息")
    current_plan: Dict[str, Any] = Field(description="当前学习计划")
    session_id: Optional[str] = Field(None, description="会话ID")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str = Field(description="AI回复内容")
    updates: List[LearningPlanNode] = Field(default_factory=list, description="计划更新部分")
    has_plan_changes: bool = Field(default=False, description="是否有计划变更")


# 新增的学习计划生成相关模型
class LearningPlanGenerationRequest(BaseModel):
    """学习计划生成请求"""
    learning_goals: List[str] = Field(description="学习目标列表")
    current_level: str = Field(default="beginner", description="当前水平")
    available_hours_per_week: int = Field(default=10, description="每周可用学习时间（小时）")
    target_duration_weeks: int = Field(default=12, description="目标学习周数")
    learning_style: str = Field(default="mixed", description="学习风格")
    specific_requirements: str = Field(default="", description="特殊要求或偏好")


class LearningPlanGenerationResponse(BaseModel):
    """学习计划生成响应"""
    plan_title: str = Field(description="计划标题")
    plan_description: str = Field(description="计划描述")
    estimated_total_hours: int = Field(description="预估总学习时长")
    recommended_goals: List[Dict[str, Any]] = Field(description="推荐的学习目标")
    weekly_schedule: Dict[str, Any] = Field(description="每周学习安排")
    milestones: List[Dict[str, Any]] = Field(description="重要里程碑")
    resources: List[Dict[str, Any]] = Field(description="推荐的学习资源")
    tips_and_strategies: List[str] = Field(description="学习技巧和策略")


# 让 LearningPlanNode 支持递归引用
LearningPlanNode.model_rebuild()
