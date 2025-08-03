"""
Gamification Learning System Models
游戏化学习系统数据模型
"""
from django.db import models
from django.contrib.auth import get_user_model
from apps.authentication.models import User
import uuid
import json

User = get_user_model()


class LearningCharacter(models.Model):
    """学习角色 - 用户的游戏化学习角色"""
    
    SKILL_FOCUS_CHOICES = [
        ('python', 'Python Programming'),
        ('javascript', 'JavaScript'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('web_dev', 'Web Development'),
        ('data_science', 'Data Science'),
        ('machine_learning', 'Machine Learning'),
        ('algorithms', 'Algorithms & Data Structures'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='character')
    
    # 角色基本信息
    name = models.CharField(max_length=100, default="Code Explorer")
    level = models.PositiveIntegerField(default=1)
    experience_points = models.PositiveIntegerField(default=0)
    total_activities = models.PositiveIntegerField(default=0)
    
    # 技能专精
    current_skill_focus = models.CharField(max_length=20, choices=SKILL_FOCUS_CHOICES, default='python')
    skill_points = models.JSONField(default=dict)  # {'python': 100, 'javascript': 50, ...}
    
    # 游戏统计
    coins = models.PositiveIntegerField(default=0)
    gems = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    max_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # 角色状态
    health = models.PositiveIntegerField(default=100)
    energy = models.PositiveIntegerField(default=100)
    mood = models.CharField(max_length=20, default='motivated')  # motivated, focused, tired, excited
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'learning_character'
        
    def __str__(self):
        return f"{self.name} (Level {self.level})"
    
    def add_experience(self, points):
        """添加经验值并检查升级"""
        self.experience_points += points
        
        # 检查升级 (每级需要 level * 100 经验)
        required_exp = self.level * 100
        while self.experience_points >= required_exp:
            self.experience_points -= required_exp
            self.level += 1
            self.coins += self.level * 10  # 升级奖励金币
            required_exp = self.level * 100
        
        self.save()
        return self.level > (self.level - 1)  # 返回是否升级了
    
    def get_stats(self):
        """获取角色统计信息"""
        return {
            'level': self.level,
            'experience_points': self.experience_points,
            'experience_to_next_level': (self.level * 100) - self.experience_points,
            'coins': self.coins,
            'gems': self.gems,
            'streak_days': self.streak_days,
            'total_activities': self.total_activities,
            'skill_points': self.skill_points,
            'health': self.health,
            'energy': self.energy,
            'mood': self.mood
        }


class Achievement(models.Model):
    """成就系统"""
    
    ACHIEVEMENT_TYPES = [
        ('learning', 'Learning Milestone'),
        ('streak', 'Streak Achievement'),
        ('social', 'Social Achievement'),
        ('mastery', 'Skill Mastery'),
        ('challenge', 'Challenge Completion'),
        ('special', 'Special Event'),
    ]
    
    RARITY_CHOICES = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 成就基本信息
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='🏆')  # Emoji icon
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common')
    
    # 解锁条件
    required_condition = models.JSONField()  # {'type': 'exercises_completed', 'count': 10}
    
    # 奖励
    experience_reward = models.PositiveIntegerField(default=0)
    coin_reward = models.PositiveIntegerField(default=0)
    gem_reward = models.PositiveIntegerField(default=0)
    
    # 成就状态
    is_active = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)  # 隐藏成就
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'achievement'
        
    def __str__(self):
        return f"{self.icon} {self.title}"


