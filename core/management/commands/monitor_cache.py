"""
缓存监控管理命令
"""
import time
from django.core.management.base import BaseCommand
from django.core.cache import caches
from core.cache import get_default_cache, get_api_cache, get_session_cache


class Command(BaseCommand):
    help = '监控 Redis 缓存性能'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='监控间隔时间（秒）'
        )
        
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='监控持续时间（秒）'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        duration = options['duration']
        
        self.stdout.write(
            self.style.SUCCESS(f'🔍 开始监控缓存性能 (间隔: {interval}s, 持续: {duration}s)')
        )
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                self.check_cache_performance()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⏹️  监控已停止')
            )
        
        self.stdout.write(
            self.style.SUCCESS('✅ 监控完成')
        )
    
    def check_cache_performance(self):
        """检查缓存性能"""
        timestamp = time.strftime('%H:%M:%S')
        self.stdout.write(f'\n📊 [{timestamp}] 缓存状态:')
        
        caches_to_check = [
            ('Default', get_default_cache()),
            ('API', get_api_cache()),
            ('Sessions', get_session_cache())
        ]
        
        for cache_name, cache_service in caches_to_check:
            try:
                # 测试缓存读写性能
                test_key = f'perf_test_{int(time.time())}'
                test_value = 'performance_test_data'
                
                # 写入测试
                write_start = time.time()
                cache_service.set(test_key, test_value, 10)
                write_time = (time.time() - write_start) * 1000
                
                # 读取测试
                read_start = time.time()
                retrieved_value = cache_service.get(test_key)
                read_time = (time.time() - read_start) * 1000
                
                # 清理测试数据
                cache_service.delete(test_key)
                
                # 检查结果
                status = '✅' if retrieved_value == test_value else '❌'
                
                self.stdout.write(
                    f'  {cache_name}: {status} '
                    f'写入: {write_time:.2f}ms, 读取: {read_time:.2f}ms'
                )
                
                # 性能警告
                if write_time > 100 or read_time > 100:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠️  {cache_name} 缓存响应较慢')
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  {cache_name}: ❌ 错误 - {str(e)}')
                )
    
    def get_cache_info(self, cache_service):
        """获取缓存信息（如果支持）"""
        try:
            # 尝试获取缓存统计信息
            cache_backend = cache_service.cache
            if hasattr(cache_backend, '_cache'):
                return {
                    'backend': str(type(cache_backend)),
                    'location': getattr(cache_backend, '_servers', 'Unknown')
                }
        except:
            pass
        
        return {'backend': 'Unknown', 'location': 'Unknown'}
