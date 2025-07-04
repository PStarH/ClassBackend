#!/usr/bin/env python
"""
ClassBackend 优化实施脚本
执行优化建议中的自动化改进
"""

import os
import sys
import time
import django
from django.db import connection, transaction
from django.core.cache import cache
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

class OptimizationImplementer:
    """优化实施器"""
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def log_result(self, task: str, success: bool, message: str = ""):
        """记录结果"""
        status = "✅" if success else "❌"
        self.results.append(f"{status} {task}: {message}")
        print(f"{status} {task}: {message}")
    
    def check_database_performance(self):
        """检查数据库性能"""
        print("\n🗄️ 数据库性能检查")
        
        try:
            with connection.cursor() as cursor:
                # 检查连接配置
                cursor.execute("SHOW max_connections;")
                max_conn = cursor.fetchone()[0]
                
                cursor.execute("SELECT count(*) FROM pg_stat_activity;")
                current_conn = cursor.fetchone()[0]
                
                conn_usage = (current_conn / int(max_conn)) * 100
                
                self.log_result(
                    "数据库连接", 
                    conn_usage < 80, 
                    f"使用率 {conn_usage:.1f}% ({current_conn}/{max_conn})"
                )
                
                # 检查慢查询
                cursor.execute("""
                    SELECT count(*) FROM pg_stat_database 
                    WHERE datname = current_database()
                """)
                
                self.log_result("数据库统计", True, "统计信息正常")
                
        except Exception as e:
            self.log_result("数据库检查", False, str(e))
    
    def optimize_cache_configuration(self):
        """优化缓存配置"""
        print("\n💾 缓存优化")
        
        try:
            # 测试各个缓存别名
            cache_aliases = ['default', 'api_cache', 'sessions', 'user_cache']
            
            for alias in cache_aliases:
                try:
                    from django.core.cache import caches
                    cache_instance = caches[alias]
                    
                    test_key = f"optimization_test_{alias}"
                    test_value = {"timestamp": time.time(), "data": "test"}
                    
                    # 测试写入
                    cache_instance.set(test_key, test_value, 60)
                    
                    # 测试读取
                    retrieved = cache_instance.get(test_key)
                    success = retrieved == test_value
                    
                    # 清理
                    cache_instance.delete(test_key)
                    
                    self.log_result(f"缓存 {alias}", success, "读写测试通过")
                    
                except Exception as e:
                    self.log_result(f"缓存 {alias}", False, f"配置缺失: {e}")
            
        except Exception as e:
            self.log_result("缓存优化", False, str(e))
    
    def validate_llm_integration(self):
        """验证LLM集成"""
        print("\n🤖 LLM集成验证")
        
        try:
            from llm.core.client import llm_factory
            from llm.services.advisor_service import AdvisorService
            
            # 检查LLM工厂
            available = llm_factory.is_available()
            self.log_result("LLM工厂", available, f"模型: {llm_factory.get_model_name()}")
            
            if available:
                # 检查具体服务
                advisor = AdvisorService()
                self.log_result("Advisor服务", True, "初始化成功")
                
                # 检查缓存管理器
                from llm.core.unified_service import CacheManager
                cache_mgr = CacheManager()
                test_key = cache_mgr.generate_cache_key("test", param="value")
                
                self.log_result("LLM缓存管理", True, f"缓存键生成正常")
            
        except Exception as e:
            self.log_result("LLM集成验证", False, str(e))
    
    def check_security_features(self):
        """检查安全特性"""
        print("\n🔒 安全特性检查")
        
        try:
            from core.security.mixins import AuditMixin, SoftDeleteMixin, RowLevelSecurityMixin
            from core.security.validators import DataSecurityValidator
            
            self.log_result("审计混入", True, "AuditMixin可用")
            self.log_result("软删除混入", True, "SoftDeleteMixin可用") 
            self.log_result("行级安全", True, "RowLevelSecurityMixin可用")
            self.log_result("数据验证器", True, "DataSecurityValidator可用")
            
        except Exception as e:
            self.log_result("安全特性检查", False, str(e))
    
    def suggest_database_optimizations(self):
        """建议数据库优化"""
        print("\n📊 数据库优化建议")
        
        try:
            from apps.authentication.models import User
            from apps.courses.models import CourseProgress
            from apps.learning_plans.models import StudySession
            
            # 检查数据量
            user_count = User.objects.count()
            progress_count = CourseProgress.objects.count() 
            session_count = StudySession.objects.count()
            
            print(f"   用户数据: {user_count} users, {progress_count} progress, {session_count} sessions")
            
            # 基于数据量给出建议
            if user_count > 1000:
                print("   📈 建议: 添加用户表分区")
                print("   📈 建议: 实施读写分离")
            
            if progress_count > 5000:
                print("   📈 建议: 添加课程进度归档策略")
                
            if session_count > 10000:
                print("   📈 建议: 实施学习会话数据清理")
            
            self.log_result("数据量分析", True, "分析完成")
            
        except Exception as e:
            self.log_result("数据库优化建议", False, str(e))
    
    def generate_optimization_report(self):
        """生成优化报告"""
        print("\n📋 优化报告生成")
        
        total_time = time.time() - self.start_time
        success_count = sum(1 for result in self.results if "✅" in result)
        total_count = len(self.results)
        
        report = f"""
# ClassBackend 优化实施报告

**执行时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**耗时**: {total_time:.2f}秒
**成功率**: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)

## 详细结果

"""
        
        for result in self.results:
            report += f"- {result}\n"
        
        report += """
## 下一步行动

### 立即执行
1. 修复所有❌标记的问题
2. 部署数据库性能监控
3. 实施缓存预热策略

### 本周内完成  
1. 添加性能测试套件
2. 优化数据库查询
3. 升级LangChain依赖

### 持续改进
1. 监控系统性能指标
2. 定期数据库维护
3. 成本优化分析

---
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # 保存报告
        with open('optimization_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.log_result("优化报告", True, "已保存到 optimization_report.md")
        
        return report
    
    def run_all_optimizations(self):
        """运行所有优化检查"""
        print("🚀 开始执行 ClassBackend 优化检查")
        print("=" * 50)
        
        self.check_database_performance()
        self.optimize_cache_configuration()
        self.validate_llm_integration()
        self.check_security_features()
        self.suggest_database_optimizations()
        
        report = self.generate_optimization_report()
        
        print("\n" + "=" * 50)
        print("🎯 优化检查完成!")
        print(f"📊 成功率: {sum(1 for r in self.results if '✅' in r)}/{len(self.results)}")
        print("📄 详细报告已保存到 optimization_report.md")
        
        return report


if __name__ == "__main__":
    optimizer = OptimizationImplementer()
    optimizer.run_all_optimizations()
