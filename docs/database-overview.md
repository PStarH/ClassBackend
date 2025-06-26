# 数据库表结构总览

## 项目当前数据库表汇总

本文档展示了ClassBackend项目当前的完整数据库表结构，包括最新添加的课程进度管理功能。

### 📊 表结构汇总

我们的系统目前包含以下主要功能模块的数据表：

| 模块 | 表名 | 功能描述 |
|------|------|----------|
| **用户认证** | `users` | 用户基础信息（UUID主键） |
| **用户认证** | `user_sessions` | 用户会话管理 |
| **用户设置** | `user_settings` | 用户学习偏好设置 ✨新增 |
| **课程进度** | `course_progress` | 课程学习进度跟踪 ✨新增 |
| **学习计划** | `learning_plans` | 用户学习计划 |
| **学习目标** | `learning_goals` | 学习目标定义 |
| **计划目标关联** | `learning_plan_goals` | 学习计划与目标关联 |
| **学习会话** | `study_sessions` | 学习会话记录 |
| **用户档案** | `user_profiles` | 用户详细档案 |
| **邮箱验证** | `email_verifications` | 邮箱验证功能 |
| **教程** | `tutorials_tutorial` | 教程内容 |

---

## 🏗️ 详细表结构

### 1. **USERS** - 用户基础表
```sql
uuid                 UUID PRIMARY KEY    -- 用户唯一标识
email                VARCHAR UNIQUE      -- 邮箱地址
username             VARCHAR             -- 用户名
password             VARCHAR             -- 加密密码
last_login           TIMESTAMP NULL      -- 最后登录时间
created_at           TIMESTAMP           -- 注册时间
is_active            BOOLEAN             -- 是否激活
is_staff             BOOLEAN             -- 是否管理员
is_superuser         BOOLEAN             -- 是否超级用户
```

### 2. **USER_SETTINGS** - 用户设置表 ✨新增
```sql
user_uuid_id         UUID PRIMARY KEY    -- 外键关联用户
preferred_pace       VARCHAR(20)         -- 学习节奏偏好
preferred_style      VARCHAR(20)         -- 学习风格偏好
tone                 VARCHAR(20)         -- AI语调风格
feedback_frequency   VARCHAR(20)         -- 反馈频率
major                VARCHAR(100)        -- 专业方向
education_level      VARCHAR(20)         -- 教育水平
notes                TEXT                -- 备注信息
skills               JSONB               -- 技能列表（数组）
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间
```

### 3. **COURSE_PROGRESS** - 课程进度表 ✨新增
```sql
course_uuid          UUID PRIMARY KEY    -- 课程进度唯一标识
user_uuid_id         UUID                -- 外键关联用户
subject_name         VARCHAR(100)        -- 学科名称
content_id           UUID                -- 课程内容ID
user_experience      TEXT                -- 用户经验描述
proficiency_level    INTEGER             -- 掌握程度(0-100)
learning_hour_week   INTEGER             -- 本周学习时长
learning_hour_total  INTEGER             -- 累计学习时长
est_finish_hour      INTEGER NULL        -- 预计完成时长
difficulty           INTEGER             -- 课程难度(1-10)
feedback             JSONB               -- 用户反馈
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间

-- 唯一约束：user_uuid_id + content_id
```

### 4. **USER_SESSIONS** - 用户会话表
```sql
session_id           UUID PRIMARY KEY    -- 会话ID
user_id              UUID                -- 外键关联用户
token                VARCHAR UNIQUE      -- 访问令牌
created_at           TIMESTAMP           -- 创建时间
last_activity        TIMESTAMP           -- 最后活动时间
expires_at           TIMESTAMP           -- 过期时间
is_active            BOOLEAN             -- 是否激活
user_agent           TEXT                -- 用户代理
ip_address           INET NULL           -- IP地址
```

### 5. **LEARNING_PLANS** - 学习计划表
```sql
id                   UUID PRIMARY KEY    -- 计划ID
user_id              INTEGER             -- 外键关联用户
title                VARCHAR             -- 计划标题
description          TEXT                -- 计划描述
status               VARCHAR             -- 计划状态
start_date           DATE NULL           -- 开始日期
target_end_date      DATE NULL           -- 目标结束日期
actual_end_date      DATE NULL           -- 实际结束日期
total_estimated_hours INTEGER            -- 总预计时长
ai_recommendations   JSONB               -- AI推荐
is_active            BOOLEAN             -- 是否激活
is_deleted           BOOLEAN             -- 是否删除
deleted_at           TIMESTAMP NULL      -- 删除时间
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间
```

