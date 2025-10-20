"""OpenAI LLM service for intelligent assessment generation."""

import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

import openai
from openai import AsyncOpenAI
from sqlalchemy import select, or_, func

from src.common.config import settings
from src.knowledge.base import RAGKnowledgeBase

from src.common.logging_config import get_assessment_logger
from src.models.certification import CertificationProfile
from src.service.database import AsyncSessionLocal

logger = get_assessment_logger()


class LLMService:
    """Service for OpenAI LLM integration with RAG context enhancement."""

    def __init__(self):
        """Initialize OpenAI client and RAG knowledge base."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.knowledge_base = RAGKnowledgeBase()
        self.model = settings.openai_model
        self.token_usage = {"total_tokens": 0, "total_cost": 0.0}
        self._profile_cache: Dict[str, CertificationProfile] = {}

    def _log_llm_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit JSON-formatted LLM telemetry."""
        record = {"event": event, **payload}
        try:
            logger.info(json.dumps(record))
        except Exception as exc:  # pragma: no cover
            logger.info(json.dumps({"event": event, "log_error": str(exc)}))

    async def generate_text(
        self,
        *,
        prompt: str,
        max_tokens: int = 600,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate free-form text using the configured OpenAI model."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        choice = response.choices[0] if response.choices else None
        content = (choice.message.content if choice and choice.message else "") or ""
        content = content.strip()

        usage = getattr(response, "usage", None)
        if usage:
            self.token_usage["total_tokens"] += usage.total_tokens
            self.token_usage["total_cost"] += self._calculate_cost(usage.total_tokens)

            self._log_llm_event(
                "text_generation_complete",
                {
                    "model": self.model,
                    "prompt_tokens": getattr(usage, "prompt_tokens", None),
                    "completion_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": usage.total_tokens,
                    "metadata": metadata or {},
                    "preview": content[:200]
                }
            )
        else:
            self._log_llm_event(
                "text_generation_complete",
                {
                    "model": self.model,
                    "metadata": metadata or {},
                    "preview": content[:200],
                    "total_tokens": None
                }
            )

        return content

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

            # ✅ PHASE 2 FIX: Log certification_id at function entry
            logger.info(
                f"🎯 generate_assessment_questions | certification_id={certification_id} | "
                f"domain={domain} | question_count={question_count} | difficulty={difficulty_level} | "
                f"use_rag_context={use_rag_context}"
            )

            # Load certification profile details (prompt, slug, etc.)
            certification_profile = await self._get_certification_profile(certification_id)
            cert_prompt = self._get_assessment_prompt_text(certification_profile)
            cert_slug = self._derive_cert_slug(certification_profile, certification_id)
            focus_areas = self._determine_focus_areas(domain, certification_profile)

            # ✅ PHASE 2 FIX: Log detailed certification profile resolution
            if certification_profile is None:
                logger.warning(
                    f"⚠️ Certification profile NOT FOUND | identifier={certification_id} | "
                    f"using_fallback_prompt=True | cert_slug={cert_slug}"
                )
            else:
                logger.info(
                    f"✅ Certification profile loaded | "
                    f"profile_id={certification_profile.id} | "
                    f"profile_name={certification_profile.name} | "
                    f"cert_slug={cert_slug} | "
                    f"has_assessment_prompt={bool(cert_prompt)} | "
                    f"prompt_length={len(cert_prompt) if cert_prompt else 0}"
                )
                if not cert_prompt:
                    logger.warning(
                        f"⚠️ Certification profile missing assessment_prompt | "
                        f"profile_id={certification_profile.id} | "
                        f"profile_name={certification_profile.name} | "
                        f"using_default_prompt=True"
                    )

            # Retrieve RAG context for the domain
            knowledge_base_context = ""
            citations = []
            if use_rag_context:
                # ✅ PHASE 2 FIX: Log RAG retrieval attempt with certification details
                rag_query = f"{domain} certification exam questions and concepts"
                logger.info(
                    f"🔍 Initiating RAG retrieval | certification_id={cert_slug} | "
                    f"query={rag_query} | k=8 | balance_sources=True"
                )

                context_result = await self.knowledge_base.retrieve_context_for_assessment(
                    query=rag_query,
                    certification_id=cert_slug,
                    k=8,
                    balance_sources=True
                )
                context_result = context_result or {}

                # ✅ PHASE 2 FIX: Log RAG retrieval results
                total_results = context_result.get("total_results", 0)
                logger.info(
                    f"📊 RAG retrieval result | certification_id={cert_slug} | "
                    f"total_results={total_results} | "
                    f"exam_guides={context_result.get('sources', {}).get('exam_guides', {}).get('count', 0)} | "
                    f"transcripts={context_result.get('sources', {}).get('transcripts', {}).get('count', 0)}"
                )

                if total_results == 0 and certification_profile is not None:
                    # ✅ PHASE 2 FIX: Log fallback attempt
                    fallback_id = str(certification_profile.id)
                    logger.warning(
                        f"⚠️ RAG returned 0 results for cert_slug={cert_slug}, "
                        f"trying fallback with profile_id={fallback_id}"
                    )

                    fallback_result = await self.knowledge_base.retrieve_context_for_assessment(
                        query=rag_query,
                        certification_id=fallback_id,
                        k=8,
                        balance_sources=True
                    )
                    fallback_total = (fallback_result or {}).get("total_results", 0)
                    if fallback_total > 0:
                        logger.info(
                            f"✅ Fallback RAG retrieval succeeded | "
                            f"certification_profile_id={fallback_id} | total_results={fallback_total}"
                        )
                        context_result = fallback_result
                    else:
                        logger.warning(
                            f"⚠️ Fallback RAG also returned 0 results | "
                            f"certification_profile_id={fallback_id}"
                        )
                    context_result = context_result or {}

                knowledge_base_context = (context_result or {}).get("combined_context", "")
                citations = (context_result or {}).get("citations", [])

                # ✅ PHASE 2 FIX: Log final RAG context summary
                logger.info(
                    f"✅ RAG context prepared | certification_id={cert_slug} | "
                    f"context_chars={len(knowledge_base_context)} | citations_count={len(citations)}"
                )

            # Generate questions using LLM
            questions = await self._generate_questions_with_context(
                domain=domain,
                question_count=question_count,
                difficulty_level=difficulty_level,
                question_types=question_types,
                knowledge_base_context=knowledge_base_context,
                base_prompt=cert_prompt,
                focus_areas=focus_areas
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
                "rag_context_used": bool(knowledge_base_context),
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
        knowledge_base_context: str,
        base_prompt: Optional[str],
        focus_areas: str
    ) -> List[Dict]:
        """Generate questions using OpenAI with RAG context."""

        # Build the prompt with RAG context
        prompt = self._build_assessment_prompt(
            domain=domain,
            question_count=question_count,
            difficulty_level=difficulty_level,
            question_types=question_types,
            knowledge_base_context=knowledge_base_context,
            base_prompt=base_prompt,
            focus_areas=focus_areas
        )

        # ✅ PHASE 2 FIX: Enhanced LLM request logging with complete messages
        system_prompt = self._get_system_prompt()
        self._log_llm_event(
            "generate_questions_request",
            {
                "model": self.model,
                "domain": domain,
                "question_count": question_count,
                "difficulty_level": difficulty_level,
                "question_types": question_types,
                "knowledge_base_context_chars": len(knowledge_base_context or ""),
                "prompt_chars": len(prompt),
                "assessment_prompt_source": "profile" if base_prompt else "default",
                # ✅ COMPLETE MESSAGES LOGGED
                "system_message": system_prompt,
                "user_message": prompt,
                "knowledge_base_context_preview": (knowledge_base_context[:500] + "...") if len(knowledge_base_context) > 500 else knowledge_base_context,
            },
        )

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
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

        # ✅ PHASE 2 FIX: Enhanced LLM response logging with complete response
        self._log_llm_event(
            "generate_questions_response",
            {
                "model": self.model,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason,
                # ✅ COMPLETE RESPONSE LOGGED
                "raw_response": response.choices[0].message.content,
                "response_preview": response.choices[0].message.content[:200],
            },
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
        knowledge_base_context: str,
        base_prompt: Optional[str],
        focus_areas: str
    ) -> str:
        """Build comprehensive prompt for assessment generation."""

        primary_prompt = base_prompt.strip() if base_prompt else self._get_default_assessment_prompt(question_count)
        prompt_sections = [primary_prompt]

        if focus_areas:
            prompt_sections.append(f"FOCUS AREAS:\n- {focus_areas}")

        if knowledge_base_context:
            prompt_sections.append(
                "## Reference Context\n"
                "Use the following context from official exam guides and course materials to inform your question generation:\n\n"
                f"{knowledge_base_context}\n\n"
                "IMPORTANT: Base your questions on the concepts, terminology, and scenarios found in the reference context above."
            )

        prompt_sections.append(
            "## Requirements:\n"
            f"- Difficulty Level: {difficulty_level}\n"
            f"- Question Types: {', '.join(question_types)}\n"
            f"- Domain Focus: {domain}\n"
            "- Each question must test practical knowledge and real-world application\n"
            "- Include detailed explanations referencing the source material\n"
            "- Ensure questions align with current industry best practices\n"
            "- Each question must be unique—do not repeat, rephrase, or lightly modify any previously generated question within this assessment\n"
            "- If you detect overlap or redundancy, replace the question with a new one covering a distinct concept\n"
            "- Before finalizing, compare every new question against earlier ones in this assessment and regenerate anything that overlaps in topic, structure, or wording"
        )

        prompt_sections.append(
            "## Question Format:\n"
            "For each question, provide:\n"
            "1. **question_text**: Clear, concise question statement\n"
            f"2. **question_type**: One of {question_types}\n"
            "3. **options**: Array of 4 answer choices (A, B, C, D) for multiple choice\n"
            "4. **correct_answer**: The correct option (A, B, C, or D)\n"
            "5. **explanation**: Detailed explanation of why the answer is correct\n"
            f"6. **domain**: {domain}\n"
            "7. **subdomain**: Specific area within the domain\n"
            "8. **bloom_level**: Cognitive level (remember, understand, apply, analyze, evaluate, create)\n"
            f"9. **difficulty**: Numeric difficulty (0.0-1.0, where {self._get_difficulty_range(difficulty_level)})\n"
            "10. **time_limit_seconds**: Recommended time limit (60-300 seconds)"
        )

        prompt_sections.append(
            "## Bloom's Taxonomy Distribution:\n"
            "- Remember/Understand: 20%\n"
            "- Apply/Analyze: 60%\n"
            "- Evaluate/Create: 20%"
        )

        prompt_sections.append(
            "## Response Format:\n"
            "Return a JSON object with this structure:\n"
            "{\n"
            '    "questions": [\n'
            "        {\n"
            '            "id": "q1",\n'
            '            "question_text": "...",\n'
            '            "question_type": "multiple_choice",\n'
            '            "options": [\n'
            '                {"letter": "A", "text": "..."},\n'
            '                {"letter": "B", "text": "..."},\n'
            '                {"letter": "C", "text": "..."},\n'
            '                {"letter": "D", "text": "..."}\n'
            "            ],\n"
            '            "correct_answer": "A",\n'
            '            "explanation": "...",\n'
            f'            "domain": "{domain}",\n'
            '            "subdomain": "...",\n'
            '            "bloom_level": "apply",\n'
            '            "difficulty": 0.6,\n'
            '            "time_limit_seconds": 180\n'
            "        }\n"
            "    ]\n"
            "}\n\n"
            "Generate questions that are challenging but fair, testing both theoretical knowledge and practical application."
        )

        return "\n\n".join(section.strip() for section in prompt_sections if section)

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

    def _get_default_assessment_prompt(self, question_count: int) -> str:
        """Default assessment prompt when certification profile lacks custom prompt."""
        return (
            "You are an expert assessment designer creating high-quality certification exam questions.\n\n"
            "GENERATION REQUIREMENTS:\n"
            "- Clarity: Questions must be unambiguous and clearly written\n"
            "- Relevance: Directly aligned with certification objectives\n"
            "- Difficulty Appropriateness: Matched to target competency level\n"
            "- Discrimination: Effectively separates competent from non-competent candidates\n\n"
            "COGNITIVE LEVEL DISTRIBUTION:\n"
            "- Remember/Understand (30%): Foundational knowledge and comprehension\n"
            "- Apply/Analyze (50%): Practical application and analysis\n"
            "- Evaluate/Create (20%): Higher-order thinking and synthesis\n\n"
            f"Use the uploaded knowledge base content to ensure accuracy and generate {question_count} questions.\n\n"
            "DUPLICATION SAFEGUARDS:\n"
            "- Each question must be genuinely unique; do not reuse, rephrase, or lightly modify earlier questions in this assessment\n"
            "- Before finalizing, compare every new question against the full set already written and regenerate anything that overlaps in concept, structure, or wording\n"
            "- Cover distinct focus areas so no two questions assess the exact same scenario or knowledge point"
        )

    def _get_difficulty_range(self, difficulty_level: str) -> str:
        """Get difficulty range description for prompt."""
        ranges = {
            "beginner": "0.2-0.4 represents basic recall and understanding",
            "intermediate": "0.5-0.7 represents application and analysis",
            "advanced": "0.7-0.9 represents evaluation and synthesis"
        }
        return ranges.get(difficulty_level, "0.5-0.7")

    async def _get_certification_profile(self, certification_identifier: str) -> Optional[CertificationProfile]:
        """Fetch certification profile by UUID or slug."""
        if not certification_identifier:
            return None

        cached = self._profile_cache.get(certification_identifier)
        if cached:
            return cached

        stmt = None
        try:
            profile_uuid = UUID(certification_identifier)
            stmt = select(CertificationProfile).where(CertificationProfile.id == profile_uuid)
        except ValueError:
            slug = self._sanitize_slug(certification_identifier)
            stmt = select(CertificationProfile).where(
                or_(
                    CertificationProfile.collection_name == slug,
                    func.lower(CertificationProfile.name) == slug.replace("-", " ")
                )
            )

        if stmt is None:
            return None

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(stmt)
                profile = result.scalars().first()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "⚠️ Unable to load certification profile for identifier=%s: %s",
                certification_identifier,
                exc
            )
            return None

        if profile:
            self._profile_cache[str(profile.id)] = profile
            slug_key = self._derive_cert_slug(profile, str(profile.id))
            if slug_key:
                self._profile_cache[slug_key] = profile
        return profile

    def _derive_cert_slug(self, profile: Optional[CertificationProfile], fallback: str) -> str:
        """Derive slug used for knowledge base lookups."""
        if profile:
            if getattr(profile, "collection_name", None):
                return profile.collection_name
            if getattr(profile, "name", None):
                return self._sanitize_slug(profile.name)
        return self._sanitize_slug(fallback)

    @staticmethod
    def _sanitize_slug(value: str) -> str:
        """Sanitize strings into slug-compatible format."""
        if not value:
            return ""
        sanitized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
        return sanitized.strip("-")

    @staticmethod
    def _get_assessment_prompt_text(profile: Optional[CertificationProfile]) -> Optional[str]:
        """Extract trimmed assessment prompt from profile."""
        if profile and getattr(profile, "assessment_prompt", None):
            prompt = profile.assessment_prompt.strip()
            return prompt or None
        return None

    def _determine_focus_areas(self, domain: str, profile: Optional[CertificationProfile]) -> str:
        """Derive focus areas based on certification profile domain metadata."""
        if not profile or not getattr(profile, "exam_domains", None):
            return domain

        try:
            for domain_info in profile.exam_domains:
                if isinstance(domain_info, dict) and domain_info.get("name") == domain:
                    subdomains = domain_info.get("subdomains") or domain_info.get("focus_areas")
                    if subdomains:
                        if isinstance(subdomains, list):
                            return ", ".join(subdomains)
                        return str(subdomains)
        except Exception:  # pragma: no cover - defensive
            pass

        return domain

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

            context_log = {
                "event": "course_outline_context",
                "target_slide_count": target_slide_count,
                "certification_id": certification_id,
                "assessment_summary": {
                    "score": assessment_results.get("score"),
                    "overall_questions": assessment_results.get("question_count"),
                    "domain_keys": list((assessment_results.get("domain_scores") or {}).keys()),
                },
                "gap_summary": {
                    "priority_learning_areas": gap_analysis.get("priority_learning_areas", []),
                    "readiness_score": gap_analysis.get("overall_readiness_score"),
                    "metrics_keys": list(gap_analysis.keys()),
                },
            }
            logger.info(json.dumps(context_log))

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
            outline_log = {
                "event": "course_outline_response",
                "success": outline.get("success", True),
                "section_count": len(outline.get("sections", [])),
                "learning_objectives": outline.get("learning_objectives", []),
                "citations": outline.get("citations", []),
            }
            logger.info(json.dumps(outline_log))

            return outline

        except Exception as e:
            logger.error(f"❌ Failed to generate course outline: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_refined_course_outline(
        self,
        *,
        recommended_course: Dict[str, Any],
        presentation_prompt: Optional[str],
        rag_context: str,
        rag_citations: List[Dict[str, Any]],
        gap_analysis: Dict[str, Any],
        assessment_results: Dict[str, Any],
        target_slide_count: int
    ) -> Dict[str, Any]:
        """Regenerate course outline using existing recommendations, prompt guidance, and RAG context."""

        payload_preview = {
            "event": "refined_outline_context",
            "course_title": recommended_course.get("course_title"),
            "slide_count": target_slide_count,
            "learning_objectives": recommended_course.get("learning_objectives", []),
            "sections": [s.get("title") for s in recommended_course.get("sections", [])],
            "rag_chars": len(rag_context or ""),
            "presentation_prompt_chars": len(presentation_prompt or ""),
            "priority_learning_areas": gap_analysis.get("priority_learning_areas", []),
        }
        logger.info(json.dumps(payload_preview))

        prompt = self._build_refined_outline_prompt(
            recommended_course=recommended_course,
            presentation_prompt=presentation_prompt,
            rag_context=rag_context,
            gap_analysis=gap_analysis,
            assessment_results=assessment_results,
            target_slide_count=target_slide_count
        )

        # ✅ Phase 10 Task 1.1 - Log COMPLETE LLM request (not just metadata)
        self._log_llm_event(
            "refined_outline_request_full",
            {
                "model": self.model,
                "temperature": 0.5,
                "max_tokens": 2500,
                "prompt_text": prompt,  # Full prompt
                "recommended_course_summary": {
                    "skill_name": recommended_course.get("skill_name"),
                    "course_title": recommended_course.get("course_title"),
                    "difficulty_level": recommended_course.get("difficulty_level"),
                    "learning_objectives_count": len(recommended_course.get("learning_objectives", [])),
                    "sections_count": len(recommended_course.get("sections", [])),
                },
                "rag_context_preview": rag_context[:500] + "..." if len(rag_context) > 500 else rag_context,
                "rag_context_chars": len(rag_context),
                "gap_analysis_summary": {
                    "priority_learning_areas": gap_analysis.get("priority_learning_areas", []),
                    "overall_readiness_score": gap_analysis.get("overall_readiness_score"),
                },
                "assessment_results_summary": {
                    "score": assessment_results.get("score"),
                    "domains_count": len(assessment_results.get("domain_scores", {})),
                },
                "target_slide_count": target_slide_count,
            },
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert instructional designer. Always respond with valid JSON."
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

        result_content = response.choices[0].message.content

        # ✅ Phase 10 Task 1.2 - Log COMPLETE LLM response (not just preview)
        self._log_llm_event(
            "refined_outline_response_full",
            {
                "raw_response": result_content,  # Complete LLM response
                "token_usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason,
                "response_length_chars": len(result_content),
            },
        )

        try:
            result = json.loads(result_content)
            result["success"] = True
            result["citations"] = rag_citations
            result["rag_context_used"] = bool(rag_context)
            self._log_llm_event(
                "refined_outline_response_detail",
                {
                    "model": self.model,
                    "section_titles": [section.get("section_title") for section in result.get("sections", [])],
                    "learning_objectives": result.get("learning_objectives", []),
                },
            )
            return result
        except json.JSONDecodeError as exc:
            logger.error(f"❌ Failed to parse refined outline response: {exc}")
            return {"success": False, "error": "Failed to parse response"}

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
        self._log_llm_event(
            "generate_outline_request",
            {
                "model": self.model,
                "target_slide_count": target_slide_count,
                "rag_context_chars": len(rag_context or ""),
                "prompt_chars": len(prompt),
            },
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
        self._log_llm_event(
            "generate_outline_response",
            {
                "model": self.model,
                "token_usage": getattr(response.usage, "total_tokens", None),
                "response_preview": response.choices[0].message.content[:200],
            },
        )

        # Track token usage
        usage = response.usage
        self.token_usage["total_tokens"] += usage.total_tokens
        self.token_usage["total_cost"] += self._calculate_cost(usage.total_tokens)

        try:
            result = json.loads(response.choices[0].message.content)
            result["success"] = True
            self._log_llm_event(
                "generate_outline_response_detail",
                {
                    "model": self.model,
                    "section_titles": [section.get("section_title") for section in result.get("sections", [])],
                    "learning_objectives": result.get("learning_objectives", []),
                },
            )
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

    def _build_refined_outline_prompt(
        self,
        *,
        recommended_course: Dict[str, Any],
        presentation_prompt: Optional[str],
        rag_context: str,
        gap_analysis: Dict[str, Any],
        assessment_results: Dict[str, Any],
        target_slide_count: int
    ) -> str:
        """Build prompt for regenerated course outline with variable mapping validation."""

        course_title = recommended_course.get("course_title", "Untitled Course")
        skill_name = recommended_course.get("skill_name", "Unknown Skill")
        description = recommended_course.get("course_description", "")
        estimated_minutes = recommended_course.get("estimated_duration_minutes", 60)
        difficulty = recommended_course.get("difficulty_level", "intermediate")
        learning_objectives = recommended_course.get("learning_objectives", [])
        sections = recommended_course.get("sections", [])

        objectives_block = "\n".join(f"- {obj}" for obj in learning_objectives) or "None provided."
        sections_block = json.dumps(sections, indent=2)
        prompt_block = presentation_prompt or "Follow best practices for certification training presentations."
        rag_block = rag_context or "No external transcripts or exam guidelines provided."

        assessment_summary = json.dumps(
            {
                "score": assessment_results.get("score"),
                "domain_scores": assessment_results.get("domain_scores", {}),
            },
            indent=2,
        )
        gap_summary = json.dumps(
            {
                "priority_learning_areas": gap_analysis.get("priority_learning_areas", []),
                "overall_readiness_score": gap_analysis.get("overall_readiness_score"),
            },
            indent=2,
        )

        # ✅ NEW: Phase 10 Task 3.1 - Variable Mapping Validation
        # Log all variable mappings BEFORE substitution
        variable_map = {
            "course_record.skill_name": skill_name,
            "course_record.course_title": course_title,
            "course_record.course_description": description,
            "course_record.estimated_duration_minutes": estimated_minutes,
            "course_record.difficulty_level": difficulty,
            "course_record.learning_objectives": learning_objectives,
            "course_record.content_outline.sections": sections,
            "knowledge_base_context": rag_context[:1000] + "..." if len(rag_context) > 1000 else rag_context,
            "slide_count": target_slide_count,
            "assessment_results.score": assessment_results.get("score"),
            "gap_analysis.priority_learning_areas": gap_analysis.get("priority_learning_areas", []),
        }

        self._log_llm_event(
            "prompt_variable_mapping",
            {
                "event_type": "before_substitution",
                "variables": variable_map,
                "presentation_prompt_template_preview": (prompt_block[:500] + "...") if len(prompt_block) > 500 else prompt_block,
                "rag_context_available": len(rag_context) > 0,
                "rag_context_chars": len(rag_context),
            },
        )

        prompt = f"""Regenerate and improve the course outline for a personalized certification training presentation.

## Existing Recommended Course
- Title: {course_title}
- Description: {description}
- Estimated Duration (minutes): {estimated_minutes}
- Difficulty Level: {difficulty}
- Learning Objectives:
{objectives_block}

### Current Sections
{sections_block}

## Presentation Creation Prompt
{prompt_block}

## Assessment Summary
{assessment_summary}

## Gap Analysis Summary
{gap_summary}

## Reference Transcripts and Exam Guidelines
{rag_block}

## Requirements
- Produce a structured outline that directly addresses the learner's gaps.
- Return a JSON object with fields:
{{
  "course_title": "string",
  "estimated_duration_minutes": number,
  "learning_objectives": ["..."],
  "sections": [
     {{
        "section_title": "...",
        "slide_count": number,
        "learning_outcomes": ["..."],
        "content_outline": ["point1", "point2", "..."],
        "estimated_minutes": number
     }}
  ],
  "success": true
}}
- The total slide_count across all sections must equal exactly {target_slide_count}.
- Include practical examples, real-world scenarios, and hands-on activities.
- Ensure the outline flows from foundational concepts to advanced application.
- Highlight where transcripts/exam guidelines influenced the outline.
"""

        # ✅ NEW: Phase 10 Task 3.1 - Validate substitution completed
        # Check for unresolved placeholders
        # Only match {variable_name} patterns, not JSON objects like {"key": "value"}
        import re
        unresolved_placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", prompt)

        self._log_llm_event(
            "prompt_after_substitution",
            {
                "event_type": "after_substitution",
                "final_prompt_preview": prompt[:1000] + "..." if len(prompt) > 1000 else prompt,
                "prompt_length_chars": len(prompt),
                "unresolved_placeholders": unresolved_placeholders,
                "substitution_success": len(unresolved_placeholders) == 0,
                "rag_context_included": "Reference Transcripts and Exam Guidelines" in prompt and len(rag_block) > 50,
            },
        )

        if unresolved_placeholders:
            logger.warning(f"⚠️ Unresolved variables in refined outline prompt: {unresolved_placeholders}")

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
