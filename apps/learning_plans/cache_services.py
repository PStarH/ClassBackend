"""
学习统计缓存服务 - 使用 Redis 缓存热点数据
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.core.cache import cache
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from django.conf import settings

from .models import StudySession
from apps.courses.models import CourseProgress

logger = logging.getLogger(__name__)


class LearningStatsCacheService:
    """学习统计缓存服务"""
    
    # 缓存键前缀
    CACHE_PREFIX = 'learning_stats'
    
    # 缓存过期时间（秒）
    CACHE_TIMEOUTS = {
        'user_daily_stats': 300,        # 5分钟
        'user_weekly_stats': 900,       # 15分钟
        'user_monthly_stats': 1800,     # 30分钟
        'user_session_analytics': 600,  # 10分钟
        'global_stats': 3600,           # 1小时
        'hot_data': 180,                # 3分钟
    }
    
    @classmethod
    def _get_cache_key(cls, key_type: str, user_id: str = None, **kwargs) -> str:
        """生成缓存键"""
        if user_id:
            base_key = f"{cls.CACHE_PREFIX}:{key_type}:user_{user_id}"
        else:
            base_key = f"{cls.CACHE_PREFIX}:{key_type}"
        
        # 添加额外参数
        if kwargs:
            params = "_".join([f"{k}_{v}" for k, v in sorted(kwargs.items())])
            base_key += f":{params}"
        
        return base_key
    
    @classmethod
    def get_user_daily_stats(cls, user_id: str, date: datetime = None) -> Dict[str, Any]:
        """获取用户日统计（带缓存）"""
        if not date:
            date = timezone.now().date()
        
        cache_key = cls._get_cache_key('user_daily_stats', user_id, date=date.isoformat())
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"从缓存获取用户日统计: {user_id}")
            return json.loads(cached_data)
        
        # 计算统计数据
        from django.utils import timezone as tz
        start_time = tz.make_aware(datetime.combine(date, datetime.min.time()))
        end_time = tz.make_aware(datetime.combine(date, datetime.max.time()))
        
        sessions = StudySession.objects.filter(
            user_id=user_id,
            start_time__range=[start_time, end_time]
        )
        
        stats = {
            'date': date.isoformat(),
            'total_sessions': sessions.count(),
            'total_duration': sessions.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0,
            'avg_effectiveness': sessions.aggregate(Avg('effectiveness_rating'))['effectiveness_rating__avg'] or 0,
            'completed_sessions': sessions.filter(end_time__isnull=False).count(),
            'active_sessions': sessions.filter(is_active=True).count(),
            'productive_sessions': 0,  # 需要计算
            'environments': {},
            'devices': {},
            'subjects': {},
        }
        
        # 计算高效会话数量
        for session in sessions:
            if hasattr(session, 'is_productive_session') and session.is_productive_session:
                stats['productive_sessions'] += 1
        
        # 统计环境分布
        env_stats = sessions.values('learning_environment').annotate(count=Count('id'))
        stats['environments'] = {item['learning_environment']: item['count'] for item in env_stats}
        
        # 统计设备分布
        device_stats = sessions.values('device_type').annotate(count=Count('id'))
        stats['devices'] = {item['device_type']: item['count'] for item in device_stats}
        
        # 统计学科分布
        subject_stats = sessions.values('subject_category').annotate(count=Count('id'))
        stats['subjects'] = {item['subject_category']: item['count'] for item in subject_stats if item['subject_category']}
        
        # 缓存数据
        cache.set(cache_key, json.dumps(stats, default=str), cls.CACHE_TIMEOUTS['user_daily_stats'])
        logger.info(f"缓存用户日统计: {user_id}")
        
        return stats
    
    @classmethod
    def get_user_weekly_stats(cls, user_id: str, week_start: datetime = None) -> Dict[str, Any]:
        """获取用户周统计（带缓存）"""
        if not week_start:
            week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
        
        cache_key = cls._get_cache_key('user_weekly_stats', user_id, week=week_start.isoformat())
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # 计算一周的数据
        week_end = week_start + timedelta(days=6)
        sessions = StudySession.objects.filter(
            user_id=user_id,
            start_time__date__range=[week_start, week_end]
        )
        
        stats = {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'total_sessions': sessions.count(),
            'total_duration': sessions.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0,
            'avg_session_duration': sessions.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0,
            'daily_breakdown': {},
            'streak_days': 0,
            'most_productive_day': None,
            'consistency_score': 0.0,
        }
        
        # 按天分解
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_sessions = sessions.filter(start_time__date=day)
            daily_duration = day_sessions.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
            
            stats['daily_breakdown'][day.isoformat()] = {
                'sessions': day_sessions.count(),
                'duration': daily_duration,
                'completed': day_sessions.filter(end_time__isnull=False).count()
            }
            
            if daily_duration > 0:
                stats['streak_days'] += 1
        
        # 计算一致性分数（基于每日学习时间的标准差）
        daily_durations = [stats['daily_breakdown'][day]['duration'] for day in stats['daily_breakdown']]
        if daily_durations:
            avg_duration = sum(daily_durations) / len(daily_durations)
            if avg_duration > 0:
                variance = sum((x - avg_duration) ** 2 for x in daily_durations) / len(daily_durations)
                std_dev = variance ** 0.5
                stats['consistency_score'] = max(0, 1 - (std_dev / avg_duration))
        
        cache.set(cache_key, json.dumps(stats, default=str), cls.CACHE_TIMEOUTS['user_weekly_stats'])
        return stats
    
    @classmethod
    def get_user_session_analytics(cls, user_id: str) -> Dict[str, Any]:
        """获取用户学习会话分析（带缓存）"""
        cache_key = cls._get_cache_key('user_session_analytics', user_id)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # 最近30天的会话数据
        thirty_days_ago = timezone.now() - timedelta(days=30)
        sessions = StudySession.objects.filter(
            user_id=user_id,
            start_time__gte=thirty_days_ago
        )
        
        analytics = {
            'total_sessions': sessions.count(),
            'avg_effectiveness': sessions.aggregate(Avg('effectiveness_rating'))['effectiveness_rating__avg'] or 0,
            'avg_focus_score': sessions.aggregate(Avg('focus_score'))['focus_score__avg'] or 0,
            'preferred_environment': None,
            'preferred_device': None,
            'peak_hours': {},
            'improvement_trend': 'stable',
            'recommendations': [],
        }
        
        if analytics['total_sessions'] > 0:
            # 找出偏好环境
            env_preference = sessions.values('learning_environment').annotate(
                count=Count('id')
            ).order_by('-count').first()
            if env_preference:
                analytics['preferred_environment'] = env_preference['learning_environment']
            
            # 找出偏好设备
            device_preference = sessions.values('device_type').annotate(
                count=Count('id')
            ).order_by('-count').first()
            if device_preference:
                analytics['preferred_device'] = device_preference['device_type']
            
            # 计算高峰时段
            for session in sessions.filter(start_time__isnull=False):
                hour = session.start_time.hour
                if hour not in analytics['peak_hours']:
                    analytics['peak_hours'][hour] = 0
                analytics['peak_hours'][hour] += 1
            
            # 计算改进趋势（比较最近15天和之前15天）
            mid_point = thirty_days_ago + timedelta(days=15)
            recent_avg = sessions.filter(start_time__gte=mid_point).aggregate(
                Avg('effectiveness_rating')
            )['effectiveness_rating__avg'] or 0
            previous_avg = sessions.filter(start_time__lt=mid_point).aggregate(
                Avg('effectiveness_rating')
            )['effectiveness_rating__avg'] or 0
            
            if recent_avg > previous_avg + 0.2:
                analytics['improvement_trend'] = 'improving'
            elif recent_avg < previous_avg - 0.2:
                analytics['improvement_trend'] = 'declining'
            
            # 生成推荐
            analytics['recommendations'] = cls._generate_recommendations(sessions, analytics)
        
        cache.set(cache_key, json.dumps(analytics, default=str), cls.CACHE_TIMEOUTS['user_session_analytics'])
        return analytics
    
    @classmethod
    def _generate_recommendations(cls, sessions, analytics: Dict) -> List[str]:
        """生成学习建议"""
        recommendations = []
        
        avg_duration = sessions.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0
        avg_effectiveness = analytics['avg_effectiveness']
        
        if avg_duration < 30:
            recommendations.append("建议增加单次学习时长至30分钟以上，提高学习连续性")
        
        if avg_effectiveness < 3:
            recommendations.append("学习效果有待提高，考虑调整学习方法或环境")
        
        if analytics['preferred_environment'] == 'home':
            recommendations.append("家庭学习环境可能存在干扰，试试图书馆或专门的学习空间")
        
        # 检查学习时间分布
        peak_hours = analytics.get('peak_hours', {})
        if peak_hours:
            best_hour = max(peak_hours, key=peak_hours.get)
            if 6 <= best_hour <= 10:
                recommendations.append("您在早晨学习效果较好，建议保持早起学习的习惯")
            elif 20 <= best_hour <= 23:
                recommendations.append("注意晚间学习对睡眠的影响，建议适当提前学习时间")
        
        return recommendations
    
    @classmethod
    def precompute_hot_data(cls, user_id: str) -> None:
        """预计算热点数据"""
        try:
            # 预计算今日统计
            cls.get_user_daily_stats(user_id)
            
            # 预计算本周统计
            cls.get_user_weekly_stats(user_id)
            
            # 预计算会话分析
            cls.get_user_session_analytics(user_id)
            
            logger.info(f"预计算热点数据完成: user_{user_id}")
            
        except Exception as e:
            logger.error(f"预计算热点数据失败: user_{user_id}, error: {str(e)}")
    
    @classmethod
    def invalidate_user_cache(cls, user_id: str) -> None:
        """清除用户相关缓存"""
        cache_patterns = [
            f"{cls.CACHE_PREFIX}:user_daily_stats:user_{user_id}:*",
            f"{cls.CACHE_PREFIX}:user_weekly_stats:user_{user_id}:*",
            f"{cls.CACHE_PREFIX}:user_session_analytics:user_{user_id}",
        ]
        
        for pattern in cache_patterns:
            # Django cache doesn't support pattern deletion by default
            # You might need django-redis for this functionality
            cache.delete_many([pattern])
        
        logger.info(f"清除用户缓存: user_{user_id}")
    
    @classmethod
    def get_global_stats(cls) -> Dict[str, Any]:
        """获取全局统计数据（带缓存）"""
        cache_key = cls._get_cache_key('global_stats')
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        # 计算全局统计
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        stats = {
            'total_users': StudySession.objects.values('user').distinct().count(),
            'total_sessions_today': StudySession.objects.filter(start_time__date=today).count(),
            'total_sessions_week': StudySession.objects.filter(start_time__date__gte=week_ago).count(),
            'avg_session_duration': StudySession.objects.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0,
            'most_popular_environment': None,
            'most_popular_device': None,
        }
        
        # 最受欢迎的学习环境
        env_stats = StudySession.objects.values('learning_environment').annotate(
            count=Count('id')
        ).order_by('-count').first()
        if env_stats:
            stats['most_popular_environment'] = env_stats['learning_environment']
        
        # 最受欢迎的设备
        device_stats = StudySession.objects.values('device_type').annotate(
            count=Count('id')
        ).order_by('-count').first()
        if device_stats:
            stats['most_popular_device'] = device_stats['device_type']
        
        cache.set(cache_key, json.dumps(stats, default=str), cls.CACHE_TIMEOUTS['global_stats'])
        return stats


class CourseProgressCacheService:
    """课程进度缓存服务"""
    
    CACHE_PREFIX = 'course_progress'
    CACHE_TIMEOUT = 900  # 15分钟
    
    @classmethod
    def get_user_course_summary(cls, user_id: str) -> Dict[str, Any]:
        """获取用户课程进度摘要（带缓存）"""
        cache_key = f"{cls.CACHE_PREFIX}:summary:user_{user_id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        progresses = CourseProgress.objects.filter(user_uuid_id=user_id)
        
        summary = {
            'total_courses': progresses.count(),
            'avg_proficiency': progresses.aggregate(Avg('proficiency_level'))['proficiency_level__avg'] or 0,
            'total_hours': progresses.aggregate(Sum('learning_hour_total'))['learning_hour_total__sum'] or 0,
            'weekly_hours': progresses.aggregate(Sum('learning_hour_week'))['learning_hour_week__sum'] or 0,
            'completed_courses': sum(1 for p in progresses if p.is_completed()),
            'subjects': list(progresses.values_list('subject_name', flat=True).distinct()),
        }
        
        cache.set(cache_key, json.dumps(summary, default=str), cls.CACHE_TIMEOUT)
        return summary
    
    @classmethod
    def invalidate_user_cache(cls, user_id: str) -> None:
        """清除用户课程进度缓存"""
        cache_key = f"{cls.CACHE_PREFIX}:summary:user_{user_id}"
        cache.delete(cache_key)