### 6. **LEARNING_GOALS** - 学习目标表
```sql
id                   UUID PRIMARY KEY    -- 目标ID
title                VARCHAR             -- 目标标题
description          TEXT                -- 目标描述
goal_type            VARCHAR             -- 目标类型
difficulty           VARCHAR             -- 难度等级
estimated_hours      INTEGER             -- 预计时长
is_active            BOOLEAN             -- 是否激活
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间
```

### 7. **LEARNING_PLAN_GOALS** - 学习计划目标关联表
```sql
id                   UUID PRIMARY KEY    -- 关联ID
learning_plan_id     UUID                -- 外键关联学习计划
learning_goal_id     UUID                -- 外键关联学习目标
status               VARCHAR             -- 完成状态
order                INTEGER             -- 目标顺序
actual_hours         INTEGER             -- 实际时长
completion_date      TIMESTAMP NULL      -- 完成日期
notes                TEXT                -- 备注
is_active            BOOLEAN             -- 是否激活
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间
```

### 8. **STUDY_SESSIONS** - 学习会话表
```sql
id                   UUID PRIMARY KEY    -- 会话ID
learning_plan_id     UUID                -- 外键关联学习计划
goal_id              UUID                -- 外键关联目标
start_time           TIMESTAMP           -- 开始时间
end_time             TIMESTAMP NULL      -- 结束时间
duration_minutes     INTEGER             -- 持续时间（分钟）
content_covered      TEXT                -- 学习内容
effectiveness_rating SMALLINT NULL       -- 效果评分
notes                TEXT                -- 会话备注
is_active            BOOLEAN             -- 是否激活
created_at           TIMESTAMP           -- 创建时间
updated_at           TIMESTAMP           -- 更新时间
```

---

## 🔗 表关系说明

### 核心关系链
```
users (1) ←→ (1) user_settings         用户-设置：一对一
users (1) ←→ (N) course_progress       用户-课程进度：一对多
users (1) ←→ (N) user_sessions         用户-会话：一对多
users (1) ←→ (N) learning_plans        用户-学习计划：一对多

learning_plans (1) ←→ (N) learning_plan_goals    计划-目标关联：一对多
learning_goals (1) ←→ (N) learning_plan_goals    目标-计划关联：一对多

learning_plans (1) ←→ (N) study_sessions         计划-学习会话：一对多
learning_plan_goals (1) ←→ (N) study_sessions    目标-学习会话：一对多
```

### 约束说明
- **用户设置唯一性**：每个用户只能有一个设置记录
- **课程进度唯一性**：同一用户对同一课程内容只能有一个进度记录
- **会话令牌唯一性**：每个会话令牌必须唯一

---

## 📋 API接口汇总

### 新增的课程进度API
```
GET    /courses/progress/                    # 获取课程进度列表
POST   /courses/progress/                    # 创建课程进度
GET    /courses/progress/{uuid}/             # 获取课程进度详情
PUT    /courses/progress/{uuid}/             # 更新课程进度
DELETE /courses/progress/{uuid}/             # 删除课程进度

GET    /courses/stats/                       # 获取学习统计
POST   /courses/progress/{uuid}/feedback/    # 添加课程反馈
POST   /courses/progress/{uuid}/hours/       # 更新学习时长
```

### 用户设置API
```
GET    /auth/settings/                       # 获取用户设置
POST   /auth/settings/                       # 创建用户设置
PUT    /auth/settings/                       # 更新用户设置
POST   /auth/settings/skills/                # 添加技能
DELETE /auth/settings/skills/                # 删除技能
```

---

## 🎯 系统特点

### 数据完整性
- ✅ UUID主键确保分布式环境下的唯一性
- ✅ 外键约束保证数据关系完整性
- ✅ 唯一约束防止重复数据
- ✅ 时间戳字段支持审计追踪

### 功能完整性
- ✅ 用户认证与会话管理
- ✅ 个性化学习设置
- ✅ 课程进度跟踪
- ✅ 学习计划管理
- ✅ 学习目标设定
- ✅ 学习会话记录
- ✅ 用户反馈收集

### 扩展性
- ✅ JSON字段支持灵活的结构化数据存储
- ✅ 软删除机制保留历史数据
- ✅ 状态字段支持工作流管理
- ✅ 模块化设计便于功能扩展

---

## 📈 下一步发展方向

1. **课程内容管理** - 添加课程内容表和章节管理
2. **成就系统** - 添加徽章和成就跟踪
3. **社交功能** - 添加用户关注和分享功能
4. **分析报表** - 添加学习分析和报表功能
5. **通知系统** - 添加消息通知和提醒功能

该数据库结构为ClassBackend提供了完整的学习管理平台基础，支持个性化学习体验和全面的学习进度追踪。
