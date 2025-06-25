"""
学习计划相关的提示词模板
"""
from langchain.prompts import PromptTemplate


# 创建学习计划提示词
CREATE_LEARNING_PLAN_PROMPT = PromptTemplate(
    input_variables=["topic"],
    template="""你是一位专业的教育规划专家。
请为以下主题创建一个详细的学习计划，以JSON树状图格式返回，每个节点包含 'title'、'index' 和 'children' 字段。
不要包含JSON结构之外的任何额外文本或格式。

示例格式：
[
  {{
    "index": 1,
    "title": "基础知识",
    "children": [
      {{
        "index": 1.1,
        "title": "入门概念",
        "children": []
      }}
    ]
  }}
]

请为以下主题创建学习计划：{topic}

要求：
1. 计划应该循序渐进，从基础到高级
2. 每个部分都应该有明确的学习目标
3. 包含理论学习和实践练习
4. 适合初学者到中级学习者"""
)

# 更新学习计划提示词
UPDATE_LEARNING_PLAN_PROMPT = PromptTemplate(
    input_variables=["current_plan", "feedback"],
    template="""你是一位专业的教育规划专家。
根据现有的学习计划和教师反馈，输出只需要更新或替换的JSON节点。
不要包含完整计划，只返回需要变更的部分作为JSON树。

当前学习计划：
{current_plan}

教师反馈：
```markdown
{feedback}
```

请只返回需要更新的JSON片段。"""
)

# 学习计划聊天代理提示词
LEARNING_PLAN_CHAT_PROMPT = PromptTemplate(
    input_variables=["current_plan", "message"],
    template="""你是一位专业的教育规划专家。
你可以与用户聊天来回答问题或调整学习计划。
根据用户的消息和当前学习计划，返回一个JSON对象：
{{
  "reply": "<文本回复>",
  "updates": [ ... ]  // 只包含需要更新的JSON节点，如果没有计划变更则为空数组
}}
只包含计划中变更的部分。
不要包含任何其他字段。

当前学习计划：
{current_plan}

用户消息：
{message}"""
)
