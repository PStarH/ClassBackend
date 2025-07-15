# 教育平台后端 API

一个基于 Django + AI 的教育平台后端服务，提供用户管理、课程内容、学习进度跟踪和 AI 驱动的个性化学习功能。

## ✅ 项目状态 (2025-07-11)

**🎉 所有核心服务已验证并正常运行:**
- ✅ Django REST API Framework - 生产就绪
- ✅ PostgreSQL 数据库 - 已优化索引
- ✅ LangChain AI 服务 - 支持优雅降级
- ✅ Redis 缓存 - 多层缓存策略
- ✅ 用户认证 - Token 认证完整实现
- ✅ 跨服务集成 - 所有组件协调工作
- ✅ 前端文档 - 完整的 API 文档已提供

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd ClassBackend

# 创建虚拟环境 (推荐使用 Python 3.13+)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements/base.txt
```

### 2. 环境配置

复制示例环境配置文件并填入实际值：

```bash
cp .env.example .env
# 然后编辑 .env 文件，填入你的实际配置
```

必需的环境变量：
- `SECRET_KEY`: Django 密钥（生产环境需要设置为复杂的随机字符串）
- `DB_PASSWORD`: PostgreSQL 数据库密码
- `DEEPSEEK_API_KEY`: DeepSeek AI API 密钥（可选）

其他配置项请参考 `.env.example` 文件。

### 3. 数据库设置

```bash
# 运行数据库迁移
python manage.py migrate

# 创建超级用户（可选）
python manage.py createsuperuser
```

### 4. 启动服务

```bash
# 启动开发服务器
python manage.py runserver

