"""
系统监控和警报
"""
import time
import logging
import threading
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict

from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """警报类"""
    id: str
    severity: str  # 'critical', 'warning', 'info'
    message: str
    timestamp: datetime
    component: str
    metric_value: float = 0.0
    threshold: float = 0.0
    resolved: bool = False
    resolved_at: datetime = None


@dataclass
class Metric:
    """指标类"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_samples: int = 1000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.lock = threading.RLock()
    
    def record(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录指标"""
        with self.lock:
            metric = Metric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics[name].append(metric)
    
    def get_latest(self, name: str, count: int = 1) -> List[Metric]:
        """获取最新的指标值"""
        with self.lock:
            metrics = list(self.metrics[name])
            return metrics[-count:] if metrics else []
    
    def get_average(self, name: str, minutes: int = 5) -> float:
        """获取指定时间内的平均值"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            recent_metrics = [
                m for m in self.metrics[name] 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return 0.0
            
            return sum(m.value for m in recent_metrics) / len(recent_metrics)
    
    def get_percentile(self, name: str, percentile: float, minutes: int = 5) -> float:
        """获取指定时间内的百分位数"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            recent_values = [
                m.value for m in self.metrics[name] 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_values:
                return 0.0
            
            recent_values.sort()
            index = int(len(recent_values) * percentile / 100)
            return recent_values[min(index, len(recent_values) - 1)]


