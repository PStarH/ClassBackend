# Django Redis 缓存配置说明

本项目使用 `django-redis` 来提供高性能的 Redis 缓存支持，确保 API 的稳定性和性能。

## 🚀 功能特性

### 1. 多层缓存架构
- **Default Cache**: 默认缓存，用于通用数据缓存
- **API Cache**: 专用于 API 响应缓存
- **Sessions Cache**: 用户会话缓存

### 2. 智能中间件
- **速率限制中间件**: 防止 API 被恶意调用
- **响应缓存中间件**: 自动缓存 GET 请求的响应
- **健康检查中间件**: 监控 Redis 连接状态

### 3. 缓存工具类
- **CacheService**: 统一的缓存操作接口
- **UserCacheManager**: 用户相关数据缓存管理
- **APICacheManager**: API 响应缓存管理

## 📦 安装和配置

### 1. 安装依赖
```bash
pip install redis django-redis
```

### 2. 环境变量配置
```bash
# Redis 连接配置
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_SESSIONS_URL=redis://127.0.0.1:6379/2
REDIS_API_CACHE_URL=redis://127.0.0.1:6379/3

# API 限制配置
API_RATE_LIMIT=100              # 每分钟最大请求数
API_RATE_LIMIT_PERIOD=60        # 速率限制时间窗口（秒）
API_CACHE_TIMEOUT=300           # API 缓存超时时间（秒）
```

### 3. 启动 Redis
```bash
# 使用 Docker
docker run -d --name redis -p 6379:6379 redis:latest

# 或使用 Homebrew (macOS)
brew install redis
brew services start redis
```

## 🛠️ 使用方法

### 1. 在视图中使用缓存

#### 继承 CachedAPIView
```python
from core.views import CachedAPIView

class MyAPIView(CachedAPIView):
    cache_timeout = 600  # 10分钟缓存
    
    def get(self, request):
        # 自动缓存 GET 请求响应
        return Response(data)
```

#### 使用缓存装饰器
```python
from core.cache import cache_result

@cache_result(timeout=300, cache_alias='api_cache')
def expensive_calculation():
    # 耗时的计算
    return result
```

#### 手动缓存管理
```python
from core.cache import UserCacheManager, APICacheManager

# 用户缓存
UserCacheManager.set_user_cache(user_id, 'profile', data, 1800)
cached_profile = UserCacheManager.get_user_cache(user_id, 'profile')

# API 缓存
APICacheManager.cache_api_response('users', data, 600)
cached_response = APICacheManager.get_cached_api_response('users')
```

### 2. 管理命令

#### 清理缓存
```bash
# 清理所有缓存
python manage.py clear_cache --cache all

# 清理特定缓存
python manage.py clear_cache --cache default
python manage.py clear_cache --cache api

# 按模式清理
python manage.py clear_cache --pattern "user:*"

# 预览模式（不实际删除）
python manage.py clear_cache --dry-run
```

#### 监控缓存性能
```bash
# 监控缓存性能
python manage.py monitor_cache --interval 5 --duration 60
```

### 3. 健康检查

访问以下端点检查系统状态：
- `/api/v1/health/` - 基础健康检查
- `/health/` - 详细健康检查页面
- `/api/v1/cache-stats/` - 缓存统计信息

## 🔧 配置说明

### 缓存配置参数
- `max_connections`: 连接池最大连接数
- `retry_on_timeout`: 超时时自动重试
- `socket_keepalive`: 保持 socket 连接
- `health_check_interval`: 健康检查间隔
- `IGNORE_EXCEPTIONS`: 忽略 Redis 异常，不影响应用

### 性能优化建议
1. **合理设置缓存超时时间**：根据数据更新频率调整
2. **使用压缩器**：对大数据启用压缩
3. **分离不同类型的缓存**：使用不同的 Redis 数据库
4. **监控缓存命中率**：定期检查缓存效果

## 🚨 故障处理

### Redis 连接问题
1. 检查 Redis 服务是否启动
2. 验证连接字符串是否正确
3. 检查防火墙设置
4. 查看 Django 日志获取详细错误信息

### 缓存性能问题
1. 监控 Redis 内存使用
2. 检查缓存键的设计是否合理
3. 调整连接池大小
4. 考虑使用 Redis 集群

## 📊 监控和调试

### 缓存命中率监控
```python
# 在视图中添加缓存命中统计
response['X-Cache'] = 'HIT' if cached else 'MISS'
```

### 日志记录
项目已配置详细的缓存操作日志，可以通过日志分析缓存使用情况。

## 🔐 安全考虑

1. **Redis 访问控制**: 在生产环境中配置 Redis 密码
2. **网络安全**: 使用 VPN 或私有网络连接 Redis
3. **数据加密**: 敏感数据在缓存前进行加密
4. **键命名空间**: 使用适当的键前缀避免冲突

## 📈 性能指标

通过 Redis 缓存，预期可以获得：
- API 响应时间减少 60-80%
- 数据库查询量减少 70-90%
- 系统并发能力提升 3-5 倍
- 用户体验显著改善

## 🤝 最佳实践

1. **缓存键设计**: 使用有意义且唯一的键名
2. **缓存失效策略**: 合理设置过期时间
3. **缓存预热**: 对热点数据进行预缓存
4. **错误处理**: 缓存失败时的降级策略
5. **版本控制**: 使用版本号管理缓存数据结构变更

---

通过以上配置，你的 Django API 将具备高性能的缓存支持，确保在高并发情况下的稳定运行。