# 服务器将在 http://127.0.0.1:8000/ 启动
```

## 📊 数据库结构

### 标准化数据库设计

经过精简和标准化，本项目仅保留 **5 个核心数据表**，确保结构清晰、性能优化：

#### 1. 用户相关表 (authentication 应用)

**users** - 用户账户表
- `uuid` - 主键 (UUID, Primary Key)
- `username` - 用户名 (VARCHAR, 唯一)
- `email` - 邮箱地址 (VARCHAR, 唯一)
- `first_name` - 名字 (VARCHAR)
- `last_name` - 姓氏 (VARCHAR)
- `password` - 密码哈希 (VARCHAR)
- `is_active` - 激活状态 (BOOLEAN)
- `is_staff` - 管理员状态 (BOOLEAN)
- `date_joined` - 注册时间 (TIMESTAMP)
- `last_login` - 最后登录时间 (TIMESTAMP)

**user_settings** - 用户设置表
- `user_uuid_id` - 用户UUID (UUID, Primary Key, FK → users.uuid)
- `preferred_pace` - 学习节奏 (slow/normal/fast)
- `preferred_style` - 学习风格 (visual/auditory/reading/kinesthetic)
- `tone` - 交互语调 (encouraging/professional/casual)
- `feedback_frequency` - 反馈频率 (low/medium/high)
- `major` - 专业方向 (VARCHAR)
- `education_level` - 教育水平 (VARCHAR)
- `notes` - 备注 (TEXT)
- `skills` - 技能列表 (TEXT[], PostgreSQL Array)
- `created_at`, `updated_at` - 时间戳

#### 2. 课程相关表 (courses 应用)

**course_contents** - 课程内容表
- `content_id` - 主键 (UUID, Primary Key)
- `title` - 内容标题 (VARCHAR)
- `description` - 内容描述 (TEXT)
- `content_type` - 内容类型 (VARCHAR)
- `difficulty_level` - 难度等级 (VARCHAR)
- `estimated_duration` - 预估时长 (INTEGER, 分钟)
- `prerequisites` - 前置要求 (TEXT)
- `learning_objectives` - 学习目标 (TEXT)
- `content_url` - 内容链接 (URL)
- `is_active` - 激活状态 (BOOLEAN)
- `created_at`, `updated_at` - 时间戳

**course_progress** - 课程进度表
- `course_uuid` - 主键 (UUID, Primary Key)
- `user_uuid_id` - 用户UUID (UUID, FK → users.uuid)
- `content_id` - 内容ID (UUID, FK → course_contents.content_id)
- `progress_percentage` - 进度百分比 (DECIMAL, 0-100)
- `status` - 状态 (not_started/in_progress/completed/paused)
- `started_at` - 开始时间 (TIMESTAMP)
- `completed_at` - 完成时间 (TIMESTAMP)
- `time_spent_minutes` - 学习时长 (INTEGER, 分钟)
- `last_accessed` - 最后访问时间 (TIMESTAMP)
- `notes` - 学习笔记 (TEXT)
- `created_at`, `updated_at` - 时间戳
- **唯一约束**: (user_uuid_id, content_id)

#### 3. 学习会话表 (learning_plans 应用)

**study_sessions** - 学习会话表
- `id` - 主键 (UUID, Primary Key)
- `user_id` - 用户ID (UUID, FK → users.uuid)
- `start_time` - 开始时间 (TIMESTAMP)
- `end_time` - 结束时间 (TIMESTAMP, 可空)
- `duration_minutes` - 学习时长 (INTEGER, 分钟)
- `content_covered` - 学习内容 (TEXT)
- `effectiveness_rating` - 效果评分 (SMALLINT, 1-5)
- `is_active` - 当前是否进行中 (BOOLEAN)
- `notes` - 学习笔记 (TEXT)
- `goal_id` - 学习目标ID (UUID, 可空)
- `learning_plan_id` - 学习计划ID (UUID, 可空)
- `created_at`, `updated_at` - 时间戳

### 🔗 数据库关系

```
users (1) ←→ (1) user_settings
users (1) ←→ (n) course_progress ←→ (1) course_contents  
users (1) ←→ (n) study_sessions
```

### 🚀 性能优化

#### 高级索引策略
- **主键索引**: 所有表的主键自动创建索引
- **外键索引**: 所有外键字段自动创建索引
- **复合索引**: 
  - `course_progress(user_uuid_id, content_id)` - 查询用户课程进度
  - `study_sessions(user_id, start_time)` - 查询用户学习记录
  - `study_sessions(is_active, start_time)` - 查询活跃会话
  - `study_sessions(user, effectiveness_rating, duration_minutes)` - 性能分析
  - `study_sessions(learning_environment, effectiveness_rating)` - 环境效果分析
- **唯一索引**: `users.email`, `course_progress(user_uuid_id, content_id)`
- **部分索引**: 仅针对活跃数据的条件索引
- **函数索引**: 基于时间函数的索引优化

#### 缓存策略
- **多层缓存**: Redis 多数据库分离（默认/会话/API/用户）
- **智能缓存**: 基于标签的缓存失效机制
- **查询缓存**: 自动缓存频繁查询的结果
- **用户数据预热**: 活跃用户数据自动预热
- **缓存压缩**: Zlib 压缩减少内存使用

#### 数据库连接优化
- **连接池**: 支持连接复用和健康检查
- **查询优化**: 自动 select_related 和 prefetch_related
- **批处理**: 优化的批量创建和更新操作
- **慢查询监控**: 自动检测和记录慢查询

#### 约束保障
- **外键约束**: 确保数据完整性
- **唯一约束**: 防止重复数据
- **检查约束**: 
  - 学习进度百分比 0-100
  - 学习效果评分 1-5
  - 结束时间晚于开始时间
  - 学习时长非负数
  - 密码强度验证
  - 登录失败次数限制

## 🔐 安全性增强

### 数据安全
- **密码强度**: 要求包含大小写字母、数字和特殊字符
- **账户锁定**: 5次失败登录后锁定30分钟
- **双因素认证**: 支持 TOTP 双因素认证
- **邮箱验证**: 强制邮箱验证机制
- **会话安全**: IP地址和设备指纹跟踪
- **数据脱敏**: 敏感数据自动脱敏处理

### 访问控制
- **行级安全**: 用户只能访问自己的数据
- **权限验证**: 细粒度的权限检查
- **API限流**: 防止API滥用和攻击
- **CSRF保护**: 跨站请求伪造防护
- **XSS防护**: 跨站脚本攻击防护

### 审计和监控
- **审计日志**: 完整的用户操作审计
- **安全事件**: 自动记录可疑活动
- **性能监控**: 慢查询和异常操作监控
- **缓存监控**: Redis 缓存状态监控

### 数据保护
- **软删除**: 重要数据软删除机制
- **数据备份**: 支持数据备份和恢复
- **隐私控制**: 用户隐私设置管理
- **合规支持**: GDPR 等数据保护法规支持

## ⚡ 性能优化功能

### 自动化优化
- **查询优化**: 自动优化 ORM 查询
- **索引建议**: 智能索引使用分析
- **批处理**: 大数据量操作优化
- **连接池**: 数据库连接复用

### 缓存系统
- **多级缓存**: 分层缓存策略
- **智能失效**: 基于模型变更的自动失效
- **预热机制**: 热点数据预加载
- **压缩存储**: 减少内存占用

### 监控工具
- **性能分析**: 实时性能指标监控
- **资源使用**: 数据库和缓存使用统计
- **告警机制**: 异常情况自动告警

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查PostgreSQL是否运行
   pg_ctl status
   # 检查数据库配置
   python manage.py check --database
   ```

