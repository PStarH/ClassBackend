"""
性能监控和成本分析系统
"""
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    timestamp: float
    metric_type: str  # 'database', 'cache', 'llm', 'api'
    operation: str
    duration_ms: float
    success: bool
    metadata: Dict[str, Any] = None
    cost_cents: float = 0.0  # 成本（美分）
    
    def to_dict(self):
        return asdict(self)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_metrics=10000):
        self.metrics = deque(maxlen=max_metrics)
        self.lock = threading.Lock()
        self._cost_tracking = {
            'llm_requests': 0,
            'database_queries': 0,
            'cache_operations': 0,
            'total_cost_cents': 0.0
        }
    
    def record_metric(self, metric: PerformanceMetric):
        """记录性能指标"""
        with self.lock:
            self.metrics.append(metric)
            self._update_cost_tracking(metric)
    
    def _update_cost_tracking(self, metric: PerformanceMetric):
        """更新成本跟踪"""
        if metric.metric_type == 'llm':
            self._cost_tracking['llm_requests'] += 1
            self._cost_tracking['total_cost_cents'] += metric.cost_cents
        elif metric.metric_type == 'database':
            self._cost_tracking['database_queries'] += 1
        elif metric.metric_type == 'cache':
            self._cost_tracking['cache_operations'] += 1
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取指标摘要"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {"message": "No metrics found for the specified time period"}
        
        # 按类型分组
        by_type = defaultdict(list)
        for metric in recent_metrics:
            by_type[metric.metric_type].append(metric)
        
        summary = {}
        total_cost = 0.0
        
        for metric_type, metrics in by_type.items():
            durations = [m.duration_ms for m in metrics]
            costs = [m.cost_cents for m in metrics]
            
            summary[metric_type] = {
                'count': len(metrics),
                'avg_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations),
                'success_rate': sum(1 for m in metrics if m.success) / len(metrics),
                'total_cost_cents': sum(costs)
            }
            total_cost += sum(costs)
        
        summary['total_cost_cents'] = total_cost
        summary['time_period_hours'] = hours
        summary['total_operations'] = len(recent_metrics)
        
        return summary
    
    def get_slow_operations(self, threshold_ms: float = 1000, limit: int = 10) -> List[Dict]:
        """获取慢操作"""
        with self.lock:
            slow_ops = [
                m.to_dict() for m in self.metrics 
                if m.duration_ms > threshold_ms
            ]
        
        # 按持续时间排序
        slow_ops.sort(key=lambda x: x['duration_ms'], reverse=True)
        return slow_ops[:limit]


class DatabaseMonitor:
    """数据库监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
        self.query_count = 0
    
    def monitor_query(self, sql: str):
        """监控数据库查询"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.query_count += 1
                    
                    metric = PerformanceMetric(
                        timestamp=time.time(),
                        metric_type='database',
                        operation='query',
                        duration_ms=duration_ms,
                        success=success,
                        metadata={
                            'sql_hash': hash(sql) % 10000,  # SQL哈希用于分组
                            'query_number': self.query_count
                        }
                    )
                    self.collector.record_metric(metric)
            
            return wrapper
        return decorator
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        try:
            with connection.cursor() as cursor:
                # 活跃连接数
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                active_connections = cursor.fetchone()[0]
                
                # 总连接数
                cursor.execute("SELECT count(*) FROM pg_stat_activity;")
                total_connections = cursor.fetchone()[0]
                
                # 数据库大小
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
                db_size = cursor.fetchone()[0]
                
                return {
                    'active_connections': active_connections,
                    'total_connections': total_connections,
                    'database_size': db_size,
                    'timestamp': time.time()
                }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return {'error': str(e)}


class CacheMonitor:
    """缓存监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
        self.hit_count = 0
        self.miss_count = 0
    
    def monitor_cache_operation(self, operation: str, cache_alias: str = 'default'):
        """监控缓存操作"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                is_hit = False
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 检测缓存命中/未命中
                    if operation == 'get' and result is not None:
                        is_hit = True
                        self.hit_count += 1
                    elif operation == 'get' and result is None:
                        self.miss_count += 1
                    
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    metric = PerformanceMetric(
                        timestamp=time.time(),
                        metric_type='cache',
                        operation=operation,
                        duration_ms=duration_ms,
                        success=success,
                        metadata={
                            'cache_alias': cache_alias,
                            'is_hit': is_hit,
                            'hit_rate': self.get_hit_rate()
                        }
                    )
                    self.collector.record_metric(metric)
            
            return wrapper
        return decorator
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total) if total > 0 else 0.0


