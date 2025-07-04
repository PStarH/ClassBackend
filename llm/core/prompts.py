"""
Prompt Templates - AI 提示词管理
"""

try:
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # 简单的提示词模板实现
    class PromptTemplate:
        def __init__(self, input_variables, template):
            self.input_variables = input_variables
            self.template = template
        
        def format(self, **kwargs):
            return self.template.format(**kwargs)


# 教育计划相关提示词
CREATE_PLAN_PROMPT = PromptTemplate(
    input_variables=["topic"],
    template="""You are an expert educational planning agent.
Generate a learning plan as a JSON tree diagram where each node has 'title','index', and 'children'.
Do not include any additional text or formatting outside the JSON structure.
For example:
[
  {{
    "index": 1,
    "title": "Fundamentals",
    "children": [
      {{
        "index": 1.1,
        "title": "Getting Started",
        "children": []
      }}
    ]
  }}
]

Create a study plan for {topic} with topics and their learning sequence."""
)

UPDATE_PLAN_PROMPT = PromptTemplate(
    input_variables=["current_plan", "feedback"],
    template="""You are an expert educational planning agent.
Given an existing study plan and teacher feedback, output only the JSON nodes that need to be updated or replaced.
Do not include any additional text or full plan, only the changed sections as a JSON tree.

Here is the current study plan:
{current_plan}

Teacher feedback as markdown:
```markdown
{feedback}
```

Return only the JSON segments to update."""
)

CHAT_AGENT_PROMPT = PromptTemplate(
    input_variables=["current_plan", "message"],
    template="""You are an expert educational planning agent.
You can chat with the user to answer questions or adjust the study plan.
Given the user's message and the current study plan, respond with a JSON object:
{{
  "reply": "<text response>",
  "updates": [ ... ]  // only the JSON nodes to update, if any changes to plan
}}
Only include changed plan segments in 'updates'.
Do not include any additional fields.

Current study plan:
{current_plan}

User message:
{message}"""
)

# 教师课程相关提示词
CREATE_OUTLINE_PROMPT = PromptTemplate(
    input_variables=["topic"],
    template="""You are an expert educational content developer.
Generate a detailed course outline for the given topic as a JSON array. Each element should have:
- 'index': section number or identifier
- 'title': section title
Return ONLY the JSON array, no markdown formatting, no code blocks, no additional text.

Generate a course outline for the topic: {topic}"""
)

SECTION_DETAIL_PROMPT = PromptTemplate(
    input_variables=["index", "title"],
    template="""You are an expert educational content developer.
Generate detailed content for the given section. If graphs are needed, use placeholders and provide separate graph definitions.
Include in the response:
- 'index' and 'title' as provided
- 'content': detailed explanatory text; include placeholder '{{{{GRAPH_ID}}}}' where graphs should be rendered (e.g., {{{{GRAPH_1}}}}, {{{{GRAPH_2}}}})
- 'graphs': object with GRAPH_ID as keys and DOT language definition strings as values, or empty object if no graphs needed
Return ONLY the JSON object with these fields, no markdown formatting, no code blocks, no additional text.

Generate details for the section with index {index} and title '{title}'"""
)

# 练习题生成相关提示词
EXERCISE_PROMPT = PromptTemplate(
    input_variables=["subject_name", "content_covered", "difficulty_level", "proficiency_level", 
                     "num_questions", "learning_hour_week", "feedback"],
    template="""你是一位专业的教育评估专家，负责根据学生的学习情况生成个性化练习题。

学生学习情况：
- 学科：{subject_name}
- 已学内容：{content_covered}
- 难度等级：{difficulty_level}
- 熟练程度：{proficiency_level}
- 每周学习时长：{learning_hour_week}小时
- 学习反馈：{feedback}

请生成 {num_questions} 道练习题，要求：
1. 题目必须基于已学内容，不能出现学生未学过的知识点
2. 难度要与学生的熟练程度和课程难度相匹配
3. 题目类型主要为选择题，每题4个选项（A、B、C、D）
4. 提供正确答案和详细解析
5. 根据学习时长调整题目复杂度：学习时间长的学生可以有更复杂的题目

返回格式要求（仅返回JSON，不要包含任何其他文字或格式）：
{{
    "exercises": [
        {{
            "id": "q_1",
            "question": "题目内容",
            "type": "multiple_choice",
            "options": [
                {{"id": "A", "text": "选项A内容"}},
                {{"id": "B", "text": "选项B内容"}},
                {{"id": "C", "text": "选项C内容"}},
                {{"id": "D", "text": "选项D内容"}}
            ],
            "correct_answer": "A",
            "explanation": "答案解析说明为什么选择A",
            "difficulty": 5,
            "points": 10
        }}
    ]
}}"""
)