2. **Token认证失败**
   ```bash
   # 确保Header格式正确
   Authorization: Token your_actual_token_here
   ```

3. **AI服务不可用**
   ```bash
   # 检查DeepSeek API配置
   python -c "from config.settings import base; print(base.DEEPSEEK_API_KEY)"
   ```

### 日志查看
```bash
# 查看Django日志（开发环境会在控制台显示）
python manage.py runserver --verbosity=2

# 查看特定应用日志（在代码中使用logger）
import logging
logger = logging.getLogger('apps')
logger.debug('Debug message')
```

## 📚 技术文档

### 架构设计
- **MVC架构**: Django的MVT模式
- **REST API**: 基于Django REST Framework
- **数据库**: PostgreSQL关系型数据库
- **AI集成**: 可选的AI服务支持
- **认证**: Token-based认证

### 核心组件
1. **用户管理**: Django内置用户系统 + 用户设置扩展
2. **课程管理**: 课程内容和学习进度跟踪
3. **学习会话**: 学习过程记录和统计
4. **设置管理**: 个性化学习偏好配置

### 数据流
```
用户请求 → Django路由 → 视图处理 → 业务逻辑 → 数据库操作 → JSON响应
```

### 项目结构
```
ClassBackend/
├── apps/
│   ├── authentication/     # 用户认证和设置
│   ├── courses/           # 课程内容和进度
│   └── learning_plans/    # 学习会话管理
├── config/
│   ├── settings/          # 环境配置
│   ├── urls.py           # 全局路由
│   └── wsgi.py           # WSGI配置
├── core/
│   ├── models/           # 基础模型
│   ├── middleware.py     # 中间件
│   └── views.py          # 通用视图
├── requirements/         # 依赖管理
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
└── manage.py            # Django管理脚本
```

## 🤝 贡献指南

### 开发流程
1. Fork项目到个人仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 开发和测试新功能
4. 提交代码: `git commit -m "Add new feature"`
5. 推送分支: `git push origin feature/new-feature`
6. 创建Pull Request

### 代码规范
- 遵循PEP 8代码风格
- 使用有意义的变量和函数名
- 添加适当的注释和文档字符串
- 编写单元测试

### 提交信息格式
```
type(scope): description

body

footer
```

示例:
```
feat(auth): add email verification functionality

- Add email verification model
- Create verification code generation
- Implement email sending service

Closes #123
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- **项目维护者**: [您的姓名]
- **邮箱**: [您的邮箱]
- **GitHub**: [您的GitHub地址]
- **问题反馈**: 请在GitHub Issues中提交

---

## 🔄 更新日志

### v2.0.0 (2025-06-26) - 数据库标准化重构
- ✅ **数据库标准化**: 精简至5个核心表，提升性能和可维护性
- ✅ **外键完整性**: 为study_sessions表添加用户外键关联
- ✅ **字段标准化**: 统一字段类型和命名规范
- ✅ **索引优化**: 添加复合索引，提升查询效率
- ✅ **约束加强**: 添加检查约束，确保数据有效性
- ✅ **代码清理**: 移除冗余应用和无用代码
- ✅ **迁移整理**: 清理历史迁移，生成标准化迁移文件

### v1.0.0 (2025-06-25)
- ✅ 完成用户认证系统
- ✅ 实现学习计划管理
- ✅ 集成AI学习顾问服务
- ✅ 支持Token认证
- ✅ 完整的API文档

### 即将推出
- 📝 学习进度可视化
- 🎯 个性化推荐算法
- 📊 学习数据分析
- 🔔 消息通知系统

---

**注意**: 
- 确保PostgreSQL数据库正在运行
- 配置正确的环境变量（.env文件）
- 在生产环境中使用强密码和HTTPS
- 定期备份数据库

**快速验证项目是否正常运行**:
```bash
# 启动服务后访问
curl http://127.0.0.1:8000/health/
# 应该返回HTTP 200状态码

# 检查数据库结构
python manage.py check
# 应该显示 "System check identified no issues"
```

**数据库结构验证**:
```bash
# 验证核心表存在
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT table_name FROM information_schema.tables WHERE table_name IN ('users', 'user_settings', 'course_contents', 'course_progress', 'study_sessions')\")
print('核心表:', [row[0] for row in cursor.fetchall()])
"
```