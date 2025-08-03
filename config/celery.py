"""
Celery配置 - 异步LLM任务队列
基于Redis作为消息代理和结果后端
"""
import os
from celery import Celery
from django.conf import settings
from decouple import config

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# 创建Celery实例
app = Celery('smart_classroom')

# 配置选项
app.config_from_object('django.conf:settings', namespace='CELERY')

# 基础配置
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/2')

app.conf.update(
    # 消息代理设置
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 结果过期时间
    result_expires=3600,  # 1小时
    
    # 任务路由 - LLM任务使用专用队列
    task_routes={
        'llm.core.enhanced_async_service.async_llm_completion_task': {'queue': 'llm_queue'},
        'llm.core.enhanced_async_service.batch_llm_completion_task': {'queue': 'llm_batch_queue'},
        'apps.*.tasks.*': {'queue': 'general_queue'},
    },
    
    # 队列配置
    task_default_queue='general_queue',
    task_queues={
        'llm_queue': {
            'exchange': 'llm',
            'exchange_type': 'direct',
            'routing_key': 'llm',
        },
        'llm_batch_queue': {
            'exchange': 'llm_batch',
            'exchange_type': 'direct', 
            'routing_key': 'llm_batch',
        },
        'general_queue': {
            'exchange': 'general',
            'exchange_type': 'direct',
            'routing_key': 'general',
        },
    },
    
    # Worker配置
    worker_prefetch_multiplier=1,  # LLM任务比较重，每次只处理一个
    worker_max_tasks_per_child=50,  # 防止内存泄漏
    worker_disable_rate_limits=False,
    
    # 任务优先级
    task_inherit_parent_priority=True,
    task_default_priority=5,
    worker_direct=True,
    
    # 重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 默认重试延迟
    task_max_retries=3,
    
    # 监控
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 安全设置
    worker_hijack_root_logger=False,
    worker_log_color=False,
    
    # 性能优化
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Redis连接池
    broker_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        },
        'connection_pool_kwargs': {
            'max_connections': 20,
            'retry_on_timeout': True,
        }
    },
    
    # 结果后端设置
    result_backend_transport_options={
        'master_name': 'mymaster',
        'retry_policy': {
            'timeout': 5.0
        },
        'connection_pool_kwargs': {
            'max_connections': 20,
            'retry_on_timeout': True,
        }
    },
    
    # Beat调度器设置 (如果需要定时任务)
    beat_schedule={
        'cleanup-llm-cache': {
            'task': 'apps.learning_plans.tasks.cleanup_cache',
            'schedule': 3600.0,  # 每小时清理一次
        },
        'update-performance-metrics': {
            'task': 'core.monitoring.tasks.update_metrics',
            'schedule': 300.0,  # 每5分钟更新指标
        },
    },
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
)

# 自动发现任务
app.autodiscover_tasks()

# LLM专用配置
LLM_TASK_CONFIG = {
    'soft_time_limit': config('LLM_TASK_SOFT_TIMEOUT', default=60, cast=int),
    'time_limit': config('LLM_TASK_HARD_TIMEOUT', default=120, cast=int),
    'max_retries': config('LLM_TASK_MAX_RETRIES', default=3, cast=int),
    'default_retry_delay': config('LLM_TASK_RETRY_DELAY', default=60, cast=int),
    'rate_limit': config('LLM_TASK_RATE_LIMIT', default='10/m'),  # 每分钟最多10个任务
}

# 应用LLM任务配置
for task_name in ['async_llm_completion_task', 'batch_llm_completion_task']:
    if hasattr(app, 'tasks') and task_name in app.tasks:
        task = app.tasks[task_name]
        for key, value in LLM_TASK_CONFIG.items():
            setattr(task, key, value)


@app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')


# 信号处理
from celery.signals import worker_ready, worker_shutdown, task_prerun, task_postrun
import logging

logger = logging.getLogger(__name__)

@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Worker启动信号"""
    logger.info(f"Celery worker ready: {sender}")

@worker_shutdown.connect 
def worker_shutdown_handler(sender=None, **kwargs):
    """Worker关闭信号"""
    logger.info(f"Celery worker shutdown: {sender}")

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """任务开始前信号"""
    if 'llm' in str(task):
        logger.info(f"LLM任务开始: {task_id} - {task}")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """任务完成后信号"""
    if 'llm' in str(task):
        logger.info(f"LLM任务完成: {task_id} - 状态: {state}")


# 健康检查任务
@app.task
def health_check():
    """健康检查任务"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # 检查Redis连接
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        
        return {'status': 'healthy', 'timestamp': app.now()}
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {'status': 'unhealthy', 'error': str(e), 'timestamp': app.now()}


# 性能监控任务
@app.task
def collect_performance_metrics():
    """收集性能指标"""
    try:
        from llm.core.enhanced_async_service import EnhancedAsyncLLMService
        
        service = EnhancedAsyncLLMService()
        stats = service.get_performance_stats()
        
        # 存储到缓存或数据库
        from django.core.cache import cache
        cache.set('llm_performance_stats', stats, 300)  # 5分钟
        
        return stats
    except Exception as e:
        logger.error(f"性能指标收集失败: {e}")
        return {'error': str(e)}


if __name__ == '__main__':
    app.start()