"""
Enhanced Personalization Engine with Advanced Context Integration
Real-time learning effectiveness feedback loops and adaptive optimization
"""
import json
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone

# Import new context components
from .advanced_context_engine import (
    LearningContext, LearningModalityType, EmotionalState, CognitiveLoadLevel
)
from .dynamic_context_engine import DynamicContextEngine, PersistentContextManager
from .contextual_prompt_engine import ContextualPromptEngine

# Import existing services
from .memory_service import memory_service
from .student_analyzer import student_analyzer
from ..core.base_service import LLMBaseService
from apps.authentication.models import User
from apps.learning_plans.models import StudySession
from apps.learning_plans.student_notes_models import StudentLearningPattern


class LearningEffectivenessTracker:
    """Tracks and analyzes learning effectiveness in real-time"""
    
    def __init__(self):
        self.effectiveness_cache_prefix = "learning_effectiveness:"
        self.feedback_cache_prefix = "effectiveness_feedback:"
        
    def track_interaction_effectiveness(self, user_id: str, session_id: str, 
                                      interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track effectiveness of a single interaction"""
        
        # Calculate immediate effectiveness indicators
        effectiveness_metrics = {
            'response_quality': self._assess_response_quality(interaction_data),
            'engagement_indicator': self._calculate_engagement_indicator(interaction_data),
            'comprehension_score': self._assess_comprehension(interaction_data),
            'emotional_response': self._analyze_emotional_response(interaction_data),
            'learning_progress': self._measure_learning_progress(interaction_data),
            'time_efficiency': self._calculate_time_efficiency(interaction_data)
        }
        
        # Calculate overall effectiveness score
        overall_score = self._calculate_overall_effectiveness(effectiveness_metrics)
        
        # Store effectiveness data
        self._store_effectiveness_data(user_id, session_id, {
            'timestamp': datetime.now().isoformat(),
            'metrics': effectiveness_metrics,
            'overall_score': overall_score,
            'interaction_data': interaction_data
        })
        
        return {
            'effectiveness_score': overall_score,
            'metrics': effectiveness_metrics,
            'recommendations': self._generate_recommendations(effectiveness_metrics)
        }
    
    def analyze_session_effectiveness(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Analyze overall session effectiveness"""
        
        effectiveness_key = f"{self.effectiveness_cache_prefix}{user_id}:{session_id}"
        session_data = cache.get(effectiveness_key, [])
        
        if not session_data:
            return {'status': 'no_data'}
        
        # Calculate session-level metrics
        session_metrics = {
            'average_effectiveness': np.mean([d['overall_score'] for d in session_data]),
            'effectiveness_trend': self._calculate_trend([d['overall_score'] for d in session_data]),
            'peak_performance': max(d['overall_score'] for d in session_data),
            'consistency_score': 1.0 - np.std([d['overall_score'] for d in session_data]),
            'improvement_rate': self._calculate_improvement_rate(session_data),
            'engagement_pattern': self._analyze_engagement_pattern(session_data),
            'learning_velocity': self._calculate_learning_velocity(session_data)
        }
        
        # Generate session insights
        insights = self._generate_session_insights(session_metrics, session_data)
        
        return {
            'session_metrics': session_metrics,
            'insights': insights,
            'recommendations': self._generate_session_recommendations(session_metrics)
        }
    
    def get_effectiveness_trends(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Analyze effectiveness trends over time"""
        
        # Get historical effectiveness data
        historical_data = self._get_historical_effectiveness(user_id, days)
        
        if not historical_data:
            return {'status': 'insufficient_data'}
        
        # Calculate trends
        trends = {
            'overall_trend': self._calculate_long_term_trend(historical_data),
            'best_performance_periods': self._identify_peak_periods(historical_data),
            'learning_patterns': self._identify_learning_patterns(historical_data),
            'modality_effectiveness': self._analyze_modality_effectiveness(historical_data),
            'emotional_state_impact': self._analyze_emotional_impact(historical_data),
            'optimal_conditions': self._identify_optimal_conditions(historical_data)
        }
        
        return trends
    
    def _assess_response_quality(self, interaction_data: Dict[str, Any]) -> float:
        """Assess the quality of student's response"""
        
        student_response = interaction_data.get('student_response', '')
        expected_complexity = interaction_data.get('question_complexity', 0.5)
        
        # Simple heuristic assessment (can be enhanced with NLP)
        quality_indicators = []
        
        # Length appropriateness
        response_length = len(student_response.split())
        if expected_complexity > 0.7 and response_length > 20:
            quality_indicators.append(0.3)
        elif expected_complexity < 0.3 and 5 <= response_length <= 15:
            quality_indicators.append(0.3)
        elif 10 <= response_length <= 25:
            quality_indicators.append(0.2)
        
        # Keyword relevance (simplified)
        topic_keywords = interaction_data.get('topic_keywords', [])
        keyword_matches = sum(1 for keyword in topic_keywords 
                            if keyword.lower() in student_response.lower())
        if keyword_matches > 0:
            quality_indicators.append(min(keyword_matches * 0.1, 0.3))
        
        # Question indicators
        if '?' in student_response and expected_complexity > 0.5:
            quality_indicators.append(0.2)  # Good critical thinking
        
        return min(sum(quality_indicators), 1.0) if quality_indicators else 0.3
    
    def _calculate_engagement_indicator(self, interaction_data: Dict[str, Any]) -> float:
        """Calculate engagement indicator from interaction"""
        
        engagement_factors = []
        
        # Response time analysis
        response_time = interaction_data.get('response_time', 10)
        optimal_time = interaction_data.get('optimal_response_time', 8)
        
        if 0.5 * optimal_time <= response_time <= 2 * optimal_time:
            engagement_factors.append(0.3)  # Appropriate thinking time
        elif response_time > 3 * optimal_time:
            engagement_factors.append(-0.2)  # Possible disengagement
        
        # Interaction frequency
        recent_interactions = interaction_data.get('recent_interaction_count', 1)
        if recent_interactions > 3:
            engagement_factors.append(0.2)
        
        # Question quality
        if interaction_data.get('asks_questions', False):
            engagement_factors.append(0.3)
        
        # Follow-up engagement
        if interaction_data.get('requests_clarification', False):
            engagement_factors.append(0.2)
        
        return max(0.0, min(sum(engagement_factors) + 0.5, 1.0))  # Baseline 0.5
    
    def _assess_comprehension(self, interaction_data: Dict[str, Any]) -> float:
        """Assess student comprehension from response"""
        
        comprehension_indicators = []
        
        # Correct concept usage
        if interaction_data.get('uses_correct_terminology', False):
            comprehension_indicators.append(0.3)
        
        # Logical reasoning
        if interaction_data.get('shows_logical_reasoning', False):
            comprehension_indicators.append(0.3)
        
        # Application of concepts
        if interaction_data.get('applies_concepts', False):
            comprehension_indicators.append(0.2)
        
        # Asks relevant questions
        if interaction_data.get('asks_relevant_questions', False):
            comprehension_indicators.append(0.2)
        
        # No major misconceptions
        if not interaction_data.get('shows_misconceptions', False):
            comprehension_indicators.append(0.1)
        
        return min(sum(comprehension_indicators), 1.0) if comprehension_indicators else 0.3
    
    def _analyze_emotional_response(self, interaction_data: Dict[str, Any]) -> float:
        """Analyze emotional response to learning interaction"""
        
        emotional_indicators = interaction_data.get('emotional_indicators', {})
        
        positive_emotions = emotional_indicators.get('positive', 0)
        negative_emotions = emotional_indicators.get('negative', 0)
        neutral_emotions = emotional_indicators.get('neutral', 1)
        
        total_emotions = positive_emotions + negative_emotions + neutral_emotions
        
        if total_emotions == 0:
            return 0.5  # Neutral baseline
        
        # Weight positive emotions more heavily
        emotional_score = (positive_emotions * 1.0 + neutral_emotions * 0.5) / total_emotions
        
        return max(0.0, min(emotional_score, 1.0))
    
    def _measure_learning_progress(self, interaction_data: Dict[str, Any]) -> float:
        """Measure learning progress in this interaction"""
        
        progress_indicators = []
        
        # Concept mastery progression
        if interaction_data.get('concept_mastered', False):
            progress_indicators.append(0.4)
        elif interaction_data.get('concept_improved', False):
            progress_indicators.append(0.2)
        
        # Skill development
        if interaction_data.get('skill_demonstrated', False):
            progress_indicators.append(0.2)
        
        # Knowledge connection
        if interaction_data.get('connects_to_prior_knowledge', False):
            progress_indicators.append(0.2)
        
        # Problem-solving improvement
        if interaction_data.get('problem_solving_improved', False):
            progress_indicators.append(0.2)
        
        return min(sum(progress_indicators), 1.0) if progress_indicators else 0.3
    
    def _calculate_time_efficiency(self, interaction_data: Dict[str, Any]) -> float:
        """Calculate time efficiency of learning interaction"""
        
        actual_time = interaction_data.get('interaction_duration', 60)  # seconds
        expected_time = interaction_data.get('expected_duration', 60)
        learning_achieved = interaction_data.get('learning_progress', 0.3)
        
        # Efficiency = Learning achieved per unit time
        if actual_time <= 0:
            return 0.0
        
        time_ratio = expected_time / actual_time if actual_time > 0 else 0
        efficiency = learning_achieved * min(time_ratio, 2.0)  # Cap at 2x expected efficiency
        
        return max(0.0, min(efficiency, 1.0))
    
    def _calculate_overall_effectiveness(self, metrics: Dict[str, float]) -> float:
        """Calculate overall effectiveness score"""
        
        # Weighted combination of metrics
        weights = {
            'response_quality': 0.2,
            'engagement_indicator': 0.15,
            'comprehension_score': 0.25,
            'emotional_response': 0.15,
            'learning_progress': 0.15,
            'time_efficiency': 0.1
        }
        
        weighted_score = sum(metrics[metric] * weights[metric] 
                           for metric in weights if metric in metrics)
        
        return max(0.0, min(weighted_score, 1.0))
    
    def _store_effectiveness_data(self, user_id: str, session_id: str, effectiveness_data: Dict[str, Any]):
        """Store effectiveness data for analysis"""
        
        effectiveness_key = f"{self.effectiveness_cache_prefix}{user_id}:{session_id}"
        session_data = cache.get(effectiveness_key, [])
        
        session_data.append(effectiveness_data)
        
        # Keep last 100 interactions per session
        if len(session_data) > 100:
            session_data = session_data[-100:]
        
        cache.set(effectiveness_key, session_data, timeout=86400)  # 24 hours
        
        # Also store in historical data
        historical_key = f"{self.effectiveness_cache_prefix}{user_id}:historical"
        historical_data = cache.get(historical_key, [])
        historical_data.append({
            'session_id': session_id,
            'timestamp': effectiveness_data['timestamp'],
            'overall_score': effectiveness_data['overall_score'],
            'metrics': effectiveness_data['metrics']
        })
        
        # Keep last 1000 historical records
        if len(historical_data) > 1000:
            historical_data = historical_data[-1000:]
        
        cache.set(historical_key, historical_data, timeout=2592000)  # 30 days
    
    def _generate_recommendations(self, metrics: Dict[str, float]) -> List[str]:
        """Generate recommendations based on effectiveness metrics"""
        
        recommendations = []
        
        # Response quality recommendations
        if metrics['response_quality'] < 0.5:
            recommendations.append("Encourage more detailed responses and use of subject terminology")
        
        # Engagement recommendations
        if metrics['engagement_indicator'] < 0.4:
            recommendations.append("Try more interactive content or check if topic interests the student")
        
        # Comprehension recommendations
        if metrics['comprehension_score'] < 0.5:
            recommendations.append("Provide additional examples and check understanding more frequently")
        
        # Emotional response recommendations
        if metrics['emotional_response'] < 0.4:
            recommendations.append("Focus on building confidence and reducing learning anxiety")
        
        # Learning progress recommendations
        if metrics['learning_progress'] < 0.3:
            recommendations.append("Break down concepts into smaller steps and provide more scaffolding")
        
        # Time efficiency recommendations
        if metrics['time_efficiency'] < 0.4:
            recommendations.append("Adjust pacing and provide more focused content")
        
        return recommendations
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from list of values"""
        if len(values) < 3:
            return 'insufficient_data'
        
        # Simple linear trend
        x = np.arange(len(values))
        slope = np.corrcoef(x, values)[0, 1] if np.std(values) > 0 else 0
        
        if slope > 0.1:
            return 'improving'
        elif slope < -0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_improvement_rate(self, session_data: List[Dict]) -> float:
        """Calculate rate of improvement during session"""
        if len(session_data) < 2:
            return 0.0
        
        scores = [d['overall_score'] for d in session_data]
        first_half_avg = np.mean(scores[:len(scores)//2])
        second_half_avg = np.mean(scores[len(scores)//2:])
        
        return second_half_avg - first_half_avg
    
    def _analyze_engagement_pattern(self, session_data: List[Dict]) -> Dict[str, Any]:
        """Analyze engagement patterns throughout session"""
        engagement_scores = [d['metrics']['engagement_indicator'] for d in session_data]
        
        return {
            'average_engagement': np.mean(engagement_scores),
            'engagement_stability': 1.0 - np.std(engagement_scores),
            'peak_engagement': max(engagement_scores),
            'engagement_trend': self._calculate_trend(engagement_scores)
        }
    
    def _calculate_learning_velocity(self, session_data: List[Dict]) -> float:
        """Calculate how quickly learning is occurring"""
        progress_scores = [d['metrics']['learning_progress'] for d in session_data]
        time_points = [i for i in range(len(progress_scores))]
        
        if len(progress_scores) < 2:
            return 0.0
        
        # Calculate rate of learning progress
        velocity = (progress_scores[-1] - progress_scores[0]) / len(progress_scores)
        return max(0.0, velocity)


class RealTimeFeedbackProcessor:
    """Processes real-time feedback to improve learning effectiveness"""
    
    def __init__(self):
        self.feedback_weights = {
            'explicit_feedback': 1.0,  # Direct user feedback
            'behavioral_feedback': 0.7,  # Inferred from behavior
            'performance_feedback': 0.8,  # Based on assessment results
            'engagement_feedback': 0.6   # Based on engagement metrics
        }
        
    def process_feedback(self, user_id: str, session_id: str, 
                        feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process various types of feedback to adjust learning approach"""
        
        # Categorize feedback
        feedback_categories = self._categorize_feedback(feedback_data)
        
        # Calculate weighted feedback score
        overall_feedback_score = self._calculate_weighted_feedback(feedback_categories)
        
        # Generate adaptive adjustments
        adaptations = self._generate_adaptive_adjustments(feedback_categories, overall_feedback_score)
        
        # Update user learning model
        model_updates = self._update_learning_model(user_id, adaptations)
        
        return {
            'feedback_score': overall_feedback_score,
            'adaptations': adaptations,
            'model_updates': model_updates,
            'next_interaction_adjustments': self._get_immediate_adjustments(adaptations)
        }
    
    def _categorize_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, List]:
        """Categorize different types of feedback"""
        
        categories = {
            'explicit_feedback': [],
            'behavioral_feedback': [],
            'performance_feedback': [],
            'engagement_feedback': []
        }
        
        # Explicit feedback (ratings, comments)
        if 'user_rating' in feedback_data:
            categories['explicit_feedback'].append({
                'type': 'rating',
                'value': feedback_data['user_rating'],
                'weight': 1.0
            })
        
        if 'user_comment' in feedback_data:
            categories['explicit_feedback'].append({
                'type': 'comment',
                'sentiment': self._analyze_comment_sentiment(feedback_data['user_comment']),
                'weight': 0.8
            })
        
        # Behavioral feedback
        if 'response_time' in feedback_data:
            categories['behavioral_feedback'].append({
                'type': 'response_time',
                'value': self._analyze_response_time(feedback_data['response_time']),
                'weight': 0.6
            })
        
        if 'navigation_pattern' in feedback_data:
            categories['behavioral_feedback'].append({
                'type': 'navigation',
                'pattern': feedback_data['navigation_pattern'],
                'weight': 0.5
            })
        
        # Performance feedback
        if 'quiz_score' in feedback_data:
            categories['performance_feedback'].append({
                'type': 'assessment',
                'score': feedback_data['quiz_score'],
                'weight': 0.9
            })
        
        if 'concept_mastery' in feedback_data:
            categories['performance_feedback'].append({
                'type': 'mastery',
                'level': feedback_data['concept_mastery'],
                'weight': 0.8
            })
        
        # Engagement feedback
        if 'session_duration' in feedback_data:
            categories['engagement_feedback'].append({
                'type': 'duration',
                'value': self._analyze_session_duration(feedback_data['session_duration']),
                'weight': 0.6
            })
        
        if 'interaction_frequency' in feedback_data:
            categories['engagement_feedback'].append({
                'type': 'frequency',
                'value': feedback_data['interaction_frequency'],
                'weight': 0.5
            })
        
        return categories
    
    def _calculate_weighted_feedback(self, categories: Dict[str, List]) -> float:
        """Calculate overall weighted feedback score"""
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for category, feedback_items in categories.items():
            category_weight = self.feedback_weights[category]
            
            if feedback_items:
                category_score = np.mean([item.get('value', item.get('score', 0.5)) * item['weight'] 
                                        for item in feedback_items])
                total_weighted_score += category_score * category_weight
                total_weight += category_weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.5
    
    def _generate_adaptive_adjustments(self, feedback_categories: Dict[str, List], 
                                     overall_score: float) -> Dict[str, Any]:
        """Generate adaptive adjustments based on feedback"""
        
        adjustments = {
            'difficulty_adjustment': 0.0,
            'pace_adjustment': 0.0,
            'modality_preference_shift': {},
            'emotional_support_level': 0.0,
            'content_presentation_changes': [],
            'interaction_style_changes': []
        }
        
        # Difficulty adjustments
        performance_feedback = feedback_categories.get('performance_feedback', [])
        if performance_feedback:
            avg_performance = np.mean([item.get('score', item.get('level', 0.5)) 
                                     for item in performance_feedback])
            if avg_performance > 0.8:
                adjustments['difficulty_adjustment'] = 0.1  # Increase difficulty
            elif avg_performance < 0.4:
                adjustments['difficulty_adjustment'] = -0.2  # Decrease difficulty
        
        # Pace adjustments
        behavioral_feedback = feedback_categories.get('behavioral_feedback', [])
        for feedback_item in behavioral_feedback:
            if feedback_item['type'] == 'response_time':
                if feedback_item['value'] < 0.3:  # Very slow responses
                    adjustments['pace_adjustment'] = -0.1  # Slow down
                elif feedback_item['value'] > 0.8:  # Very fast responses
                    adjustments['pace_adjustment'] = 0.1  # Speed up
        
        # Emotional support adjustments
        explicit_feedback = feedback_categories.get('explicit_feedback', [])
        for feedback_item in explicit_feedback:
            if feedback_item['type'] == 'comment':
                sentiment = feedback_item.get('sentiment', 0.5)
                if sentiment < 0.3:
                    adjustments['emotional_support_level'] = 0.3  # Increase support
        
        # Engagement-based adjustments
        engagement_feedback = feedback_categories.get('engagement_feedback', [])
        low_engagement_count = sum(1 for item in engagement_feedback 
                                 if item.get('value', 0.5) < 0.4)
        if low_engagement_count >= 2:
            adjustments['content_presentation_changes'].append('increase_interactivity')
            adjustments['interaction_style_changes'].append('more_engaging_questions')
        
        return adjustments
    
    def _update_learning_model(self, user_id: str, adaptations: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's learning model based on adaptations"""
        
        # Get current user profile
        try:
            user_profile = student_analyzer.get_student_profile(user_id)
            current_preferences = user_profile.get('profile', {}).get('settings', {})
            
            model_updates = {}
            
            # Update difficulty preference
            if adaptations['difficulty_adjustment'] != 0:
                current_difficulty = current_preferences.get('preferred_difficulty', 0.5)
                new_difficulty = max(0.1, min(0.9, current_difficulty + adaptations['difficulty_adjustment']))
                model_updates['preferred_difficulty'] = new_difficulty
            
            # Update pace preference
            if adaptations['pace_adjustment'] != 0:
                pace_mapping = {'slow': 0.3, 'medium': 0.5, 'fast': 0.7}
                current_pace_val = pace_mapping.get(current_preferences.get('preferred_pace', 'medium'), 0.5)
                new_pace_val = max(0.2, min(0.8, current_pace_val + adaptations['pace_adjustment']))
                
                if new_pace_val < 0.35:
                    model_updates['preferred_pace'] = 'slow'
                elif new_pace_val > 0.65:
                    model_updates['preferred_pace'] = 'fast'
                else:
                    model_updates['preferred_pace'] = 'medium'
            
            # Update support level
            if adaptations['emotional_support_level'] != 0:
                current_support = current_preferences.get('support_level', 0.5)
                new_support = max(0.1, min(1.0, current_support + adaptations['emotional_support_level']))
                model_updates['support_level'] = new_support
            
            # Cache the updates
            cache_key = f"learning_model_updates:{user_id}"
            cache.set(cache_key, model_updates, timeout=86400)  # 24 hours
            
            return model_updates
            
        except Exception as e:
            print(f"Error updating learning model for user {user_id}: {e}")
            return {}
    
    def _get_immediate_adjustments(self, adaptations: Dict[str, Any]) -> Dict[str, Any]:
        """Get adjustments to apply immediately to the next interaction"""
        
        immediate_adjustments = {}
        
        # Immediate difficulty adjustment
        if abs(adaptations['difficulty_adjustment']) > 0.1:
            immediate_adjustments['adjust_difficulty'] = adaptations['difficulty_adjustment']
        
        # Immediate pace adjustment
        if abs(adaptations['pace_adjustment']) > 0.05:
            immediate_adjustments['adjust_pace'] = adaptations['pace_adjustment']
        
        # Immediate emotional support
        if adaptations['emotional_support_level'] > 0.1:
            immediate_adjustments['increase_support'] = True
        
        # Content presentation changes
        if adaptations['content_presentation_changes']:
            immediate_adjustments['content_changes'] = adaptations['content_presentation_changes']
        
        # Interaction style changes
        if adaptations['interaction_style_changes']:
            immediate_adjustments['interaction_changes'] = adaptations['interaction_style_changes']
        
        return immediate_adjustments


class EnhancedPersonalizationEngine(LLMBaseService):
    """Enhanced personalization engine with advanced context integration"""
    
    def __init__(self):
        super().__init__()
        self.context_engine = DynamicContextEngine()
        self.prompt_engine = ContextualPromptEngine()
        self.effectiveness_tracker = LearningEffectivenessTracker()
        self.feedback_processor = RealTimeFeedbackProcessor()
        self.persistent_context = PersistentContextManager()
        
    async def create_ultra_personalized_response(self, user_id: str, session_id: str, 
                                               user_message: str, response_time: float,
                                               additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an ultra-personalized response using advanced context engineering"""
        
        try:
            # 1. Analyze comprehensive learning context
            learning_context = await self.context_engine.analyze_comprehensive_context(
                user_id, session_id, user_message, response_time, additional_context
            )
            
            # 2. Generate contextual prompt
            personalized_prompt = await self.prompt_engine.generate_personalized_prompt(
                user_id, session_id, user_message, response_time, 'explain', additional_context
            )
            
            # 3. Generate AI response using personalized prompt
            ai_response = await self._generate_contextual_response(personalized_prompt, learning_context)
            
            # 4. Track interaction effectiveness
            interaction_data = self._build_interaction_data(
                user_message, ai_response, learning_context, additional_context
            )
            
            effectiveness_metrics = self.effectiveness_tracker.track_interaction_effectiveness(
                user_id, session_id, interaction_data
            )
            
            # 5. Process any feedback for real-time adaptation
            if additional_context and 'feedback' in additional_context:
                feedback_results = self.feedback_processor.process_feedback(
                    user_id, session_id, additional_context['feedback']
                )
            else:
                feedback_results = None
            
            # 6. Generate adaptive recommendations for next interaction
            next_interaction_guidance = self._generate_next_interaction_guidance(
                learning_context, effectiveness_metrics, feedback_results
            )
            
            return {
                'ai_response': ai_response,
                'learning_context': learning_context,
                'effectiveness_metrics': effectiveness_metrics,
                'personalization_data': {
                    'emotional_state': learning_context.emotional_state.value,
                    'cognitive_load': learning_context.cognitive_load.value,
                    'optimal_modality': learning_context.preferred_modality.value,
                    'confidence_level': learning_context.confidence_level,
                    'engagement_score': learning_context.engagement_score
                },
                'next_interaction_guidance': next_interaction_guidance,
                'feedback_results': feedback_results,
                'success': True
            }
            
        except Exception as e:
            print(f"Error in ultra-personalized response generation: {e}")
            return {
                'error': str(e),
                'success': False,
                'fallback_response': await self._generate_fallback_response(user_message)
            }
    
    async def _generate_contextual_response(self, personalized_prompt: str, 
                                          context: LearningContext) -> str:
        """Generate AI response using contextual prompt"""
        
        try:
            if self.langchain_llm:
                # Use LangChain for more sophisticated processing
                response = await self._execute_langchain_response(personalized_prompt, context)
            else:
                # Use simple OpenAI client
                response = self.simple_chat(personalized_prompt)
            
            # Post-process response based on context
            processed_response = self._post_process_response(response, context)
            
            return processed_response
            
        except Exception as e:
            print(f"Error generating contextual response: {e}")
            return f"I understand you're asking about {context.current_topic}. Let me help you with that..."
    
    async def _execute_langchain_response(self, prompt: str, context: LearningContext) -> str:
        """Execute response generation using LangChain with context awareness"""
        
        # This would implement more sophisticated LangChain chains
        # For now, using simple approach
        return self.simple_chat(prompt)
    
    def _post_process_response(self, response: str, context: LearningContext) -> str:
        """Post-process AI response based on learning context"""
        
        # Adjust response based on cognitive load
        if context.cognitive_load == CognitiveLoadLevel.HIGH:
            response = self._simplify_response(response)
        elif context.cognitive_load == CognitiveLoadLevel.OVERLOAD:
            response = self._emergency_simplify_response(response)
        
        # Adjust for emotional state
        if context.emotional_state == EmotionalState.FRUSTRATED:
            response = self._add_encouragement(response)
        elif context.emotional_state == EmotionalState.CONFUSED:
            response = self._add_clarification_offers(response)
        
        # Adjust for learning modality
        response = self._adapt_for_modality(response, context.preferred_modality)
        
        return response
    
    def _build_interaction_data(self, user_message: str, ai_response: str, 
                              context: LearningContext, 
                              additional_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build interaction data for effectiveness tracking"""
        
        return {
            'user_message': user_message,
            'ai_response': ai_response,
            'response_time': context.response_time,
            'question_complexity': self._assess_question_complexity(user_message),
            'topic_keywords': self._extract_topic_keywords(user_message, context.current_topic),
            'emotional_indicators': {
                'positive': 1 if context.emotional_state in [EmotionalState.MOTIVATED, EmotionalState.CONFIDENT] else 0,
                'negative': 1 if context.emotional_state in [EmotionalState.FRUSTRATED, EmotionalState.ANXIOUS] else 0,
                'neutral': 1 if context.emotional_state in [EmotionalState.SATISFIED, EmotionalState.ENGAGED] else 0
            },
            'cognitive_load_level': context.cognitive_load.value,
            'engagement_level': context.engagement_score,
            'confidence_level': context.confidence_level,
            'interaction_duration': additional_context.get('interaction_duration', 60) if additional_context else 60,
            'expected_duration': 60,  # Default expected duration
            'learning_progress': self._estimate_learning_progress(user_message, ai_response, context)
        }
    
    def _generate_next_interaction_guidance(self, context: LearningContext,
                                          effectiveness: Dict[str, Any],
                                          feedback: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate guidance for the next interaction"""
        
        guidance = {
            'suggested_difficulty_adjustment': 0.0,
            'emotional_support_needed': False,
            'modality_recommendations': [],
            'pacing_adjustments': [],
            'content_focus_areas': [],
            'engagement_strategies': []
        }
        
        # Difficulty adjustments based on effectiveness
        if effectiveness['effectiveness_score'] < 0.4:
            guidance['suggested_difficulty_adjustment'] = -0.2
        elif effectiveness['effectiveness_score'] > 0.8:
            guidance['suggested_difficulty_adjustment'] = 0.1
        
        # Emotional support assessment
        if context.emotional_state in [EmotionalState.FRUSTRATED, EmotionalState.ANXIOUS] or \
           context.confidence_level < 0.3:
            guidance['emotional_support_needed'] = True
        
        # Modality recommendations
        if effectiveness['effectiveness_score'] < 0.5:
            guidance['modality_recommendations'].append('try_alternative_modality')
        
        # Pacing adjustments
        if context.cognitive_load == CognitiveLoadLevel.HIGH:
            guidance['pacing_adjustments'].append('slow_down')
        elif effectiveness['effectiveness_score'] > 0.8:
            guidance['pacing_adjustments'].append('can_increase_pace')
        
        # Content focus
        if context.concepts_struggling:
            guidance['content_focus_areas'] = context.concepts_struggling[:3]
        
        # Engagement strategies
        if context.engagement_score < 0.4:
            guidance['engagement_strategies'] = ['increase_interactivity', 'add_real_world_examples']
        
        return guidance
    
    async def _generate_fallback_response(self, user_message: str) -> str:
        """Generate fallback response when personalization fails"""
        return f"I understand you're asking about this topic. Let me help you step by step..."
    
    # Helper methods for response processing
    def _simplify_response(self, response: str) -> str:
        """Simplify response for high cognitive load"""
        # Simple sentence splitting and shortening
        sentences = response.split('. ')
        if len(sentences) > 3:
            return '. '.join(sentences[:3]) + "."
        return response
    
    def _emergency_simplify_response(self, response: str) -> str:
        """Emergency simplification for cognitive overload"""
        sentences = response.split('. ')
        if sentences:
            return sentences[0] + ". Let's focus on this one idea first."
        return response
    
    def _add_encouragement(self, response: str) -> str:
        """Add encouraging elements to response"""
        encouragement_phrases = [
            "You're doing great! ",
            "Don't worry, this is challenging but you can do it! ",
            "I believe in you! "
        ]
        import random
        return random.choice(encouragement_phrases) + response
    
    def _add_clarification_offers(self, response: str) -> str:
        """Add clarification offers to response"""
        return response + "\n\nDoes this make sense so far? Feel free to ask if you need me to explain anything differently!"
    
    def _adapt_for_modality(self, response: str, modality: LearningModalityType) -> str:
        """Adapt response for specific learning modality"""
        
        if modality == LearningModalityType.VISUAL:
            return response + "\n\n(Try to visualize this concept as we go through it)"
        elif modality == LearningModalityType.AUDITORY:
            return response + "\n\n(Feel free to read this aloud or talk through the steps)"
        elif modality == LearningModalityType.KINESTHETIC:
            return response + "\n\n(Try working through this hands-on if possible)"
        
        return response
    
    def _assess_question_complexity(self, message: str) -> float:
        """Assess complexity of user question"""
        # Simple heuristic - can be enhanced with NLP
        complexity_keywords = ['why', 'how', 'analyze', 'compare', 'evaluate', 'synthesize']
        complexity_score = sum(1 for keyword in complexity_keywords if keyword.lower() in message.lower())
        return min(complexity_score * 0.2, 1.0)
    
    def _extract_topic_keywords(self, message: str, topic: str) -> List[str]:
        """Extract relevant topic keywords from message"""
        # Simple keyword extraction
        words = message.lower().split()
        topic_words = topic.lower().split()
        return [word for word in words if word in topic_words or len(word) > 6]
    
    def _estimate_learning_progress(self, user_message: str, ai_response: str, 
                                  context: LearningContext) -> float:
        """Estimate learning progress from interaction"""
        # Simple heuristic based on context
        progress_factors = []
        
        if context.current_performance > 0.6:
            progress_factors.append(0.3)
        if context.engagement_score > 0.6:
            progress_factors.append(0.2)
        if '?' in user_message:  # Student asking questions
            progress_factors.append(0.2)
        if len(user_message.split()) > 10:  # Detailed response
            progress_factors.append(0.1)
        
        return min(sum(progress_factors), 1.0) if progress_factors else 0.3