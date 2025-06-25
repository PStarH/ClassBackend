# 教育平台后端 API

一个基于 Django + LangChain 的教育平台后端服务，提供 AI 驱动的学习规划和课程管理功能。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd ClassBackend

# 创建虚拟环境 (推荐使用 Python 3.8+)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements/development.txt
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
- `DEEPSEEK_API_KEY`: DeepSeek AI API 密钥

其他配置项请参考 `.env.example` 文件。

### 3. 数据库设置

```bash
# 运行数据库迁移
python manage.py makemigrations
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

### 实际数据库表结构

#### 1. 用户认证相关表

**user_profiles** - 用户资料扩展表
- `id` - 主键 (UUID)
- `user_id` - 关联Django用户表 (OneToOne)
- `phone` - 手机号
- `avatar` - 头像 (ImageField)
- `bio` - 个人简介
- `birth_date` - 出生日期
- `learning_style` - 学习风格 (visual/auditory/kinesthetic/reading/mixed)
- `timezone` - 时区
- `email_notifications` - 邮件通知设置
- `is_profile_public` - 资料公开设置
- `is_active` - 激活状态
- `created_at`, `updated_at` - 时间戳

**email_verifications** - 邮箱验证表
- `id` - 主键 (UUID)
- `user_id` - 关联用户 (ForeignKey)
- `email` - 邮箱地址
- `verification_code` - 验证码 (6位)
- `is_verified` - 验证状态
- `verified_at` - 验证时间
- `expires_at` - 过期时间
- `is_active` - 激活状态
- `created_at`, `updated_at` - 时间戳

#### 2. 学习计划相关表

**learning_goals** - 学习目标表
- `id` - 主键 (UUID)
- `title` - 目标标题
- `description` - 目标描述
- `goal_type` - 目标类型 (skill/knowledge/certification/project)
- `difficulty` - 难度等级 (beginner/intermediate/advanced)
- `estimated_hours` - 预估学习时长
- `is_active` - 激活状态
- `created_at`, `updated_at` - 时间戳

**learning_plans** - 学习计划表
- `id` - 主键 (UUID)
- `user_id` - 关联用户 (ForeignKey)
- `title` - 计划标题
- `description` - 计划描述
- `status` - 状态 (draft/active/completed/paused/cancelled)
- `start_date` - 开始日期
- `target_end_date` - 目标结束日期
- `actual_end_date` - 实际结束日期
- `total_estimated_hours` - 总预估时长
- `ai_recommendations` - AI推荐内容 (JSON字段)
- `is_active` - 激活状态
- `is_deleted` - 软删除标记
- `deleted_at` - 删除时间
- `created_at`, `updated_at` - 时间戳

**learning_plan_goals** - 学习计划目标关联表
- `id` - 主键 (UUID)
- `learning_plan_id` - 关联学习计划 (ForeignKey)
- `learning_goal_id` - 关联学习目标 (ForeignKey)
- `status` - 状态 (not_started/in_progress/completed/skipped)
- `order` - 顺序
- `actual_hours` - 实际学习时长
- `completion_date` - 完成时间
- `notes` - 学习笔记
- `is_active` - 激活状态
- `created_at`, `updated_at` - 时间戳

**study_sessions** - 学习会话表
- `id` - 主键 (UUID)
- `learning_plan_id` - 关联学习计划 (ForeignKey)
- `goal_id` - 关联学习目标 (ForeignKey)
- `start_time` - 开始时间
- `end_time` - 结束时间
- `duration_minutes` - 学习时长(分钟)
- `content_covered` - 学习内容
- `effectiveness_rating` - 学习效果评分(1-5)
- `notes` - 学习笔记
- `is_active` - 激活状态
- `created_at`, `updated_at` - 时间戳

#### 3. 其他表

**tutorials** - 教程表
- `id` - 主键 (BigAutoField)
- `title` - 教程标题
- `description` - 教程描述
- `published` - 发布状态

**authtoken_token** - API认证令牌表 (Django REST Framework)
- `key` - 令牌键 (主键)
- `user_id` - 关联用户
- `created` - 创建时间

#### 4. Django系统表

**auth_user** - Django用户表
- Django内置用户表，包含username, email, password等字段

**django_migrations** - Django迁移记录表
- 记录数据库迁移历史

**django_session** - Django会话表
- 存储用户会话信息

## 🔗 API 接口文档

### 基础URL
- 开发环境: `http://127.0.0.1:8000/`
- API版本: `v1`
- API根路径: `/api/v1/`

### 1. 用户认证接口

**基础路径**: `/api/v1/auth/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/register/` | 用户注册 | 否 |
| POST | `/login/` | 用户登录 | 否 |
| POST | `/logout/` | 用户登出 | 是 |
| GET | `/profile/` | 获取用户资料 | 是 |
| PUT/PATCH | `/profile/` | 更新用户资料 | 是 |
| GET | `/profile/detail/` | 获取详细用户资料 | 是 |
| POST | `/password/change/` | 修改密码 | 是 |
| POST | `/email/send-code/` | 发送邮箱验证码 | 是 |
| POST | `/email/verify/` | 验证邮箱 | 是 |

#### 注册示例
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "password_confirm": "testpass123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

#### 登录示例
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpass123"
  }'
```

### 2. 学习计划接口

**基础路径**: `/api/v1/learning-plans/api/`

#### 学习目标 (Goals)
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/goals/` | 获取学习目标列表 | 是 |
| POST | `/goals/` | 创建学习目标 | 是 |
| GET | `/goals/{id}/` | 获取单个学习目标 | 是 |
| PUT/PATCH | `/goals/{id}/` | 更新学习目标 | 是 |
| DELETE | `/goals/{id}/` | 删除学习目标 | 是 |

