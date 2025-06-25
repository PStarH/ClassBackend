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
# 验证配置是否正确
python manage.py check

# 启动开发服务器
python manage.py runserver

# 服务将在 http://127.0.0.1:8000 启动
```

启动成功后，可以访问：
- 健康检查: http://127.0.0.1:8000/health/
- 管理后台: http://127.0.0.1:8000/admin/

## 📁 项目结构

```
ClassBackend/
├── config/                         # Django 配置管理
│   ├── settings/                   # 分环境配置
│   │   ├── base.py                # 基础配置
│   │   ├── development.py         # 开发环境
│   │   ├── production.py          # 生产环境
│   │   └── testing.py             # 测试环境
│   ├── urls.py                    # 主路由配置（新架构）
│   └── wsgi.py                    # WSGI 配置
├── core/                          # 核心功能模块
│   ├── models/                    # 基础数据模型
│   │   ├── base.py               # 基础模型类
│   │   └── mixins.py             # 模型混入
│   └── views.py                  # 核心视图
├── apps/                          # 业务应用模块
│   ├── ai_services/               # AI 服务模块（新架构）
│   ├── learning_plans/            # 学习计划模块
│   ├── courses/                   # 课程管理模块
│   └── user_sessions/             # 用户会话模块
├── llm/                           # LLM AI 服务（重构后）
│   ├── core/                      # 核心AI服务
│   │   ├── base_service.py       # AI基础服务类
│   │   ├── client.py             # LLM客户端管理
│   │   ├── config.py             # AI配置
│   │   ├── models.py             # Pydantic数据模型
│   │   └── prompts.py            # 提示词模板
│   ├── services/                  # AI业务服务
│   │   ├── advisor_service.py    # 学习顾问服务
│   │   ├── teacher_service.py    # 教师服务
│   │   └── memory_service.py     # 记忆管理服务
│   ├── advisor/                   # 学习顾问API
│   │   ├── views.py              # 顾问视图
│   │   └── urls.py               # 顾问路由
│   └── teacher/                   # 教师服务API
│       ├── views.py              # 教师视图
│       └── urls.py               # 教师路由
├── infrastructure/                # 基础设施
│   └── ai/                       # AI 基础设施（新架构）
├── tutorials/                     # 原有教程模块
└── DjangoRestApisPostgreSQL/      # AI配置文件（保留DeepSeek配置）
```

## 📋 API 端点

### 健康检查
- `GET /health/` - 服务健康检查
- `GET /admin/` - Django 管理后台

### 学习顾问 API
基础路径: `/api/advisor/`

- `POST /api/advisor/plan/create` - 创建学习计划
  ```json
  {
    "topic": "Python编程",
    "level": "beginner",
    "duration": "30天"
  }
  ```

- `POST /api/advisor/plan/update` - 更新学习计划
  ```json
  {
    "plan_id": "123",
    "feedback": "需要更多实践项目",
    "adjustments": ["增加项目练习", "减少理论部分"]
  }
  ```

- `POST /api/advisor/plan/chat` - 与学习顾问聊天
  ```json
  {
    "message": "我在学习函数时遇到困难",
    "context": "正在学习Python基础"
  }
  ```

- `GET /api/advisor/session/plan` - 获取会话中的学习计划
- `POST /api/advisor/session/clear` - 清除会话数据

### 教师服务 API
基础路径: `/api/teacher/`

- `POST /api/teacher/create-outline/` - 创建课程大纲
  ```json
  {
    "subject": "数据结构与算法",
    "level": "intermediate",
    "duration": "12周"
  }
  ```

- `POST /api/teacher/generate-section-detail/` - 生成章节详细内容
  ```json
  {
    "outline_id": "456",
    "section_id": "2.1",
    "detail_level": "comprehensive"
  }
  ```

### 教程模块 API
基础路径: `/api/v1/tutorials/`

- `GET /api/v1/tutorials/` - 获取所有教程
- `POST /api/v1/tutorials/` - 创建新教程
- `GET /api/v1/tutorials/{id}/` - 获取特定教程
- `PUT /api/v1/tutorials/{id}/` - 更新教程
- `DELETE /api/v1/tutorials/{id}/` - 删除教程

### 学习计划模块 API（新架构）
基础路径: `/api/v1/learning-plans/`

- `GET /api/v1/learning-plans/api/goals/` - 获取学习目标列表
- `POST /api/v1/learning-plans/api/goals/` - 创建学习目标
- `GET /api/v1/learning-plans/api/plans/` - 获取学习计划列表
- `POST /api/v1/learning-plans/api/plans/` - 创建学习计划
- `POST /api/v1/learning-plans/api/ai/generate-plan/` - AI生成学习计划

## 🛠️ 技术栈

- **后端框架**: Django 4.2.13
- **API框架**: Django REST Framework 3.14.0
- **AI服务**: LangChain 0.1.0 + DeepSeek API
- **数据库**: PostgreSQL (通过 psycopg2-binary)
- **数据验证**: Pydantic 2.5.0
- **配置管理**: python-decouple
- **跨域处理**: django-cors-headers

## 🔧 故障排除

### 常见问题

1. **环境变量未设置**
   ```bash
   # 确保 .env 文件存在并包含所需配置
   cp .env.example .env
   # 编辑 .env 文件并填入正确的值
   ```

2. **数据库连接错误**
   ```bash
   # 检查数据库配置
   python manage.py check --database
   # 确保PostgreSQL服务正在运行
   ```

3. **AI服务配置错误**
   ```bash
   # 确保DEEPSEEK_API_KEY已正确设置
   echo $DEEPSEEK_API_KEY
   ```

### 开发指南

### 配置说明

项目使用分环境配置：
- **开发环境**: `config.settings.development`
- **生产环境**: `config.settings.production`
- **测试环境**: `config.settings.testing`

默认使用开发环境配置，可通过设置 `DJANGO_SETTINGS_MODULE` 环境变量切换。

### AI 服务使用

项目集成了 DeepSeek AI 服务，通过环境变量进行配置：

```env
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

