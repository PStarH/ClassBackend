"""
学习数据相关的 Celery 任务
"""
import logging
from datetime import datetime, timedelta
try:
    from celery import shared_task
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    # Celery 不可用时的备用方案
    CELERY_AVAILABLE = False
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from django.utils import timezone
from django.contrib.auth import get_user_model

from .cache_services import LearningStatsCacheService, CourseProgressCacheService
from .models import StudySession

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def precompute_user_cache_task(self, user_id: str):
    """预计算用户缓存任务"""
    try:
        LearningStatsCacheService.precompute_hot_data(user_id)
        CourseProgressCacheService.get_user_course_summary(user_id)
        
        logger.info(f"用户缓存预计算完成: user_{user_id}")
        return f"Success: user_{user_id}"
        
    except Exception as exc:
        logger.error(f"用户缓存预计算失败: user_{user_id}, error: {str(exc)}")
        
        # 重试机制
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return f"Failed after {self.max_retries} retries: user_{user_id}"


@shared_task
def precompute_active_users_cache():
    """预计算活跃用户缓存任务"""
    try:
        # 获取最近7天有学习活动的用户
        cutoff_date = timezone.now() - timedelta(days=7)
        active_user_ids = StudySession.objects.filter(
            start_time__gte=cutoff_date
        ).values_list('user_id', flat=True).distinct()
        
        success_count = 0
        error_count = 0
        
        for user_id in active_user_ids:
            try:
                precompute_user_cache_task.delay(str(user_id))
                success_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"任务分发失败: user_{user_id}, error: {str(e)}")
        
        logger.info(f"活跃用户缓存预计算任务分发完成: 成功 {success_count}, 失败 {error_count}")
        return f"Dispatched: {success_count} tasks, Failed: {error_count}"
        
    except Exception as e:
        logger.error(f"活跃用户缓存预计算任务失败: {str(e)}")
        return f"Failed: {str(e)}"


@shared_task
def cleanup_expired_cache():
    """清理过期缓存任务"""
    try:
        from django.core.cache import cache
        
        # 这里可以添加特定的缓存清理逻辑
        # Django的默认缓存会自动处理过期，但可以添加手动清理
        
        logger.info("过期缓存清理完成")
        return "Cache cleanup completed"
        
    except Exception as e:
        logger.error(f"缓存清理失败: {str(e)}")
        return f"Failed: {str(e)}"


@shared_task
def archive_old_learning_data():
    """归档旧学习数据任务"""
    try:
        from django.core.management import call_command
        
        # 调用管理命令进行数据清理
        call_command(
            'cleanup_learning_data',
            '--archive-older-than=365',
            '--cleanup-invalid',
            '--batch-size=500'
        )
        
        logger.info("学习数据归档任务完成")
        return "Data archiving completed"
        
    except Exception as e:
        logger.error(f"数据归档任务失败: {str(e)}")
        return f"Failed: {str(e)}"


@shared_task
def update_learning_analytics():
    """更新学习分析数据任务"""
    try:
        from .analytics_models import LearningAnalytics, LearningStreak
        from django.db.models import Count, Avg, Sum
        
        # 获取昨天的日期
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # 为所有活跃用户生成昨天的分析数据
        active_users = User.objects.filter(
            study_sessions__start_time__date=yesterday
        ).distinct()
        
        created_count = 0
        
        for user in active_users:
            # 检查是否已存在分析记录
            if LearningAnalytics.objects.filter(
                user=user, 
                analysis_date=yesterday
            ).exists():
                continue
            
            # 计算昨天的学习统计
            sessions = StudySession.objects.filter(
                user=user,
                start_time__date=yesterday
            )
            
            total_time = sessions.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
            session_count = sessions.count()
            avg_effectiveness = sessions.aggregate(Avg('effectiveness_rating'))['effectiveness_rating__avg'] or 0
            
            # 创建分析记录
            LearningAnalytics.objects.create(
                user=user,
                analysis_date=yesterday,
                week_of_year=yesterday.isocalendar()[1],
                month=yesterday.month,
                total_study_time=total_time,
                session_count=session_count,
                average_session_duration=total_time / session_count if session_count > 0 else 0,
                average_effectiveness=avg_effectiveness,
                productive_sessions_count=sum(
                    1 for s in sessions if hasattr(s, 'is_productive_session') and s.is_productive_session
                ),
                productivity_rate=0.0,  # 需要进一步计算
            )
            
            created_count += 1
        
        logger.info(f"学习分析数据更新完成，创建了 {created_count} 条记录")
        return f"Created {created_count} analytics records"
        
    except Exception as e:
        logger.error(f"学习分析数据更新失败: {str(e)}")
        return f"Failed: {str(e)}"


# Celery Beat 调度配置（在 settings.py 中配置）
if CELERY_AVAILABLE:
    CELERY_BEAT_SCHEDULE = {
        # 每5分钟预热活跃用户缓存
        'precompute-active-cache': {
            'task': 'apps.learning_plans.tasks.precompute_active_users_cache',
            'schedule': 300.0,  # 5分钟
        },
        
        # 每小时清理过期缓存
        'cleanup-expired-cache': {
            'task': 'apps.learning_plans.tasks.cleanup_expired_cache',
            'schedule': 3600.0,  # 1小时
        },
        
        # 每天凌晨2点归档数据
        'archive-old-data': {
            'task': 'apps.learning_plans.tasks.archive_old_learning_data',
            'schedule': crontab(hour=2, minute=0),
        },
        
        # 每天凌晨3点更新分析数据
        'update-analytics': {
            'task': 'apps.learning_plans.tasks.update_learning_analytics',
            'schedule': crontab(hour=3, minute=0),
        },
    }
