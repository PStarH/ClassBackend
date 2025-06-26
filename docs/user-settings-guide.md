# 用户设置功能文档

## 概述

用户设置功能允许用户在注册后填写个人学习偏好和设置，用于个性化学习体验。

## 数据库模型

### UserSettings 模型

| 字段名 | 类型 | 说明 | 选择项 |
|--------|------|------|--------|
| `user_uuid` | OneToOneField | 关联用户表（主键） | - |
| `preferred_pace` | CharField(20) | 学习节奏偏好 | slow, normal, fast, flexible |
| `preferred_style` | CharField(20) | 学习风格偏好 | visual, auditory, kinesthetic, reading, mixed |
| `tone` | CharField(20) | AI语调风格 | friendly, professional, encouraging, casual, formal |
| `feedback_frequency` | CharField(20) | 反馈频率 | immediate, lesson_end, daily, weekly, monthly |
| `major` | CharField(100) | 专业方向 | - |
| `education_level` | CharField(20) | 教育水平 | high_school, undergraduate, graduate, phd, professional, other |
| `notes` | TextField | 备注信息 | - |
| `skills` | JSONField | 技能列表（字符串数组） | - |
| `created_at` | DateTimeField | 创建时间 | - |
| `updated_at` | DateTimeField | 更新时间 | - |

## API 接口

### 1. 获取用户设置

```http
GET /auth/settings/
Authorization: Bearer <token>
```

**响应示例：**
```json
{
    "success": true,
    "data": {
        "user_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "preferred_pace": "normal",
        "preferred_style": "mixed",
        "tone": "friendly",
        "feedback_frequency": "lesson_end",
        "major": "计算机科学",
        "education_level": "undergraduate",
        "notes": "喜欢通过实践学习",
        "skills": ["Python", "Django", "JavaScript"],
        "created_at": "2025-06-26T03:30:00Z",
        "updated_at": "2025-06-26T03:30:00Z"
    }
}
```

### 2. 创建用户设置（注册后首次设置）

```http
POST /auth/settings/
Authorization: Bearer <token>
Content-Type: application/json

{
    "preferred_pace": "normal",
    "preferred_style": "mixed",
    "tone": "friendly",
    "feedback_frequency": "lesson_end",
    "major": "计算机科学",
    "education_level": "undergraduate",
    "notes": "喜欢通过实践学习",
    "skills": ["Python", "Django"]
}
```

### 3. 更新用户设置

```http
PUT /auth/settings/
Authorization: Bearer <token>
Content-Type: application/json

{
    "preferred_pace": "fast",
    "skills": ["Python", "Django", "React"]
}
```

### 4. 添加技能

```http
POST /auth/settings/skills/
Authorization: Bearer <token>
Content-Type: application/json

{
    "skill": "React"
}
```

### 5. 删除技能

```http
DELETE /auth/settings/skills/
Authorization: Bearer <token>
Content-Type: application/json

{
    "skill": "React"
}
```

## 使用流程

### 注册后设置流程

1. **用户注册** - 使用 `/auth/register/` 创建账号
2. **用户登录** - 使用 `/auth/login/` 获取认证令牌
3. **填写设置** - 使用 `/auth/settings/` POST 方法创建用户设置
4. **后续更新** - 使用 `/auth/settings/` PUT 方法更新设置

### 前端实现建议

```javascript
// 检查用户是否已填写设置
async function checkUserSettings() {
    try {
        const response = await fetch('/auth/settings/', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 404) {
            // 用户还未填写设置，跳转到设置页面
            redirectToSettingsPage();
        } else if (response.ok) {
            // 用户已有设置，继续正常流程
            const data = await response.json();
            console.log('用户设置:', data.data);
        }
    } catch (error) {
        console.error('检查用户设置失败:', error);
    }
}

// 创建用户设置
async function createUserSettings(settingsData) {
    try {
        const response = await fetch('/auth/settings/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settingsData)
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('设置创建成功:', data.data);
            // 跳转到主应用
            redirectToMainApp();
        } else {
            const error = await response.json();
            console.error('创建设置失败:', error);
        }
    } catch (error) {
        console.error('网络错误:', error);
    }
}
```

## 数据验证

### 技能列表验证

- 最多20个技能
- 每个技能必须是非空字符串
- 自动去重和去除空白字符

### 字段长度限制

- `major`: 最多100字符
- `notes`: 最多1000字符

## 管理后台

用户设置可以通过Django管理后台进行管理：

1. 访问 `/admin/authentication/usersettings/`
2. 可以查看、编辑、删除用户设置
3. 支持按各种字段过滤和搜索

## 错误处理

常见错误响应：

- `404`: 用户设置不存在
- `409`: 尝试重复创建设置
- `400`: 请求参数错误
- `401`: 未认证或令牌无效

## 测试

运行测试脚本验证功能：

```bash
python test_user_settings_model.py
```

## 下一步开发建议

1. 添加设置历史记录功能
2. 实现设置导入/导出功能
3. 添加设置预设模板
4. 实现基于设置的智能推荐
5. 添加设置同步到其他平台的功能
