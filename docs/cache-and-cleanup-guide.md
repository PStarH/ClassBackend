# 缓存优化和数据清理使用指南

## 🚀 缓存层优化

### 1. 缓存服务使用

#### 获取用户日统计（带缓存）
```python
from apps.learning_plans.cache_services import LearningStatsCacheService

# 获取用户今日统计
daily_stats = LearningStatsCacheService.get_user_daily_stats(user_id)

# 获取指定日期统计
from datetime import date
daily_stats = LearningStatsCacheService.get_user_daily_stats(
    user_id, 
    date=date(2025, 6, 26)
)
```

#### 获取用户周统计
```python
# 获取用户本周统计
weekly_stats = LearningStatsCacheService.get_user_weekly_stats(user_id)

# 获取指定周统计
from datetime import date
week_start = date(2025, 6, 23)  # 周一
weekly_stats = LearningStatsCacheService.get_user_weekly_stats(user_id, week_start)
```

#### 获取用户学习分析
```python
# 获取用户会话分析（最近30天）
analytics = LearningStatsCacheService.get_user_session_analytics(user_id)

# 包含推荐建议
recommendations = analytics['recommendations']
```

#### 课程进度缓存
```python
from apps.learning_plans.cache_services import CourseProgressCacheService

# 获取用户课程进度摘要
summary = CourseProgressCacheService.get_user_course_summary(user_id)
```

### 2. 手动缓存管理

#### 预热用户缓存
```python
# 预计算用户的所有热点数据
LearningStatsCacheService.precompute_hot_data(user_id)

# 清除用户相关缓存
LearningStatsCacheService.invalidate_user_cache(user_id)
```

#### 缓存预热服务
```python
from apps.learning_plans.cache_signals import CacheWarmupService

# 预热指定用户缓存
CacheWarmupService.warmup_user_cache(user_id, force=True)

# 预热全局缓存
CacheWarmupService.warmup_global_cache()
```

### 3. 自动缓存管理

缓存会在以下情况自动失效和预热：

- **StudySession 保存/删除** → 自动清除用户统计缓存
- **CourseProgress 保存/删除** → 自动清除课程进度缓存
- **新学习会话完成** → 延迟5秒后自动预热缓存

## 🧹 数据清理策略

### 1. 手动数据清理

#### 基本清理命令
```bash
# 清理无效数据和归档历史数据（预演模式）
python manage.py cleanup_learning_data --dry-run

# 执行实际清理
python manage.py cleanup_learning_data

# 仅清理无效数据
python manage.py cleanup_learning_data --cleanup-invalid

# 自定义归档和删除时间
python manage.py cleanup_learning_data \
    --archive-older-than=180 \
    --delete-older-than=730 \
    --batch-size=500
```

#### 清理功能说明

1. **无效数据清理**：
   - 负数学习时长
   - 结束时间早于开始时间
   - 无效的评分和专注度数据
   - 重复的课程进度记录
   - 孤立的学习会话

2. **历史数据归档**：
   - 将旧数据移动到归档表
   - 保留数据完整性
   - 批量处理避免性能问题

3. **超旧数据删除**：
   - 删除归档表中的超旧数据
   - 清理非活跃用户的数据

### 2. 缓存预计算

#### 手动预计算
```bash
# 为所有活跃用户预计算缓存
python manage.py precompute_cache --precompute-cache

# 仅为最近7天活跃的用户预计算
python manage.py precompute_cache --precompute-cache --active-users-only

# 自定义活跃天数
python manage.py precompute_cache --precompute-cache --active-users-only --days-active=3
```

### 3. 定时任务配置

#### 如果使用 Celery

在 `settings.py` 中添加：

```python
# Celery 配置
CELERY_BEAT_SCHEDULE = {
    'precompute-active-cache': {
        'task': 'apps.learning_plans.tasks.precompute_active_users_cache',
        'schedule': 300.0,  # 每5分钟
    },
    'cleanup-expired-cache': {
        'task': 'apps.learning_plans.tasks.cleanup_expired_cache',
        'schedule': 3600.0,  # 每小时
    },
    'archive-old-data': {
        'task': 'apps.learning_plans.tasks.archive_old_learning_data',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
    'update-analytics': {
        'task': 'apps.learning_plans.tasks.update_learning_analytics',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨3点
    },
}
```

#### 如果使用系统 Cron

```bash
# 编辑 crontab
crontab -e

# 添加定时任务
# 每天凌晨2点执行数据清理
0 2 * * * cd /path/to/project && python manage.py cleanup_learning_data

# 每小时预计算活跃用户缓存
0 * * * * cd /path/to/project && python manage.py precompute_cache --precompute-cache --active-users-only
```

## 📊 监控和维护

### 1. 缓存效果监控

在日志中查看缓存命中情况：

```python
import logging
logger = logging.getLogger(__name__)

# 监控缓存命中率
def monitor_cache_performance():
    # 在 cache_services.py 中添加监控逻辑
    pass
```

### 2. 数据库优化建议

- **定期执行清理**：建议每周执行一次数据清理
- **监控表大小**：关注 `study_sessions` 表的增长速度
- **索引维护**：定期分析索引使用情况
- **备份策略**：在清理前确保有可靠的数据备份

### 3. 性能调优

#### 缓存配置优化
```python
# settings.py 中的缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        },
        'KEY_PREFIX': 'learning_platform',
        'TIMEOUT': 300,  # 默认5分钟过期
    }
}
```

#### 批处理优化
- 调整 `--batch-size` 参数适应服务器性能
- 在低峰期执行数据清理任务
- 使用数据库连接池优化

## 🔧 故障排除

### 常见问题

1. **缓存不生效**：
   - 检查 Redis 连接
   - 确认缓存键名正确
   - 查看日志中的错误信息

2. **数据清理失败**：
   - 检查数据库权限
   - 确认表结构完整
   - 使用 `--dry-run` 先测试

3. **性能问题**：
   - 减小批处理大小
   - 增加缓存过期时间
   - 优化数据库索引

### 日志监控

关键日志位置：
- 缓存相关：`apps.learning_plans.cache_services`
- 数据清理：`apps.learning_plans.management.commands`
- 信号处理：`apps.learning_plans.cache_signals`