class UserAchievement(models.Model):
    """用户获得的成就"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(LearningCharacter, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    
    unlocked_at = models.DateTimeField(auto_now_add=True)
    progress_data = models.JSONField(default=dict)  # 解锁时的进度数据
    
    class Meta:
        db_table = 'user_achievement'
        unique_together = ['user', 'achievement']
        
    def __str__(self):
        return f"{self.user.email} - {self.achievement.title}"


class DailyQuest(models.Model):
    """每日任务系统"""
    
    QUEST_TYPES = [
        ('exercise', 'Complete Exercises'),
        ('ai_chat', 'Chat with AI Teacher'),
        ('study_time', 'Study for X Minutes'),
        ('streak', 'Maintain Learning Streak'),
        ('help_others', 'Help Other Students'),
        ('review', 'Review Previous Material'),
    ]
    
    DIFFICULTY_LEVELS = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(LearningCharacter, on_delete=models.CASCADE)
    
    # 任务信息
    title = models.CharField(max_length=200)
    description = models.TextField()
    quest_type = models.CharField(max_length=20, choices=QUEST_TYPES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_LEVELS, default='medium')
    
    # 任务目标和进度
    target_value = models.PositiveIntegerField()  # 目标值
    current_progress = models.PositiveIntegerField(default=0)  # 当前进度
    
    # 奖励
    experience_reward = models.PositiveIntegerField()
    coin_reward = models.PositiveIntegerField()
    bonus_rewards = models.JSONField(default=list)  # 额外奖励
    
    # 任务状态
    is_completed = models.BooleanField(default=False)
    is_claimed = models.BooleanField(default=False)
    
    # 时间管理
    assigned_date = models.DateField()
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'daily_quest'
        unique_together = ['user', 'quest_type', 'assigned_date']
        
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    @property
    def progress_percentage(self):
        """获取进度百分比"""
        if self.target_value == 0:
            return 0
        return min(100, (self.current_progress / self.target_value) * 100)
    
    def update_progress(self, increment=1):
        """更新任务进度"""
        self.current_progress = min(self.target_value, self.current_progress + increment)
        if self.current_progress >= self.target_value and not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()
        return self.is_completed


class LearningBadge(models.Model):
    """学习徽章系统"""
    
    BADGE_CATEGORIES = [
        ('skill', 'Skill Mastery'),
        ('consistency', 'Consistency'),
        ('challenge', 'Challenge'),
        ('community', 'Community'),
        ('achievement', 'Special Achievement'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 徽章信息
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='🎖️')
    category = models.CharField(max_length=20, choices=BADGE_CATEGORIES)
    
    # 获得条件
    unlock_condition = models.JSONField()
    
    # 徽章等级（可选）
    level = models.PositiveIntegerField(default=1)
    is_tiered = models.BooleanField(default=False)  # 是否有多个等级
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'learning_badge'
        
    def __str__(self):
        return f"{self.icon} {self.name}"


class UserBadge(models.Model):
    """用户获得的徽章"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    badge = models.ForeignKey(LearningBadge, on_delete=models.CASCADE)
    
    # 获得信息
    earned_at = modules.DateTimeField(auto_now_add=True)
    current_level = models.PositiveIntegerField(default=1)
    progress_data = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'user_badge'
        unique_together = ['user', 'badge']
        
    def __str__(self):
        return f"{self.user.email} - {self.badge.name} (Level {self.current_level})"


class Leaderboard(models.Model):
    """排行榜系统"""
    
    LEADERBOARD_TYPES = [
        ('weekly_exp', 'Weekly Experience'),
        ('monthly_exp', 'Monthly Experience'),
        ('daily_streak', 'Daily Streak'),
        ('skill_points', 'Skill Points'),
        ('achievements', 'Total Achievements'),
        ('exercises_completed', 'Exercises Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(LearningCharacter, on_delete=models.CASCADE)
    
    # 排行榜信息
    leaderboard_type = models.CharField(max_length=30, choices=LEADERBOARD_TYPES)
    score = models.PositiveIntegerField()
    rank = models.PositiveIntegerField()
    
    # 时间周期
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # 元数据
    metadata = models.JSONField(default=dict)  # 额外的排行榜数据
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leaderboard'
        unique_together = ['user', 'leaderboard_type', 'period_start']
        ordering = ['rank']
        
    def __str__(self):
        return f"#{self.rank} {self.user.email} - {self.leaderboard_type}"


class GamificationActivity(models.Model):
    """游戏化活动记录"""
    
    ACTIVITY_TYPES = [
        ('exercise_completed', 'Exercise Completed'),
        ('ai_chat', 'AI Teacher Chat'),
        ('course_lesson', 'Course Lesson'),
        ('project_completed', 'Project Completed'),
        ('peer_help', 'Helped Another Student'),
        ('streak_milestone', 'Streak Milestone'),
        ('level_up', 'Level Up'),
        ('badge_earned', 'Badge Earned'),
        ('achievement_unlocked', 'Achievement Unlocked'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    character = models.ForeignKey(LearningCharacter, on_delete=models.CASCADE)
    
    # 活动信息
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()
    
    # 奖励信息
    experience_gained = models.PositiveIntegerField(default=0)
    coins_gained = models.PositiveIntegerField(default=0)
    gems_gained = models.PositiveIntegerField(default=0)
    
    # 活动详情
    activity_data = models.JSONField(default=dict)  # 具体的活动数据
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gamification_activity'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} - {self.activity_type} (+{self.experience_gained} XP)"