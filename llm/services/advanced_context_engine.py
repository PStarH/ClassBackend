"""
Advanced Context Engineering System for Personalized Learning
Enhanced AI Agent Service with Dynamic Context Management
"""
import json
import time
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from django.core.cache import cache
from django.utils import timezone

# Import existing services
from .memory_service import memory_service
from .student_analyzer import student_analyzer
from ..core.base_service import LLMBaseService
from apps.authentication.models import User
from apps.learning_plans.models import StudySession


class LearningModalityType(Enum):
    """Learning modality preferences"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    READING_WRITING = "reading_writing"
    MULTIMODAL = "multimodal"


class EmotionalState(Enum):
    """Student emotional states"""
    MOTIVATED = "motivated"
    FRUSTRATED = "frustrated"
    CONFIDENT = "confident"
    CONFUSED = "confused"
    ENGAGED = "engaged"
    BORED = "bored"
    ANXIOUS = "anxious"
    SATISFIED = "satisfied"


class CognitiveLoadLevel(Enum):
    """Cognitive load assessment levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    OVERLOAD = "overload"


@dataclass
class LearningContext:
    """Comprehensive learning context data structure"""
    user_id: str
    session_id: str
    timestamp: datetime
    
    # Immediate Context (current interaction)
    current_topic: str
    current_difficulty: float  # 0.0 to 1.0
    current_performance: float  # 0.0 to 1.0
    response_time: float  # seconds
    interaction_count: int
    
    # Session Context (multi-turn conversation)
    session_duration: float  # minutes
    topics_covered: List[str]
    concepts_mastered: List[str]
    concepts_struggling: List[str]
    questions_asked: int
    mistakes_made: int
    
    # Behavioral Context (learning patterns)
    preferred_modality: LearningModalityType
    learning_pace: str  # "slow", "medium", "fast"
    attention_span: int  # minutes
    optimal_session_length: int  # minutes
    peak_performance_time: str  # "morning", "afternoon", "evening"
    
    # Emotional Context (motivational state)
    emotional_state: EmotionalState
    motivation_level: float  # 0.0 to 1.0
    confidence_level: float  # 0.0 to 1.0
    frustration_indicators: List[str]
    engagement_score: float  # 0.0 to 1.0
    
    # Historical Context (long-term learning history)
    total_study_time: float  # hours
    mastery_rate: float  # 0.0 to 1.0
    retention_score: float  # 0.0 to 1.0
    improvement_trend: str  # "improving", "stable", "declining"
    learning_streaks: Dict[str, int]
    
    # Environmental Context (learning environment)
    device_type: str  # "desktop", "tablet", "mobile"
    session_time: str  # "morning", "afternoon", "evening"
    estimated_distractions: int
    study_location: str  # "home", "library", "other"
    
    # Cognitive Context (mental state)
    cognitive_load: CognitiveLoadLevel
    working_memory_capacity: int
    processing_speed: str  # "fast", "medium", "slow"
    metacognitive_awareness: float  # 0.0 to 1.0


