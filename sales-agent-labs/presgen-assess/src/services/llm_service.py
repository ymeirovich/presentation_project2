"""OpenAI LLM service for intelligent assessment generation."""

import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import openai
from openai import AsyncOpenAI

from src.common.config import settings
from src.knowledge.base import RAGKnowledgeBase

logger = logging.getLogger(__name__)


class LLMService:
    """Service for OpenAI LLM integration with RAG context enhancement."""

    def __init__(self):
        """Initialize OpenAI client and RAG knowledge base."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.knowledge_base = RAGKnowledgeBase()
        self.model = "gpt-4"
        self.token_usage = {"total_tokens": 0, "total_cost": 0.0}

    async def generate_assessment_questions(
        self,
        certification_id: str,
        domain: str,
        question_count: int = 5,
        difficulty_level: str = "intermediate",
        question_types: List[str] = None,
        use_rag_context: bool = True
    ) -> Dict:
        """Generate assessment questions with RAG context enhancement."""
        try:
            if question_types is None:
                question_types = ["multiple_choice", "scenario"]

            # Retrieve RAG context for the domain
            rag_context = ""
            citations = []
            if use_rag_context:
                context_result = await self.knowledge_base.retrieve_context_for_assessment(
                    query=f"{domain} certification exam questions and concepts",
                    certification_id=certification_id,
                    k=8,
                    balance_sources=True
                )
                rag_context = context_result.get("combined_context", "")
                citations = context_result.get("citations", [])

            # Generate questions using LLM
            questions = await self._generate_questions_with_context(
                domain=domain,
                question_count=question_count,
                difficulty_level=difficulty_level,
                question_types=question_types,
                rag_context=rag_context
            )

            # Add citations to each question
            for question in questions:
                question["rag_sources"] = citations

            logger.info(
                f"✅ Generated {len(questions)} questions for {domain} "
                f"(difficulty: {difficulty_level})"
            )

            return {
                "success": True,
                "questions": questions,
                "domain": domain,
                "difficulty_level": difficulty_level,
                "rag_context_used": bool(rag_context),
                "citations": citations,
                "token_usage": self.token_usage
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate assessment questions: {e}")
            return {
                "success": False,
                "error": str(e),
                "questions": []
            }

    async def _generate_questions_with_context(
        self,
        domain: str,
        question_count: int,
        difficulty_level: str,
        question_types: List[str],
        rag_context: str
    ) -> List[Dict]:
        """Generate questions using OpenAI with RAG context."""

        # Build the prompt with RAG context
        prompt = self._build_assessment_prompt(
            domain=domain,
            question_count=question_count,
            difficulty_level=difficulty_level,
            question_types=question_types,
            rag_context=rag_context
        )

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        # Track token usage
        usage = response.usage
        self.token_usage["total_tokens"] += usage.total_tokens
        self.token_usage["total_cost"] += self._calculate_cost(usage.total_tokens)

        # Parse response
        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM response: {e}")
            return []

    def _build_assessment_prompt(
        self,
        domain: str,
        question_count: int,
        difficulty_level: str,
        question_types: List[str],
        rag_context: str
    ) -> str:
        """Build comprehensive prompt for assessment generation."""

        context_section = ""
        if rag_context:
            context_section = f"""
## Reference Context
Use the following context from official exam guides and course materials to inform your question generation:

{rag_context}

IMPORTANT: Base your questions on the concepts, terminology, and scenarios found in the reference context above.
"""

        prompt = f"""Generate {question_count} high-quality certification exam questions for the {domain} domain.

{context_section}

## Requirements:
- Difficulty Level: {difficulty_level}
- Question Types: {', '.join(question_types)}
- Domain Focus: {domain}
- Each question must test practical knowledge and real-world application
- Include detailed explanations referencing the source material
- Ensure questions align with current industry best practices

