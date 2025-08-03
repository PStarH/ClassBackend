"""
Gamification Service - 游戏化学习系统核心服务
"""
import random
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Max

from .models import (
    LearningCharacter, Achievement, UserAchievement, DailyQuest,
    LearningBadge, UserBadge, Leaderboard, GamificationActivity
)
from apps.authentication.models import User
from apps.learning_plans.models import StudySession


class GamificationService:
    """游戏化系统核心服务"""
    
    def __init__(self):
        self.experience_multipliers = {
            'exercise': 1.0,
            'ai_chat': 0.5,
            'course_lesson': 1.2,
            'project': 2.0,
            'peer_help': 1.5,
            'streak': 0.3
        }
        
        self.difficulty_multipliers = {
            'easy': 0.8,
            'medium': 1.0,
            'hard': 1.5,
            'expert': 2.0
        }

    def get_or_create_character(self, user: User) -> LearningCharacter:
        """获取或创建用户的学习角色"""
        character, created = LearningCharacter.objects.get_or_create(
            user=user,
            defaults={
                'name': f"{user.first_name or 'Code'} Explorer",
                'level': 1,
                'experience_points': 0,
                'coins': 50,  # 新手奖励
                'gems': 5,
                'health': 100,
                'energy': 100,
                'mood': 'motivated'
            }
        )
        
        if created:
            # 为新角色创建初始每日任务
            self._generate_daily_quests(character)
            
            # 记录创建角色活动
            self._log_activity(
                character, 
                'character_created', 
                'Welcome to your learning journey!',
                experience_gained=10,
                coins_gained=50
            )
        
        return character

    def complete_learning_activity(
        self, 
        user: User, 
        activity_type: str, 
        difficulty: str = 'medium',
        duration_minutes: int = 0,
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """完成学习活动并获得奖励"""
        
        character = self.get_or_create_character(user)
        
        # 计算基础经验值
        base_exp = {
            'exercise': 15,
            'ai_chat': 8,
            'course_lesson': 20,
            'project': 50,
            'peer_help': 25,
            'review': 10
        }.get(activity_type, 10)
        
        # 应用难度和时长加成
        difficulty_mult = self.difficulty_multipliers.get(difficulty, 1.0)
        duration_mult = min(2.0, 1 + (duration_minutes / 60))  # 最多2倍加成
        
        total_exp = int(base_exp * difficulty_mult * duration_mult)
        
        # 计算金币奖励
        coins_earned = max(1, total_exp // 5)
        
        # 检查连击奖励
        streak_bonus = self._check_streak_bonus(character)
        total_exp += streak_bonus['experience']
        coins_earned += streak_bonus['coins']
        
        # 更新角色状态
        with transaction.atomic():
            # 添加经验值
            level_up = character.add_experience(total_exp)
            character.coins += coins_earned
            character.total_activities += 1
            
            # 更新每日活动
            self._update_daily_activity(character)
            
            # 检查并更新每日任务进度
            quest_rewards = self._update_daily_quests(character, activity_type)
            
            # 检查成就
            achievement_rewards = self._check_achievements(character, activity_type, additional_data)
            
            # 检查徽章
            badge_rewards = self._check_badges(character, activity_type)
            
            character.save()
        
        # 记录活动
        activity_record = self._log_activity(
            character,
            f"{activity_type}_completed",
            f"Completed {activity_type} activity",
            experience_gained=total_exp,
            coins_gained=coins_earned,
            activity_data=additional_data or {}
        )
        
        # 准备返回结果
        result = {
            'success': True,
            'experience_gained': total_exp,
            'coins_gained': coins_earned,
            'level_up': level_up,
            'new_level': character.level if level_up else None,
            'streak_bonus': streak_bonus,
            'quest_progress': quest_rewards,
            'achievements_unlocked': achievement_rewards,
            'badges_earned': badge_rewards,
            'character_stats': character.get_stats(),
            'activity_id': str(activity_record.id)
        }
        
        return result

    def get_daily_quests(self, user: User) -> List[Dict]:
        """获取用户的每日任务"""
        character = self.get_or_create_character(user)
        today = date.today()
        
        # 获取今天的任务
        quests = DailyQuest.objects.filter(
            user=user,
            assigned_date=today
        ).order_by('difficulty', 'created_at')
        
        # 如果没有今天的任务，生成新的
        if not quests.exists():
            self._generate_daily_quests(character)
            quests = DailyQuest.objects.filter(
                user=user,
                assigned_date=today
            ).order_by('difficulty', 'created_at')
        
        quest_list = []
        for quest in quests:
            quest_list.append({
                'id': str(quest.id),
                'title': quest.title,
                'description': quest.description,
                'type': quest.quest_type,
                'difficulty': quest.difficulty,
                'progress': quest.current_progress,
                'target': quest.target_value,
                'progress_percentage': quest.progress_percentage,
                'is_completed': quest.is_completed,
                'is_claimed': quest.is_claimed,
                'rewards': {
                    'experience': quest.experience_reward,
                    'coins': quest.coin_reward,
                    'bonus': quest.bonus_rewards
                },
                'expires_at': quest.expires_at.isoformat()
            })
        
        return quest_list

    def claim_quest_reward(self, user: User, quest_id: str) -> Dict[str, Any]:
        """领取任务奖励"""
        try:
            quest = DailyQuest.objects.get(id=quest_id, user=user)
            
            if not quest.is_completed:
                return {'success': False, 'error': 'Quest not completed yet'}
            
            if quest.is_claimed:
                return {'success': False, 'error': 'Reward already claimed'}
            
            character = self.get_or_create_character(user)
            
            with transaction.atomic():
                # 添加奖励
                character.add_experience(quest.experience_reward)
                character.coins += quest.coin_reward
                character.save()
                
                # 标记为已领取
                quest.is_claimed = True
                quest.save()
                
                # 记录活动
                self._log_activity(
                    character,
                    'quest_completed',
                    f'Completed quest: {quest.title}',
                    experience_gained=quest.experience_reward,
                    coins_gained=quest.coin_reward
                )
            
            return {
                'success': True,
                'rewards_claimed': {
                    'experience': quest.experience_reward,
                    'coins': quest.coin_reward,
                    'bonus': quest.bonus_rewards
                },
                'character_stats': character.get_stats()
            }
            
        except DailyQuest.DoesNotExist:
            return {'success': False, 'error': 'Quest not found'}

    def get_leaderboard(self, leaderboard_type: str = 'weekly_exp', limit: int = 50) -> List[Dict]:
        """获取排行榜"""
        
        # 计算时间范围
        now = timezone.now()
        if 'weekly' in leaderboard_type:
            start_date = now - timedelta(days=7)
        elif 'monthly' in leaderboard_type:
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=1)
        
        # 根据排行榜类型获取数据
        if leaderboard_type == 'weekly_exp':
            # 获取本周经验排行
            activities = GamificationActivity.objects.filter(
                created_at__gte=start_date
            ).values('user', 'character').annotate(
                total_exp=Sum('experience_gained')
            ).order_by('-total_exp')[:limit]
            
        elif leaderboard_type == 'daily_streak':
            # 获取连击天数排行
            characters = LearningCharacter.objects.order_by('-streak_days')[:limit]
            activities = [
                {
                    'user': char.user_id,
                    'character': char.id,
                    'total_exp': char.streak_days,
                    'character_data': char
                }
                for char in characters
            ]
        
        else:
            activities = []
        
        # 格式化排行榜数据
        leaderboard = []
        for i, activity in enumerate(activities, 1):
            if hasattr(activity, 'get'):
                user_id = activity.get('user')
                score = activity.get('total_exp', 0)
                character_data = activity.get('character_data')
            else:
                user_id = activity['user']
                score = activity['total_exp']
                character_data = None
            
            try:
                user = User.objects.get(id=user_id)
                if not character_data:
                    character = LearningCharacter.objects.get(user=user)
                else:
                    character = character_data
                
                leaderboard.append({
                    'rank': i,
                    'user': {
                        'id': str(user.uuid),
                        'email': user.email,
                        'name': user.first_name or user.email.split('@')[0]
                    },
                    'character': {
                        'name': character.name,
                        'level': character.level,
                        'avatar': f"🎓",  # 可以后续添加头像系统
                    },
                    'score': score,
                    'score_type': leaderboard_type
                })
            except (User.DoesNotExist, LearningCharacter.DoesNotExist):
                continue
        
        return leaderboard

    def get_user_achievements(self, user: User) -> Dict[str, Any]:
        """获取用户成就"""
        character = self.get_or_create_character(user)
        
        # 获取已解锁的成就
        unlocked_achievements = UserAchievement.objects.filter(
            user=user
        ).select_related('achievement').order_by('-unlocked_at')
        
        # 获取可用成就
        all_achievements = Achievement.objects.filter(is_active=True)
        
        unlocked_list = []
        for ua in unlocked_achievements:
            unlocked_list.append({
                'id': str(ua.achievement.id),
                'title': ua.achievement.title,
                'description': ua.achievement.description,
                'icon': ua.achievement.icon,
                'type': ua.achievement.achievement_type,
                'rarity': ua.achievement.rarity,
                'unlocked_at': ua.unlocked_at.isoformat(),
                'progress_data': ua.progress_data
            })
        
        # 计算进度中的成就
        in_progress = []
        unlocked_ids = {ua.achievement.id for ua in unlocked_achievements}
        
        for achievement in all_achievements:
            if achievement.id not in unlocked_ids and not achievement.is_hidden:
                progress = self._calculate_achievement_progress(character, achievement)
                if progress > 0:
                    in_progress.append({
                        'id': str(achievement.id),
                        'title': achievement.title,
                        'description': achievement.description,
                        'icon': achievement.icon,
                        'type': achievement.achievement_type,
                        'rarity': achievement.rarity,
                        'progress': progress,
                        'required_condition': achievement.required_condition
                    })
        
        return {
            'unlocked': unlocked_list,
            'in_progress': in_progress,
            'total_unlocked': len(unlocked_list),
            'total_available': all_achievements.count()
        }

    def _generate_daily_quests(self, character: LearningCharacter):
        """生成每日任务"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        expires_at = timezone.make_aware(datetime.combine(tomorrow, datetime.min.time()))
        
        # 预定义的任务模板
        quest_templates = [
            {
                'title': 'Daily Practice',
                'description': 'Complete 3 coding exercises',
                'type': 'exercise',
                'difficulty': 'medium',
                'target': 3,
                'exp_reward': 30,
                'coin_reward': 15
            },
            {
                'title': 'AI Mentor Chat',
                'description': 'Have a meaningful conversation with your AI teacher',
                'type': 'ai_chat',
                'difficulty': 'easy',
                'target': 1,
                'exp_reward': 20,
                'coin_reward': 10
            },
            {
                'title': 'Study Session',
                'description': 'Study for at least 30 minutes',
                'type': 'study_time',
                'difficulty': 'medium',
                'target': 30,
                'exp_reward': 25,
                'coin_reward': 12
            },
            {
                'title': 'Review & Reflect',
                'description': 'Review previously learned material',
                'type': 'review',
                'difficulty': 'easy',
                'target': 1,
                'exp_reward': 15,
                'coin_reward': 8
            }
        ]
        
        # 随机选择3个任务
        selected_templates = random.sample(quest_templates, 3)
        
        for template in selected_templates:
            DailyQuest.objects.create(
                user=character.user,
                character=character,
                title=template['title'],
                description=template['description'],
                quest_type=template['type'],
                difficulty=template['difficulty'],
                target_value=template['target'],
                experience_reward=template['exp_reward'],
                coin_reward=template['coin_reward'],
                assigned_date=today,
                expires_at=expires_at
            )

    def _update_daily_activity(self, character: LearningCharacter):
        """更新每日活动状态"""
        today = date.today()
        
        if character.last_activity_date != today:
            if character.last_activity_date == today - timedelta(days=1):
                # 连续学习，增加连击
                character.streak_days += 1
                character.max_streak = max(character.max_streak, character.streak_days)
            else:
                # 连击断了
                character.streak_days = 1
            
            character.last_activity_date = today

    def _check_streak_bonus(self, character: LearningCharacter) -> Dict[str, int]:
        """检查连击奖励"""
        streak = character.streak_days
        
        if streak >= 7:
            return {'experience': 10, 'coins': 5}
        elif streak >= 3:
            return {'experience': 5, 'coins': 2}
        else:
            return {'experience': 0, 'coins': 0}

    def _update_daily_quests(self, character: LearningCharacter, activity_type: str) -> List[Dict]:
        """更新每日任务进度"""
        today = date.today()
        quests = DailyQuest.objects.filter(
            user=character.user,
            assigned_date=today,
            is_completed=False
        )
        
        updated_quests = []
        
        for quest in quests:
            if quest.quest_type == activity_type:
                quest.update_progress(1)
                updated_quests.append({
                    'id': str(quest.id),
                    'title': quest.title,
                    'progress': quest.current_progress,
                    'target': quest.target_value,
                    'completed': quest.is_completed
                })
        
        return updated_quests

    def _check_achievements(self, character: LearningCharacter, activity_type: str, additional_data: Optional[Dict]) -> List[Dict]:
        """检查并解锁成就"""
        # 这里可以实现复杂的成就检查逻辑
        # 暂时返回空列表，后续可以扩展
        return []

    def _check_badges(self, character: LearningCharacter, activity_type: str) -> List[Dict]:
        """检查并授予徽章"""
        # 这里可以实现徽章检查逻辑
        # 暂时返回空列表，后续可以扩展
        return []

    def _calculate_achievement_progress(self, character: LearningCharacter, achievement: Achievement) -> float:
        """计算成就进度"""
        condition = achievement.required_condition
        condition_type = condition.get('type')
        required_count = condition.get('count', 1)
        
        if condition_type == 'exercises_completed':
            completed = character.total_activities
            return min(100, (completed / required_count) * 100)
        elif condition_type == 'streak_days':
            return min(100, (character.streak_days / required_count) * 100)
        elif condition_type == 'level_reached':
            return min(100, (character.level / required_count) * 100)
        
        return 0

    def _log_activity(
        self, 
        character: LearningCharacter, 
        activity_type: str, 
        description: str,
        experience_gained: int = 0,
        coins_gained: int = 0,
        gems_gained: int = 0,
        activity_data: Optional[Dict] = None
    ) -> GamificationActivity:
        """记录游戏化活动"""
        
        return GamificationActivity.objects.create(
            user=character.user,
            character=character,
            activity_type=activity_type,
            description=description,
            experience_gained=experience_gained,
            coins_gained=coins_gained,
            gems_gained=gems_gained,
            activity_data=activity_data or {}
        )


# 全局服务实例
_gamification_service = None

def get_gamification_service():
    """获取游戏化服务实例"""
    global _gamification_service
    if _gamification_service is None:
        _gamification_service = GamificationService()
    return _gamification_service