class ImmediateContextAnalyzer:
    """Analyzes immediate interaction context"""
    
    def analyze_current_interaction(self, user_message: str, response_time: float, 
                                  interaction_history: List[Dict]) -> Dict[str, Any]:
        """Analyze immediate context from current interaction"""
        return {
            'complexity_level': self._assess_question_complexity(user_message),
            'topic_focus': self._extract_topic_focus(user_message),
            'urgency_level': self._detect_urgency(user_message),
            'confusion_indicators': self._detect_confusion(user_message),
            'response_time_analysis': self._analyze_response_time(response_time, interaction_history)
        }
    
    def _assess_question_complexity(self, message: str) -> float:
        """Assess complexity of user's question/input"""
        complexity_indicators = {
            'keywords': ['why', 'how', 'explain', 'analyze', 'compare', 'evaluate'],
            'length': len(message.split()),
            'technical_terms': len([w for w in message.split() if len(w) > 8]),
            'question_marks': message.count('?')
        }
        
        # Simple heuristic scoring
        score = 0.0
        if any(kw in message.lower() for kw in complexity_indicators['keywords']):
            score += 0.3
        if complexity_indicators['length'] > 20:
            score += 0.2
        if complexity_indicators['technical_terms'] > 2:
            score += 0.3
        if complexity_indicators['question_marks'] > 1:
            score += 0.2
        
        return min(score, 1.0)
    
    def _extract_topic_focus(self, message: str) -> str:
        """Extract main topic from user message"""
        # Simple keyword extraction (can be enhanced with NLP)
        common_topics = {
            'mathematics': ['math', 'algebra', 'geometry', 'calculus', 'statistics'],
            'science': ['physics', 'chemistry', 'biology', 'science'],
            'programming': ['code', 'python', 'javascript', 'programming', 'algorithm'],
            'language': ['grammar', 'writing', 'literature', 'language'],
            'history': ['history', 'historical', 'past', 'ancient']
        }
        
        message_lower = message.lower()
        for topic, keywords in common_topics.items():
            if any(keyword in message_lower for keyword in keywords):
                return topic
        
        return 'general'
    
    def _detect_urgency(self, message: str) -> float:
        """Detect urgency in user message"""
        urgency_indicators = ['urgent', 'asap', 'quickly', 'help!', 'stuck', 'confused', 'lost']
        message_lower = message.lower()
        urgency_count = sum(1 for indicator in urgency_indicators if indicator in message_lower)
        return min(urgency_count * 0.3, 1.0)
    
    def _detect_confusion(self, message: str) -> List[str]:
        """Detect confusion indicators in user message"""
        confusion_patterns = [
            "i don't understand",
            "confused",
            "not clear",
            "doesn't make sense",
            "lost",
            "help",
            "stuck"
        ]
        
        message_lower = message.lower()
        detected = [pattern for pattern in confusion_patterns if pattern in message_lower]
        return detected
    
    def _analyze_response_time(self, current_time: float, history: List[Dict]) -> Dict[str, Any]:
        """Analyze response time patterns"""
        if not history:
            return {'status': 'first_interaction', 'relative_speed': 'baseline'}
        
        recent_times = [h.get('response_time', 0) for h in history[-5:]]
        avg_time = np.mean(recent_times) if recent_times else current_time
        
        if current_time > avg_time * 2:
            return {'status': 'much_slower', 'possible_difficulty': True}
        elif current_time > avg_time * 1.5:
            return {'status': 'slower', 'possible_difficulty': False}
        elif current_time < avg_time * 0.5:
            return {'status': 'much_faster', 'possible_confidence': True}
        else:
            return {'status': 'normal', 'consistent_pace': True}


