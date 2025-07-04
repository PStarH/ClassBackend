"""
使用改进后的LLM和数据库服务示例
"""

# 1. 使用统一的LLM服务
from llm.core.unified_service import BaseLLMService
from llm.core.error_handling import retry_llm_request, STANDARD_RETRY

class ImprovedTeacherService(BaseLLMService):
    def get_service_name(self) -> str:
        return "improved_teacher"
    
    @retry_llm_request(STANDARD_RETRY)
    def generate_course_outline(self, topic: str):
        """生成课程大纲 - 带重试机制"""
        prompt = f"为'{topic}'创建详细的课程大纲，返回JSON格式。"
        
        return self.structured_completion(
            prompt,
            use_cache=True
        )

# 2. 使用智能缓存
from core.performance.cache_strategies import smart_cache

class CourseService:
    @smart_cache(
        key_pattern="course_list",
        ttl=300,
        tags=["course"],
        use_adaptive_ttl=True
    )
    def get_course_list(self, user_id: str):
        """获取课程列表 - 使用智能缓存"""
        # 数据库查询逻辑
        return courses

# 3. 使用性能监控
from core.performance.optimizers import performance_monitor

class StudySessionService:
    @performance_monitor
    def create_session(self, user_id: str, course_id: str):
        """创建学习会话 - 性能监控"""
        # 业务逻辑
        return session

# 4. 使用数据库优化
from core.performance.optimizers import query_profiler, DatabaseOptimizer

def get_user_progress(user_id: str):
    """获取用户进度 - 查询优化"""
    from apps.courses.models import CourseProgress
    
    queryset = CourseProgress.objects.filter(user_uuid=user_id)
    
    # 自动优化查询
    optimized_queryset = DatabaseOptimizer.optimize_queryset(queryset)
    
    return optimized_queryset
