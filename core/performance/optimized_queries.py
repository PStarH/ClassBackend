# Performance-Optimized Query Manager for Learning Platform
"""
Enhanced database query optimization using Django ORM best practices
Implements select_related, prefetch_related, and custom query optimizations
"""

from django.db import models, connection
from django.core.cache import cache
from django.db.models import Count, Avg, Sum, Max, Min, Q, F, Prefetch, Extract
from django.utils import timezone
from datetime import timedelta
import logging
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger('performance')

class OptimizedQueryManager:
    """Centralized query optimization manager"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5 minutes default
        
    @contextmanager
    def query_debugger(self, query_name: str):
        """Context manager to debug and log slow queries"""
        start_time = timezone.now()
        initial_queries = len(connection.queries)
        
        try:
            yield
        finally:
            execution_time = (timezone.now() - start_time).total_seconds()
            query_count = len(connection.queries) - initial_queries
            
            if execution_time > 0.1:  # Log queries taking more than 100ms
                logger.warning(
                    f"Slow query detected: {query_name} took {execution_time:.3f}s "
                    f"with {query_count} database queries"
                )
            
            # Log to performance monitoring
            self._record_query_performance(query_name, execution_time, query_count)
    
    def _record_query_performance(self, query_name: str, execution_time: float, query_count: int):
        """Record query performance metrics"""
        performance_data = cache.get('query_performance', {})
        
        if query_name not in performance_data:
            performance_data[query_name] = []
        
        performance_data[query_name].append({
            'execution_time': execution_time,
            'query_count': query_count,
            'timestamp': timezone.now().isoformat()
        })
        
        # Keep only last 100 records per query
        performance_data[query_name] = performance_data[query_name][-100:]
        
        cache.set('query_performance', performance_data, 3600)  # 1 hour
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics"""
        performance_data = cache.get('query_performance', {})
        stats = {}
        
        for query_name, records in performance_data.items():
            if records:
                execution_times = [r['execution_time'] for r in records]
                query_counts = [r['query_count'] for r in records]
                
                stats[query_name] = {
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'max_execution_time': max(execution_times),
                    'avg_query_count': sum(query_counts) / len(query_counts),
                    'total_calls': len(records)
                }
        
        return stats

