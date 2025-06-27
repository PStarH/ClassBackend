"""
高级缓存策略
"""
import json
import hashlib
from functools import wraps
from django.core.cache import cache
from django.core.cache.utils import make_key
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


class SmartCacheManager:
    """智能缓存管理器"""
    
    def __init__(self):
        self.default_timeout = getattr(settings, 'CACHE_DEFAULT_TIMEOUT', 300)
        self.long_timeout = 3600  # 1小时
        self.short_timeout = 60   # 1分钟
    
    def get_cache_key(self, prefix, *args, **kwargs):
        """生成缓存键"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        
        # 如果键太长，使用哈希
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
        
        return key_string
    
    def set_with_tags(self, key, value, timeout=None, tags=None):
        """设置带标签的缓存"""
        if timeout is None:
            timeout = self.default_timeout
        
        # 设置主缓存
        cache.set(key, value, timeout)
        
        # 设置标签关联
        if tags:
            for tag in tags:
                tag_key = f"tag:{tag}"
                tagged_keys = cache.get(tag_key, set())
                tagged_keys.add(key)
                cache.set(tag_key, tagged_keys, timeout + 300)  # 标签缓存稍长
    
    def invalidate_by_tags(self, tags):
        """根据标签失效缓存"""
        keys_to_delete = set()
        
        for tag in tags:
            tag_key = f"tag:{tag}"
            tagged_keys = cache.get(tag_key, set())
            keys_to_delete.update(tagged_keys)
            cache.delete(tag_key)
        
        if keys_to_delete:
            cache.delete_many(keys_to_delete)
            logger.info(f"通过标签失效了 {len(keys_to_delete)} 个缓存项")
    
    def get_or_set_queryset(self, queryset, cache_key, timeout=None, tags=None):
        """获取或设置查询集缓存"""
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"缓存命中: {cache_key}")
            return cached_data
        
        # 执行查询
        try:
            data = list(queryset.values())  # 序列化为字典列表
            self.set_with_tags(cache_key, data, timeout, tags)
            logger.debug(f"缓存设置: {cache_key}")
            return data
        except Exception as e:
            logger.error(f"查询集缓存失败: {str(e)}")
            return []
    
    def cache_user_data(self, user_id, data_type, data, timeout=None):
        """缓存用户数据"""
        cache_key = self.get_cache_key('user_data', user_id, data_type)
        tags = [f'user:{user_id}', f'type:{data_type}']
        self.set_with_tags(cache_key, data, timeout, tags)
    
    def get_user_data(self, user_id, data_type):
        """获取用户缓存数据"""
        cache_key = self.get_cache_key('user_data', user_id, data_type)
        return cache.get(cache_key)
    
    def invalidate_user_cache(self, user_id):
        """失效用户相关缓存"""
        self.invalidate_by_tags([f'user:{user_id}'])


# 全局缓存管理器实例
cache_manager = SmartCacheManager()


def cache_result(timeout=300, key_prefix='func', tags=None):
    """结果缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_manager.get_cache_key(
                key_prefix, 
                func.__name__, 
                *args, 
                **kwargs
            )
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"函数缓存命中: {func.__name__}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set_with_tags(cache_key, result, timeout, tags)
            logger.debug(f"函数结果已缓存: {func.__name__}")
            
            return result
        return wrapper
    return decorator