配置在 `llm/core/config.py` 中统一管理。

### 添加新功能

1. **新的AI服务**: 在 `llm/services/` 下创建新的服务类
2. **新的API端点**: 在对应应用的 `views.py` 和 `urls.py` 中添加
3. **数据模型**: 在 `core/models/` 或应用的 `models.py` 中定义

### 代码规范

- 遵循 PEP 8 Python代码规范
- 使用 Django 最佳实践
- API返回统一的JSON格式
- 错误处理使用 Django REST Framework 的异常处理

## 🧪 测试

```bash
# 验证项目配置
python manage.py check

# 运行所有测试
python manage.py test

# 运行特定应用的测试
python manage.py test tutorials
python manage.py test llm
```

## 📦 部署

### 开发环境
```bash
python manage.py runserver --settings=config.settings.development
```

### 生产环境
```bash
# 设置生产环境变量
export DJANGO_SETTINGS_MODULE=config.settings.production
export DEBUG=False

# 收集静态文件
python manage.py collectstatic --noinput

# 使用 Gunicorn 启动
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 🔄 架构说明

项目采用统一的新架构：
- **配置中心**: `config/` 目录管理所有Django配置
- **模块化结构**: `apps/` 下按功能划分的Django应用
- **AI服务**: `llm/` 模块提供完整的AI功能
- **基础设施**: `infrastructure/` 提供通用的基础服务

所有新功能都基于这个统一架构开发。

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -m '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建 Pull Request

## 📞 支持

如有问题，请通过以下方式联系：
- 创建 GitHub Issue
- 查看项目文档
- 联系项目维护者

---

**注意**: 确保在使用 AI 功能前正确配置 `DEEPSEEK_API_KEY` 环境变量。