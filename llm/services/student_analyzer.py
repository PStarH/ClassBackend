"""
学生数据分析服务
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone

from apps.authentication.models import User, UserSettings
from apps.courses.models import CourseProgress
from apps.learning_plans.models import StudySession
from apps.learning_plans.student_notes_models import StudentQuestion, StudentLearningPattern, TeacherNotes


class StudentDataAnalyzer:
    """学生数据分析器"""
    
    def __init__(self):
        self.analysis_window_days = 30  # 默认分析最近30天的数据
    
    def get_student_profile(self, user_id: str) -> Dict[str, Any]:
        """获取学生的完整档案信息"""
        try:
            user = User.objects.get(uuid=user_id)
            
            # 基础信息
            profile = {
                'user_id': user_id,
                'email': user.email,
                'username': user.username,
                'profile': self._get_basic_profile(user),
                'learning_stats': self._get_learning_statistics(user),
                'question_analysis': self._analyze_student_questions(user),
                'learning_pattern': self._get_learning_pattern(user),
                'recent_performance': self._get_recent_performance(user),
                'teacher_observations': self._get_teacher_observations(user),
            }
            
            return profile
            
        except User.DoesNotExist:
            raise ValueError(f"User with ID {user_id} not found")
    
    def _get_basic_profile(self, user: User) -> Dict[str, Any]:
        """获取基础档案信息"""
        profile = {
            'settings': {},
            'preferences': {},
            'background': {}
        }
        
        # 获取用户设置
        try:
            settings = user.settings
            profile['settings'] = {
                'preferred_pace': settings.preferred_pace,
                'preferred_style': settings.preferred_style,
                'tone': settings.tone,
                'feedback_frequency': settings.feedback_frequency,
                'education_level': settings.education_level,
                'major': settings.major,
                'skills': settings.skills,
            }
        except:
            pass
        
        # 获取课程进度统计
        progresses = CourseProgress.objects.filter(user_uuid=user)
        if progresses.exists():
            profile['background'] = {
                'total_courses': progresses.count(),
                'subjects': list(progresses.values_list('subject_name', flat=True).distinct()),
                'avg_proficiency': progresses.aggregate(avg=Avg('proficiency_level'))['avg'] or 0,
                'total_learning_hours': progresses.aggregate(total=Avg('learning_hour_total'))['total'] or 0,
            }
        
        return profile
    
    def _get_learning_statistics(self, user: User) -> Dict[str, Any]:
        """获取学习统计数据"""
        recent_date = timezone.now() - timedelta(days=self.analysis_window_days)
        sessions = StudySession.objects.filter(
            user=user,
            start_time__gte=recent_date
        )
        
        stats = {
            'total_sessions': sessions.count(),
            'total_duration_minutes': sessions.aggregate(total=Count('duration_minutes'))['total'] or 0,
            'avg_effectiveness': sessions.aggregate(avg=Avg('effectiveness_rating'))['avg'] or 0,
            'avg_focus_score': sessions.aggregate(avg=Avg('focus_score'))['avg'] or 0,
            'productive_sessions': 0,
            'learning_environments': {},
            'devices_used': {},
            'peak_learning_hours': {},
        }
        
        # 计算高效会话
        for session in sessions:
            if hasattr(session, 'is_productive_session') and session.is_productive_session:
                stats['productive_sessions'] += 1
        
        # 分析学习环境偏好
        env_stats = sessions.values('learning_environment').annotate(count=Count('id'))
        stats['learning_environments'] = {item['learning_environment']: item['count'] for item in env_stats}
        
        # 分析设备使用
        device_stats = sessions.values('device_type').annotate(count=Count('id'))
        stats['devices_used'] = {item['device_type']: item['count'] for item in device_stats}
        
        # 分析学习时间偏好
        for session in sessions.filter(start_time__isnull=False):
            hour = session.start_time.hour
            if hour not in stats['peak_learning_hours']:
                stats['peak_learning_hours'][hour] = 0
            stats['peak_learning_hours'][hour] += 1
        
        return stats
    
    def _analyze_student_questions(self, user: User) -> Dict[str, Any]:
        """分析学生提问模式"""
        recent_date = timezone.now() - timedelta(days=self.analysis_window_days)
        questions = StudentQuestion.objects.filter(
            user=user,
            created_at__gte=recent_date
        )
        
        analysis = {
            'total_questions': questions.count(),
            'resolved_rate': 0,
            'question_types': {},
            'difficulty_distribution': {},
            'frequent_topics': [],
            'common_confusion_points': [],
            'question_frequency_trend': 'stable',
        }
        
        if questions.exists():
            # 解决率
            resolved_count = questions.filter(is_resolved=True).count()
            analysis['resolved_rate'] = (resolved_count / questions.count()) * 100
            
            # 问题类型分布
            type_stats = questions.values('question_type').annotate(count=Count('id'))
            analysis['question_types'] = {item['question_type']: item['count'] for item in type_stats}
            
            # 难度分布
            difficulty_stats = questions.values('difficulty_level').annotate(count=Count('id'))
            analysis['difficulty_distribution'] = {item['difficulty_level']: item['count'] for item in difficulty_stats}
            
            # 提取常见标签作为频繁话题
            all_tags = []
            for q in questions:
                all_tags.extend(q.tags)
            
            if all_tags:
                from collections import Counter
                tag_counts = Counter(all_tags)
                analysis['frequent_topics'] = [tag for tag, count in tag_counts.most_common(5)]
            
            # 分析趋势（比较前半段和后半段的问题数量）
            mid_point = recent_date + timedelta(days=self.analysis_window_days // 2)
            recent_questions = questions.filter(created_at__gte=mid_point).count()
            earlier_questions = questions.filter(created_at__lt=mid_point).count()
            
            if earlier_questions > 0:
                trend_ratio = recent_questions / earlier_questions
                if trend_ratio > 1.2:
                    analysis['question_frequency_trend'] = 'increasing'
                elif trend_ratio < 0.8:
                    analysis['question_frequency_trend'] = 'decreasing'
        
        return analysis
    
    def _get_learning_pattern(self, user: User) -> Dict[str, Any]:
        """获取学习模式分析"""
        try:
            pattern = user.learning_pattern
            return {
                'strengths': pattern.strengths,
                'weaknesses': pattern.weaknesses,
                'frequent_question_types': pattern.frequent_question_types,
                'preferred_learning_time': pattern.preferred_learning_time,
                'attention_span_minutes': pattern.attention_span_minutes,
                'difficulty_progression_rate': pattern.difficulty_progression_rate,
                'concept_mastery_patterns': pattern.concept_mastery_patterns,
                'last_analyzed': pattern.last_analyzed.isoformat() if pattern.last_analyzed else None,
            }
        except:
            # 如果没有学习模式记录，返回基于会话数据的简单分析
            return self._analyze_learning_pattern_from_sessions(user)
    
    def _analyze_learning_pattern_from_sessions(self, user: User) -> Dict[str, Any]:
        """基于学习会话分析学习模式"""
        recent_date = timezone.now() - timedelta(days=self.analysis_window_days)
        sessions = StudySession.objects.filter(
            user=user,
            start_time__gte=recent_date
        )
        
        pattern = {
            'strengths': [],
            'weaknesses': [],
            'frequent_question_types': [],
            'preferred_learning_time': {},
            'attention_span_minutes': 30,
            'difficulty_progression_rate': 1.0,
            'concept_mastery_patterns': {},
            'analysis_source': 'session_data',
        }
        
        if sessions.exists():
            # 分析注意力持续时间
            avg_duration = sessions.aggregate(avg=Avg('duration_minutes'))['avg'] or 30
            pattern['attention_span_minutes'] = int(avg_duration)
            
            # 分析偏好学习时间
            time_effectiveness = {}
            for session in sessions.filter(start_time__isnull=False, effectiveness_rating__isnull=False):
                hour = session.start_time.hour
                if hour not in time_effectiveness:
                    time_effectiveness[hour] = []
                time_effectiveness[hour].append(session.effectiveness_rating)
            
            # 计算各时间段的平均效果
            for hour, ratings in time_effectiveness.items():
                pattern['preferred_learning_time'][str(hour)] = sum(ratings) / len(ratings)
            
            # 基于效果评分分析优势和弱项
            avg_effectiveness = sessions.aggregate(avg=Avg('effectiveness_rating'))['avg'] or 3
            avg_focus = sessions.aggregate(avg=Avg('focus_score'))['avg'] or 0.7
            
            if avg_effectiveness >= 4:
                pattern['strengths'].append('high_learning_effectiveness')
            elif avg_effectiveness <= 2:
                pattern['weaknesses'].append('learning_effectiveness_issues')
            
            if avg_focus >= 0.8:
                pattern['strengths'].append('good_focus')
            elif avg_focus <= 0.5:
                pattern['weaknesses'].append('attention_difficulties')
        
        return pattern
    
    def _get_recent_performance(self, user: User) -> Dict[str, Any]:
        """获取最近学习表现"""
        recent_date = timezone.now() - timedelta(days=7)  # 最近一周
        
        performance = {
            'weekly_summary': {},
            'trend_analysis': {},
            'achievements': [],
            'areas_for_improvement': [],
        }
        
        # 最近一周的会话
        recent_sessions = StudySession.objects.filter(
            user=user,
            start_time__gte=recent_date
        )
        
        if recent_sessions.exists():
            performance['weekly_summary'] = {
                'total_sessions': recent_sessions.count(),
                'total_hours': sum(s.duration_minutes for s in recent_sessions) / 60,
                'avg_effectiveness': recent_sessions.aggregate(avg=Avg('effectiveness_rating'))['avg'] or 0,
                'consistency_score': self._calculate_consistency_score(recent_sessions),
            }
            
            # 趋势分析（比较最近3天和之前4天）
            mid_point = recent_date + timedelta(days=3)
            recent_3days = recent_sessions.filter(start_time__gte=mid_point)
            previous_4days = recent_sessions.filter(start_time__lt=mid_point)
            
            if previous_4days.exists() and recent_3days.exists():
                recent_avg = recent_3days.aggregate(avg=Avg('effectiveness_rating'))['avg'] or 0
                previous_avg = previous_4days.aggregate(avg=Avg('effectiveness_rating'))['avg'] or 0
                
                performance['trend_analysis'] = {
                    'effectiveness_trend': 'improving' if recent_avg > previous_avg else 'declining' if recent_avg < previous_avg else 'stable',
                    'recent_avg_effectiveness': recent_avg,
                    'previous_avg_effectiveness': previous_avg,
                }
        
        # 基于课程进度的成就
        progresses = CourseProgress.objects.filter(user_uuid=user)
        for progress in progresses:
            if progress.proficiency_level >= 75:
                performance['achievements'].append(f"在{progress.subject_name}中达到高级水平")
            elif progress.get_completion_progress() >= 80:
                performance['achievements'].append(f"{progress.subject_name}课程完成度超过80%")
        
        return performance
    
    def _calculate_consistency_score(self, sessions) -> float:
        """计算学习一致性评分"""
        if not sessions:
            return 0.0
        
        # 基于学习频率和持续时间的一致性
        session_dates = [s.start_time.date() for s in sessions if s.start_time]
        unique_dates = set(session_dates)
        
        # 计算日均学习天数占比
        total_days = 7  # 一周
        learning_days = len(unique_dates)
        frequency_score = learning_days / total_days
        
        # 计算学习时长的一致性（标准差越小越一致）
        durations = [s.duration_minutes for s in sessions]
        if len(durations) > 1:
            import statistics
            duration_std = statistics.stdev(durations)
            avg_duration = statistics.mean(durations)
            consistency_score = max(0, 1 - (duration_std / avg_duration) if avg_duration > 0 else 0)
        else:
            consistency_score = 1.0
        
        return (frequency_score + consistency_score) / 2
    
    def _get_teacher_observations(self, user: User) -> Dict[str, Any]:
        """获取教师观察记录"""
        recent_date = timezone.now() - timedelta(days=self.analysis_window_days)
        notes = TeacherNotes.objects.filter(
            user=user,
            created_at__gte=recent_date
        )
        
        observations = {
            'total_notes': notes.count(),
            'note_types': {},
            'priority_distribution': {},
            'recent_highlights': [],
            'action_items': [],
        }
        
        if notes.exists():
            # 笔记类型分布
            type_stats = notes.values('note_type').annotate(count=Count('id'))
            observations['note_types'] = {item['note_type']: item['count'] for item in type_stats}
            
            # 优先级分布
            priority_stats = notes.values('priority').annotate(count=Count('id'))
            observations['priority_distribution'] = {item['priority']: item['count'] for item in priority_stats}
            
            # 最近的重要观察
            recent_important = notes.filter(
                Q(priority='high') | Q(priority='urgent')
            ).order_by('-created_at')[:3]
            
            observations['recent_highlights'] = [
                {
                    'title': note.title,
                    'content': note.content[:200] + ('...' if len(note.content) > 200 else ''),
                    'type': note.note_type,
                    'priority': note.priority,
                    'date': note.created_at.isoformat(),
                }
                for note in recent_important
            ]
            
            # 收集所有行动项
            all_action_items = []
            for note in notes:
                all_action_items.extend(note.action_items)
            observations['action_items'] = list(set(all_action_items))[:10]  # 去重并限制数量
        
        return observations
    
    def generate_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """生成学习洞察和建议"""
        profile = self.get_student_profile(user_id)
        
        insights = {
            'strengths': [],
            'challenges': [],
            'recommendations': [],
            'personalization_suggestions': {},
            'risk_indicators': [],
        }
        
        # 分析优势
        learning_stats = profile['learning_stats']
        if learning_stats['avg_effectiveness'] >= 4:
            insights['strengths'].append("学习效果评分优秀，能够有效掌握学习内容")
        
        if learning_stats['productive_sessions'] / max(learning_stats['total_sessions'], 1) >= 0.7:
            insights['strengths'].append("高效学习会话比例较高，学习专注度良好")
        
        # 分析挑战
        question_analysis = profile['question_analysis']
        if question_analysis['resolved_rate'] < 60:
            insights['challenges'].append("问题解决率较低，可能需要更多的指导和支持")
        
        if question_analysis['question_frequency_trend'] == 'increasing':
            insights['challenges'].append("提问频率呈上升趋势，可能遇到了新的学习难点")
        
        # 生成个性化建议
        pattern = profile['learning_pattern']
        if 'attention_difficulties' in pattern.get('weaknesses', []):
            insights['recommendations'].append("建议采用番茄工作法，将学习时间分割为25分钟的专注时段")
            insights['personalization_suggestions']['break_frequency'] = 'high'
        
        if pattern.get('attention_span_minutes', 30) < 20:
            insights['recommendations'].append("考虑缩短单次学习时长，增加学习频次")
            insights['personalization_suggestions']['session_duration'] = 'short'
        
        # 风险指标
        recent_performance = profile['recent_performance']
        if recent_performance['weekly_summary'].get('consistency_score', 0) < 0.5:
            insights['risk_indicators'].append("学习一致性较低，建议建立规律的学习计划")
        
        if recent_performance['trend_analysis'].get('effectiveness_trend') == 'declining':
            insights['risk_indicators'].append("学习效果呈下降趋势，需要及时调整学习策略")
        
        return insights
    
    def update_learning_pattern(self, user_id: str) -> Dict[str, Any]:
        """更新学生学习模式分析"""
        try:
            user = User.objects.get(uuid=user_id)
            
            # 获取或创建学习模式记录
            pattern, created = StudentLearningPattern.objects.get_or_create(
                user=user,
                defaults={
                    'strengths': [],
                    'weaknesses': [],
                    'frequent_question_types': [],
                    'preferred_learning_time': {},
                    'attention_span_minutes': 30,
                    'difficulty_progression_rate': 1.0,
                    'concept_mastery_patterns': {},
                }
            )
            
            # 基于最新数据更新模式
            session_analysis = self._analyze_learning_pattern_from_sessions(user)
            question_analysis = self._analyze_student_questions(user)
            
            # 更新字段
            pattern.preferred_learning_time = session_analysis['preferred_learning_time']
            pattern.attention_span_minutes = session_analysis['attention_span_minutes']
            
            # 更新常见问题类型
            pattern.frequent_question_types = list(question_analysis['question_types'].keys())
            
            # 分析学习强项和弱项
            updated_strengths = set(pattern.strengths)
            updated_weaknesses = set(pattern.weaknesses)
            
            # 基于会话数据更新
            for strength in session_analysis.get('strengths', []):
                updated_strengths.add(strength)
                updated_weaknesses.discard(strength)  # 移除相反的弱项
            
            for weakness in session_analysis.get('weaknesses', []):
                updated_weaknesses.add(weakness)
                updated_strengths.discard(weakness)  # 移除相反的强项
            
            pattern.strengths = list(updated_strengths)
            pattern.weaknesses = list(updated_weaknesses)
            pattern.save()
            
            return {
                'success': True,
                'pattern_id': str(pattern.id),
                'updated_fields': [
                    'preferred_learning_time',
                    'attention_span_minutes',
                    'frequent_question_types',
                    'strengths',
                    'weaknesses'
                ],
                'last_analyzed': pattern.last_analyzed.isoformat(),
            }
            
        except User.DoesNotExist:
            return {
                'success': False,
                'error': f"User with ID {user_id} not found"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# 全局分析器实例
student_analyzer = StudentDataAnalyzer()
