"""
Learning Plan Prompts for AI Services
"""

# 学习计划生成提示词
LEARNING_PLAN_GENERATION_PROMPT = """
你是一个专业的学习计划顾问。请根据以下信息为学生制定详细的学习计划：

学生信息：
- 姓名：{student_name}
- 年级：{grade}
- 学科：{subject}
- 当前水平：{current_level}
- 学习目标：{learning_goals}
- 可用时间：{available_time}
- 学习偏好：{learning_preferences}

课程信息：
{course_info}

请制定一个详细的学习计划，包括：
1. 学习目标分解
2. 时间安排
3. 学习内容和顺序
4. 评估方式
5. 学习建议

请用中文回复，格式清晰，内容具体可操作。
"""

# 学习计划优化提示词
LEARNING_PLAN_OPTIMIZATION_PROMPT = """
你是一个学习计划优化专家。请根据学生的学习进度和反馈，优化现有的学习计划。

当前学习计划：
{current_plan}

学习进度：
{progress_data}

学生反馈：
{student_feedback}

请提供优化建议，包括：
1. 进度调整
2. 内容调整
3. 方法改进
4. 时间重新分配
5. 个性化建议

请用中文回复，重点关注实用性和可操作性。
"""

# 学习路径推荐提示词
LEARNING_PATH_RECOMMENDATION_PROMPT = """
你是一个学习路径推荐专家。请根据学生的情况推荐最适合的学习路径。

学生档案：
- 学习能力：{learning_ability}
- 兴趣爱好：{interests}
- 学习风格：{learning_style}
- 时间安排：{time_schedule}
- 目标课程：{target_courses}

可选学习路径：
{available_paths}

请推荐最适合的学习路径，并说明推荐理由。包括：
1. 推荐路径
2. 推荐理由
3. 预期效果
4. 注意事项
5. 替代方案

请用中文回复。
"""

# 学习计划评估提示词
LEARNING_PLAN_EVALUATION_PROMPT = """
你是一个学习计划评估专家。请对学生的学习计划执行情况进行全面评估。

学习计划：
{learning_plan}

执行数据：
{execution_data}

学习成果：
{learning_outcomes}

请提供详细的评估报告，包括：
1. 完成度评估
2. 效果分析
3. 问题识别
4. 改进建议
5. 后续规划

请用中文回复，提供具体的数据分析和建议。
"""

# 自适应学习提示词
ADAPTIVE_LEARNING_PROMPT = """
你是一个自适应学习系统专家。请根据学生的实时学习数据，动态调整学习内容和难度。

学生能力模型：
{student_model}

当前学习状态：
{current_state}

学习历史：
{learning_history}

可用资源：
{available_resources}

请提供自适应调整方案：
1. 内容调整
2. 难度调整
3. 节奏调整
4. 方法调整
5. 资源推荐

请用中文回复，确保调整方案科学合理。
"""
