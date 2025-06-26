"""
学习数据定时任务 - 缓存预热和数据清理
"""
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.learning_plans.cache_services import LearningStatsCacheService, CourseProgressCacheService
from apps.learning_plans.models import StudySession

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '预热缓存和执行定时数据处理任务'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--precompute-cache',
            action='store_true',
            help='预计算热点数据缓存'
        )
        
        parser.add_argument(
            '--active-users-only',
            action='store_true',
            help='仅为活跃用户预计算缓存'
        )
        
        parser.add_argument(
            '--days-active',
            type=int,
            default=7,
            help='定义活跃用户的天数（默认7天）'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始执行定时任务...'))
        
        if options['precompute_cache']:
            self._precompute_hot_data(
                active_only=options['active_users_only'],
                days_active=options['days_active']
            )
        
        self.stdout.write(self.style.SUCCESS('定时任务完成'))
    
    def _precompute_hot_data(self, active_only: bool = False, days_active: int = 7):
        """预计算热点数据"""
        self.stdout.write("开始预计算热点数据...")
        
        # 确定需要处理的用户
        if active_only:
            cutoff_date = timezone.now() - timedelta(days=days_active)
            active_user_ids = StudySession.objects.filter(
                start_time__gte=cutoff_date
            ).values_list('user_id', flat=True).distinct()
            
            users = User.objects.filter(id__in=active_user_ids)
            self.stdout.write(f"找到 {users.count()} 个活跃用户")
        else:
            users = User.objects.filter(is_active=True)
            self.stdout.write(f"处理所有 {users.count()} 个活跃用户")
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                # 预计算学习统计缓存
                LearningStatsCacheService.precompute_hot_data(str(user.uuid))
                
                # 预计算课程进度缓存
                CourseProgressCacheService.get_user_course_summary(str(user.uuid))
                
                success_count += 1
                
                if success_count % 100 == 0:
                    self.stdout.write(f"已处理 {success_count} 个用户")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"用户 {user.uuid} 缓存预计算失败: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"缓存预计算完成: 成功 {success_count}, 失败 {error_count}"
            )
        )
