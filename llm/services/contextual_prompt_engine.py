"""
Contextual Prompt Engineering System
Advanced prompt generation with dynamic context integration
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .advanced_context_engine import (
    LearningContext, 
    LearningModalityType, 
    EmotionalState, 
    CognitiveLoadLevel
)
from .dynamic_context_engine import DynamicContextEngine


class ContextualPromptTemplate:
    """Template system for context-aware prompts"""
    
    def __init__(self, template_name: str, base_template: str, 
                 context_variables: List[str], priority_level: int = 5):
        self.template_name = template_name
        self.base_template = base_template
        self.context_variables = context_variables
        self.priority_level = priority_level
        self.usage_count = 0
        self.effectiveness_score = 0.5  # Will be updated based on user feedback
    
    def render(self, context_data: Dict[str, Any]) -> str:
        """Render template with context data"""
        try:
            # Replace context variables in template
            rendered_template = self.base_template
            
            for variable in self.context_variables:
                placeholder = f"{{{variable}}}"
                value = context_data.get(variable, "")
                rendered_template = rendered_template.replace(placeholder, str(value))
            
            self.usage_count += 1
            return rendered_template
            
        except Exception as e:
            print(f"Error rendering template {self.template_name}: {e}")
            return self.base_template


class AdaptivePromptGenerator:
    """Generates adaptive prompts based on learning context"""
    
    def __init__(self):
        self.prompt_templates = self._initialize_prompt_templates()
        self.context_modifiers = self._initialize_context_modifiers()
        self.emotional_adaptations = self._initialize_emotional_adaptations()
        self.cognitive_load_adjustments = self._initialize_cognitive_adjustments()
        
    def generate_contextual_prompt(self, base_intent: str, learning_context: LearningContext,
                                 user_query: str, conversation_history: List[Dict]) -> str:
        """Generate a contextually adapted prompt"""
        
        # 1. Select appropriate base template
        base_template = self._select_base_template(base_intent, learning_context)
        
        # 2. Build context enrichment data
        context_data = self._build_context_data(learning_context, user_query, conversation_history)
        
        # 3. Apply emotional adaptations
        emotional_adaptations = self._get_emotional_adaptations(learning_context.emotional_state)
        
        # 4. Apply cognitive load adjustments
        cognitive_adjustments = self._get_cognitive_adjustments(learning_context.cognitive_load)
        
        # 5. Apply learning style modifications
        modality_mods = self._get_modality_modifications(learning_context.preferred_modality)
        
        # 6. Render final prompt
        final_prompt = self._render_adaptive_prompt(
            base_template, context_data, emotional_adaptations, 
            cognitive_adjustments, modality_mods
        )
        
        return final_prompt
    
    def _initialize_prompt_templates(self) -> Dict[str, ContextualPromptTemplate]:
        """Initialize library of contextual prompt templates"""
        templates = {}
        
        # Explanation Templates
        templates['explanation_basic'] = ContextualPromptTemplate(
            'explanation_basic',
            """You are an AI tutor helping {user_name} learn {current_topic}. 
            Based on their {learning_style} learning preference and {confidence_level} confidence level,
            provide a clear explanation of {user_query}.
            
            Student Context:
            - Current performance: {current_performance}
            - Learning pace: {learning_pace}
            - Session progress: {session_progress}
            
            {emotional_guidance}
            {cognitive_adjustment}
            {modality_instruction}""",
            ['user_name', 'current_topic', 'learning_style', 'confidence_level', 'user_query',
             'current_performance', 'learning_pace', 'session_progress', 'emotional_guidance',
             'cognitive_adjustment', 'modality_instruction']
        )
        
        # Problem Solving Templates
        templates['problem_solving'] = ContextualPromptTemplate(
            'problem_solving',
            """Help {user_name} solve this {current_topic} problem step by step.
            
            Student Profile:
            - Strengths: {student_strengths}
            - Areas for improvement: {struggle_areas}
            - Preferred approach: {learning_style}
            - Current emotional state: {emotional_state}
            
            Problem: {user_query}
            
            {emotional_guidance}
            {difficulty_adjustment}
            {step_by_step_guidance}""",
            ['user_name', 'current_topic', 'student_strengths', 'struggle_areas',
             'learning_style', 'emotional_state', 'user_query', 'emotional_guidance',
             'difficulty_adjustment', 'step_by_step_guidance']
        )
        
        # Review and Assessment Templates
        templates['review_assessment'] = ContextualPromptTemplate(
            'review_assessment',
            """Conduct a learning review with {user_name} for {current_topic}.
            
            Session Summary:
            - Topics covered: {topics_covered}
            - Concepts mastered: {concepts_mastered}
            - Areas needing work: {concepts_struggling}
            - Session duration: {session_duration} minutes
            
            Student's current state:
            - Performance level: {current_performance}
            - Confidence: {confidence_level}
            - Engagement: {engagement_score}
            
            {emotional_guidance}
            {next_steps_guidance}""",
            ['user_name', 'current_topic', 'topics_covered', 'concepts_mastered',
             'concepts_struggling', 'session_duration', 'current_performance',
             'confidence_level', 'engagement_score', 'emotional_guidance', 'next_steps_guidance']
        )
        
        # Motivational Support Templates
        templates['motivational_support'] = ContextualPromptTemplate(
            'motivational_support',
            """Provide motivational support to {user_name} who is studying {current_topic}.
            
            Current Situation:
            - Emotional state: {emotional_state}
            - Motivation level: {motivation_level}
            - Recent challenges: {frustration_indicators}
            - Strengths to build on: {student_strengths}
            
            {emotional_guidance}
            {encouragement_strategy}
            {goal_refocusing}""",
            ['user_name', 'current_topic', 'emotional_state', 'motivation_level',
             'frustration_indicators', 'student_strengths', 'emotional_guidance',
             'encouragement_strategy', 'goal_refocusing']
        )
        
        # Adaptive Difficulty Templates
        templates['adaptive_explanation'] = ContextualPromptTemplate(
            'adaptive_explanation',
            """Explain {current_topic} to {user_name} at the appropriate difficulty level.
            
            Adaptation Factors:
            - Current cognitive load: {cognitive_load}
            - Processing speed: {processing_speed}
            - Working memory capacity: {working_memory}
            - Recent performance: {current_performance}
            
            Query: {user_query}
            
            {cognitive_adjustment}
            {complexity_guidance}
            {scaffolding_instruction}""",
            ['current_topic', 'user_name', 'cognitive_load', 'processing_speed',
             'working_memory', 'current_performance', 'user_query', 'cognitive_adjustment',
             'complexity_guidance', 'scaffolding_instruction']
        )
        
        return templates
    
    def _initialize_context_modifiers(self) -> Dict[str, Dict[str, str]]:
        """Initialize context modification strategies"""
        return {
            'performance_based': {
                'high_performer': "Build on their strong foundation and introduce advanced concepts.",
                'average_performer': "Provide balanced support with clear examples and practice.",
                'struggling_performer': "Focus on fundamental concepts with extra scaffolding and encouragement."
            },
            'pace_based': {
                'fast': "Present information efficiently with challenging extensions.",
                'medium': "Use a balanced pace with adequate examples and practice time.",
                'slow': "Break down concepts into smaller steps with frequent check-ins."
            },
            'session_progress': {
                'early_session': "Start with a warm-up and build momentum gradually.",
                'mid_session': "Maintain focus with engaging activities and clear progress markers.",
                'late_session': "Keep content concise and provide regular summary points."
            }
        }
    
    def _initialize_emotional_adaptations(self) -> Dict[EmotionalState, str]:
        """Initialize emotional adaptation strategies"""
        return {
            EmotionalState.FRUSTRATED: """
            EMOTIONAL GUIDANCE: The student is showing signs of frustration.
            - Acknowledge their effort and provide reassurance
            - Break down the problem into smaller, manageable steps  
            - Offer alternative approaches or perspectives
            - Emphasize progress made so far
            - Suggest a brief mental break if needed
            """,
            
            EmotionalState.CONFUSED: """
            EMOTIONAL GUIDANCE: The student appears confused.
            - Use simpler language and shorter sentences
            - Provide concrete examples before abstract concepts
            - Check understanding frequently with simple questions
            - Offer multiple explanations using different approaches
            - Be patient and encouraging
            """,
            
            EmotionalState.CONFIDENT: """
            EMOTIONAL GUIDANCE: The student is displaying confidence.
            - Challenge them with slightly more advanced concepts
            - Encourage them to explain their understanding
            - Introduce extension activities or applications
            - Praise their competence while maintaining appropriate challenge
            """,
            
            EmotionalState.MOTIVATED: """
            EMOTIONAL GUIDANCE: The student is highly motivated.
            - Capitalize on their enthusiasm with engaging content
            - Provide opportunities for deeper exploration
            - Connect to their personal interests and goals
            - Encourage active participation and questions
            """,
            
            EmotionalState.BORED: """
            EMOTIONAL GUIDANCE: The student seems disengaged.
            - Introduce variety in teaching methods
            - Connect content to real-world applications
            - Use interactive elements and questions
            - Adjust difficulty level to maintain challenge
            - Incorporate their personal interests
            """,
            
            EmotionalState.ANXIOUS: """
            EMOTIONAL GUIDANCE: The student appears anxious about learning.
            - Provide constant reassurance and positive feedback
            - Use low-stakes questioning and gentle corrections
            - Create a supportive, non-judgmental environment
            - Focus on effort and process rather than outcomes
            - Break tasks into very small, achievable steps
            """
        }
    
    def _initialize_cognitive_adjustments(self) -> Dict[CognitiveLoadLevel, str]:
        """Initialize cognitive load adjustment strategies"""
        return {
            CognitiveLoadLevel.LOW: """
            COGNITIVE ADJUSTMENT: Student has low cognitive load - can handle complexity.
            - Present comprehensive information with multiple perspectives
            - Include advanced connections and implications
            - Encourage critical thinking and analysis
            - Introduce challenging problem-solving scenarios
            """,
            
            CognitiveLoadLevel.MODERATE: """
            COGNITIVE ADJUSTMENT: Student has moderate cognitive load - balanced approach.
            - Present information in organized, logical sequences
            - Use clear examples to illustrate each point
            - Provide adequate processing time between concepts
            - Include some challenge while maintaining support
            """,
            
            CognitiveLoadLevel.HIGH: """
            COGNITIVE ADJUSTMENT: Student has high cognitive load - simplify approach.
            - Break information into small, digestible chunks
            - Use simple, clear language and shorter sentences
            - Provide frequent summaries and check-ins
            - Reduce extraneous information and focus on essentials
            - Offer one concept at a time before moving forward
            """,
            
            CognitiveLoadLevel.OVERLOAD: """
            COGNITIVE ADJUSTMENT: Student is experiencing cognitive overload - emergency simplification.
            - STOP introducing new information immediately
            - Focus only on the most essential core concept
            - Use the simplest possible language and explanations
            - Provide immediate scaffolding and support
            - Suggest a brief break to reset cognitive capacity
            - Check understanding before any progression
            """
        }
    
    def _select_base_template(self, intent: str, context: LearningContext) -> ContextualPromptTemplate:
        """Select the most appropriate base template"""
        
        # Map common intents to templates
        intent_mapping = {
            'explain': 'explanation_basic',
            'solve': 'problem_solving', 
            'review': 'review_assessment',
            'motivate': 'motivational_support',
            'adapt': 'adaptive_explanation'
        }
        
        # Check if student needs motivational support
        if context.emotional_state in [EmotionalState.FRUSTRATED, EmotionalState.ANXIOUS] or \
           context.motivation_level < 0.3:
            return self.prompt_templates['motivational_support']
        
        # Check if cognitive load requires special handling
        if context.cognitive_load in [CognitiveLoadLevel.HIGH, CognitiveLoadLevel.OVERLOAD]:
            return self.prompt_templates['adaptive_explanation']
        
        # Use intent-based selection
        template_key = intent_mapping.get(intent, 'explanation_basic')
        return self.prompt_templates.get(template_key, self.prompt_templates['explanation_basic'])
    
    def _build_context_data(self, context: LearningContext, user_query: str, 
                          history: List[Dict]) -> Dict[str, Any]:
        """Build comprehensive context data for template rendering"""
        
        return {
            'user_name': "Student",  # Could be personalized from user profile
            'current_topic': context.current_topic,
            'user_query': user_query,
            'learning_style': context.preferred_modality.value,
            'confidence_level': self._format_confidence_level(context.confidence_level),
            'current_performance': self._format_performance_level(context.current_performance),
            'learning_pace': context.learning_pace,
            'session_progress': f"{context.interaction_count} interactions, {context.session_duration:.1f} minutes",
            'emotional_state': context.emotional_state.value,
            'motivation_level': self._format_motivation_level(context.motivation_level),
            'engagement_score': self._format_engagement_score(context.engagement_score),
            'topics_covered': ", ".join(context.topics_covered),
            'concepts_mastered': ", ".join(context.concepts_mastered) or "None yet",
            'concepts_struggling': ", ".join(context.concepts_struggling) or "None identified",
            'session_duration': int(context.session_duration),
            'frustration_indicators': ", ".join(context.frustration_indicators) or "None",
            'student_strengths': self._infer_strengths(context),
            'struggle_areas': ", ".join(context.concepts_struggling) or "None currently identified",
            'cognitive_load': context.cognitive_load.value,
            'processing_speed': context.processing_speed,
            'working_memory': str(context.working_memory_capacity)
        }
    
    def _get_emotional_adaptations(self, emotional_state: EmotionalState) -> str:
        """Get emotional adaptation guidance"""
        return self.emotional_adaptations.get(emotional_state, "")
    
    def _get_cognitive_adjustments(self, cognitive_load: CognitiveLoadLevel) -> str:
        """Get cognitive load adjustment guidance"""
        return self.cognitive_load_adjustments.get(cognitive_load, "")
    
    def _get_modality_modifications(self, preferred_modality: LearningModalityType) -> str:
        """Get learning modality-specific modifications"""
        modality_instructions = {
            LearningModalityType.VISUAL: """
            MODALITY INSTRUCTION: Student prefers visual learning.
            - Use descriptive language that helps them visualize concepts
            - Suggest diagrams, charts, or mental imagery when relevant
            - Organize information spatially and hierarchically
            - Use examples that can be easily visualized
            """,
            
            LearningModalityType.AUDITORY: """
            MODALITY INSTRUCTION: Student prefers auditory learning.
            - Use clear, verbal explanations with good flow
            - Encourage them to talk through problems out loud
            - Use analogies and stories to explain concepts
            - Suggest reading content aloud for better retention
            """,
            
            LearningModalityType.KINESTHETIC: """
            MODALITY INSTRUCTION: Student prefers hands-on learning.
            - Encourage active engagement and practice
            - Suggest physical manipulation of concepts when possible
            - Use step-by-step processes they can follow along
            - Incorporate movement or tactile elements where relevant
            """,
            
            LearningModalityType.READING_WRITING: """
            MODALITY INSTRUCTION: Student prefers reading/writing approach.
            - Provide clear, well-structured written explanations
            - Encourage note-taking and written summaries
            - Use lists, outlines, and organized text formats
            - Suggest written practice exercises
            """,
            
            LearningModalityType.MULTIMODAL: """
            MODALITY INSTRUCTION: Student benefits from multiple modalities.
            - Combine visual, auditory, and kinesthetic elements
            - Offer multiple ways to engage with the content
            - Vary your teaching approach within the explanation
            - Allow them to choose their preferred interaction style
            """
        }
        
        return modality_instructions.get(preferred_modality, "")
    
    def _render_adaptive_prompt(self, template: ContextualPromptTemplate, 
                               context_data: Dict[str, Any],
                               emotional_adaptations: str,
                               cognitive_adjustments: str,
                               modality_mods: str) -> str:
        """Render the final adaptive prompt"""
        
        # Add adaptation instructions to context data
        context_data['emotional_guidance'] = emotional_adaptations
        context_data['cognitive_adjustment'] = cognitive_adjustments
        context_data['modality_instruction'] = modality_mods
        
        # Add additional contextual guidance
        context_data['difficulty_adjustment'] = self._generate_difficulty_guidance(context_data)
        context_data['step_by_step_guidance'] = self._generate_step_guidance(context_data)
        context_data['scaffolding_instruction'] = self._generate_scaffolding_guidance(context_data)
        context_data['complexity_guidance'] = self._generate_complexity_guidance(context_data)
        context_data['encouragement_strategy'] = self._generate_encouragement_strategy(context_data)
        context_data['goal_refocusing'] = self._generate_goal_refocusing(context_data)
        context_data['next_steps_guidance'] = self._generate_next_steps(context_data)
        
        # Render the template
        final_prompt = template.render(context_data)
        
        # Post-process to clean up any remaining placeholders
        final_prompt = self._clean_prompt(final_prompt)
        
        return final_prompt
    
    def _format_confidence_level(self, confidence: float) -> str:
        """Format confidence level for human reading"""
        if confidence > 0.8:
            return "very confident"
        elif confidence > 0.6:
            return "confident"
        elif confidence > 0.4:
            return "somewhat confident"
        elif confidence > 0.2:
            return "low confidence"
        else:
            return "very low confidence"
    
    def _format_performance_level(self, performance: float) -> str:
        """Format performance level for human reading"""
        if performance > 0.8:
            return "excellent performance"
        elif performance > 0.6:
            return "good performance"
        elif performance > 0.4:
            return "moderate performance"
        elif performance > 0.2:
            return "below average performance"
        else:
            return "struggling performance"
    
    def _format_motivation_level(self, motivation: float) -> str:
        """Format motivation level for human reading"""
        if motivation > 0.7:
            return "highly motivated"
        elif motivation > 0.5:
            return "motivated"
        elif motivation > 0.3:
            return "somewhat motivated"
        else:
            return "low motivation"
    
    def _format_engagement_score(self, engagement: float) -> str:
        """Format engagement score for human reading"""
        if engagement > 0.7:
            return "highly engaged"
        elif engagement > 0.5:
            return "engaged"
        elif engagement > 0.3:
            return "moderately engaged"
        else:
            return "disengaged"
    
    def _infer_strengths(self, context: LearningContext) -> str:
        """Infer student strengths from context"""
        strengths = []
        
        if context.current_performance > 0.7:
            strengths.append("strong performance")
        if context.engagement_score > 0.6:
            strengths.append("good engagement")
        if context.confidence_level > 0.6:
            strengths.append("self-confidence")
        if context.session_duration > context.optimal_session_length * 0.8:
            strengths.append("sustained attention")
        if len(context.concepts_mastered) > len(context.concepts_struggling):
            strengths.append("concept mastery")
        
        return ", ".join(strengths) if strengths else "developing fundamental skills"
    
    def _generate_difficulty_guidance(self, context_data: Dict[str, Any]) -> str:
        """Generate difficulty adjustment guidance"""
        performance = context_data.get('current_performance', '')
        
        if 'excellent' in performance or 'good' in performance:
            return "Feel free to introduce challenging concepts and extensions."
        elif 'moderate' in performance:
            return "Maintain current difficulty with good scaffolding."
        else:
            return "Simplify concepts and provide additional support and examples."
    
    def _generate_step_guidance(self, context_data: Dict[str, Any]) -> str:
        """Generate step-by-step guidance"""
        cognitive_load = context_data.get('cognitive_load', '')
        
        if cognitive_load in ['high', 'overload']:
            return "Break down into very small, clear steps. Wait for understanding before proceeding."
        else:
            return "Provide logical step-by-step progression with clear reasoning."
    
    def _generate_scaffolding_guidance(self, context_data: Dict[str, Any]) -> str:
        """Generate scaffolding instruction"""
        confidence = context_data.get('confidence_level', '')
        
        if 'low' in confidence:
            return "Provide extensive scaffolding with examples, hints, and guided practice."
        elif 'somewhat' in confidence:
            return "Offer moderate scaffolding with opportunities for independent thinking."
        else:
            return "Minimal scaffolding needed - encourage independent problem-solving."
    
    def _generate_complexity_guidance(self, context_data: Dict[str, Any]) -> str:
        """Generate complexity guidance based on cognitive load"""
        cognitive_load = context_data.get('cognitive_load', '')
        
        if cognitive_load == 'overload':
            return "CRITICAL: Use simplest possible language and concepts only."
        elif cognitive_load == 'high':
            return "Reduce complexity significantly - focus on core essentials only."
        elif cognitive_load == 'moderate':
            return "Balanced complexity with clear explanations."
        else:
            return "Can handle full complexity with rich connections."
    
    def _generate_encouragement_strategy(self, context_data: Dict[str, Any]) -> str:
        """Generate encouragement strategy"""
        emotional_state = context_data.get('emotional_state', '')
        motivation = context_data.get('motivation_level', '')
        
        if emotional_state in ['frustrated', 'anxious'] or 'low' in motivation:
            return "Provide frequent positive reinforcement and acknowledge effort over outcome."
        elif emotional_state == 'confident':
            return "Acknowledge competence while maintaining appropriate challenge."
        else:
            return "Provide balanced encouragement and constructive feedback."
    
    def _generate_goal_refocusing(self, context_data: Dict[str, Any]) -> str:
        """Generate goal refocusing guidance"""
        concepts_struggling = context_data.get('concepts_struggling', '')
        
        if concepts_struggling and concepts_struggling != "None identified":
            return f"Refocus on mastering: {concepts_struggling}. Break into smaller, achievable goals."
        else:
            return "Maintain focus on current learning objectives with clear progress markers."
    
    def _generate_next_steps(self, context_data: Dict[str, Any]) -> str:
        """Generate next steps guidance"""
        performance = context_data.get('current_performance', '')
        concepts_mastered = context_data.get('concepts_mastered', '')
        
        if 'excellent' in performance or 'good' in performance:
            return "Ready for next level concepts or practical applications."
        elif concepts_mastered and concepts_mastered != "None yet":
            return "Build on mastered concepts while reinforcing current learning."
        else:
            return "Focus on solidifying current concepts before advancing."
    
    def _clean_prompt(self, prompt: str) -> str:
        """Clean up the prompt by removing empty sections and formatting"""
        # Remove empty guidance sections
        lines = prompt.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that are just guidance headers with no content
            if line.strip() and not (line.strip().endswith(':') and len(line.strip()) < 50):
                cleaned_lines.append(line)
        
        # Remove excessive whitespace
        cleaned_prompt = '\n'.join(cleaned_lines)
        cleaned_prompt = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_prompt)
        
        return cleaned_prompt.strip()


class ContextualPromptEngine:
    """Main engine for contextual prompt generation"""
    
    def __init__(self):
        self.prompt_generator = AdaptivePromptGenerator()
        self.context_engine = DynamicContextEngine()
        
    async def generate_personalized_prompt(self, user_id: str, session_id: str,
                                         user_message: str, response_time: float,
                                         intent: str = 'explain',
                                         additional_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fully personalized prompt based on comprehensive context"""
        
        # Analyze comprehensive learning context
        learning_context = await self.context_engine.analyze_comprehensive_context(
            user_id, session_id, user_message, response_time, additional_data
        )
        
        # Get conversation history
        from .memory_service import memory_service
        conversation_history = memory_service.get_conversation_history(user_id, session_id)
        history_messages = conversation_history.get('messages', [])
        
        # Generate contextual prompt
        personalized_prompt = self.prompt_generator.generate_contextual_prompt(
            intent, learning_context, user_message, history_messages
        )
        
        return personalized_prompt
    
    def update_template_effectiveness(self, template_name: str, effectiveness_score: float):
        """Update template effectiveness based on user feedback"""
        template = self.prompt_generator.prompt_templates.get(template_name)
        if template:
            # Update effectiveness using weighted average
            current_score = template.effectiveness_score
            usage_count = template.usage_count
            
            # Weighted average with more recent feedback having higher weight
            new_score = (current_score * (usage_count - 1) + effectiveness_score) / usage_count
            template.effectiveness_score = new_score