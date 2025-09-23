"""Assessment generation engine with RAG context integration."""

import logging
import asyncio
from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from src.services.llm_service import LLMService
from src.knowledge.base import RAGKnowledgeBase
from src.models.certification import CertificationProfile

logger = logging.getLogger(__name__)


class AssessmentEngine:
    """Engine for generating comprehensive assessments with RAG enhancement."""

    def __init__(self):
        """Initialize assessment engine with LLM and knowledge base services."""
        self.llm_service = LLMService()
        self.knowledge_base = RAGKnowledgeBase()

    async def generate_comprehensive_assessment(
        self,
        certification_profile: CertificationProfile,
        question_count: int = 30,
        difficulty_level: str = "intermediate",
        balance_domains: bool = True,
        use_rag_context: bool = True
    ) -> Dict:
        """Generate a comprehensive assessment based on certification profile."""
        try:
            # Validate inputs
            if not 1 <= question_count <= 100:
                raise ValueError("Question count must be between 1 and 100")

            if difficulty_level not in ["beginner", "intermediate", "advanced"]:
                raise ValueError("Difficulty level must be beginner, intermediate, or advanced")

            # Calculate question distribution across domains
            domain_distribution = self._calculate_domain_distribution(
                certification_profile.exam_domains,
                question_count,
                balance_domains
            )

            # Generate questions for each domain
            all_questions = []
            generation_tasks = []

            for domain_info in certification_profile.exam_domains:
                domain_name = domain_info["name"]
                questions_for_domain = domain_distribution.get(domain_name, 0)

                if questions_for_domain > 0:
                    task = self._generate_domain_questions(
                        certification_id=str(certification_profile.id),
                        domain=domain_name,
                        question_count=questions_for_domain,
                        difficulty_level=difficulty_level,
                        use_rag_context=use_rag_context
                    )
                    generation_tasks.append(task)

            # Execute question generation in parallel
            domain_results = await asyncio.gather(*generation_tasks, return_exceptions=True)

            # Collect successful results
            for result in domain_results:
                if isinstance(result, Exception):
                    logger.error(f"❌ Domain question generation failed: {result}")
                    continue

                if result.get("success"):
                    all_questions.extend(result["questions"])

            # Shuffle questions for randomization
            import random
            random.shuffle(all_questions)

            # Calculate assessment metadata
            assessment_metadata = self._calculate_assessment_metadata(
                all_questions,
                certification_profile,
                difficulty_level
            )

            logger.info(
                f"✅ Generated assessment with {len(all_questions)} questions "
                f"for {certification_profile.name} v{certification_profile.version}"
            )

            return {
                "success": True,
                "assessment_id": str(uuid4()),
                "certification_profile_id": str(certification_profile.id),
                "questions": all_questions,
                "metadata": assessment_metadata,
                "domain_distribution": domain_distribution,
                "generation_timestamp": datetime.now().isoformat(),
                "rag_context_used": use_rag_context
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate comprehensive assessment: {e}")
            return {
                "success": False,
                "error": str(e),
                "assessment_id": None,
                "questions": []
            }

    async def _generate_domain_questions(
        self,
        certification_id: str,
        domain: str,
        question_count: int,
        difficulty_level: str,
        use_rag_context: bool
    ) -> Dict:
        """Generate questions for a specific domain."""

        # Determine question type distribution
        question_types = self._get_question_type_distribution(question_count)

        result = await self.llm_service.generate_assessment_questions(
            certification_id=certification_id,
            domain=domain,
            question_count=question_count,
            difficulty_level=difficulty_level,
            question_types=list(question_types.keys()),
            use_rag_context=use_rag_context
        )

        # Add domain-specific metadata to questions
        if result.get("success"):
            for question in result["questions"]:
                question["id"] = f"{domain.lower().replace(' ', '_')}_{uuid4().hex[:8]}"
                question["generated_at"] = datetime.now().isoformat()

        return result

    def _calculate_domain_distribution(
        self,
        exam_domains: List[Dict],
        total_questions: int,
        balance_domains: bool
    ) -> Dict[str, int]:
        """Calculate how many questions to generate for each domain."""

        if balance_domains:
            # Distribute based on domain weight percentages
            distribution = {}
            for domain_info in exam_domains:
                domain_name = domain_info["name"]
                weight_percentage = domain_info["weight_percentage"]
                questions_for_domain = max(1, round((weight_percentage / 100) * total_questions))
                distribution[domain_name] = questions_for_domain

            # Adjust for rounding errors
            total_allocated = sum(distribution.values())
            if total_allocated != total_questions:
                # Add/remove questions from the largest domain
                largest_domain = max(distribution.keys(), key=lambda k: distribution[k])
                distribution[largest_domain] += (total_questions - total_allocated)

            return distribution
        else:
            # Equal distribution across domains
            questions_per_domain = total_questions // len(exam_domains)
            remainder = total_questions % len(exam_domains)

            distribution = {}
            for i, domain_info in enumerate(exam_domains):
                domain_name = domain_info["name"]
                questions_for_domain = questions_per_domain
                if i < remainder:
                    questions_for_domain += 1
                distribution[domain_name] = questions_for_domain

            return distribution

    def _get_question_type_distribution(self, question_count: int) -> Dict[str, int]:
        """Determine distribution of question types for a domain."""

        # Standard distribution: 70% multiple choice, 20% scenario, 10% true/false
        distributions = {
            "multiple_choice": max(1, round(0.7 * question_count)),
            "scenario": max(0, round(0.2 * question_count)),
            "true_false": max(0, round(0.1 * question_count))
        }

        # Adjust for small question counts
        if question_count <= 3:
            distributions = {"multiple_choice": question_count}
        elif question_count <= 5:
            distributions = {
                "multiple_choice": question_count - 1,
                "scenario": 1
            }

        return distributions

    def _calculate_assessment_metadata(
        self,
        questions: List[Dict],
        certification_profile: CertificationProfile,
        difficulty_level: str
    ) -> Dict:
        """Calculate assessment metadata and statistics."""

        # Calculate time estimates
        total_time_seconds = sum(q.get("time_limit_seconds", 120) for q in questions)

        # Analyze question distribution
        domain_counts = {}
        bloom_levels = {}
        question_types = {}

        for question in questions:
            # Domain distribution
            domain = question.get("domain", "Unknown")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

            # Bloom's taxonomy distribution
            bloom_level = question.get("bloom_level", "apply")
            bloom_levels[bloom_level] = bloom_levels.get(bloom_level, 0) + 1

            # Question type distribution
            question_type = question.get("question_type", "multiple_choice")
            question_types[question_type] = question_types.get(question_type, 0) + 1

        # Calculate difficulty statistics
        difficulties = [q.get("difficulty", 0.5) for q in questions]
        avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0.5

        return {
            "total_questions": len(questions),
            "estimated_duration_minutes": round(total_time_seconds / 60),
            "average_difficulty": round(avg_difficulty, 2),
            "difficulty_level": difficulty_level,
            "domain_distribution": domain_counts,
            "bloom_taxonomy_distribution": bloom_levels,
            "question_type_distribution": question_types,
            "certification_name": certification_profile.name,
            "certification_version": certification_profile.version,
            "passing_score": certification_profile.passing_score or 70,
            "exam_domains": [d["name"] for d in certification_profile.exam_domains]
        }

    async def generate_adaptive_assessment(
        self,
        certification_profile: CertificationProfile,
        user_skill_level: str = "unknown",
        focus_domains: List[str] = None,
        question_count: int = 20
    ) -> Dict:
        """Generate an adaptive assessment based on user skill level and focus areas."""
        try:
            # Determine difficulty progression
            if user_skill_level == "beginner":
                difficulty_levels = ["beginner"] * question_count
            elif user_skill_level == "advanced":
                difficulty_levels = ["intermediate", "advanced"] * (question_count // 2)
                if question_count % 2:
                    difficulty_levels.append("advanced")
            else:  # unknown or intermediate
                # Progressive difficulty: start easy, increase complexity
                easy_count = question_count // 3
                medium_count = question_count // 3
                hard_count = question_count - easy_count - medium_count

                difficulty_levels = (
                    ["beginner"] * easy_count +
                    ["intermediate"] * medium_count +
                    ["advanced"] * hard_count
                )

            # Focus on specific domains if requested
            if focus_domains:
                target_domains = [d for d in certification_profile.exam_domains
                               if d["name"] in focus_domains]
            else:
                target_domains = certification_profile.exam_domains

            # Generate questions with adaptive difficulty
            adaptive_questions = []
            for i, difficulty in enumerate(difficulty_levels):
                # Select domain (round-robin through target domains)
                domain_info = target_domains[i % len(target_domains)]
                domain_name = domain_info["name"]

                result = await self.llm_service.generate_assessment_questions(
                    certification_id=str(certification_profile.id),
                    domain=domain_name,
                    question_count=1,
                    difficulty_level=difficulty,
                    question_types=["multiple_choice", "scenario"],
                    use_rag_context=True
                )

                if result.get("success") and result["questions"]:
                    question = result["questions"][0]
                    question["adaptive_position"] = i + 1
                    question["adaptive_difficulty"] = difficulty
                    adaptive_questions.append(question)

            logger.info(
                f"✅ Generated adaptive assessment with {len(adaptive_questions)} questions "
                f"for skill level: {user_skill_level}"
            )

            return {
                "success": True,
                "assessment_id": str(uuid4()),
                "assessment_type": "adaptive",
                "user_skill_level": user_skill_level,
                "focus_domains": focus_domains or [],
                "questions": adaptive_questions,
                "difficulty_progression": difficulty_levels,
                "generation_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate adaptive assessment: {e}")
            return {
                "success": False,
                "error": str(e),
                "assessment_id": None,
                "questions": []
            }

    async def validate_assessment_quality(self, assessment_data: Dict) -> Dict:
        """Validate the quality of a generated assessment."""
        try:
            questions = assessment_data.get("questions", [])
            if not questions:
                return {
                    "valid": False,
                    "issues": ["No questions found in assessment"],
                    "quality_score": 0.0
                }

            issues = []
            warnings = []

            # Check question count
            if len(questions) < 5:
                warnings.append("Assessment has fewer than 5 questions")
            elif len(questions) > 100:
                issues.append("Assessment exceeds maximum of 100 questions")

            # Check question quality
            for i, question in enumerate(questions):
                question_issues = self._validate_question_quality(question, i + 1)
                issues.extend(question_issues)

            # Check domain coverage
            domains = set(q.get("domain") for q in questions)
            expected_domains = set(d["name"] for d in assessment_data.get("metadata", {}).get("exam_domains", []))

            if len(domains) < len(expected_domains) * 0.8:
                warnings.append("Assessment may not cover all required domains adequately")

            # Calculate quality score
            total_checks = len(questions) * 5 + 3  # 5 checks per question + 3 overall checks
            quality_score = max(0.0, 1.0 - (len(issues) * 0.1 + len(warnings) * 0.05))

            return {
                "valid": len(issues) == 0,
                "quality_score": round(quality_score, 2),
                "issues": issues,
                "warnings": warnings,
                "question_count": len(questions),
                "domain_coverage": len(domains)
            }

        except Exception as e:
            logger.error(f"❌ Assessment validation failed: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "quality_score": 0.0
            }

    def _validate_question_quality(self, question: Dict, question_num: int) -> List[str]:
        """Validate individual question quality."""
        issues = []

        # Required fields
        required_fields = ["question_text", "question_type", "correct_answer", "explanation"]
        for field in required_fields:
            if not question.get(field):
                issues.append(f"Question {question_num}: Missing {field}")

        # Question text length
        question_text = question.get("question_text", "")
        if len(question_text) < 20:
            issues.append(f"Question {question_num}: Question text too short")
        elif len(question_text) > 500:
            issues.append(f"Question {question_num}: Question text too long")

        # Multiple choice validation
        if question.get("question_type") == "multiple_choice":
            options = question.get("options", [])
            if len(options) != 4:
                issues.append(f"Question {question_num}: Multiple choice must have exactly 4 options")

            correct_answer = question.get("correct_answer")
            if correct_answer not in ["A", "B", "C", "D"]:
                issues.append(f"Question {question_num}: Invalid correct answer format")

        # Explanation quality
        explanation = question.get("explanation", "")
        if len(explanation) < 50:
            issues.append(f"Question {question_num}: Explanation too brief")

        return issues

    async def get_engine_stats(self) -> Dict:
        """Get assessment engine statistics."""
        llm_stats = await self.llm_service.get_usage_stats()

        return {
            "service_status": "active",
            "llm_integration": llm_stats,
            "supported_question_types": ["multiple_choice", "true_false", "scenario"],
            "supported_difficulty_levels": ["beginner", "intermediate", "advanced"],
            "max_questions_per_assessment": 100,
            "adaptive_assessment_supported": True
        }