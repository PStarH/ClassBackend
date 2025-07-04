"""
智能缓存策略 - 增强版
"""
import json
import hashlib
import time
from functools import wraps
from typing import Dict, List, Any, Optional, Set, Callable
from django.core.cache import cache
from django.core.cache.utils import make_key
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class CacheKeyManager:
    """缓存键管理器"""
    
    def __init__(self):
        self.key_patterns = {}
        self.dependency_graph = defaultdict(set)
    
    def register_pattern(self, pattern: str, dependencies: List[str] = None):
        """注册缓存键模式和依赖关系"""
        self.key_patterns[pattern] = {
            'dependencies': dependencies or [],
            'created_at': time.time()
        }
        
        # 建立依赖图
        if dependencies:
            for dep in dependencies:
                self.dependency_graph[dep].add(pattern)
    
    def get_dependent_patterns(self, changed_entity: str) -> Set[str]:
        """获取受影响的缓存模式"""
        return self.dependency_graph.get(changed_entity, set())
    
    def generate_key(self, pattern: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [pattern]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        
        # 如果键太长，使用哈希
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{pattern}:hash:{key_hash}"
        
        return key_string


class AdaptiveCacheManager:
    """自适应缓存管理器"""
    
    def __init__(self):
        self.access_stats = Counter()
        self.hit_rates = defaultdict(list)
        self.key_manager = CacheKeyManager()
        self.adaptive_ttl = {}
        
    def track_access(self, key: str, hit: bool):
        """跟踪缓存访问"""
        self.access_stats[key] += 1
        self.hit_rates[key].append(1 if hit else 0)
        
        # 保持最近100次访问记录
        if len(self.hit_rates[key]) > 100:
            self.hit_rates[key] = self.hit_rates[key][-100:]
    
    def calculate_hit_rate(self, key: str) -> float:
        """计算命中率"""
        hits = self.hit_rates.get(key, [])
        if not hits:
            return 0.0
        return sum(hits) / len(hits)
    
    def get_adaptive_ttl(self, key: str, base_ttl: int = 300) -> int:
        """根据访问模式计算自适应TTL"""
        hit_rate = self.calculate_hit_rate(key)
        access_count = self.access_stats.get(key, 0)
        
        # 高命中率和高访问频率 -> 更长的TTL
        if hit_rate > 0.8 and access_count > 50:
            return base_ttl * 3
        elif hit_rate > 0.6 and access_count > 20:
            return base_ttl * 2
        elif hit_rate < 0.3:
            return base_ttl // 2
        
        return base_ttl
    
    def should_cache(self, key: str) -> bool:
        """判断是否应该缓存"""
        hit_rate = self.calculate_hit_rate(key)
        access_count = self.access_stats.get(key, 0)
        
        # 低命中率且访问次数少的不缓存
        return not (hit_rate < 0.2 and access_count > 10)


class HierarchicalCacheStrategy:
    """分层缓存策略"""
    
    def __init__(self):
        self.l1_cache = {}  # 内存缓存
        self.l1_max_size = 1000
        self.l1_access_order = []
    
    def get(self, key: str, use_l1: bool = True) -> Any:
        """分层获取缓存"""
        # L1缓存（内存）
        if use_l1 and key in self.l1_cache:
            self._update_l1_access(key)
            logger.debug(f"L1缓存命中: {key}")
            return self.l1_cache[key]
        
        # L2缓存（Redis）
        value = cache.get(key)
        if value is not None:
            # 提升到L1缓存
            if use_l1:
                self._set_l1(key, value)
            logger.debug(f"L2缓存命中: {key}")
            return value
        
        logger.debug(f"缓存未命中: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300, use_l1: bool = True):
        """分层设置缓存"""
        # 设置L2缓存
        cache.set(key, value, ttl)
        
        # 设置L1缓存
        if use_l1:
            self._set_l1(key, value)
    
    def _set_l1(self, key: str, value: Any):
        """设置L1缓存"""
        if len(self.l1_cache) >= self.l1_max_size:
            # LRU淘汰
            oldest_key = self.l1_access_order.pop(0)
            del self.l1_cache[oldest_key]
        
        self.l1_cache[key] = value
        self._update_l1_access(key)
    
    def _update_l1_access(self, key: str):
        """更新L1访问顺序"""
        if key in self.l1_access_order:
            self.l1_access_order.remove(key)
        self.l1_access_order.append(key)
    
    def invalidate(self, key: str):
        """失效缓存"""
        # 清除L1缓存
        if key in self.l1_cache:
            del self.l1_cache[key]
            if key in self.l1_access_order:
                self.l1_access_order.remove(key)
        
        # 清除L2缓存
        cache.delete(key)


class SemanticCacheInvalidation:
    """语义缓存失效"""
    
    def __init__(self):
        self.invalidation_rules = {}
        self.tag_relationships = defaultdict(set)
    
    def register_rule(self, model_name: str, invalidation_callback: Callable):
        """注册失效规则"""
        self.invalidation_rules[model_name] = invalidation_callback
    
    def register_tag_relationship(self, parent_tag: str, child_tags: List[str]):
        """注册标签关系"""
        for child in child_tags:
            self.tag_relationships[parent_tag].add(child)
    
    def invalidate_by_model(self, model_name: str, instance):
        """根据模型变更失效缓存"""
        if model_name in self.invalidation_rules:
            callback = self.invalidation_rules[model_name]
            affected_tags = callback(instance)
            
            for tag in affected_tags:
                self._invalidate_tag_hierarchy(tag)
    
    def _invalidate_tag_hierarchy(self, tag: str):
        """递归失效标签层次结构"""
        # 失效当前标签
        tag_key = f"tag:{tag}"
        tagged_keys = cache.get(tag_key, set())
        
        if tagged_keys:
            cache.delete_many(tagged_keys)
            cache.delete(tag_key)
            logger.info(f"失效标签 {tag}，影响 {len(tagged_keys)} 个缓存项")
        
        # 失效子标签
        for child_tag in self.tag_relationships.get(tag, set()):
            self._invalidate_tag_hierarchy(child_tag)


class CacheWarmupManager:
    """缓存预热管理器"""
    
    def __init__(self):
        self.warmup_strategies = {}
        self.warmup_schedule = {}
    
    def register_warmup_strategy(self, key_pattern: str, warmup_func: Callable):
        """注册预热策略"""
        self.warmup_strategies[key_pattern] = warmup_func
    
    def schedule_warmup(self, key_pattern: str, interval_seconds: int):
        """调度预热任务"""
        self.warmup_schedule[key_pattern] = {
            'interval': interval_seconds,
            'last_warmup': 0
        }
    
    def execute_warmup(self, key_pattern: str = None):
        """执行预热"""
        patterns_to_warmup = [key_pattern] if key_pattern else self.warmup_strategies.keys()
        
        for pattern in patterns_to_warmup:
            if pattern in self.warmup_strategies:
                try:
                    warmup_func = self.warmup_strategies[pattern]
                    warmup_func()
                    
                    if pattern in self.warmup_schedule:
                        self.warmup_schedule[pattern]['last_warmup'] = time.time()
                    
                    logger.info(f"完成缓存预热: {pattern}")
                    
                except Exception as e:
                    logger.error(f"缓存预热失败 {pattern}: {e}")
    
    def check_scheduled_warmup(self):
        """检查并执行计划的预热"""
        current_time = time.time()
        
        for pattern, schedule_info in self.warmup_schedule.items():
            time_since_last = current_time - schedule_info['last_warmup']
            
            if time_since_last >= schedule_info['interval']:
                self.execute_warmup(pattern)


class CacheMetricsCollector:
    """缓存指标收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(int)
        self.start_time = time.time()
    
    def record_hit(self, key: str):
        """记录缓存命中"""
        self.metrics['total_hits'] += 1
        self.metrics[f'hits:{key}'] += 1
    
    def record_miss(self, key: str):
        """记录缓存未命中"""
        self.metrics['total_misses'] += 1
        self.metrics[f'misses:{key}'] += 1
    
    def record_set(self, key: str):
        """记录缓存设置"""
        self.metrics['total_sets'] += 1
        self.metrics[f'sets:{key}'] += 1
    
    def record_delete(self, key: str):
        """记录缓存删除"""
        self.metrics['total_deletes'] += 1
        self.metrics[f'deletes:{key}'] += 1
    
    def get_hit_rate(self) -> float:
        """获取总体命中率"""
        total_requests = self.metrics['total_hits'] + self.metrics['total_misses']
        if total_requests == 0:
            return 0.0
        return self.metrics['total_hits'] / total_requests
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        runtime = time.time() - self.start_time
        
        return {
            'runtime_seconds': runtime,
            'total_hits': self.metrics['total_hits'],
            'total_misses': self.metrics['total_misses'],
            'total_sets': self.metrics['total_sets'],
            'total_deletes': self.metrics['total_deletes'],
            'hit_rate': self.get_hit_rate(),
            'requests_per_second': (self.metrics['total_hits'] + self.metrics['total_misses']) / max(runtime, 1)
        }


# 全局实例
adaptive_cache_manager = AdaptiveCacheManager()
hierarchical_cache = HierarchicalCacheStrategy()
semantic_invalidation = SemanticCacheInvalidation()
warmup_manager = CacheWarmupManager()
metrics_collector = CacheMetricsCollector()


def smart_cache(key_pattern: str, ttl: int = 300, tags: List[str] = None, use_adaptive_ttl: bool = True):
    """智能缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = adaptive_cache_manager.key_manager.generate_key(key_pattern, *args, **kwargs)
            
            # 尝试获取缓存
            cached_value = hierarchical_cache.get(cache_key)
            if cached_value is not None:
                adaptive_cache_manager.track_access(cache_key, True)
                metrics_collector.record_hit(cache_key)
                return cached_value
            
            # 缓存未命中
            adaptive_cache_manager.track_access(cache_key, False)
            metrics_collector.record_miss(cache_key)
            
            # 检查是否应该缓存
            if not adaptive_cache_manager.should_cache(cache_key):
                return func(*args, **kwargs)
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 计算TTL
            actual_ttl = ttl
            if use_adaptive_ttl:
                actual_ttl = adaptive_cache_manager.get_adaptive_ttl(cache_key, ttl)
            
            # 设置缓存
            hierarchical_cache.set(cache_key, result, actual_ttl)
            metrics_collector.record_set(cache_key)
            
            # 设置标签关联
            if tags:
                for tag in tags:
                    tag_key = f"tag:{tag}"
                    tagged_keys = cache.get(tag_key, set())
                    tagged_keys.add(cache_key)
                    cache.set(tag_key, tagged_keys, actual_ttl + 300)
            
            return result
        
        return wrapper
    return decorator


# 注册常用的失效规则
def register_common_invalidation_rules():
    """注册常用的缓存失效规则"""
    
    def user_invalidation(instance):
        """用户相关的缓存失效"""
        return [f'user:{instance.id}', f'user:{instance.username}']
    
    def course_invalidation(instance):
        """课程相关的缓存失效"""
        return [f'course:{instance.id}', 'course:all']
    
    semantic_invalidation.register_rule('User', user_invalidation)
    semantic_invalidation.register_rule('Course', course_invalidation)


# 初始化
register_common_invalidation_rules()

# 自动缓存失效信号处理
@receiver([post_save, post_delete])
def smart_cache_invalidation(sender, instance, **kwargs):
    """智能缓存失效"""
    model_name = sender.__name__.lower()
    
    # 使用语义失效管理器
    semantic_invalidation.invalidate_by_model(model_name, instance)