class LLMCostTracker:
    """LLM成本跟踪器"""
    
    # DeepSeek API 定价（美分）
    PRICING = {
        'deepseek-chat': {
            'input_tokens': 0.014,   # 每1K token
            'output_tokens': 0.028   # 每1K token
        }
    }
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.collector = metrics_collector
    
    def track_llm_request(self, model: str, input_tokens: int, output_tokens: int):
        """跟踪LLM请求成本"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # 计算成本
                    cost_cents = self.calculate_cost(model, input_tokens, output_tokens)
                    
                    metric = PerformanceMetric(
                        timestamp=time.time(),
                        metric_type='llm',
                        operation='completion',
                        duration_ms=duration_ms,
                        success=success,
                        cost_cents=cost_cents,
                        metadata={
                            'model': model,
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'total_tokens': input_tokens + output_tokens
                        }
                    )
                    self.collector.record_metric(metric)
            
            return wrapper
        return decorator
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算请求成本"""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        input_cost = (input_tokens / 1000) * pricing['input_tokens']
        output_cost = (output_tokens / 1000) * pricing['output_tokens']
        
        return input_cost + output_cost


class PerformanceMonitor:
    """性能监控主类"""
    
    def __init__(self):
        self.collector = MetricsCollector()
        self.db_monitor = DatabaseMonitor(self.collector)
        self.cache_monitor = CacheMonitor(self.collector)
        self.llm_tracker = LLMCostTracker(self.collector)
        
        # 启动定期报告
        self._start_periodic_reporting()
    
    def _start_periodic_reporting(self):
        """启动定期报告"""
        def report_task():
            while True:
                try:
                    time.sleep(3600)  # 每小时报告一次
                    self.generate_hourly_report()
                except Exception as e:
                    logger.error(f"Periodic reporting error: {e}")
        
        thread = threading.Thread(target=report_task, daemon=True)
        thread.start()
    
    def generate_hourly_report(self):
        """生成小时报告"""
        summary = self.collector.get_metrics_summary(hours=1)
        slow_ops = self.collector.get_slow_operations()
        db_stats = self.db_monitor.get_connection_stats()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'period': '1_hour',
            'metrics_summary': summary,
            'slow_operations': slow_ops,
            'database_stats': db_stats,
            'cache_hit_rate': self.cache_monitor.get_hit_rate()
        }
        
        # 缓存报告
        cache.set('performance_report_latest', report, timeout=3600)
        
        # 记录到日志
        logger.info(f"Hourly performance report: {json.dumps(summary, indent=2)}")
        
        return report
    
    def get_cost_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """获取成本分析"""
        summary = self.collector.get_metrics_summary(hours=hours)
        
        analysis = {
            'time_period_hours': hours,
            'total_cost_cents': summary.get('total_cost_cents', 0),
            'total_cost_usd': summary.get('total_cost_cents', 0) / 100,
            'cost_breakdown': {},
            'projected_monthly_cost_usd': 0
        }
        
        # 成本分解
        for metric_type, data in summary.items():
            if isinstance(data, dict) and 'total_cost_cents' in data:
                analysis['cost_breakdown'][metric_type] = {
                    'cost_cents': data['total_cost_cents'],
                    'cost_usd': data['total_cost_cents'] / 100,
                    'operations': data['count']
                }
        
        # 月度成本预测
        if hours > 0:
            hourly_cost = summary.get('total_cost_cents', 0) / hours
            monthly_cost_cents = hourly_cost * 24 * 30
            analysis['projected_monthly_cost_usd'] = monthly_cost_cents / 100
        
        return analysis
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        return {
            'current_metrics': self.collector.get_metrics_summary(hours=1),
            'slow_operations': self.collector.get_slow_operations(limit=5),
            'database_stats': self.db_monitor.get_connection_stats(),
            'cache_hit_rate': self.cache_monitor.get_hit_rate(),
            'cost_analysis': self.get_cost_analysis(hours=24),
            'system_health': self._assess_system_health()
        }
    
    def _assess_system_health(self) -> Dict[str, str]:
        """评估系统健康状况"""
        health = {
            'overall': 'good',
            'database': 'good',
            'cache': 'good',
            'llm': 'good'
        }
        
        try:
            # 检查数据库
            db_stats = self.db_monitor.get_connection_stats()
            if db_stats.get('active_connections', 0) > 80:
                health['database'] = 'warning'
            
            # 检查缓存
            hit_rate = self.cache_monitor.get_hit_rate()
            if hit_rate < 0.6:
                health['cache'] = 'warning'
            
            # 检查慢操作
            slow_ops = self.collector.get_slow_operations(threshold_ms=2000, limit=5)
            if len(slow_ops) > 3:
                health['overall'] = 'warning'
            
        except Exception as e:
            logger.error(f"Health assessment error: {e}")
            health['overall'] = 'error'
        
        return health


# 全局监控实例
performance_monitor = PerformanceMonitor()
