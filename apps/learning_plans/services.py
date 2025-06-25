"""
学习计划服务层
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db import transaction, models
from django.utils import timezone

from infrastructure.ai.services.base_service import AIBaseService
from infrastructure.ai.schemas.learning_plan_schemas import (
    LearningPlanGenerationRequest,
    LearningPlanGenerationResponse
)
from .models import LearningPlan, LearningGoal, LearningPlanGoal, StudySession

logger = logging.getLogger(__name__)


class LearningGoalService:
    """学习目标服务"""
    
    @staticmethod
    def create_goal(data: Dict[str, Any]) -> LearningGoal:
        """创建学习目标"""
        try:
            goal = LearningGoal.objects.create(**data)
            logger.info(f"学习目标创建成功: {goal.title}")
            return goal
        except Exception as e:
            logger.error(f"学习目标创建失败: {str(e)}")
            raise
    
    @staticmethod
    def get_goals_by_difficulty(difficulty: str) -> List[LearningGoal]:
        """根据难度获取目标"""
        return LearningGoal.objects.filter(difficulty=difficulty)
    
    @staticmethod
    def get_goals_by_type(goal_type: str) -> List[LearningGoal]:
        """根据类型获取目标"""
        return LearningGoal.objects.filter(goal_type=goal_type)
    
    @staticmethod
    def search_goals(query: str) -> List[LearningGoal]:
        """搜索目标"""
        return LearningGoal.objects.filter(
            models.Q(title__icontains=query) |
            models.Q(description__icontains=query)
        )


class LearningPlanService:
    """学习计划服务"""
    
    @staticmethod
    def create_plan(user: User, data: Dict[str, Any]) -> LearningPlan:
        """创建学习计划"""
        try:
            with transaction.atomic():
                goal_ids = data.pop('goal_ids', [])
                plan = LearningPlan.objects.create(user=user, **data)
                
                if goal_ids:
                    goals = LearningGoal.objects.filter(id__in=goal_ids)
                    for i, goal in enumerate(goals):
                        LearningPlanGoal.objects.create(
                            learning_plan=plan,
                            learning_goal=goal,
                            order=i + 1
                        )
                    
                    # 计算总预估时长
                    total_hours = sum(goal.estimated_hours for goal in goals)
                    plan.total_estimated_hours = total_hours
                    plan.save()
                
                logger.info(f"学习计划创建成功: {plan.title}")
                return plan
        except Exception as e:
            logger.error(f"学习计划创建失败: {str(e)}")
            raise
    
    @staticmethod
    def get_user_plans(user: User, status: Optional[str] = None) -> List[LearningPlan]:
        """获取用户学习计划"""
        queryset = LearningPlan.objects.filter(user=user, is_deleted=False)
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @staticmethod
    def update_plan_status(plan: LearningPlan, status: str) -> LearningPlan:
        """更新计划状态"""
        try:
            plan.status = status
            if status == 'completed':
                plan.actual_end_date = timezone.now().date()
            plan.save()
            logger.info(f"学习计划状态更新成功: {plan.title} -> {status}")
            return plan
        except Exception as e:
            logger.error(f"学习计划状态更新失败: {str(e)}")
            raise
    
    @staticmethod
    def add_goal_to_plan(plan: LearningPlan, goal: LearningGoal, order: Optional[int] = None) -> LearningPlanGoal:
        """向计划添加目标"""
        try:
            if order is None:
                order = plan.learningplangoal_set.count() + 1
            
            plan_goal = LearningPlanGoal.objects.create(
                learning_plan=plan,
                learning_goal=goal,
                order=order
            )
            
            # 更新总预估时长
            plan.total_estimated_hours += goal.estimated_hours
            plan.save()
            
            logger.info(f"目标添加到计划成功: {goal.title} -> {plan.title}")
            return plan_goal
        except Exception as e:
            logger.error(f"目标添加到计划失败: {str(e)}")
            raise
    
    @staticmethod
    def complete_goal_in_plan(plan_goal: LearningPlanGoal, actual_hours: int, notes: str = "") -> LearningPlanGoal:
        """完成计划中的目标"""
        try:
            plan_goal.status = 'completed'
            plan_goal.actual_hours = actual_hours
            plan_goal.completion_date = timezone.now()
            plan_goal.notes = notes
            plan_goal.save()
            
            # 检查是否所有目标都完成，更新计划状态
            plan = plan_goal.learning_plan
            if not plan.learningplangoal_set.exclude(status='completed').exists():
                plan.status = 'completed'
                plan.actual_end_date = timezone.now().date()
                plan.save()
            
            logger.info(f"计划目标完成: {plan_goal.learning_goal.title}")
            return plan_goal
        except Exception as e:
            logger.error(f"计划目标完成失败: {str(e)}")
            raise
    
    @staticmethod
    def get_plan_statistics(plan: LearningPlan) -> Dict[str, Any]:
        """获取计划统计信息"""
        plan_goals = plan.learningplangoal_set.all()
        total_goals = plan_goals.count()
        completed_goals = plan_goals.filter(status='completed').count()
        in_progress_goals = plan_goals.filter(status='in_progress').count()
        
        total_actual_hours = sum(pg.actual_hours for pg in plan_goals)
        total_study_sessions = StudySession.objects.filter(learning_plan=plan).count()
        
        return {
            'total_goals': total_goals,
            'completed_goals': completed_goals,
            'in_progress_goals': in_progress_goals,
            'progress_percentage': plan.progress_percentage,
            'total_estimated_hours': plan.total_estimated_hours,
            'total_actual_hours': total_actual_hours,
            'total_study_sessions': total_study_sessions,
            'efficiency_ratio': (
                total_actual_hours / plan.total_estimated_hours 
                if plan.total_estimated_hours > 0 else 0
            )
        }


class StudySessionService:
    """学习会话服务"""
    
    @staticmethod
    def create_session(data: Dict[str, Any]) -> StudySession:
        """创建学习会话"""
        try:
            session = StudySession.objects.create(**data)
            logger.info(f"学习会话创建成功: {session.id}")
            return session
        except Exception as e:
            logger.error(f"学习会话创建失败: {str(e)}")
            raise
    
    @staticmethod
    def end_session(session: StudySession, end_time: datetime, 
                   effectiveness_rating: Optional[int] = None, notes: str = "") -> StudySession:
        """结束学习会话"""
        try:
            session.end_time = end_time
            session.duration_minutes = int(
                (end_time - session.start_time).total_seconds() / 60
            )
            if effectiveness_rating:
                session.effectiveness_rating = effectiveness_rating
            if notes:
                session.notes = notes
            session.save()
            
            logger.info(f"学习会话结束: {session.id}, 时长: {session.duration_minutes}分钟")
            return session
        except Exception as e:
            logger.error(f"学习会话结束失败: {str(e)}")
            raise
    
    @staticmethod
    def get_user_sessions(user: User, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> List[StudySession]:
        """获取用户学习会话"""
        queryset = StudySession.objects.filter(learning_plan__user=user)
        
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)
        
        return queryset
    
    @staticmethod
    def get_session_statistics(user: User, days: int = 30) -> Dict[str, Any]:
        """获取学习会话统计"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        sessions = StudySessionService.get_user_sessions(
            user, start_date, end_date
        )
        
        total_sessions = sessions.count()
        total_minutes = sum(s.duration_minutes for s in sessions)
        avg_session_minutes = total_minutes / total_sessions if total_sessions > 0 else 0
        
        # 按日期分组统计
        daily_stats = {}
        for session in sessions:
            date_key = session.start_time.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'sessions': 0,
                    'minutes': 0,
                    'effectiveness': []
                }
            daily_stats[date_key]['sessions'] += 1
            daily_stats[date_key]['minutes'] += session.duration_minutes
            if session.effectiveness_rating:
                daily_stats[date_key]['effectiveness'].append(session.effectiveness_rating)
        
        # 计算平均效果评分
        all_ratings = [s.effectiveness_rating for s in sessions if s.effectiveness_rating]
        avg_effectiveness = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        
        return {
            'total_sessions': total_sessions,
            'total_hours': round(total_minutes / 60, 2),
            'avg_session_minutes': round(avg_session_minutes, 2),
            'avg_effectiveness_rating': round(avg_effectiveness, 2),
            'daily_stats': daily_stats,
            'period_days': days
        }