class OptimizedStudySessionManager(models.Manager):
    """Optimized manager for StudySession queries"""
    
    def get_user_sessions_optimized(self, user_id, days_back=30):
        """Get user sessions with optimized queries"""
        with OptimizedQueryManager().query_debugger('get_user_sessions_optimized'):
            cutoff_date = timezone.now() - timedelta(days=days_back)
            
            return self.select_related('user', 'course_progress__content_id').filter(
                user_id=user_id,
                start_time__gte=cutoff_date
            ).order_by('-start_time')
    
    def get_session_analytics(self, user_id=None, days_back=30):
        """Get comprehensive session analytics with single query"""
        cache_key = f"session_analytics_{user_id}_{days_back}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        with OptimizedQueryManager().query_debugger('get_session_analytics'):
            cutoff_date = timezone.now() - timedelta(days=days_back)
            queryset = self.filter(start_time__gte=cutoff_date)
            
            if user_id:
                queryset = queryset.filter(user_id=user_id)
            
            # Use database aggregation for better performance
            analytics = queryset.aggregate(
                total_sessions=Count('id'),
                total_duration=Sum('duration_minutes'),
                avg_duration=Avg('duration_minutes'),
                avg_effectiveness=Avg('effectiveness_rating'),
                max_duration=Max('duration_minutes'),
                min_duration=Min('duration_minutes'),
                active_sessions=Count('id', filter=Q(is_active=True)),
                completed_sessions=Count('id', filter=Q(end_time__isnull=False))
            )
            
            # Additional computed metrics
            if analytics['total_sessions']:
                analytics['completion_rate'] = (
                    analytics['completed_sessions'] / analytics['total_sessions'] * 100
                )
                analytics['avg_daily_sessions'] = analytics['total_sessions'] / days_back
            else:
                analytics['completion_rate'] = 0
                analytics['avg_daily_sessions'] = 0
            
            cache.set(cache_key, analytics, 600)  # Cache for 10 minutes
            return analytics
    
    def get_productivity_insights(self, user_id, limit=10):
        """Get productivity insights with efficient queries"""
        cache_key = f"productivity_insights_{user_id}_{limit}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        with OptimizedQueryManager().query_debugger('get_productivity_insights'):
            # Most productive learning environments
            env_stats = self.filter(
                user_id=user_id,
                end_time__isnull=False
            ).values('learning_environment').annotate(
                session_count=Count('id'),
                avg_effectiveness=Avg('effectiveness_rating'),
                total_duration=Sum('duration_minutes')
            ).order_by('-avg_effectiveness')[:5]
            
            # Best performing time slots - using safe database functions
            time_stats = self.filter(
                user_id=user_id,
                effectiveness_rating__gte=4
            ).annotate(
                hour=Extract('start_time', 'hour')
            ).values('hour').annotate(
                session_count=Count('id'),
                avg_effectiveness=Avg('effectiveness_rating')
            ).order_by('-session_count')[:5]
            
            # Subject performance
            subject_stats = self.filter(
                user_id=user_id,
                subject_category__isnull=False
            ).exclude(subject_category='').values('subject_category').annotate(
                session_count=Count('id'),
                avg_effectiveness=Avg('effectiveness_rating'),
                total_duration=Sum('duration_minutes')
            ).order_by('-avg_effectiveness')[:5]
            
            insights = {
                'productive_environments': list(env_stats),
                'optimal_time_slots': list(time_stats),
                'subject_performance': list(subject_stats),
                'generated_at': timezone.now().isoformat()
            }
            
            cache.set(cache_key, insights, 1800)  # Cache for 30 minutes
            return insights