class AlertManager:
    """警报管理器"""
    
    def __init__(self):
        self.alerts = {}
        self.handlers = []
        self.lock = threading.RLock()
    
    def add_handler(self, handler: Callable[[Alert], None]):
        """添加警报处理器"""
        self.handlers.append(handler)
    
    def trigger_alert(
        self, 
        alert_id: str, 
        severity: str, 
        message: str, 
        component: str,
        metric_value: float = 0.0,
        threshold: float = 0.0
    ):
        """触发警报"""
        with self.lock:
            # 检查是否已存在相同的警报
            if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                return  # 避免重复警报
            
            alert = Alert(
                id=alert_id,
                severity=severity,
                message=message,
                timestamp=datetime.now(),
                component=component,
                metric_value=metric_value,
                threshold=threshold
            )
            
            self.alerts[alert_id] = alert
            
            # 通知所有处理器
            for handler in self.handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"警报处理器失败: {e}")
    
    def resolve_alert(self, alert_id: str):
        """解决警报"""
        with self.lock:
            if alert_id in self.alerts:
                self.alerts[alert_id].resolved = True
                self.alerts[alert_id].resolved_at = datetime.now()
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃警报"""
        with self.lock:
            return [alert for alert in self.alerts.values() if not alert.resolved]


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics = metrics_collector
        self.alerts = alert_manager
        self.checks = {}
        self.running = False
        self.check_thread = None
    
    def register_check(self, name: str, check_func: Callable[[], Dict[str, Any]], interval: int = 60):
        """注册健康检查"""
        self.checks[name] = {
            'func': check_func,
            'interval': interval,
            'last_check': 0
        }
    
    def start(self):
        """启动健康检查"""
        if self.running:
            return
        
        self.running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        logger.info("健康检查器已启动")
    
    def stop(self):
        """停止健康检查"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("健康检查器已停止")
    
    def _check_loop(self):
        """检查循环"""
        while self.running:
            current_time = time.time()
            
            for name, check_info in self.checks.items():
                if current_time - check_info['last_check'] >= check_info['interval']:
                    try:
                        result = check_info['func']()
                        self._process_check_result(name, result)
                        check_info['last_check'] = current_time
                    except Exception as e:
                        logger.error(f"健康检查 {name} 失败: {e}")
                        self.alerts.trigger_alert(
                            f"health_check_{name}",
                            "critical",
                            f"健康检查 {name} 失败: {e}",
                            "health_checker"
                        )
            
            time.sleep(10)  # 每10秒检查一次
    
    def _process_check_result(self, check_name: str, result: Dict[str, Any]):
        """处理检查结果"""
        # 记录指标
        for metric_name, value in result.items():
            if isinstance(value, (int, float)):
                self.metrics.record(f"{check_name}.{metric_name}", value)


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self.health_checker = HealthChecker(self.metrics, self.alerts)
        
        # 注册默认警报处理器
        self.alerts.add_handler(self._log_alert)
        if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
            self.alerts.add_handler(self._email_alert)
        
        # 注册健康检查
        self._register_default_checks()
    
    def _log_alert(self, alert: Alert):
        """日志警报处理器"""
        log_level = {
            'critical': logger.critical,
            'warning': logger.warning,
            'info': logger.info
        }.get(alert.severity, logger.info)
        
        log_level(f"[{alert.component}] {alert.message}")
    
    def _email_alert(self, alert: Alert):
        """邮件警报处理器"""
        if alert.severity in ['critical', 'warning']:
            try:
                send_mail(
                    subject=f"[{alert.severity.upper()}] 系统警报",
                    message=f"{alert.message}\n\n"
                           f"组件: {alert.component}\n"
                           f"时间: {alert.timestamp}\n"
                           f"指标值: {alert.metric_value}\n"
                           f"阈值: {alert.threshold}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"发送警报邮件失败: {e}")
    
    def _register_default_checks(self):
        """注册默认健康检查"""
        
        def database_check():
            """数据库健康检查"""
            try:
                start_time = time.time()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                
                response_time = time.time() - start_time
                
                # 检查连接数
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """)
                connection_count = cursor.fetchone()[0]
                
                # 检查慢查询
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state = 'active'
                    AND query_start < now() - interval '10 seconds'
                """)
                slow_query_count = cursor.fetchone()[0]
                
                return {
                    'response_time': response_time,
                    'connection_count': connection_count,
                    'slow_query_count': slow_query_count
                }
                
            except Exception as e:
                self.alerts.trigger_alert(
                    "database_health",
                    "critical",
                    f"数据库健康检查失败: {e}",
                    "database"
                )
                return {'status': 0}
        
        def cache_check():
            """缓存健康检查"""
            try:
                start_time = time.time()
                test_key = f'health_check_{int(time.time())}'
                
                cache.set(test_key, 'test', 10)
                result = cache.get(test_key)
                cache.delete(test_key)
                
                response_time = time.time() - start_time
                
                if result != 'test':
                    raise Exception("缓存读写测试失败")
                
                return {
                    'response_time': response_time,
                    'status': 1
                }
                
            except Exception as e:
                self.alerts.trigger_alert(
                    "cache_health",
                    "warning",
                    f"缓存健康检查失败: {e}",
                    "cache"
                )
                return {'status': 0}
        
        def memory_check():
            """内存使用检查"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                
                memory_usage = memory.percent
                if memory_usage > 90:
                    self.alerts.trigger_alert(
                        "high_memory_usage",
                        "critical" if memory_usage > 95 else "warning",
                        f"内存使用率过高: {memory_usage:.1f}%",
                        "system",
                        memory_usage,
                        90
                    )
                
                return {
                    'usage_percent': memory_usage,
                    'available_mb': memory.available / 1024 / 1024
                }
                
            except ImportError:
                # psutil not available
                return {}
            except Exception as e:
                logger.error(f"内存检查失败: {e}")
                return {}
        
        # 注册检查
        self.health_checker.register_check('database', database_check, 30)
        self.health_checker.register_check('cache', cache_check, 60)
        self.health_checker.register_check('memory', memory_check, 60)
    
    def start(self):
        """启动监控"""
        self.health_checker.start()
        logger.info("系统监控已启动")
    
    def stop(self):
        """停止监控"""
        self.health_checker.stop()
        logger.info("系统监控已停止")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            'alerts': {
                'active': len(self.alerts.get_active_alerts()),
                'total': len(self.alerts.alerts)
            },
            'metrics': {
                'tracked_metrics': len(self.metrics.metrics),
                'total_samples': sum(len(samples) for samples in self.metrics.metrics.values())
            },
            'health_checks': {
                'registered': len(self.health_checker.checks),
                'running': self.health_checker.running
            }
        }


# 全局监控实例
system_monitor = SystemMonitor()

# 自动启动（可以在Django应用启动时调用）
def start_monitoring():
    """启动系统监控"""
    system_monitor.start()

def stop_monitoring():
    """停止系统监控"""
    system_monitor.stop()