#### 学习计划 (Plans)
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/plans/` | 获取学习计划列表 | 是 |
| POST | `/plans/` | 创建学习计划 | 是 |
| GET | `/plans/{id}/` | 获取单个学习计划 | 是 |
| PUT/PATCH | `/plans/{id}/` | 更新学习计划 | 是 |
| DELETE | `/plans/{id}/` | 删除学习计划 | 是 |

#### 学习会话 (Sessions)
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/sessions/` | 获取学习会话列表 | 是 |
| POST | `/sessions/` | 创建学习会话 | 是 |
| GET | `/sessions/{id}/` | 获取单个学习会话 | 是 |
| PUT/PATCH | `/sessions/{id}/` | 更新学习会话 | 是 |
| DELETE | `/sessions/{id}/` | 删除学习会话 | 是 |

#### AI 学习计划生成
| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/v1/learning-plans/api/ai/generate-plan/` | AI生成学习计划 | 是 |

### 3. 教程接口

**基础路径**: `/api/v1/tutorials/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/` | 获取教程列表 | 是 |
| POST | `/` | 创建教程 | 是 |
| GET | `/{id}/` | 获取单个教程 | 是 |
| PUT/PATCH | `/{id}/` | 更新教程 | 是 |
| DELETE | `/{id}/` | 删除教程 | 是 |

### 4. AI 服务接口

#### AI 顾问服务
**基础路径**: `/api/advisor/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/plan/create` | 创建AI学习计划 | 是 |
| POST | `/plan/update` | 更新AI学习计划 | 是 |
| POST | `/plan/chat` | AI对话服务 | 是 |
| GET | `/session/plan` | 获取会话学习计划 | 是 |
| POST | `/session/clear` | 清除会话 | 是 |

#### AI 教师服务
**基础路径**: `/api/teacher/`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/create-outline/` | 创建课程大纲 | 是 |
| POST | `/generate-section-detail/` | 生成章节详情 | 是 |

### 5. 系统接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/health/` | 健康检查 | 否 |
| GET | `/admin/` | 管理后台 | 管理员 |

## 🔐 认证方式

本API支持以下认证方式：

1. **Token认证** (推荐)
   ```bash
   Authorization: Token your_api_token_here
   ```

2. **Session认证** (用于Web界面)
   - 通过Django会话系统

### 获取Token
登录成功后，响应中会包含token字段：
```json
{
  "message": "登录成功",
  "user": {...},
  "token": "88cca192b4e0c7f85476203571a57c4c1db4919d"
}
```

## 📝 API 使用示例

### 创建学习计划
```bash
curl -X POST http://127.0.0.1:8000/api/v1/learning-plans/api/plans/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token_here" \
  -d '{
    "title": "Python编程学习计划",
    "description": "从基础到进阶的Python学习计划",
    "status": "active",
    "start_date": "2025-01-01",
    "target_end_date": "2025-06-01"
  }'
```

### 获取用户学习计划
```bash
curl -X GET http://127.0.0.1:8000/api/v1/learning-plans/api/plans/ \
  -H "Authorization: Token your_token_here"
```

### AI对话服务
```bash
curl -X POST http://127.0.0.1:8000/api/advisor/plan/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token_here" \
  -d '{
    "message": "我想学习Python，请帮我制定一个学习计划",
    "session_id": "optional_session_id"
  }'
```

## 🔒 错误码说明

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 🧪 测试指南

### 自动化测试
```bash
# 运行所有测试
python manage.py test

# 运行特定应用测试
python manage.py test apps.authentication
python manage.py test apps.learning_plans
```

### 手动测试API
```bash
# 1. 健康检查
curl http://127.0.0.1:8000/health/

# 2. 用户注册
curl -X POST http://127.0.0.1:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "testpass123", "password_confirm": "testpass123"}'

# 3. 用户登录
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# 4. 访问受保护资源 (使用返回的token)
curl -X GET http://127.0.0.1:8000/api/v1/auth/profile/ \
  -H "Authorization: Token your_token_here"
```

## 🚀 部署指南

### 开发环境部署
```bash
# 克隆项目
git clone <repository-url>
cd ClassBackend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements/development.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件

# 数据库迁移
python manage.py migrate

# 启动服务
python manage.py runserver
```

### 生产环境部署
```bash
# 安装生产依赖
pip install -r requirements/production.txt

# 设置环境变量
export DJANGO_SETTINGS_MODULE=config.settings.production
export DEBUG=False

# 收集静态文件
python manage.py collectstatic --noinput

# 使用Gunicorn启动
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

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
- **AI集成**: LangChain + DeepSeek API
- **认证**: Token-based认证

### 核心组件
1. **用户管理**: Django内置用户系统 + 扩展资料
2. **学习计划**: 目标导向的学习管理系统
3. **AI服务**: 智能学习建议和计划生成
4. **会话管理**: 学习过程跟踪和记录

### 数据流
```
用户请求 → Django路由 → 视图处理 → 业务逻辑 → 数据库操作 → JSON响应
                    ↓
                AI服务调用 → DeepSeek API → 智能推荐
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
- 配置正确的DeepSeek API密钥
- 在生产环境中使用强密码和HTTPS
- 定期备份数据库

**快速验证项目是否正常运行**:
```bash
# 启动服务后访问
curl http://127.0.0.1:8000/health/
# 应该返回HTTP 200状态码
```