class OptimizedCourseProgressManager(models.Manager):
    """Optimized manager for CourseProgress queries"""
    
    def get_user_progress_dashboard(self, user_id):
        """Get comprehensive user progress with minimal queries"""
        cache_key = f"user_progress_dashboard_{user_id}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        with OptimizedQueryManager().query_debugger('get_user_progress_dashboard'):
            # Single query with all related data
            progress_data = self.select_related(
                'content_id', 'user_uuid'
            ).prefetch_related(
                Prefetch('study_sessions', 
                        queryset=self.model.study_sessions.related.related_model.objects.select_related().order_by('-start_time')[:10])
            ).filter(user_uuid_id=user_id).annotate(
                recent_sessions=Count('study_sessions', 
                                    filter=Q(study_sessions__start_time__gte=timezone.now() - timedelta(days=7))),
                total_study_time=Sum('study_sessions__duration_minutes'),
                avg_effectiveness=Avg('study_sessions__effectiveness_rating'),
                completion_percentage=F('learning_hour_total') * 100.0 / F('est_finish_hour')
            )
            
            dashboard_data = {
                'progress_records': [],
                'summary': {
                    'total_courses': 0,
                    'completed_courses': 0,
                    'total_study_hours': 0,
                    'avg_proficiency': 0,
                    'courses_in_progress': 0
                }
            }
            
            total_hours = 0
            total_proficiency = 0
            completed_count = 0
            in_progress_count = 0
            
            for progress in progress_data:
                record_data = {
                    'course_uuid': str(progress.course_uuid),
                    'subject_name': progress.subject_name,
                    'proficiency_level': progress.proficiency_level,
                    'learning_hour_total': progress.learning_hour_total,
                    'difficulty': progress.difficulty,
                    'completion_percentage': min((progress.completion_percentage or 0), 100),
                    'recent_sessions': progress.recent_sessions,
                    'total_study_time': progress.total_study_time or 0,
                    'avg_effectiveness': progress.avg_effectiveness or 0,
                    'is_completed': progress.is_completed()
                }
                
                dashboard_data['progress_records'].append(record_data)
                
                # Update summary statistics
                total_hours += progress.learning_hour_total
                total_proficiency += progress.proficiency_level
                
                if progress.is_completed():
                    completed_count += 1
                else:
                    in_progress_count += 1
            
            # Calculate summary
            total_courses = len(dashboard_data['progress_records'])
            dashboard_data['summary'].update({
                'total_courses': total_courses,
                'completed_courses': completed_count,
                'total_study_hours': total_hours,
                'avg_proficiency': total_proficiency / total_courses if total_courses > 0 else 0,
                'courses_in_progress': in_progress_count,
                'completion_rate': (completed_count / total_courses * 100) if total_courses > 0 else 0
            })
            
            cache.set(cache_key, dashboard_data, 900)  # Cache for 15 minutes
            return dashboard_data
    
    def get_learning_recommendations(self, user_id, limit=5):
        """Get personalized learning recommendations"""
        cache_key = f"learning_recommendations_{user_id}_{limit}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        with OptimizedQueryManager().query_debugger('get_learning_recommendations'):
            # Analyze user's learning patterns
            user_progress = self.filter(user_uuid_id=user_id).aggregate(
                avg_proficiency=Avg('proficiency_level'),
                preferred_difficulty=Avg('difficulty'),
                total_subjects=Count('subject_name', distinct=True)
            )
            
            # Find subjects with similar difficulty and good outcomes
            similar_courses = self.exclude(
                user_uuid_id=user_id
            ).filter(
                difficulty__range=(
                    max(1, (user_progress['preferred_difficulty'] or 5) - 2),
                    min(10, (user_progress['preferred_difficulty'] or 5) + 2)
                ),
                proficiency_level__gte=user_progress['avg_proficiency'] or 50
            ).values('subject_name').annotate(
                avg_success_rate=Avg('proficiency_level'),
                student_count=Count('user_uuid_id', distinct=True),
                avg_completion_time=Avg('learning_hour_total')
            ).filter(
                student_count__gte=3  # At least 3 students
            ).order_by('-avg_success_rate')[:limit]
            
            recommendations = {
                'courses': list(similar_courses),
                'user_profile': user_progress,
                'generated_at': timezone.now().isoformat()
            }
            
            cache.set(cache_key, recommendations, 3600)  # Cache for 1 hour
            return recommendations

# Performance monitoring decorator
def monitor_query_performance(func):
    """Decorator to monitor query performance"""
    def wrapper(*args, **kwargs):
        start_time = timezone.now()
        initial_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = (timezone.now() - start_time).total_seconds()
            query_count = len(connection.queries) - initial_queries
            
            if execution_time > 0.5:  # Log slow functions
                logger.warning(
                    f"Slow function: {func.__name__} took {execution_time:.3f}s "
                    f"with {query_count} queries"
                )
    
    return wrapper

# Query optimization utilities
class QueryOptimizer:
    """Utility class for query optimization"""
    
    @staticmethod
    def optimize_bulk_create(model_class, objects, batch_size=1000):
        """Optimized bulk create with batching"""
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            model_class.objects.bulk_create(batch, ignore_conflicts=True)
    
    @staticmethod
    def optimize_bulk_update(model_class, objects, fields, batch_size=1000):
        """Optimized bulk update with batching"""
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            model_class.objects.bulk_update(batch, fields)
    
    @staticmethod
    def get_or_create_cached(model_class, cache_key, defaults=None, **kwargs):
        """Cached get_or_create to reduce database hits"""
        obj = cache.get(cache_key)
        if obj:
            return obj, False
        
        obj, created = model_class.objects.get_or_create(defaults=defaults, **kwargs)
        cache.set(cache_key, obj, 600)  # Cache for 10 minutes
        return obj, created

# Export optimized managers
__all__ = [
    'OptimizedQueryManager',
    'OptimizedStudySessionManager', 
    'OptimizedCourseProgressManager',
    'monitor_query_performance',
    'QueryOptimizer'
]