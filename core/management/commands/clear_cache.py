"""
清理缓存管理命令
"""
from django.core.management.base import BaseCommand
from django.core.cache import caches
from core.cache import get_default_cache, get_api_cache, get_session_cache


class Command(BaseCommand):
    help = '清理 Redis 缓存'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--cache',
            choices=['all', 'default', 'api', 'sessions'],
            default='all',
            help='指定要清理的缓存类型 (default: all)'
        )
        
        parser.add_argument(
            '--pattern',
            type=str,
            help='清理匹配特定模式的缓存键'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='预览要删除的缓存，但不实际删除'
        )
    
    def handle(self, *args, **options):
        cache_type = options['cache']
        pattern = options['pattern']
        dry_run = options['dry-run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 预览模式 - 不会实际删除缓存')
            )
        
        try:
            if cache_type == 'all':
                self.clear_all_caches(pattern, dry_run)
            elif cache_type == 'default':
                self.clear_cache('default', get_default_cache(), pattern, dry_run)
            elif cache_type == 'api':
                self.clear_cache('api_cache', get_api_cache(), pattern, dry_run)
            elif cache_type == 'sessions':
                self.clear_cache('sessions', get_session_cache(), pattern, dry_run)
                
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS('✅ 缓存清理完成')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 缓存清理失败: {str(e)}')
            )
    
    def clear_all_caches(self, pattern, dry_run):
        """清理所有缓存"""
        self.stdout.write('🧹 清理所有缓存...')
        
        caches_to_clear = [
            ('default', get_default_cache()),
            ('api_cache', get_api_cache()),
            ('sessions', get_session_cache())
        ]
        
        for cache_name, cache_service in caches_to_clear:
            self.clear_cache(cache_name, cache_service, pattern, dry_run)
    
    def clear_cache(self, cache_name, cache_service, pattern, dry_run):
        """清理指定缓存"""
        try:
            if pattern:
                self.stdout.write(f'🎯 清理 {cache_name} 缓存 (模式: {pattern})')
                if not dry_run:
                    deleted = cache_service.clear_pattern(pattern)
                    self.stdout.write(f'   删除了 {deleted} 个缓存键')
                else:
                    self.stdout.write(f'   将删除匹配 "{pattern}" 的缓存键')
            else:
                self.stdout.write(f'🗑️  清理 {cache_name} 所有缓存')
                if not dry_run:
                    cache_service.cache.clear()
                    self.stdout.write(f'   {cache_name} 缓存已清空')
                else:
                    self.stdout.write(f'   将清空 {cache_name} 所有缓存')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 清理 {cache_name} 缓存失败: {str(e)}')
            )