class AILearningPlanService(AIBaseService):
    """AI学习计划生成服务"""
    
    def __init__(self):
        super().__init__()
        self.model_name = "gpt-4"
    
    def generate_learning_plan(self, request: LearningPlanGenerationRequest) -> LearningPlanGenerationResponse:
        """生成AI学习计划"""
        try:
            # 构建提示词
            prompt = self._build_learning_plan_prompt(request)
            
            # 调用AI生成
            response = self._create_simple_completion(prompt, "json")
            
            # 解析响应
            parsed_response = self._parse_learning_plan_response(response)
            
            logger.info(f"AI学习计划生成成功，包含 {len(parsed_response.recommended_goals)} 个目标")
            return parsed_response
            
        except Exception as e:
            logger.error(f"AI学习计划生成失败: {str(e)}")
            raise
    
    def _build_learning_plan_prompt(self, request: LearningPlanGenerationRequest) -> str:
        """构建学习计划生成提示词"""
        prompt = f"""
        作为一名专业的学习顾问和教育专家，请为用户制定一个个性化的学习计划。

        用户信息：
        - 学习目标：{', '.join(request.learning_goals)}
        - 当前水平：{request.current_level}
        - 每周可用时间：{request.available_hours_per_week}小时
        - 计划学习周数：{request.target_duration_weeks}周
        - 学习风格：{request.learning_style}
        - 特殊要求：{request.specific_requirements or '无'}

        请生成一个结构化的学习计划，包含以下内容：

        1. 计划标题和描述
        2. 预估总学习时长
        3. 推荐的学习目标列表（包括标题、描述、难度、预估时长、顺序）
        4. 每周学习安排
        5. 重要里程碑
        6. 推荐的学习资源
        7. 学习技巧和策略

        请确保计划：
        - 符合用户的时间安排和能力水平
        - 目标循序渐进，有逻辑性
        - 考虑用户的学习风格
        - 实用且可执行
        - 包含具体的时间安排和检查点

        请以JSON格式返回结果。
        """
        return prompt
    
    def _parse_learning_plan_response(self, response: Dict[str, Any]) -> LearningPlanGenerationResponse:
        """解析AI响应为结构化数据"""
        try:
            return LearningPlanGenerationResponse(
                plan_title=response.get('plan_title', ''),
                plan_description=response.get('plan_description', ''),
                estimated_total_hours=response.get('estimated_total_hours', 0),
                recommended_goals=response.get('recommended_goals', []),
                weekly_schedule=response.get('weekly_schedule', {}),
                milestones=response.get('milestones', []),
                resources=response.get('resources', []),
                tips_and_strategies=response.get('tips_and_strategies', [])
            )
        except Exception as e:
            logger.error(f"AI响应解析失败: {str(e)}")
            # 返回默认响应
            return LearningPlanGenerationResponse(
                plan_title="个人学习计划",
                plan_description="基于您的需求定制的学习计划",
                estimated_total_hours=40,
                recommended_goals=[],
                weekly_schedule={},
                milestones=[],
                resources=[],
                tips_and_strategies=[]
            )
    
    def optimize_learning_plan(self, plan: LearningPlan, 
                                   performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于学习表现优化学习计划"""
        try:
            # 分析学习表现
            statistics = LearningPlanService.get_plan_statistics(plan)
            
            prompt = f"""
            基于用户的学习表现数据，请提供学习计划优化建议：

            当前计划：{plan.title}
            进度：{statistics['progress_percentage']}%
            完成目标：{statistics['completed_goals']}/{statistics['total_goals']}
            实际学习时长：{statistics['total_actual_hours']}小时
            预估时长：{statistics['total_estimated_hours']}小时
            效率比：{statistics['efficiency_ratio']}

            学习表现数据：
            {performance_data}

            请提供：
            1. 计划调整建议
            2. 学习方法优化
            3. 时间安排调整
            4. 目标难度调整
            5. 激励措施建议
            """
            
            response = self._create_simple_completion(prompt, "text")
            
            logger.info(f"学习计划优化建议生成成功: {plan.title}")
            return {"optimization_suggestions": response}
            
        except Exception as e:
            logger.error(f"学习计划优化失败: {str(e)}")
            raise