## Question Format:
For each question, provide:
1. **question_text**: Clear, concise question statement
2. **question_type**: One of {question_types}
3. **options**: Array of 4 answer choices (A, B, C, D) for multiple choice
4. **correct_answer**: The correct option (A, B, C, or D)
5. **explanation**: Detailed explanation of why the answer is correct
6. **domain**: {domain}
7. **subdomain**: Specific area within the domain
8. **bloom_level**: Cognitive level (remember, understand, apply, analyze, evaluate, create)
9. **difficulty**: Numeric difficulty (0.0-1.0, where {self._get_difficulty_range(difficulty_level)})
10. **time_limit_seconds**: Recommended time limit (60-300 seconds)

## Bloom's Taxonomy Distribution:
- Remember/Understand: 20%
- Apply/Analyze: 60%
- Evaluate/Create: 20%

## Response Format:
Return a JSON object with this structure:
{{
    "questions": [
        {{
            "id": "q1",
            "question_text": "...",
            "question_type": "multiple_choice",
            "options": [
                {{"letter": "A", "text": "..."}},
                {{"letter": "B", "text": "..."}},
                {{"letter": "C", "text": "..."}},
                {{"letter": "D", "text": "..."}}
            ],
            "correct_answer": "A",
            "explanation": "...",
            "domain": "{domain}",
            "subdomain": "...",
            "bloom_level": "apply",
            "difficulty": 0.6,
            "time_limit_seconds": 180
        }}
    ]
}}

Generate questions that are challenging but fair, testing both theoretical knowledge and practical application.
"""
        return prompt

    def _get_system_prompt(self) -> str:
        """Get the system prompt for assessment generation."""
        return """You are an expert certification exam question writer with deep knowledge of cloud computing, cybersecurity, and IT certifications. Your goal is to create high-quality, realistic exam questions that accurately assess candidate knowledge and skills.

Key principles:
1. Questions must be based on official exam objectives and real-world scenarios
2. Avoid trick questions or ambiguous wording
3. Ensure all distractors (wrong answers) are plausible but clearly incorrect
4. Explanations should teach and reinforce correct understanding
5. Reference authoritative sources when possible
6. Questions should reflect current industry practices and technologies

