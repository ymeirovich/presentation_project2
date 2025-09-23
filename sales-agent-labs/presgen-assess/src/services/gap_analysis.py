"""Learning gap analysis engine with confidence scoring and personalized recommendations."""

import logging
import statistics
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from uuid import uuid4

from src.knowledge.base import RAGKnowledgeBase
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class GapAnalysisEngine:
    """Engine for analyzing learning gaps and generating personalized learning paths."""

    def __init__(self):
        """Initialize gap analysis engine with knowledge base and LLM services."""
        self.knowledge_base = RAGKnowledgeBase()
        self.llm_service = LLMService()

    async def analyze_assessment_results(
        self,
        assessment_results: Dict,
        certification_profile: Dict,
        confidence_ratings: Optional[Dict] = None
    ) -> Dict:
        """Perform comprehensive gap analysis on assessment results."""
        try:
            # Extract key metrics from assessment results
            overall_score = assessment_results.get("score", 0.0)
            domain_scores = assessment_results.get("domain_scores", {})
            questions = assessment_results.get("questions", [])
            answers = assessment_results.get("answers", {})

            # Analyze confidence patterns
            confidence_analysis = self._analyze_confidence_patterns(
                questions=questions,
                answers=answers,
                confidence_ratings=confidence_ratings or {}
            )

            # Identify knowledge gaps by domain
            domain_gaps = self._identify_domain_gaps(
                domain_scores=domain_scores,
                certification_profile=certification_profile,
                questions=questions,
                answers=answers
            )

            # Calculate skill level assessments
            skill_assessments = self._assess_skill_levels(
                domain_scores=domain_scores,
                confidence_analysis=confidence_analysis,
                questions=questions
            )

            # Generate remediation recommendations
            remediation_plan = await self._generate_remediation_plan(
                domain_gaps=domain_gaps,
                skill_assessments=skill_assessments,
                certification_id=assessment_results.get("certification_profile_id"),
                overall_score=overall_score
            )

            # Calculate overall readiness score
            readiness_score = self._calculate_readiness_score(
                overall_score=overall_score,
                domain_scores=domain_scores,
                confidence_analysis=confidence_analysis
            )

            gap_analysis = {
                "analysis_id": str(uuid4()),
                "assessment_id": assessment_results.get("assessment_id"),
                "student_identifier": assessment_results.get("user_id", "anonymous"),
                "certification_target": certification_profile.get("name", "Unknown"),
                "overall_readiness_score": readiness_score,
                "confidence_analysis": confidence_analysis,
                "identified_gaps": domain_gaps,
                "skill_assessments": skill_assessments,
                "remediation_plan": remediation_plan,
                "priority_learning_areas": self._extract_priority_areas(domain_gaps),
                "estimated_preparation_time_hours": self._estimate_preparation_time(
                    domain_gaps, skill_assessments
                ),
                "recommended_study_approach": self._recommend_study_approach(
                    readiness_score, domain_gaps
                ),
                "generated_at": datetime.now().isoformat(),
                "success": True
            }

            logger.info(
                f"✅ Completed gap analysis for assessment {assessment_results.get('assessment_id')} "
                f"(readiness: {readiness_score}%, {len(domain_gaps)} gaps identified)"
            )

            return gap_analysis

        except Exception as e:
            logger.error(f"❌ Gap analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_id": None
            }

    def _analyze_confidence_patterns(
        self,
        questions: List[Dict],
        answers: Dict,
        confidence_ratings: Dict
    ) -> Dict:
        """Analyze confidence vs accuracy patterns to identify overconfidence/underconfidence."""

        confidence_accuracy_pairs = []
        overconfident_areas = []
        underconfident_areas = []

        for question in questions:
            question_id = question.get("id")
            answer = answers.get(question_id, {})
            confidence = confidence_ratings.get(question_id, 3.0)  # Default: moderate confidence

            is_correct = answer.get("is_correct", False)
            accuracy = 1.0 if is_correct else 0.0

            confidence_accuracy_pairs.append({
                "question_id": question_id,
                "domain": question.get("domain"),
                "confidence": confidence,
                "accuracy": accuracy,
                "response_time": answer.get("response_time_seconds", 0)
            })

            # Identify overconfidence (high confidence, wrong answer)
            if confidence >= 4.0 and not is_correct:
                overconfident_areas.append({
                    "domain": question.get("domain"),
                    "subdomain": question.get("subdomain"),
                    "question_id": question_id,
                    "confidence": confidence
                })

            # Identify underconfidence (low confidence, correct answer)
            if confidence <= 2.0 and is_correct:
                underconfident_areas.append({
                    "domain": question.get("domain"),
                    "subdomain": question.get("subdomain"),
                    "question_id": question_id,
                    "confidence": confidence
                })

        # Calculate overall confidence metrics
        confidences = [pair["confidence"] for pair in confidence_accuracy_pairs]
        accuracies = [pair["accuracy"] for pair in confidence_accuracy_pairs]

        avg_confidence = statistics.mean(confidences) if confidences else 3.0
        avg_accuracy = statistics.mean(accuracies) if accuracies else 0.0

        # Calculate confidence-accuracy correlation
        if len(confidences) > 1:
            correlation = self._calculate_correlation(confidences, accuracies)
        else:
            correlation = 0.0

        return {
            "average_confidence": round(avg_confidence, 2),
            "average_accuracy": round(avg_accuracy, 2),
            "confidence_accuracy_correlation": round(correlation, 3),
            "confidence_accuracy_ratio": round(avg_confidence / 5.0 / max(avg_accuracy, 0.1), 2),
            "overconfident_areas": overconfident_areas,
            "underconfident_areas": underconfident_areas,
            "confidence_distribution": self._calculate_confidence_distribution(confidences),
            "calibration_quality": self._assess_calibration_quality(correlation, avg_confidence, avg_accuracy)
        }

    def _identify_domain_gaps(
        self,
        domain_scores: Dict,
        certification_profile: Dict,
        questions: List[Dict],
        answers: Dict
    ) -> List[Dict]:
        """Identify specific learning gaps by domain and subdomain."""

        gaps = []
        exam_domains = certification_profile.get("exam_domains", [])
        passing_threshold = certification_profile.get("passing_score", 70) / 100.0

        for domain_info in exam_domains:
            domain_name = domain_info["name"]
            domain_weight = domain_info["weight_percentage"]
            domain_score = domain_scores.get(domain_name, 0.0) / 100.0

            if domain_score < passing_threshold:
                # Analyze subdomain performance
                subdomain_analysis = self._analyze_subdomain_performance(
                    domain_name, questions, answers
                )

                gap_severity = self._calculate_gap_severity(
                    domain_score, passing_threshold, domain_weight
                )

                gap = {
                    "gap_id": str(uuid4()),
                    "domain": domain_name,
                    "domain_weight_percentage": domain_weight,
                    "current_score": round(domain_score, 3),
                    "target_score": passing_threshold,
                    "gap_severity": gap_severity,
                    "subdomain_breakdown": subdomain_analysis,
                    "gap_type": self._classify_gap_type(domain_score, subdomain_analysis),
                    "evidence_sources": self._extract_evidence_sources(domain_name, questions),
                    "remediation_priority": self._calculate_remediation_priority(
                        gap_severity, domain_weight, domain_score
                    )
                }

                gaps.append(gap)

        # Sort gaps by remediation priority
        gaps.sort(key=lambda x: x["remediation_priority"], reverse=True)

        return gaps

    def _analyze_subdomain_performance(
        self,
        domain_name: str,
        questions: List[Dict],
        answers: Dict
    ) -> Dict:
        """Analyze performance within subdomains of a domain."""

        subdomain_performance = {}

        for question in questions:
            if question.get("domain") == domain_name:
                subdomain = question.get("subdomain", "General")
                question_id = question.get("id")
                answer = answers.get(question_id, {})
                is_correct = answer.get("is_correct", False)

                if subdomain not in subdomain_performance:
                    subdomain_performance[subdomain] = {
                        "correct": 0,
                        "total": 0,
                        "question_ids": []
                    }

                subdomain_performance[subdomain]["total"] += 1
                subdomain_performance[subdomain]["question_ids"].append(question_id)

                if is_correct:
                    subdomain_performance[subdomain]["correct"] += 1

        # Calculate scores for each subdomain
        for subdomain, data in subdomain_performance.items():
            score = data["correct"] / data["total"] if data["total"] > 0 else 0.0
            data["score"] = round(score, 3)

        return subdomain_performance

    def _assess_skill_levels(
        self,
        domain_scores: Dict,
        confidence_analysis: Dict,
        questions: List[Dict]
    ) -> List[Dict]:
        """Assess current skill levels across different domains."""

        skill_assessments = []

        for domain, score in domain_scores.items():
            # Determine current skill level based on score
            if score >= 90:
                current_level = "expert"
            elif score >= 80:
                current_level = "advanced"
            elif score >= 70:
                current_level = "intermediate"
            elif score >= 50:
                current_level = "beginner"
            else:
                current_level = "novice"

            # Determine target level (aim for at least intermediate, preferably advanced)
            target_level = "advanced" if score < 85 else "expert"

            # Calculate gap severity
            level_order = ["novice", "beginner", "intermediate", "advanced", "expert"]
            current_index = level_order.index(current_level)
            target_index = level_order.index(target_level)
            gap_severity = max(0.0, (target_index - current_index) / len(level_order))

            # Find evidence from questions
            domain_questions = [q for q in questions if q.get("domain") == domain]
            evidence_sources = [q.get("id") for q in domain_questions]

            skill_assessment = {
                "skill_name": domain,
                "domain": domain,
                "current_level": current_level,
                "target_level": target_level,
                "current_score": score,
                "gap_severity": round(gap_severity, 3),
                "evidence_sources": evidence_sources,
                "improvement_actions": self._generate_improvement_actions(
                    domain, current_level, target_level
                ),
                "estimated_improvement_time_hours": self._estimate_improvement_time(
                    current_level, target_level, len(domain_questions)
                )
            }

            skill_assessments.append(skill_assessment)

        return skill_assessments

    async def _generate_remediation_plan(
        self,
        domain_gaps: List[Dict],
        skill_assessments: List[Dict],
        certification_id: str,
        overall_score: float
    ) -> Dict:
        """Generate personalized remediation plan with RAG-enhanced recommendations."""

        try:
            # Extract priority areas
            priority_areas = [gap["domain"] for gap in domain_gaps[:3]]  # Top 3 gaps

            # Get RAG context for remediation recommendations
            rag_context = ""
            citations = []
            if certification_id and priority_areas:
                context_query = f"study materials and learning resources for {', '.join(priority_areas)}"
                context_result = await self.knowledge_base.retrieve_context_for_assessment(
                    query=context_query,
                    certification_id=certification_id,
                    k=6,
                    balance_sources=True
                )
                rag_context = context_result.get("combined_context", "")
                citations = context_result.get("citations", [])

            # Generate remediation actions for each gap
            remediation_actions = []
            total_estimated_hours = 0

            for gap in domain_gaps:
                actions = self._create_remediation_actions(gap, rag_context)
                remediation_actions.extend(actions)
                total_estimated_hours += sum(action.get("estimated_duration_hours", 2) for action in actions)

            # Create personalized learning path
            learning_path = {
                "student_id": "current_user",  # Will be replaced with actual user ID
                "certification_target": certification_id,
                "total_estimated_hours": total_estimated_hours,
                "recommended_study_schedule": self._recommend_study_schedule(total_estimated_hours),
                "remediation_actions": remediation_actions,
                "milestones": self._create_learning_milestones(domain_gaps, skill_assessments),
                "rag_sources_consulted": citations,
                "created_at": datetime.now().isoformat()
            }

            return {
                "personalized_learning_path": learning_path,
                "priority_actions": remediation_actions[:5],  # Top 5 actions
                "study_schedule_recommendation": self._create_study_schedule(
                    total_estimated_hours, len(remediation_actions)
                ),
                "success_metrics": self._define_success_metrics(domain_gaps),
                "rag_enhanced": bool(rag_context)
            }

        except Exception as e:
            logger.error(f"❌ Failed to generate remediation plan: {e}")
            return {
                "personalized_learning_path": None,
                "error": str(e),
                "rag_enhanced": False
            }

    def _create_remediation_actions(self, gap: Dict, rag_context: str) -> List[Dict]:
        """Create specific remediation actions for a learning gap."""

        domain = gap["domain"]
        gap_severity = gap["gap_severity"]
        subdomain_breakdown = gap.get("subdomain_breakdown", {})

        actions = []

        # High-priority action for the main domain
        main_action = {
            "action_id": str(uuid4()),
            "action_type": "study",
            "domain": domain,
            "description": f"Comprehensive study of {domain} fundamentals and advanced concepts",
            "estimated_duration_hours": max(2, int(gap_severity * 8)),
            "priority": min(5, int(gap_severity * 5) + 1),
            "resources": self._extract_study_resources(domain, rag_context),
            "success_criteria": [
                f"Achieve 80%+ score on {domain} practice questions",
                f"Complete hands-on exercises for {domain}",
                "Demonstrate practical application of concepts"
            ]
        }
        actions.append(main_action)

        # Subdomain-specific actions
        for subdomain, data in subdomain_breakdown.items():
            if data.get("score", 1.0) < 0.7:  # Focus on weak subdomains
                subdomain_action = {
                    "action_id": str(uuid4()),
                    "action_type": "practice",
                    "domain": domain,
                    "subdomain": subdomain,
                    "description": f"Focused practice on {subdomain} within {domain}",
                    "estimated_duration_hours": 1,
                    "priority": 3,
                    "resources": [f"Practice questions for {subdomain}"],
                    "success_criteria": [f"Achieve 80%+ on {subdomain} questions"]
                }
                actions.append(subdomain_action)

        return actions

    def _calculate_readiness_score(
        self,
        overall_score: float,
        domain_scores: Dict,
        confidence_analysis: Dict
    ) -> float:
        """Calculate overall exam readiness score."""

        # Base score from assessment performance
        base_score = overall_score

        # Adjust for domain consistency
        domain_values = list(domain_scores.values())
        if domain_values:
            domain_std = statistics.stdev(domain_values) if len(domain_values) > 1 else 0
            consistency_penalty = min(10, domain_std / 2)  # Penalize inconsistent performance
            base_score -= consistency_penalty

        # Adjust for confidence calibration
        calibration_quality = confidence_analysis.get("calibration_quality", "poor")
        calibration_bonus = {
            "excellent": 5,
            "good": 2,
            "fair": 0,
            "poor": -3
        }.get(calibration_quality, 0)

        base_score += calibration_bonus

        # Ensure score is within bounds
        readiness_score = max(0, min(100, base_score))

        return round(readiness_score, 1)

    def _extract_priority_areas(self, domain_gaps: List[Dict]) -> List[str]:
        """Extract priority learning areas from identified gaps."""
        return [gap["domain"] for gap in domain_gaps[:5]]  # Top 5 priority areas

    def _estimate_preparation_time(
        self,
        domain_gaps: List[Dict],
        skill_assessments: List[Dict]
    ) -> int:
        """Estimate total preparation time needed in hours."""

        total_hours = 0

        # Base time from domain gaps
        for gap in domain_gaps:
            gap_severity = gap["gap_severity"]
            domain_weight = gap["domain_weight_percentage"]
            hours_for_gap = int(gap_severity * domain_weight * 0.5)  # 0.5 hours per severity-weight point
            total_hours += hours_for_gap

        # Additional time from skill assessments
        for assessment in skill_assessments:
            improvement_time = assessment.get("estimated_improvement_time_hours", 0)
            total_hours += improvement_time

        # Add buffer time (20% additional)
        total_hours = int(total_hours * 1.2)

        return max(10, min(200, total_hours))  # Between 10-200 hours

    def _recommend_study_approach(self, readiness_score: float, domain_gaps: List[Dict]) -> str:
        """Recommend overall study approach based on analysis."""

        if readiness_score >= 85:
            return "maintenance"
        elif readiness_score >= 70:
            return "targeted"
        else:
            return "comprehensive"

    # Helper methods
    def _calculate_correlation(self, list1: List[float], list2: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(list1) != len(list2) or len(list1) < 2:
            return 0.0

        mean1 = statistics.mean(list1)
        mean2 = statistics.mean(list2)

        numerator = sum((x - mean1) * (y - mean2) for x, y in zip(list1, list2))
        sum_sq1 = sum((x - mean1) ** 2 for x in list1)
        sum_sq2 = sum((y - mean2) ** 2 for y in list2)

        denominator = (sum_sq1 * sum_sq2) ** 0.5

        return numerator / denominator if denominator != 0 else 0.0

    def _calculate_gap_severity(self, current_score: float, target_score: float, domain_weight: float) -> float:
        """Calculate gap severity considering score difference and domain importance."""
        score_gap = max(0, target_score - current_score)
        weight_factor = domain_weight / 100.0
        severity = score_gap * weight_factor * 2  # Scale to 0-2 range
        return round(min(1.0, severity), 3)

    def _classify_gap_type(self, domain_score: float, subdomain_analysis: Dict) -> str:
        """Classify the type of learning gap."""
        if domain_score < 0.3:
            return "fundamental"
        elif domain_score < 0.6:
            return "conceptual"
        else:
            return "application"

    def _extract_evidence_sources(self, domain_name: str, questions: List[Dict]) -> List[str]:
        """Extract question IDs that serve as evidence for the gap."""
        return [q.get("id") for q in questions if q.get("domain") == domain_name]

    def _calculate_remediation_priority(self, gap_severity: float, domain_weight: float, domain_score: float) -> int:
        """Calculate remediation priority (1-5 scale)."""
        priority_score = (gap_severity * 2) + (domain_weight / 25) + ((1 - domain_score) * 2)
        return min(5, max(1, round(priority_score)))

    def _calculate_confidence_distribution(self, confidences: List[float]) -> Dict:
        """Calculate distribution of confidence ratings."""
        if not confidences:
            return {}

        bins = {"very_low": 0, "low": 0, "medium": 0, "high": 0, "very_high": 0}
        for conf in confidences:
            if conf <= 1.5:
                bins["very_low"] += 1
            elif conf <= 2.5:
                bins["low"] += 1
            elif conf <= 3.5:
                bins["medium"] += 1
            elif conf <= 4.5:
                bins["high"] += 1
            else:
                bins["very_high"] += 1

        total = len(confidences)
        return {k: round(v / total, 2) for k, v in bins.items()}

    def _assess_calibration_quality(self, correlation: float, avg_confidence: float, avg_accuracy: float) -> str:
        """Assess confidence calibration quality."""
        if correlation > 0.7 and abs(avg_confidence / 5.0 - avg_accuracy) < 0.2:
            return "excellent"
        elif correlation > 0.5 and abs(avg_confidence / 5.0 - avg_accuracy) < 0.3:
            return "good"
        elif correlation > 0.2:
            return "fair"
        else:
            return "poor"

    def _generate_improvement_actions(self, domain: str, current_level: str, target_level: str) -> List[str]:
        """Generate specific improvement actions for skill level advancement."""
        return [
            f"Complete advanced practice questions in {domain}",
            f"Study real-world case studies for {domain}",
            f"Hands-on practice with {domain} tools and scenarios"
        ]

    def _estimate_improvement_time(self, current_level: str, target_level: str, question_count: int) -> int:
        """Estimate time needed for skill level improvement."""
        level_gaps = {
            ("novice", "beginner"): 8,
            ("beginner", "intermediate"): 12,
            ("intermediate", "advanced"): 16,
            ("advanced", "expert"): 20
        }

        level_order = ["novice", "beginner", "intermediate", "advanced", "expert"]
        current_idx = level_order.index(current_level)
        target_idx = level_order.index(target_level)

        total_hours = 0
        for i in range(current_idx, target_idx):
            gap_key = (level_order[i], level_order[i + 1])
            total_hours += level_gaps.get(gap_key, 10)

        # Adjust based on question coverage
        coverage_factor = min(2.0, question_count / 5)
        return int(total_hours * coverage_factor)

    def _extract_study_resources(self, domain: str, rag_context: str) -> List[str]:
        """Extract relevant study resources from RAG context."""
        # This would be enhanced with actual RAG content parsing
        return [
            f"Official documentation for {domain}",
            f"Hands-on labs and exercises",
            f"Practice tests and assessments"
        ]

    def _recommend_study_schedule(self, total_hours: int) -> str:
        """Recommend study schedule intensity."""
        if total_hours <= 20:
            return "relaxed"
        elif total_hours <= 50:
            return "moderate"
        else:
            return "intensive"

    def _create_learning_milestones(self, domain_gaps: List[Dict], skill_assessments: List[Dict]) -> List[Dict]:
        """Create learning milestones for progress tracking."""
        milestones = []

        for i, gap in enumerate(domain_gaps[:3]):  # Top 3 gaps
            milestone = {
                "milestone_id": str(uuid4()),
                "name": f"Master {gap['domain']} Fundamentals",
                "target_score": 80,
                "estimated_completion_weeks": i + 2,
                "success_criteria": [
                    f"Score 80%+ on {gap['domain']} practice tests",
                    "Complete all recommended study materials"
                ]
            }
            milestones.append(milestone)

        return milestones

    def _create_study_schedule(self, total_hours: int, action_count: int) -> Dict:
        """Create detailed study schedule recommendation."""
        hours_per_week = min(20, max(5, total_hours / 8))  # 8-week target
        sessions_per_week = min(5, max(2, action_count))

        return {
            "total_study_hours": total_hours,
            "recommended_weeks": max(4, total_hours // int(hours_per_week)),
            "hours_per_week": round(hours_per_week, 1),
            "sessions_per_week": sessions_per_week,
            "session_duration_hours": round(hours_per_week / sessions_per_week, 1)
        }

    def _define_success_metrics(self, domain_gaps: List[Dict]) -> List[Dict]:
        """Define success metrics for tracking progress."""
        return [
            {
                "metric": "Overall Assessment Score",
                "target": "85%+",
                "current": "Baseline established"
            },
            {
                "metric": "Domain Coverage",
                "target": f"80%+ in all {len(domain_gaps)} weak domains",
                "current": "Gaps identified"
            },
            {
                "metric": "Confidence Calibration",
                "target": "Good calibration (correlation > 0.5)",
                "current": "Baseline measured"
            }
        ]