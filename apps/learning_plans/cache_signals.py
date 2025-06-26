"""
缓存信号处理器 - 自动缓存失效和预热
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import StudySession
from .cache_services import LearningStatsCacheService, CourseProgressCacheService
from apps.courses.models import CourseProgress

logger = logging.getLogger(__name__)


@receiver(post_save, sender=StudySession)
def invalidate_study_session_cache(sender, instance, created, **kwargs):
    """学习会话保存后清除相关缓存"""
    try:
        user_id = str(instance.user_id)
        
        # 清除用户统计缓存
        LearningStatsCacheService.invalidate_user_cache(user_id)
        
        # 如果是新会话或会话完成，预热缓存
        if created or (instance.end_time and not instance.is_active):
            # 异步预热缓存
            from django.utils import timezone
            import threading
            
            def precompute_async():
                try:
                    LearningStatsCacheService.precompute_hot_data(user_id)
                except Exception as e:
                    logger.error(f"异步预热缓存失败: {str(e)}")
            
            # 延迟5秒后执行，避免频繁更新
            timer = threading.Timer(5.0, precompute_async)
            timer.start()
        
        logger.debug(f"学习会话缓存已失效: user_{user_id}")
        
    except Exception as e:
        logger.error(f"学习会话缓存处理失败: {str(e)}")


@receiver(post_delete, sender=StudySession)
def invalidate_deleted_session_cache(sender, instance, **kwargs):
    """学习会话删除后清除相关缓存"""
    try:
        user_id = str(instance.user_id)
        LearningStatsCacheService.invalidate_user_cache(user_id)
        logger.debug(f"删除会话后缓存已失效: user_{user_id}")
        
    except Exception as e:
        logger.error(f"删除会话缓存处理失败: {str(e)}")


@receiver(post_save, sender=CourseProgress)
def invalidate_course_progress_cache(sender, instance, created, **kwargs):
    """课程进度保存后清除相关缓存"""
    try:
        user_id = str(instance.user_uuid_id)
        CourseProgressCacheService.invalidate_user_cache(user_id)
        logger.debug(f"课程进度缓存已失效: user_{user_id}")
        
    except Exception as e:
        logger.error(f"课程进度缓存处理失败: {str(e)}")


@receiver(post_delete, sender=CourseProgress)
def invalidate_deleted_progress_cache(sender, instance, **kwargs):
    """课程进度删除后清除相关缓存"""
    try:
        user_id = str(instance.user_uuid_id)
        CourseProgressCacheService.invalidate_user_cache(user_id)
        logger.debug(f"删除进度后缓存已失效: user_{user_id}")
        
    except Exception as e:
        logger.error(f"删除进度缓存处理失败: {str(e)}")


class CacheWarmupService:
    """缓存预热服务"""
    
    @staticmethod
    def warmup_user_cache(user_id: str, force: bool = False):
        """预热用户缓存"""
        try:
            if force:
                # 强制刷新缓存
                LearningStatsCacheService.invalidate_user_cache(user_id)
                CourseProgressCacheService.invalidate_user_cache(user_id)
            
            # 预计算数据
            LearningStatsCacheService.precompute_hot_data(user_id)
            CourseProgressCacheService.get_user_course_summary(user_id)
            
            logger.info(f"用户缓存预热完成: user_{user_id}")
            
        except Exception as e:
            logger.error(f"用户缓存预热失败: user_{user_id}, error: {str(e)}")
    
    @staticmethod
    def warmup_global_cache():
        """预热全局缓存"""
        try:
            LearningStatsCacheService.get_global_stats()
            logger.info("全局缓存预热完成")
            
        except Exception as e:
            logger.error(f"全局缓存预热失败: {str(e)}")


# 在应用启动时连接信号
def connect_cache_signals():
    """连接缓存相关信号"""
    logger.info("缓存信号处理器已连接")