def cache_queryset(timeout=300, key_prefix='queryset', tags=None):
    """查询集缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_manager.get_cache_key(
                key_prefix,
                func.__name__,
                *args,
                **kwargs
            )
            
            # 执行函数获取查询集
            queryset = func(*args, **kwargs)
            
            # 使用智能缓存管理器缓存查询集
            return cache_manager.get_or_set_queryset(
                queryset, cache_key, timeout, tags
            )
        return wrapper
    return decorator


class CacheWarmupService:
    """缓存预热服务"""
    
    @staticmethod
    def warmup_user_data(user_id):
        """预热用户数据"""
        from apps.authentication.models import User, UserSettings
        from apps.courses.models import CourseProgress
        from apps.learning_plans.models import StudySession
        
        try:
            # 预热用户基本信息
            user = User.objects.get(uuid=user_id)
            cache_manager.cache_user_data(user_id, 'profile', {
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
            })
            
            # 预热用户设置
            try:
                settings_obj = UserSettings.objects.get(user_uuid=user)
                cache_manager.cache_user_data(user_id, 'settings', {
                    'preferred_pace': settings_obj.preferred_pace,
                    'preferred_style': settings_obj.preferred_style,
                    'tone': settings_obj.tone,
                })
            except UserSettings.DoesNotExist:
                pass
            
            # 预热课程进度
            progress_data = list(CourseProgress.objects.filter(user_uuid=user).values(
                'content_id', 'progress_percentage', 'status'
            ))
            cache_manager.cache_user_data(user_id, 'course_progress', progress_data)
            
            # 预热最近学习会话
            recent_sessions = list(StudySession.objects.filter(user=user)[:10].values(
                'start_time', 'duration_minutes', 'effectiveness_rating'
            ))
            cache_manager.cache_user_data(user_id, 'recent_sessions', recent_sessions)
            
            logger.info(f"用户 {user_id} 数据预热完成")
            
        except Exception as e:
            logger.error(f"用户数据预热失败 {user_id}: {str(e)}")
    
    @staticmethod
    def warmup_popular_content():
        """预热热门内容"""
        from apps.courses.models import CourseContent
        from django.db.models import Count
        
        try:
            # 获取最受欢迎的课程内容
            popular_content = CourseContent.objects.annotate(
                progress_count=Count('progress_records')
            ).order_by('-progress_count')[:20]
            
            for content in popular_content:
                cache_key = cache_manager.get_cache_key('content', content.content_id)
                cache_manager.set_with_tags(
                    cache_key,
                    {
                        'title': content.title,
                        'description': content.description,
                        'difficulty_level': content.difficulty_level,
                        'estimated_duration': content.estimated_duration,
                    },
                    timeout=3600,  # 1小时
                    tags=['content', 'popular']
                )
            
            logger.info("热门内容预热完成")
            
        except Exception as e:
            logger.error(f"热门内容预热失败: {str(e)}")


class CacheAnalytics:
    """缓存分析"""
    
    @staticmethod
    def get_cache_stats():
        """获取缓存统计"""
        try:
            # Redis 缓存统计
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            info = redis_conn.info()
            stats = {
                'redis_version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'used_memory_peak': info.get('used_memory_peak_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
            
            # 计算命中率
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            if hits + misses > 0:
                stats['hit_rate'] = hits / (hits + misses) * 100
            else:
                stats['hit_rate'] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {}
    
    @staticmethod
    def analyze_cache_usage():
        """分析缓存使用情况"""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            # 获取所有键的样本
            keys = redis_conn.keys('*')[:1000]  # 限制数量避免性能问题
            
            key_patterns = {}
            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                
                # 提取键的模式
                parts = key.split(':')
                if len(parts) >= 2:
                    pattern = ':'.join(parts[:2])
                    key_patterns[pattern] = key_patterns.get(pattern, 0) + 1
            
            # 按使用频率排序
            sorted_patterns = sorted(
                key_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            
            return {
                'total_keys': len(keys),
                'pattern_distribution': sorted_patterns[:10],
                'most_used_pattern': sorted_patterns[0] if sorted_patterns else None
            }
            
        except Exception as e:
            logger.error(f"缓存使用分析失败: {str(e)}")
            return {}


# 自动缓存失效信号处理
@receiver([post_save, post_delete])
def smart_cache_invalidation(sender, instance, **kwargs):
    """智能缓存失效"""
    model_name = sender.__name__.lower()
    
    # 基于模型的缓存失效策略
    if model_name == 'user':
        cache_manager.invalidate_user_cache(instance.uuid)
    elif model_name == 'usersettings':
        cache_manager.invalidate_user_cache(instance.user_uuid.uuid)
    elif model_name == 'courseprogress':
        cache_manager.invalidate_by_tags([
            f'user:{instance.user_uuid.uuid}',
            f'content:{instance.content_id.content_id}'
        ])
    elif model_name == 'studysession':
        cache_manager.invalidate_by_tags([
            f'user:{instance.user.uuid}',
            'sessions'
        ])
    
    # 通用模型缓存失效
    cache_manager.invalidate_by_tags([f'model:{model_name}'])
