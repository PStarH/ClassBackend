"""
数据清理管理命令 - 历史数据归档和无效数据清理
"""
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from django.utils import timezone
from django.conf import settings

from apps.learning_plans.models import StudySession
from apps.courses.models import CourseProgress
from apps.authentication.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '清理和归档学习数据'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--archive-older-than',
            type=int,
            default=365,
            help='归档多少天前的数据（默认365天）'
        )
        
        parser.add_argument(
            '--delete-older-than',
            type=int,
            default=1095,  # 3年
            help='删除多少天前的数据（默认1095天）'
        )
        
        parser.add_argument(
            '--cleanup-invalid',
            action='store_true',
            help='清理无效数据'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要处理的数据，不实际执行'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='批处理大小（默认1000）'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始数据清理任务...'))
        
        archive_cutoff = timezone.now() - timedelta(days=options['archive_older_than'])
        delete_cutoff = timezone.now() - timedelta(days=options['delete_older_than'])
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('这是预演模式，不会实际修改数据'))
        
        try:
            # 1. 清理无效数据
            if options['cleanup_invalid']:
                self._cleanup_invalid_data(dry_run, batch_size)
            
            # 2. 归档历史数据
            self._archive_historical_data(archive_cutoff, dry_run, batch_size)
            
            # 3. 删除超旧数据
            self._delete_old_data(delete_cutoff, dry_run, batch_size)
            
            # 4. 优化数据库
            if not dry_run:
                self._optimize_database()
            
            self.stdout.write(self.style.SUCCESS('数据清理任务完成'))
            
        except Exception as e:
            logger.error(f"数据清理任务失败: {str(e)}")
            raise CommandError(f"数据清理失败: {str(e)}")
    
    def _cleanup_invalid_data(self, dry_run: bool, batch_size: int):
        """清理无效数据"""
        self.stdout.write("正在清理无效数据...")
        
        # 1. 清理异常的学习会话
        invalid_sessions = StudySession.objects.filter(
            models.Q(duration_minutes__lt=0) |  # 负数时长
            models.Q(end_time__lt=models.F('start_time')) |  # 结束时间早于开始时间
            models.Q(effectiveness_rating__lt=1) |  # 无效评分
            models.Q(effectiveness_rating__gt=5) |
            models.Q(focus_score__lt=0) |  # 无效专注度
            models.Q(focus_score__gt=1)
        )
        
        invalid_count = invalid_sessions.count()
        self.stdout.write(f"发现 {invalid_count} 个无效学习会话")
        
        if not dry_run and invalid_count > 0:
            deleted_count = 0
            for i in range(0, invalid_count, batch_size):
                batch = invalid_sessions[i:i + batch_size]
                batch_ids = list(batch.values_list('id', flat=True))
                deleted = StudySession.objects.filter(id__in=batch_ids).delete()[0]
                deleted_count += deleted
                self.stdout.write(f"已删除 {deleted_count}/{invalid_count} 个无效会话")
        
        # 2. 清理重复的课程进度记录
        duplicate_progress = CourseProgress.objects.values(
            'user_uuid', 'content_id'
        ).annotate(
            count=models.Count('id')
        ).filter(count__gt=1)
        
        duplicate_count = duplicate_progress.count()
        self.stdout.write(f"发现 {duplicate_count} 组重复的课程进度记录")
        
        if not dry_run and duplicate_count > 0:
            for duplicate in duplicate_progress:
                # 保留最新的记录，删除旧的
                progress_records = CourseProgress.objects.filter(
                    user_uuid=duplicate['user_uuid'],
                    content_id=duplicate['content_id']
                ).order_by('-updated_at')
                
                # 删除除第一个之外的所有记录
                to_delete = progress_records[1:]
                for record in to_delete:
                    record.delete()
        
        # 3. 清理孤立的会话（用户已删除）
        orphaned_sessions = StudySession.objects.filter(
            user__isnull=True
        )
        orphaned_count = orphaned_sessions.count()
        self.stdout.write(f"发现 {orphaned_count} 个孤立的学习会话")
        
        if not dry_run and orphaned_count > 0:
            orphaned_sessions.delete()
        
        self.stdout.write(self.style.SUCCESS("无效数据清理完成"))
    
    def _archive_historical_data(self, cutoff_date: datetime, dry_run: bool, batch_size: int):
        """归档历史数据"""
        self.stdout.write(f"正在归档 {cutoff_date.date()} 之前的数据...")
        
        # 归档学习会话
        old_sessions = StudySession.objects.filter(
            start_time__lt=cutoff_date,
            is_active=False  # 只归档已完成的会话
        )
        
        session_count = old_sessions.count()
        self.stdout.write(f"需要归档 {session_count} 个学习会话")
        
        if not dry_run and session_count > 0:
            # 创建归档表（如果不存在）
            self._create_archive_tables()
            
            # 批量归档
            archived_count = 0
            for i in range(0, session_count, batch_size):
                batch = old_sessions[i:i + batch_size]
                archived_data = []
                
                for session in batch:
                    archived_data.append({
                        'original_id': session.id,
                        'user_id': session.user_id,
                        'start_time': session.start_time,
                        'end_time': session.end_time,
                        'duration_minutes': session.duration_minutes,
                        'content_covered': session.content_covered,
                        'effectiveness_rating': session.effectiveness_rating,
                        'notes': session.notes,
                        'subject_category': session.subject_category,
                        'learning_environment': session.learning_environment,
                        'device_type': session.device_type,
                        'archived_at': timezone.now(),
                    })
                
                # 插入到归档表
                self._insert_to_archive(archived_data)
                
                # 删除原始数据
                batch_ids = list(batch.values_list('id', flat=True))
                StudySession.objects.filter(id__in=batch_ids).delete()
                
                archived_count += len(batch)
                self.stdout.write(f"已归档 {archived_count}/{session_count} 个会话")
        
        self.stdout.write(self.style.SUCCESS("历史数据归档完成"))
    
    def _delete_old_data(self, cutoff_date: datetime, dry_run: bool, batch_size: int):
        """删除超旧数据"""
        self.stdout.write(f"正在删除 {cutoff_date.date()} 之前的数据...")
        
        # 删除超旧的归档数据
        from django.db import connection
        
        with connection.cursor() as cursor:
            # 检查归档表是否存在
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'study_sessions_archive'
            """)
            
            if cursor.fetchone()[0] > 0:
                cursor.execute("""
                    SELECT COUNT(*) FROM study_sessions_archive 
                    WHERE archived_at < %s
                """, [cutoff_date])
                
                old_archive_count = cursor.fetchone()[0]
                self.stdout.write(f"需要删除 {old_archive_count} 条归档记录")
                
                if not dry_run and old_archive_count > 0:
                    cursor.execute("""
                        DELETE FROM study_sessions_archive 
                        WHERE archived_at < %s
                    """, [cutoff_date])
                    
                    self.stdout.write(f"已删除 {old_archive_count} 条归档记录")
        
        # 删除非活跃用户的超旧数据
        inactive_users = User.objects.filter(
            last_login__lt=cutoff_date,
            is_active=False
        )
        
        inactive_count = inactive_users.count()
        self.stdout.write(f"发现 {inactive_count} 个长期非活跃用户")
        
        if not dry_run and inactive_count > 0:
            for user in inactive_users:
                # 删除用户的所有学习记录
                StudySession.objects.filter(user=user).delete()
                CourseProgress.objects.filter(user_uuid=user).delete()
                
                self.stdout.write(f"已清理用户 {user.email} 的数据")
        
        self.stdout.write(self.style.SUCCESS("超旧数据删除完成"))
    
    def _create_archive_tables(self):
        """创建归档表"""
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions_archive (
                    id SERIAL PRIMARY KEY,
                    original_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_minutes INTEGER NOT NULL DEFAULT 0,
                    content_covered TEXT,
                    effectiveness_rating SMALLINT,
                    notes TEXT,
                    subject_category VARCHAR(50),
                    learning_environment VARCHAR(50),
                    device_type VARCHAR(20),
                    archived_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    
                    INDEX idx_archive_user_date (user_id, start_time),
                    INDEX idx_archive_date (archived_at)
                )
            """)
            
            self.stdout.write("归档表创建完成")
    
    def _insert_to_archive(self, data_list: list):
        """插入数据到归档表"""
        from django.db import connection
        
        if not data_list:
            return
        
        with connection.cursor() as cursor:
            values_list = []
            for data in data_list:
                end_time_value = "NULL" if not data['end_time'] else f"'{data['end_time']}'"
                content_value = "NULL" if not data['content_covered'] else f"'{data['content_covered']}'"
                rating_value = "NULL" if not data['effectiveness_rating'] else str(data['effectiveness_rating'])
                notes_value = "NULL" if not data['notes'] else f"'{data['notes']}'"
                subject_value = "NULL" if not data['subject_category'] else f"'{data['subject_category']}'"
                
                values = f"('{data['original_id']}', '{data['user_id']}', " \
                        f"'{data['start_time']}', {end_time_value}, " \
                        f"{data['duration_minutes']}, {content_value}, " \
                        f"{rating_value}, {notes_value}, {subject_value}, " \
                        f"'{data['learning_environment']}', '{data['device_type']}', " \
                        f"'{data['archived_at']}')"
                
                values_list.append(values)
            
            query = f"""
                INSERT INTO study_sessions_archive 
                (original_id, user_id, start_time, end_time, duration_minutes, 
                 content_covered, effectiveness_rating, notes, subject_category, 
                 learning_environment, device_type, archived_at)
                VALUES {', '.join(values_list)}
            """
            
            cursor.execute(query)
    
    def _optimize_database(self):
        """优化数据库"""
        self.stdout.write("正在优化数据库...")
        
        from django.db import connection
        
        with connection.cursor() as cursor:
            # 分析表统计
            cursor.execute("ANALYZE TABLE study_sessions")
            cursor.execute("ANALYZE TABLE course_progress")
            
            # 优化表
            cursor.execute("OPTIMIZE TABLE study_sessions")
            cursor.execute("OPTIMIZE TABLE course_progress")
        
        self.stdout.write(self.style.SUCCESS("数据库优化完成"))