class EmotionalContextAnalyzer:
    """Analyzes emotional and motivational context"""
    
    def analyze_emotional_state(self, user_messages: List[str], 
                              performance_data: Dict[str, Any],
                              interaction_history: List[Dict]) -> Dict[str, Any]:
        """Comprehensive emotional state analysis"""
        
        # Sentiment analysis from messages
        sentiment_scores = [self._analyze_message_sentiment(msg) for msg in user_messages]
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.5
        
        # Frustration detection
        frustration_level = self._detect_frustration_level(user_messages, performance_data)
        
        # Motivation assessment
        motivation_score = self._assess_motivation(user_messages, performance_data, interaction_history)
        
        # Confidence level
        confidence_level = self._assess_confidence(user_messages, performance_data)
        
        # Engagement scoring
        engagement_score = self._calculate_engagement(interaction_history, performance_data)
        
        # Determine primary emotional state
        primary_emotion = self._determine_primary_emotion(
            avg_sentiment, frustration_level, motivation_score, confidence_level, engagement_score
        )
        
        return {
            'primary_emotion': primary_emotion,
            'sentiment_score': avg_sentiment,
            'frustration_level': frustration_level,
            'motivation_score': motivation_score,
            'confidence_level': confidence_level,
            'engagement_score': engagement_score,
            'emotional_stability': self._assess_emotional_stability(sentiment_scores),
            'intervention_recommended': frustration_level > 0.7 or motivation_score < 0.3,
            'intervention_type': self._recommend_intervention_type(frustration_level, motivation_score)
        }
    
    def _analyze_message_sentiment(self, message: str) -> float:
        """Simple sentiment analysis (can be enhanced with NLP models)"""
        positive_words = ['good', 'great', 'excellent', 'understand', 'clear', 'helpful', 'thanks']
        negative_words = ['bad', 'difficult', 'hard', 'confused', 'stuck', 'frustrated', 'help']
        neutral_words = ['ok', 'maybe', 'think', 'question', 'about']
        
        message_lower = message.lower()
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return 0.7 + (positive_count - negative_count) * 0.1
        elif negative_count > positive_count:
            return 0.3 - (negative_count - positive_count) * 0.1
        else:
            return 0.5
    
    def _detect_frustration_level(self, messages: List[str], performance_data: Dict[str, Any]) -> float:
        """Detect user frustration level"""
        frustration_indicators = 0
        
        # Message-based indicators
        for message in messages[-5:]:  # Recent messages
            message_lower = message.lower()
            if any(indicator in message_lower for indicator in 
                   ['frustrated', 'stuck', 'difficult', 'hard', 'confused', 'help']):
                frustration_indicators += 1
            if '!' in message and len(message) < 50:  # Short exclamatory messages
                frustration_indicators += 0.5
        
        # Performance-based indicators
        if performance_data.get('recent_mistakes', 0) > 3:
            frustration_indicators += 1
        if performance_data.get('time_on_problem', 0) > 10:  # minutes
            frustration_indicators += 1
        if performance_data.get('repeat_questions', 0) > 2:
            frustration_indicators += 1
        
        return min(frustration_indicators * 0.2, 1.0)
    
    def _assess_motivation(self, messages: List[str], performance_data: Dict[str, Any], 
                          history: List[Dict]) -> float:
        """Assess user motivation level"""
        motivation_score = 0.5  # baseline
        
        # Positive engagement indicators
        if len(messages) > 5:  # Active participation
            motivation_score += 0.2
        if any('thank' in msg.lower() for msg in messages[-3:]):
            motivation_score += 0.1
        if performance_data.get('session_length', 0) > 20:  # Extended engagement
            motivation_score += 0.2
        
        # Negative motivation indicators
        if len(messages) < 3 and performance_data.get('session_length', 0) < 5:
            motivation_score -= 0.3
        if any('give up' in msg.lower() or 'quit' in msg.lower() for msg in messages):
            motivation_score -= 0.4
        
        return max(0.0, min(motivation_score, 1.0))
    
    def _assess_confidence(self, messages: List[str], performance_data: Dict[str, Any]) -> float:
        """Assess user confidence level"""
        confidence_indicators = 0.5
        
        # High confidence indicators
        if performance_data.get('correct_answers', 0) > performance_data.get('incorrect_answers', 0):
            confidence_indicators += 0.3
        if any('understand' in msg.lower() or 'got it' in msg.lower() for msg in messages[-3:]):
            confidence_indicators += 0.2
        
        # Low confidence indicators
        if any('not sure' in msg.lower() or 'maybe' in msg.lower() for msg in messages[-3:]):
            confidence_indicators -= 0.2
        if performance_data.get('help_requests', 0) > 3:
            confidence_indicators -= 0.2
        
        return max(0.0, min(confidence_indicators, 1.0))
    
    def _calculate_engagement(self, history: List[Dict], performance_data: Dict[str, Any]) -> float:
        """Calculate engagement score"""
        if not history:
            return 0.5
        
        # Factors contributing to engagement
        interaction_frequency = len(history) / max(performance_data.get('session_length', 1), 1)
        response_consistency = 1.0 - (np.std([h.get('response_time', 5) for h in history[-10:]]) / 10)
        question_quality = np.mean([h.get('question_complexity', 0.5) for h in history[-5:]])
        
        engagement = (interaction_frequency * 0.4 + response_consistency * 0.3 + question_quality * 0.3)
        return max(0.0, min(engagement, 1.0))
    
    def _determine_primary_emotion(self, sentiment: float, frustration: float, 
                                  motivation: float, confidence: float, engagement: float) -> EmotionalState:
        """Determine primary emotional state from various indicators"""
        
        if frustration > 0.6:
            return EmotionalState.FRUSTRATED
        elif confidence > 0.7 and engagement > 0.6:
            return EmotionalState.CONFIDENT
        elif motivation > 0.7 and engagement > 0.6:
            return EmotionalState.MOTIVATED
        elif engagement < 0.3:
            return EmotionalState.BORED
        elif frustration > 0.4 and confidence < 0.4:
            return EmotionalState.CONFUSED
        elif motivation > 0.6:
            return EmotionalState.ENGAGED
        elif sentiment < 0.3:
            return EmotionalState.ANXIOUS
        else:
            return EmotionalState.SATISFIED
    
    def _assess_emotional_stability(self, sentiment_scores: List[float]) -> str:
        """Assess emotional stability over time"""
        if len(sentiment_scores) < 3:
            return 'insufficient_data'
        
        variance = np.var(sentiment_scores)
        if variance < 0.1:
            return 'very_stable'
        elif variance < 0.2:
            return 'stable'
        elif variance < 0.4:
            return 'somewhat_volatile'
        else:
            return 'highly_volatile'
    
    def _recommend_intervention_type(self, frustration: float, motivation: float) -> Optional[str]:
        """Recommend type of emotional intervention"""
        if frustration > 0.7:
            return 'encouragement_and_simplification'
        elif motivation < 0.3:
            return 'motivational_boost'
        elif frustration > 0.5 and motivation < 0.5:
            return 'break_recommendation'
        else:
            return None