Always respond with valid JSON in the specified format."""

    def _get_difficulty_range(self, difficulty_level: str) -> str:
        """Get difficulty range description for prompt."""
        ranges = {
            "beginner": "0.2-0.4 represents basic recall and understanding",
            "intermediate": "0.5-0.7 represents application and analysis",
            "advanced": "0.7-0.9 represents evaluation and synthesis"
        }
        return ranges.get(difficulty_level, "0.5-0.7")

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate estimated cost for token usage."""
        # GPT-4 pricing (approximate)
        cost_per_1k_tokens = 0.03
        return (tokens / 1000) * cost_per_1k_tokens

    async def generate_course_outline(
        self,
        assessment_results: Dict,
        gap_analysis: Dict,
        target_slide_count: int = 20,
        certification_id: str = None
    ) -> Dict:
        """Generate course outline based on assessment results and gap analysis."""
        try:
            # Validate slide count
            if not 1 <= target_slide_count <= 40:
                raise ValueError("Slide count must be between 1 and 40")

            # Retrieve RAG context for identified gaps
            rag_context = ""
            citations = []
            if certification_id and gap_analysis.get("priority_learning_areas"):
                priority_areas = gap_analysis["priority_learning_areas"]
                context_query = f"learning materials for {', '.join(priority_areas)}"

                context_result = await self.knowledge_base.retrieve_context_for_assessment(
                    query=context_query,
                    certification_id=certification_id,
                    k=10,
                    balance_sources=True
                )
                rag_context = context_result.get("combined_context", "")
                citations = context_result.get("citations", [])

            # Generate course outline
            outline = await self._generate_outline_with_context(
                assessment_results=assessment_results,
                gap_analysis=gap_analysis,
                target_slide_count=target_slide_count,
                rag_context=rag_context
            )

            outline["citations"] = citations
            outline["rag_context_used"] = bool(rag_context)

            logger.info(
                f"✅ Generated course outline with {target_slide_count} slides "
                f"targeting {len(gap_analysis.get('priority_learning_areas', []))} gap areas"
            )

            return outline

        except Exception as e:
            logger.error(f"❌ Failed to generate course outline: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _generate_outline_with_context(
        self,
        assessment_results: Dict,
        gap_analysis: Dict,
        target_slide_count: int,
        rag_context: str
    ) -> Dict:
        """Generate course outline using OpenAI with context."""

        prompt = self._build_outline_prompt(
            assessment_results=assessment_results,
            gap_analysis=gap_analysis,
            target_slide_count=target_slide_count,
            rag_context=rag_context
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert instructional designer specializing in certification training programs. Create comprehensive, well-structured course outlines that address specific learning gaps and build competency systematically."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )

        # Track token usage
        usage = response.usage
        self.token_usage["total_tokens"] += usage.total_tokens
        self.token_usage["total_cost"] += self._calculate_cost(usage.total_tokens)

        try:
            result = json.loads(response.choices[0].message.content)
            result["success"] = True
            return result
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse outline response: {e}")
            return {"success": False, "error": "Failed to parse response"}

    def _build_outline_prompt(
        self,
        assessment_results: Dict,
        gap_analysis: Dict,
        target_slide_count: int,
        rag_context: str
    ) -> str:
        """Build prompt for course outline generation."""

        context_section = ""
        if rag_context:
            context_section = f"""
## Reference Learning Materials
Use the following content from official exam guides and course materials:

{rag_context}

Base your course outline on the concepts and structure found in the reference materials above.
"""

        weak_areas = gap_analysis.get("priority_learning_areas", [])
        overall_score = assessment_results.get("score", 0)
        domain_scores = assessment_results.get("domain_scores", {})

        prompt = f"""Create a personalized course outline to address the learning gaps identified in this assessment.

## Assessment Results Summary:
- Overall Score: {overall_score}%
- Weak Areas Requiring Focus: {', '.join(weak_areas)}
- Domain Performance: {json.dumps(domain_scores, indent=2)}

## Gap Analysis:
{json.dumps(gap_analysis, indent=2)}

{context_section}

## Course Requirements:
- Target Slides: {target_slide_count} (must be exactly this number)
- Focus: Address identified weak areas while reinforcing strengths
- Structure: Logical progression from foundational to advanced concepts
- Practical: Include hands-on exercises and real-world scenarios

## Required Response Format:
{{
    "course_title": "Personalized Learning Path: [Certification Name]",
    "estimated_duration_minutes": number,
    "learning_objectives": ["objective1", "objective2", ...],
    "sections": [
        {{
            "section_title": "...",
            "slide_count": number,
            "learning_outcomes": ["outcome1", "outcome2", ...],
            "content_outline": ["point1", "point2", ...],
            "estimated_minutes": number
        }}
    ],
    "target_gaps": [list of gap areas this course addresses],
    "prerequisites": ["prerequisite1", "prerequisite2", ...],
    "success_criteria": ["criteria1", "criteria2", ...]
}}

Ensure the total slide_count across all sections equals exactly {target_slide_count}.
Prioritize content that directly addresses the identified learning gaps.
"""
        return prompt

    async def get_usage_stats(self) -> Dict:
        """Get current token usage statistics."""
        return {
            "total_tokens_used": self.token_usage["total_tokens"],
            "estimated_cost_usd": self.token_usage["total_cost"],
            "model": self.model,
            "timestamp": datetime.now().isoformat()
        }

    async def health_check(self) -> Dict:
        """Check LLM service health."""
        try:
            # Test API connectivity with a simple request
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )

            return {
                "status": "healthy",
                "model_available": self.model,
                "api_accessible": True,
                "total_tokens_used": self.token_usage["total_tokens"]
            }
        except Exception as e:
            logger.error(f"❌ LLM service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_accessible": False
            }