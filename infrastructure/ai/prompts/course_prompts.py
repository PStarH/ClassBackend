"""
课程管理相关的提示词模板
"""
from langchain.prompts import PromptTemplate


# 创建课程大纲提示词
CREATE_COURSE_OUTLINE_PROMPT = PromptTemplate(
    input_variables=["topic"],
    template="""你是一位专业的教育内容开发者。
为给定主题生成详细的课程大纲，以JSON数组格式返回。每个元素应包含：
- 'index': 章节编号或标识符
- 'title': 章节标题

只返回JSON数组，不要包含markdown格式、代码块或其他额外文本。

为以下主题生成课程大纲：{topic}

要求：
1. 大纲应该逻辑清晰，循序渐进
2. 涵盖该主题的核心知识点
3. 适合系统性学习
4. 章节安排合理，每章内容量适中"""
)

# 生成章节详细内容提示词
GENERATE_SECTION_DETAIL_PROMPT = PromptTemplate(
    input_variables=["index", "title"],
    template="""你是一位专业的教育内容开发者。
为给定章节生成详细内容。如果需要图表，请使用占位符并提供单独的图表定义。
响应中应包含：
- 'index' 和 'title'（如提供的）
- 'content': 详细的解释性文本；在需要渲染图表的地方包含占位符 '{{{{GRAPH_ID}}}}'（例如，{{{{GRAPH_1}}}}、{{{{GRAPH_2}}}}）
- 'graphs': 以GRAPH_ID为键、DOT语言定义字符串为值的对象，如果不需要图表则为空对象

只返回包含这些字段的JSON对象，不要包含markdown格式、代码块或其他额外文本。

为索引为 {index}、标题为 '{title}' 的章节生成详细内容。

要求：
1. 内容应该详细且易于理解
2. 包含关键概念的解释
3. 如有必要，提供示例说明
4. 图表应该有助于理解概念"""
)