class MultimodalContextEngine:
    """Manages multimodal learning context and content adaptation"""
    
    def determine_optimal_modalities(self, learning_context: LearningContext, 
                                   current_performance: Dict[str, Any]) -> Dict[str, float]:
        """Determine optimal learning modalities for current context"""
        
        base_preferences = self._get_base_modality_preferences(learning_context.preferred_modality)
        performance_adjustments = self._analyze_modality_performance(current_performance)
        cognitive_load_adjustments = self._adjust_for_cognitive_load(learning_context.cognitive_load)
        environmental_adjustments = self._adjust_for_environment(learning_context.device_type)
        
        # Combine all factors
        modality_scores = {}
        for modality in LearningModalityType:
            score = (
                base_preferences.get(modality.value, 0.25) * 0.4 +
                performance_adjustments.get(modality.value, 0.25) * 0.3 +
                cognitive_load_adjustments.get(modality.value, 0.25) * 0.2 +
                environmental_adjustments.get(modality.value, 0.25) * 0.1
            )
            modality_scores[modality.value] = score
        
        # Normalize scores
        total_score = sum(modality_scores.values())
        if total_score > 0:
            modality_scores = {k: v/total_score for k, v in modality_scores.items()}
        
        return modality_scores
    
    def generate_multimodal_content_strategy(self, topic: str, modality_weights: Dict[str, float],
                                           difficulty_level: float) -> Dict[str, Any]:
        """Generate content strategy based on optimal modalities"""
        
        content_strategy = {
            'primary_modality': max(modality_weights, key=modality_weights.get),
            'secondary_modalities': sorted(modality_weights.items(), key=lambda x: x[1], reverse=True)[1:3],
            'content_components': {}
        }
        
        # Generate content for each modality
        for modality, weight in modality_weights.items():
            if weight > 0.1:  # Only include modalities with significant weight
                content_strategy['content_components'][modality] = self._generate_modality_content(
                    modality, topic, difficulty_level, weight
                )
        
        return content_strategy
    
    def _get_base_modality_preferences(self, preferred_modality: LearningModalityType) -> Dict[str, float]:
        """Get base modality preferences"""
        preferences = {modality.value: 0.15 for modality in LearningModalityType}
        preferences[preferred_modality.value] = 0.4
        return preferences
    
    def _analyze_modality_performance(self, performance_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze historical performance by modality"""
        # This would analyze historical performance data by modality
        # For now, return balanced weights
        return {modality.value: 0.25 for modality in LearningModalityType}
    
    def _adjust_for_cognitive_load(self, cognitive_load: CognitiveLoadLevel) -> Dict[str, float]:
        """Adjust modality preferences based on cognitive load"""
        if cognitive_load == CognitiveLoadLevel.HIGH:
            # Prefer simpler modalities when cognitive load is high
            return {
                LearningModalityType.VISUAL.value: 0.4,
                LearningModalityType.AUDITORY.value: 0.3,
                LearningModalityType.READING_WRITING.value: 0.2,
                LearningModalityType.KINESTHETIC.value: 0.1
            }
        elif cognitive_load == CognitiveLoadLevel.LOW:
            # Can handle more complex multimodal content
            return {
                LearningModalityType.MULTIMODAL.value: 0.4,
                LearningModalityType.KINESTHETIC.value: 0.3,
                LearningModalityType.VISUAL.value: 0.2,
                LearningModalityType.AUDITORY.value: 0.1
            }
        else:
            # Balanced approach for moderate cognitive load
            return {modality.value: 0.25 for modality in LearningModalityType}
    
    def _adjust_for_environment(self, device_type: str) -> Dict[str, float]:
        """Adjust modality preferences based on device and environment"""
        if device_type == 'mobile':
            # Mobile devices prefer simpler, touch-based interactions
            return {
                LearningModalityType.KINESTHETIC.value: 0.4,
                LearningModalityType.VISUAL.value: 0.3,
                LearningModalityType.AUDITORY.value: 0.2,
                LearningModalityType.READING_WRITING.value: 0.1
            }
        elif device_type == 'desktop':
            # Desktop allows for rich multimodal experiences
            return {
                LearningModalityType.MULTIMODAL.value: 0.3,
                LearningModalityType.VISUAL.value: 0.3,
                LearningModalityType.READING_WRITING.value: 0.2,
                LearningModalityType.AUDITORY.value: 0.2
            }
        else:  # tablet
            # Tablets balance between mobile and desktop capabilities
            return {modality.value: 0.25 for modality in LearningModalityType}
    
    def _generate_modality_content(self, modality: str, topic: str, 
                                  difficulty: float, weight: float) -> Dict[str, Any]:
        """Generate content specifications for a specific modality"""
        
        content_specs = {
            'modality': modality,
            'weight': weight,
            'difficulty_level': difficulty,
            'components': []
        }
        
        if modality == LearningModalityType.VISUAL.value:
            content_specs['components'] = [
                {'type': 'diagram', 'complexity': 'moderate' if difficulty > 0.5 else 'simple'},
                {'type': 'infographic', 'detail_level': 'high' if difficulty > 0.7 else 'medium'},
                {'type': 'visual_examples', 'count': int(3 * weight)}
            ]
        elif modality == LearningModalityType.AUDITORY.value:
            content_specs['components'] = [
                {'type': 'explanation_audio', 'pace': 'slow' if difficulty > 0.6 else 'normal'},
                {'type': 'discussion_prompts', 'count': int(2 * weight)},
                {'type': 'verbal_examples', 'count': int(3 * weight)}
            ]
        elif modality == LearningModalityType.KINESTHETIC.value:
            content_specs['components'] = [
                {'type': 'interactive_simulation', 'complexity': 'high' if difficulty > 0.6 else 'medium'},
                {'type': 'hands_on_exercises', 'count': int(4 * weight)},
                {'type': 'drag_drop_activities', 'count': int(2 * weight)}
            ]
        elif modality == LearningModalityType.READING_WRITING.value:
            content_specs['components'] = [
                {'type': 'detailed_text', 'length': 'long' if difficulty > 0.6 else 'medium'},
                {'type': 'writing_exercises', 'count': int(2 * weight)},
                {'type': 'note_taking_guides', 'structure': 'detailed' if difficulty > 0.5 else 'simple'}
            ]
        else:  # MULTIMODAL
            content_specs['components'] = [
                {'type': 'integrated_multimedia', 'richness': 'high'},
                {'type': 'cross_modal_exercises', 'count': int(3 * weight)},
                {'type': 'adaptive_content_mix', 'dynamic': True}
            ]
        
        return content_specs