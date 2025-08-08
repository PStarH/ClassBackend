"""
Dynamic Context Engine - Core orchestration for advanced context management
Integrates all context analysis components for personalized learning
"""
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings

# Import context components
from .advanced_context_engine import (
    LearningContext, 
    LearningModalityType, 
    EmotionalState, 
    CognitiveLoadLevel,
    ImmediateContextAnalyzer,
    EmotionalContextAnalyzer,
    MultimodalContextEngine
)

# Import existing services
from .memory_service import memory_service
from .student_analyzer import student_analyzer
from .conversation_manager import ConversationManager
from ..core.base_service import LLMBaseService
from apps.authentication.models import User
from apps.learning_plans.models import StudySession


class PersistentContextManager:
    """Manages long-term context storage and retrieval with semantic indexing"""
    
    def __init__(self):
        self.context_cache_prefix = "learning_context:"
        self.context_history_prefix = "context_history:"
        self.semantic_index_prefix = "context_semantic:"
        
    def store_learning_context(self, user_id: str, context: LearningContext) -> bool:
        """Store learning context with semantic indexing"""
        try:
            context_key = f"{self.context_cache_prefix}{user_id}:latest"
            history_key = f"{self.context_history_prefix}{user_id}"
            
            # Convert context to dictionary for storage
            context_dict = self._context_to_dict(context)
            
            # Store latest context (24 hour TTL)
            cache.set(context_key, context_dict, timeout=86400)
            
            # Add to history (7 day TTL)
            history = cache.get(history_key, [])
            history.append({
                'timestamp': context.timestamp.isoformat(),
                'context': context_dict
            })
            
            # Keep only last 100 interactions
            if len(history) > 100:
                history = history[-100:]
            
            cache.set(history_key, history, timeout=604800)  # 7 days
            
            # Generate semantic embeddings for future retrieval
            self._index_context_semantically(user_id, context_dict)
            
            return True
            
        except Exception as e:
            print(f"Error storing learning context: {e}")
            return False
    
    def retrieve_relevant_context(self, user_id: str, current_query: str, 
                                limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve most relevant historical context"""
        try:
            history_key = f"{self.context_history_prefix}{user_id}"
            history = cache.get(history_key, [])
            
            if not history:
                return []
            
            # Simple relevance scoring (can be enhanced with vector similarity)
            relevant_contexts = []
            
            for entry in history[-50:]:  # Look at recent history
                context = entry['context']
                relevance_score = self._calculate_context_relevance(context, current_query)
                
                if relevance_score > 0.3:  # Threshold for relevance
                    relevant_contexts.append({
                        'context': context,
                        'timestamp': entry['timestamp'],
                        'relevance_score': relevance_score
                    })
            
            # Sort by relevance and recency
            relevant_contexts.sort(key=lambda x: (x['relevance_score'], x['timestamp']), reverse=True)
            
            return relevant_contexts[:limit]
            
        except Exception as e:
            print(f"Error retrieving relevant context: {e}")
            return []
    
    def get_context_trends(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Analyze context trends over time"""
        try:
            history_key = f"{self.context_history_prefix}{user_id}"
            history = cache.get(history_key, [])
            
            if not history:
                return {}
            
            # Filter by date range
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_history = [
                entry for entry in history 
                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
            ]
            
            if not recent_history:
                return {}
            
            # Calculate trends
            trends = {
                'performance_trend': self._calculate_performance_trend(recent_history),
                'emotional_trend': self._calculate_emotional_trend(recent_history),
                'engagement_trend': self._calculate_engagement_trend(recent_history),
                'difficulty_progression': self._calculate_difficulty_progression(recent_history),
                'modality_preferences': self._calculate_modality_trends(recent_history),
                'study_patterns': self._analyze_study_patterns(recent_history)
            }
            
            return trends
            
        except Exception as e:
            print(f"Error calculating context trends: {e}")
            return {}
    
    def _context_to_dict(self, context: LearningContext) -> Dict[str, Any]:
        """Convert LearningContext to dictionary for storage"""
        return {
            'user_id': context.user_id,
            'session_id': context.session_id,
            'timestamp': context.timestamp.isoformat(),
            'current_topic': context.current_topic,
            'current_difficulty': context.current_difficulty,
            'current_performance': context.current_performance,
            'response_time': context.response_time,
            'interaction_count': context.interaction_count,
            'session_duration': context.session_duration,
            'topics_covered': context.topics_covered,
            'concepts_mastered': context.concepts_mastered,
            'concepts_struggling': context.concepts_struggling,
            'questions_asked': context.questions_asked,
            'mistakes_made': context.mistakes_made,
            'preferred_modality': context.preferred_modality.value,
            'learning_pace': context.learning_pace,
            'attention_span': context.attention_span,
            'optimal_session_length': context.optimal_session_length,
            'peak_performance_time': context.peak_performance_time,
            'emotional_state': context.emotional_state.value,
            'motivation_level': context.motivation_level,
            'confidence_level': context.confidence_level,
            'frustration_indicators': context.frustration_indicators,
            'engagement_score': context.engagement_score,
            'total_study_time': context.total_study_time,
            'mastery_rate': context.mastery_rate,
            'retention_score': context.retention_score,
            'improvement_trend': context.improvement_trend,
            'learning_streaks': context.learning_streaks,
            'device_type': context.device_type,
            'session_time': context.session_time,
            'estimated_distractions': context.estimated_distractions,
            'study_location': context.study_location,
            'cognitive_load': context.cognitive_load.value,
            'working_memory_capacity': context.working_memory_capacity,
            'processing_speed': context.processing_speed,
            'metacognitive_awareness': context.metacognitive_awareness
        }
    
    def _dict_to_context(self, context_dict: Dict[str, Any]) -> LearningContext:
        """Convert dictionary back to LearningContext"""
        return LearningContext(
            user_id=context_dict['user_id'],
            session_id=context_dict['session_id'],
            timestamp=datetime.fromisoformat(context_dict['timestamp']),
            current_topic=context_dict['current_topic'],
            current_difficulty=context_dict['current_difficulty'],
            current_performance=context_dict['current_performance'],
            response_time=context_dict['response_time'],
            interaction_count=context_dict['interaction_count'],
            session_duration=context_dict['session_duration'],
            topics_covered=context_dict['topics_covered'],
            concepts_mastered=context_dict['concepts_mastered'],
            concepts_struggling=context_dict['concepts_struggling'],
            questions_asked=context_dict['questions_asked'],
            mistakes_made=context_dict['mistakes_made'],
            preferred_modality=LearningModalityType(context_dict['preferred_modality']),
            learning_pace=context_dict['learning_pace'],
            attention_span=context_dict['attention_span'],
            optimal_session_length=context_dict['optimal_session_length'],
            peak_performance_time=context_dict['peak_performance_time'],
            emotional_state=EmotionalState(context_dict['emotional_state']),
            motivation_level=context_dict['motivation_level'],
            confidence_level=context_dict['confidence_level'],
            frustration_indicators=context_dict['frustration_indicators'],
            engagement_score=context_dict['engagement_score'],
            total_study_time=context_dict['total_study_time'],
            mastery_rate=context_dict['mastery_rate'],
            retention_score=context_dict['retention_score'],
            improvement_trend=context_dict['improvement_trend'],
            learning_streaks=context_dict['learning_streaks'],
            device_type=context_dict['device_type'],
            session_time=context_dict['session_time'],
            estimated_distractions=context_dict['estimated_distractions'],
            study_location=context_dict['study_location'],
            cognitive_load=CognitiveLoadLevel(context_dict['cognitive_load']),
            working_memory_capacity=context_dict['working_memory_capacity'],
            processing_speed=context_dict['processing_speed'],
            metacognitive_awareness=context_dict['metacognitive_awareness']
        )
    
    def _index_context_semantically(self, user_id: str, context_dict: Dict[str, Any]):
        """Create semantic index for context (simplified version)"""
        # This would ideally use vector embeddings
        semantic_key = f"{self.semantic_index_prefix}{user_id}"
        
        # Create searchable text from context
        searchable_text = f"{context_dict['current_topic']} {context_dict['emotional_state']} " + \
                         f"{' '.join(context_dict['concepts_mastered'])} " + \
                         f"{' '.join(context_dict['concepts_struggling'])}"
        
        # Store in semantic index
        semantic_index = cache.get(semantic_key, {})
        timestamp = context_dict['timestamp']
        semantic_index[timestamp] = searchable_text
        
        cache.set(semantic_key, semantic_index, timeout=604800)  # 7 days
    
    def _calculate_context_relevance(self, context: Dict[str, Any], query: str) -> float:
        """Calculate relevance score between stored context and current query"""
        relevance_factors = []
        
        query_lower = query.lower()
        
        # Topic relevance
        if context['current_topic'].lower() in query_lower:
            relevance_factors.append(0.4)
        
        # Concept relevance
        for concept in context.get('concepts_mastered', []):
            if concept.lower() in query_lower:
                relevance_factors.append(0.3)
        
        for concept in context.get('concepts_struggling', []):
            if concept.lower() in query_lower:
                relevance_factors.append(0.5)  # Higher weight for struggle areas
        
        # Emotional state relevance (if query indicates similar state)
        emotional_keywords = {
            'confused': ['confused', 'don\'t understand', 'unclear'],
            'frustrated': ['frustrated', 'difficult', 'hard'],
            'motivated': ['excited', 'ready', 'motivated']
        }
        
        current_emotional = context.get('emotional_state', '')
        for emotion, keywords in emotional_keywords.items():
            if emotion == current_emotional and any(kw in query_lower for kw in keywords):
                relevance_factors.append(0.2)
        
        # Return average relevance or 0 if no factors found
        return sum(relevance_factors) / len(relevance_factors) if relevance_factors else 0.0
    
    def _calculate_performance_trend(self, history: List[Dict]) -> str:
        """Calculate performance trend over time"""
        if len(history) < 2:
            return 'insufficient_data'
        
        performances = [entry['context']['current_performance'] for entry in history]
        recent_avg = sum(performances[-5:]) / min(5, len(performances))
        earlier_avg = sum(performances[:-5]) / max(1, len(performances) - 5) if len(performances) > 5 else recent_avg
        
        if recent_avg > earlier_avg + 0.1:
            return 'improving'
        elif recent_avg < earlier_avg - 0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_emotional_trend(self, history: List[Dict]) -> Dict[str, Any]:
        """Calculate emotional state trends"""
        emotions = [entry['context']['emotional_state'] for entry in history]
        emotion_counts = {}
        
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else 'unknown'
        
        # Calculate emotional stability
        recent_emotions = emotions[-10:]
        stability_score = len(set(recent_emotions)) / len(recent_emotions) if recent_emotions else 1.0
        
        return {
            'dominant_emotion': dominant_emotion,
            'emotion_distribution': emotion_counts,
            'emotional_stability': 1.0 - stability_score  # Lower diversity = higher stability
        }
    
    def _calculate_engagement_trend(self, history: List[Dict]) -> str:
        """Calculate engagement trend over time"""
        if len(history) < 2:
            return 'insufficient_data'
        
        engagement_scores = [entry['context']['engagement_score'] for entry in history]
        recent_avg = sum(engagement_scores[-5:]) / min(5, len(engagement_scores))
        earlier_avg = sum(engagement_scores[:-5]) / max(1, len(engagement_scores) - 5) if len(engagement_scores) > 5 else recent_avg
        
        if recent_avg > earlier_avg + 0.1:
            return 'increasing'
        elif recent_avg < earlier_avg - 0.1:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_difficulty_progression(self, history: List[Dict]) -> Dict[str, Any]:
        """Calculate how difficulty level has progressed"""
        difficulties = [entry['context']['current_difficulty'] for entry in history]
        
        if len(difficulties) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend
        recent_avg = sum(difficulties[-5:]) / min(5, len(difficulties))
        earlier_avg = sum(difficulties[:-5]) / max(1, len(difficulties) - 5) if len(difficulties) > 5 else recent_avg
        
        trend = 'increasing' if recent_avg > earlier_avg + 0.1 else \
                'decreasing' if recent_avg < earlier_avg - 0.1 else 'stable'
        
        return {
            'trend': trend,
            'current_average': recent_avg,
            'difficulty_range': (min(difficulties), max(difficulties)),
            'progression_rate': recent_avg - earlier_avg
        }
    
    def _calculate_modality_trends(self, history: List[Dict]) -> Dict[str, Any]:
        """Calculate learning modality preference trends"""
        modalities = [entry['context']['preferred_modality'] for entry in history]
        modality_counts = {}
        
        for modality in modalities:
            modality_counts[modality] = modality_counts.get(modality, 0) + 1
        
        return {
            'preference_distribution': modality_counts,
            'most_used': max(modality_counts, key=modality_counts.get) if modality_counts else 'unknown',
            'diversity_score': len(set(modalities)) / len(modalities) if modalities else 0
        }
    
    def _analyze_study_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze study session patterns"""
        session_times = [entry['context']['session_time'] for entry in history]
        session_durations = [entry['context']['session_duration'] for entry in history]
        
        # Time of day preferences
        time_counts = {}
        for time_slot in session_times:
            time_counts[time_slot] = time_counts.get(time_slot, 0) + 1
        
        preferred_time = max(time_counts, key=time_counts.get) if time_counts else 'unknown'
        
        # Session duration patterns
        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        return {
            'preferred_study_time': preferred_time,
            'time_distribution': time_counts,
            'average_session_duration': avg_duration,
            'session_consistency': self._calculate_consistency(session_durations)
        }
    
    def _calculate_consistency(self, values: List[float]) -> str:
        """Calculate consistency of values"""
        if len(values) < 2:
            return 'insufficient_data'
        
        import statistics
        cv = statistics.stdev(values) / statistics.mean(values) if statistics.mean(values) > 0 else 0
        
        if cv < 0.2:
            return 'very_consistent'
        elif cv < 0.4:
            return 'consistent'
        elif cv < 0.6:
            return 'somewhat_variable'
        else:
            return 'highly_variable'


class DynamicContextEngine(LLMBaseService):
    """Main context engine orchestrating all context analysis components"""
    
    def __init__(self):
        super().__init__()
        self.immediate_analyzer = ImmediateContextAnalyzer()
        self.emotional_analyzer = EmotionalContextAnalyzer()
        self.multimodal_engine = MultimodalContextEngine()
        self.persistent_manager = PersistentContextManager()
        self.conversation_manager = ConversationManager()
        
    async def analyze_comprehensive_context(self, user_id: str, session_id: str, 
                                          user_message: str, response_time: float,
                                          additional_data: Dict[str, Any] = None) -> LearningContext:
        """Perform comprehensive context analysis"""
        
        # Get base student profile
        student_profile = student_analyzer.get_student_profile(user_id)
        
        # Get conversation history
        conversation_history = memory_service.get_conversation_history(user_id, session_id)
        interaction_history = conversation_history.get('messages', [])
        
        # Immediate context analysis
        immediate_context = self.immediate_analyzer.analyze_current_interaction(
            user_message, response_time, interaction_history
        )
        
        # Emotional context analysis
        recent_messages = [msg.get('input', '') for msg in interaction_history[-10:]]
        recent_messages.append(user_message)
        
        performance_data = additional_data.get('performance_data', {}) if additional_data else {}
        emotional_context = self.emotional_analyzer.analyze_emotional_state(
            recent_messages, performance_data, interaction_history
        )
        
        # Get historical context trends
        context_trends = self.persistent_manager.get_context_trends(user_id, days=7)
        
        # Build comprehensive learning context
        learning_context = await self._build_learning_context(
            user_id, session_id, student_profile, immediate_context, 
            emotional_context, interaction_history, context_trends, additional_data
        )
        
        # Store context for future reference
        self.persistent_manager.store_learning_context(user_id, learning_context)
        
        return learning_context
    
    async def _build_learning_context(self, user_id: str, session_id: str,
                                    student_profile: Dict[str, Any],
                                    immediate_context: Dict[str, Any],
                                    emotional_context: Dict[str, Any],
                                    interaction_history: List[Dict],
                                    context_trends: Dict[str, Any],
                                    additional_data: Optional[Dict[str, Any]]) -> LearningContext:
        """Build comprehensive LearningContext object"""
        
        # Extract current session data
        session_start_time = datetime.now() - timedelta(minutes=len(interaction_history) * 2)  # Estimate
        session_duration = (datetime.now() - session_start_time).total_seconds() / 60
        
        # Extract topics and concepts from interaction history
        topics_covered = list(set([
            interaction.get('topic', immediate_context['topic_focus'])
            for interaction in interaction_history[-10:]
        ]))
        topics_covered.append(immediate_context['topic_focus'])
        
        # Determine cognitive load
        cognitive_load = self._assess_cognitive_load(immediate_context, emotional_context, student_profile)
        
        # Get device and environmental context
        device_type = additional_data.get('device_type', 'desktop') if additional_data else 'desktop'
        current_hour = datetime.now().hour
        session_time = 'morning' if 6 <= current_hour < 12 else \
                      'afternoon' if 12 <= current_hour < 18 else 'evening'
        
        # Build learning context
        learning_context = LearningContext(
            user_id=user_id,
            session_id=session_id,
            timestamp=datetime.now(),
            
            # Immediate Context
            current_topic=immediate_context['topic_focus'],
            current_difficulty=immediate_context['complexity_level'],
            current_performance=self._estimate_current_performance(immediate_context, emotional_context),
            response_time=additional_data.get('response_time', 5.0) if additional_data else 5.0,
            interaction_count=len(interaction_history) + 1,
            
            # Session Context
            session_duration=session_duration,
            topics_covered=topics_covered,
            concepts_mastered=student_profile.get('recent_performance', {}).get('concepts_mastered', []),
            concepts_struggling=student_profile.get('recent_performance', {}).get('concepts_struggling', []),
            questions_asked=len([m for m in interaction_history if '?' in m.get('input', '')]),
            mistakes_made=additional_data.get('mistakes_made', 0) if additional_data else 0,
            
            # Behavioral Context
            preferred_modality=LearningModalityType(
                student_profile.get('profile', {}).get('settings', {}).get('preferred_style', 'visual')
            ),
            learning_pace=student_profile.get('learning_pattern', {}).get('preferred_pace', 'medium'),
            attention_span=student_profile.get('learning_pattern', {}).get('attention_span', 20),
            optimal_session_length=student_profile.get('learning_pattern', {}).get('optimal_session_length', 45),
            peak_performance_time=student_profile.get('learning_pattern', {}).get('peak_performance_time', 'morning'),
            
            # Emotional Context
            emotional_state=EmotionalState(emotional_context['primary_emotion'].value),
            motivation_level=emotional_context['motivation_score'],
            confidence_level=emotional_context['confidence_level'],
            frustration_indicators=immediate_context.get('confusion_indicators', []),
            engagement_score=emotional_context['engagement_score'],
            
            # Historical Context
            total_study_time=student_profile.get('learning_stats', {}).get('total_study_hours', 0),
            mastery_rate=student_profile.get('learning_stats', {}).get('mastery_rate', 0.5),
            retention_score=student_profile.get('learning_stats', {}).get('retention_rate', 0.7),
            improvement_trend=context_trends.get('performance_trend', 'stable'),
            learning_streaks=student_profile.get('learning_pattern', {}).get('streaks', {}),
            
            # Environmental Context
            device_type=device_type,
            session_time=session_time,
            estimated_distractions=self._estimate_distractions(device_type, session_time),
            study_location=additional_data.get('study_location', 'unknown') if additional_data else 'unknown',
            
            # Cognitive Context
            cognitive_load=cognitive_load,
            working_memory_capacity=student_profile.get('learning_pattern', {}).get('working_memory', 5),
            processing_speed=student_profile.get('learning_pattern', {}).get('processing_speed', 'medium'),
            metacognitive_awareness=self._assess_metacognitive_awareness(student_profile, interaction_history)
        )
        
        return learning_context
    
    def _assess_cognitive_load(self, immediate_context: Dict[str, Any], 
                             emotional_context: Dict[str, Any], 
                             student_profile: Dict[str, Any]) -> CognitiveLoadLevel:
        """Assess current cognitive load level"""
        load_factors = []
        
        # High complexity indicates higher cognitive load
        if immediate_context['complexity_level'] > 0.7:
            load_factors.append(0.3)
        elif immediate_context['complexity_level'] > 0.4:
            load_factors.append(0.1)
        
        # Frustration and confusion increase cognitive load
        if emotional_context['frustration_level'] > 0.6:
            load_factors.append(0.4)
        elif emotional_context['frustration_level'] > 0.3:
            load_factors.append(0.2)
        
        # Low confidence indicates struggling, increasing cognitive load
        if emotional_context['confidence_level'] < 0.3:
            load_factors.append(0.3)
        elif emotional_context['confidence_level'] < 0.6:
            load_factors.append(0.1)
        
        # Multiple confusion indicators increase load
        if len(immediate_context.get('confusion_indicators', [])) > 2:
            load_factors.append(0.2)
        
        total_load = sum(load_factors)
        
        if total_load > 0.8:
            return CognitiveLoadLevel.OVERLOAD
        elif total_load > 0.5:
            return CognitiveLoadLevel.HIGH
        elif total_load > 0.2:
            return CognitiveLoadLevel.MODERATE
        else:
            return CognitiveLoadLevel.LOW
    
    def _estimate_current_performance(self, immediate_context: Dict[str, Any], 
                                    emotional_context: Dict[str, Any]) -> float:
        """Estimate current performance based on context indicators"""
        base_performance = 0.5
        
        # Adjust based on emotional state
        if emotional_context['confidence_level'] > 0.7:
            base_performance += 0.2
        elif emotional_context['confidence_level'] < 0.3:
            base_performance -= 0.2
        
        # Adjust based on engagement
        if emotional_context['engagement_score'] > 0.7:
            base_performance += 0.1
        elif emotional_context['engagement_score'] < 0.3:
            base_performance -= 0.1
        
        # Adjust based on frustration
        if emotional_context['frustration_level'] > 0.6:
            base_performance -= 0.3
        
        # Adjust based on response time analysis
        response_analysis = immediate_context.get('response_time_analysis', {})
        if response_analysis.get('possible_difficulty'):
            base_performance -= 0.1
        elif response_analysis.get('possible_confidence'):
            base_performance += 0.1
        
        return max(0.0, min(base_performance, 1.0))
    
    def _estimate_distractions(self, device_type: str, session_time: str) -> int:
        """Estimate number of distractions based on environment"""
        base_distractions = 1
        
        # Mobile devices tend to have more distractions
        if device_type == 'mobile':
            base_distractions += 2
        elif device_type == 'tablet':
            base_distractions += 1
        
        # Evening sessions might have more distractions
        if session_time == 'evening':
            base_distractions += 1
        elif session_time == 'afternoon':
            base_distractions += 0.5
        
        return int(base_distractions)
    
    def _assess_metacognitive_awareness(self, student_profile: Dict[str, Any], 
                                      interaction_history: List[Dict]) -> float:
        """Assess student's metacognitive awareness level"""
        base_awareness = 0.5
        
        # Look for metacognitive indicators in conversation
        metacognitive_phrases = [
            'i think i understand',
            'i need to practice',
            'this is difficult for me',
            'i\'m good at',
            'i struggle with',
            'let me think',
            'i realize'
        ]
        
        recent_inputs = [msg.get('input', '').lower() for msg in interaction_history[-10:]]
        metacognitive_count = sum(1 for msg in recent_inputs 
                                 for phrase in metacognitive_phrases 
                                 if phrase in msg)
        
        # Adjust awareness based on self-reflection indicators
        if metacognitive_count > 3:
            base_awareness += 0.3
        elif metacognitive_count > 1:
            base_awareness += 0.1
        
        # Factor in learning pattern data
        pattern_data = student_profile.get('learning_pattern', {})
        if pattern_data.get('self_assessment_accuracy', 0) > 0.7:
            base_awareness += 0.2
        
        return max(0.0, min(base_awareness, 1.0))