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

            # NEW: Enhanced 5-Metric Gap Analysis Engine
            skill_gap_analysis = await self._analyze_skill_gaps_five_metrics(
                questions=questions,
                answers=answers,
                domain_scores=domain_scores,
                confidence_ratings=confidence_ratings or {},
                certification_profile=certification_profile
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
                "enhanced_skill_gap_analysis": skill_gap_analysis,  # NEW: 5-metric analysis
                "remediation_plan": remediation_plan,
                "priority_learning_areas": self._extract_priority_areas(domain_gaps),
                "estimated_preparation_time_hours": self._estimate_preparation_time(
                    domain_gaps, skill_assessments
                ),
                "recommended_study_approach": self._recommend_study_approach(
                    readiness_score, domain_gaps
                ),
                "google_sheets_export_data": self._prepare_google_sheets_export(
                    skill_gap_analysis, domain_gaps, remediation_plan
                ),  # NEW: Google Sheets export preparation
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

    async def _analyze_skill_gaps_five_metrics(
        self,
        questions: List[Dict],
        answers: Dict,
        domain_scores: Dict,
        confidence_ratings: Dict,
        certification_profile: Dict
    ) -> Dict:
        """Enhanced 5-metric skill gap analysis engine."""
        try:
            # 1. Bloom's Taxonomy Depth Analysis
            bloom_analysis = self._analyze_blooms_taxonomy_performance(questions, answers)

            # 2. Learning Style & Retention Indicators
            learning_style_analysis = self._analyze_learning_style_patterns(questions, answers)

            # 4. Metacognitive Awareness Gaps
            metacognitive_analysis = self._analyze_metacognitive_awareness(
                questions, answers, confidence_ratings
            )

            # 5. Transfer Learning Assessment
            transfer_learning_analysis = self._analyze_transfer_learning_ability(
                questions, answers, domain_scores
            )

            # 8. Certification-Specific Insights
            certification_insights = self._analyze_certification_specific_readiness(
                questions, answers, certification_profile, domain_scores
            )

            return {
                "bloom_taxonomy_analysis": bloom_analysis,
                "learning_style_indicators": learning_style_analysis,
                "metacognitive_awareness": metacognitive_analysis,
                "transfer_learning_assessment": transfer_learning_analysis,
                "certification_specific_insights": certification_insights,
                "overall_skill_profile": self._synthesize_skill_profile(
                    bloom_analysis, learning_style_analysis, metacognitive_analysis,
                    transfer_learning_analysis, certification_insights
                ),
                "analyzed_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Enhanced skill gap analysis failed: {e}")
            return {
                "error": str(e),
                "success": False
            }

    def _analyze_blooms_taxonomy_performance(self, questions: List[Dict], answers: Dict) -> Dict:
        """Analyze performance across Bloom's Taxonomy cognitive levels."""
        bloom_levels = {
            "remember": {"correct": 0, "total": 0, "questions": []},
            "understand": {"correct": 0, "total": 0, "questions": []},
            "apply": {"correct": 0, "total": 0, "questions": []},
            "analyze": {"correct": 0, "total": 0, "questions": []},
            "evaluate": {"correct": 0, "total": 0, "questions": []},
            "create": {"correct": 0, "total": 0, "questions": []}
        }

        for question in questions:
            question_id = question.get("id")
            bloom_level = question.get("bloom_level", "understand").lower()
            answer = answers.get(question_id, {})
            is_correct = answer.get("is_correct", False)

            if bloom_level in bloom_levels:
                bloom_levels[bloom_level]["total"] += 1
                bloom_levels[bloom_level]["questions"].append(question_id)
                if is_correct:
                    bloom_levels[bloom_level]["correct"] += 1

        # Calculate scores and identify gaps
        bloom_scores = {}
        cognitive_gaps = []

        for level, data in bloom_levels.items():
            if data["total"] > 0:
                score = data["correct"] / data["total"]
                bloom_scores[level] = round(score, 3)

                if score < 0.7:  # Gap threshold
                    cognitive_gaps.append({
                        "bloom_level": level,
                        "score": score,
                        "gap_severity": round(0.7 - score, 3),
                        "question_count": data["total"],
                        "evidence_questions": data["questions"]
                    })

        return {
            "bloom_level_scores": bloom_scores,
            "cognitive_gaps": cognitive_gaps,
            "cognitive_depth_assessment": self._assess_cognitive_depth(bloom_scores),
            "knowledge_vs_application_ratio": self._calculate_knowledge_application_ratio(bloom_scores),
            "recommendations": self._generate_bloom_recommendations(cognitive_gaps)
        }

    def _analyze_learning_style_patterns(self, questions: List[Dict], answers: Dict) -> Dict:
        """Analyze learning style and retention patterns."""
        question_types = {
            "multiple_choice": {"correct": 0, "total": 0, "avg_time": []},
            "scenario_based": {"correct": 0, "total": 0, "avg_time": []},
            "practical": {"correct": 0, "total": 0, "avg_time": []},
            "theoretical": {"correct": 0, "total": 0, "avg_time": []}
        }

        context_switching_performance = []
        current_domain = None

        for question in questions:
            question_id = question.get("id")
            question_type = question.get("question_type", "multiple_choice")
            domain = question.get("domain")
            answer = answers.get(question_id, {})
            is_correct = answer.get("is_correct", False)
            response_time = answer.get("response_time_seconds", 0)

            # Track question type performance
            if question_type in question_types:
                question_types[question_type]["total"] += 1
                question_types[question_type]["avg_time"].append(response_time)
                if is_correct:
                    question_types[question_type]["correct"] += 1

            # Track context switching (domain changes)
            if current_domain and current_domain != domain:
                context_switching_performance.append({
                    "from_domain": current_domain,
                    "to_domain": domain,
                    "is_correct": is_correct,
                    "response_time": response_time
                })
            current_domain = domain

        # Calculate learning style indicators
        style_preferences = {}
        for style, data in question_types.items():
            if data["total"] > 0:
                accuracy = data["correct"] / data["total"]
                avg_time = statistics.mean(data["avg_time"]) if data["avg_time"] else 0
                style_preferences[style] = {
                    "accuracy": round(accuracy, 3),
                    "average_time_seconds": round(avg_time, 1),
                    "question_count": data["total"],
                    "efficiency_score": round(accuracy / max(avg_time / 60, 0.5), 3)  # accuracy per minute
                }

        return {
            "question_type_preferences": style_preferences,
            "context_switching_ability": self._analyze_context_switching(context_switching_performance),
            "learning_style_recommendations": self._recommend_learning_approaches(style_preferences),
            "retention_indicators": self._assess_retention_patterns(questions, answers)
        }

    def _analyze_metacognitive_awareness(self, questions: List[Dict], answers: Dict, confidence_ratings: Dict) -> Dict:
        """Analyze metacognitive awareness and self-assessment accuracy."""
        self_assessment_accuracy = []
        uncertainty_recognition = []
        strategy_adaptation = []

        for question in questions:
            question_id = question.get("id")
            difficulty = question.get("difficulty_level", "medium")
            answer = answers.get(question_id, {})
            confidence = confidence_ratings.get(question_id, 3.0)
            is_correct = answer.get("is_correct", False)
            response_time = answer.get("response_time_seconds", 0)

            # Self-assessment accuracy
            predicted_performance = confidence / 5.0  # Convert to 0-1 scale
            actual_performance = 1.0 if is_correct else 0.0
            accuracy_gap = abs(predicted_performance - actual_performance)

            self_assessment_accuracy.append({
                "question_id": question_id,
                "predicted": predicted_performance,
                "actual": actual_performance,
                "accuracy_gap": accuracy_gap,
                "domain": question.get("domain")
            })

            # Uncertainty recognition (appropriate low confidence on difficult questions)
            if difficulty in ["hard", "expert"] and confidence <= 2.0:
                uncertainty_recognition.append({
                    "question_id": question_id,
                    "appropriately_uncertain": True,
                    "is_correct": is_correct
                })

            # Strategy adaptation (time allocation based on difficulty)
            expected_time = {"easy": 30, "medium": 60, "hard": 120, "expert": 180}.get(difficulty, 60)
            time_ratio = response_time / expected_time
            strategy_adaptation.append({
                "question_id": question_id,
                "difficulty": difficulty,
                "time_ratio": time_ratio,
                "appropriate_time_allocation": 0.5 <= time_ratio <= 2.0
            })

        avg_self_assessment_gap = statistics.mean([item["accuracy_gap"] for item in self_assessment_accuracy])
        uncertainty_recognition_rate = len([item for item in uncertainty_recognition if item["appropriately_uncertain"]]) / max(len(uncertainty_recognition), 1)
        appropriate_time_allocation_rate = len([item for item in strategy_adaptation if item["appropriate_time_allocation"]]) / len(strategy_adaptation)

        return {
            "self_assessment_accuracy": {
                "average_gap": round(avg_self_assessment_gap, 3),
                "details": self_assessment_accuracy,
                "calibration_quality": "good" if avg_self_assessment_gap < 0.3 else "needs_improvement"
            },
            "uncertainty_recognition": {
                "recognition_rate": round(uncertainty_recognition_rate, 3),
                "quality": "good" if uncertainty_recognition_rate > 0.7 else "needs_improvement"
            },
            "strategy_adaptation": {
                "appropriate_time_allocation_rate": round(appropriate_time_allocation_rate, 3),
                "adaptation_quality": "good" if appropriate_time_allocation_rate > 0.7 else "needs_improvement"
            },
            "metacognitive_maturity_score": round((
                (1 - avg_self_assessment_gap) + uncertainty_recognition_rate + appropriate_time_allocation_rate
            ) / 3, 3)
        }

    def _analyze_transfer_learning_ability(self, questions: List[Dict], answers: Dict, domain_scores: Dict) -> Dict:
        """Analyze ability to transfer learning across domains and contexts."""
        cross_domain_connections = []
        pattern_recognition_ability = []
        conceptual_vs_procedural = {"conceptual": 0, "procedural": 0, "total": 0}

        # Group questions by concept patterns
        concept_patterns = {}
        for question in questions:
            concepts = question.get("concepts", [])
            question_id = question.get("id")
            answer = answers.get(question_id, {})
            is_correct = answer.get("is_correct", False)

            for concept in concepts:
                if concept not in concept_patterns:
                    concept_patterns[concept] = {"questions": [], "correct": 0, "total": 0}
                concept_patterns[concept]["questions"].append(question_id)
                concept_patterns[concept]["total"] += 1
                if is_correct:
                    concept_patterns[concept]["correct"] += 1

        # Analyze cross-domain performance correlation
        domains = list(domain_scores.keys())
        for i in range(len(domains)):
            for j in range(i + 1, len(domains)):
                domain1, domain2 = domains[i], domains[j]
                score1, score2 = domain_scores[domain1], domain_scores[domain2]
                correlation_strength = 1 - abs(score1 - score2) / 100  # Simple correlation measure

                cross_domain_connections.append({
                    "domain_pair": f"{domain1} <-> {domain2}",
                    "correlation_strength": round(correlation_strength, 3),
                    "transfer_potential": "high" if correlation_strength > 0.8 else "medium" if correlation_strength > 0.6 else "low"
                })

        # Analyze pattern recognition across similar concepts
        for concept, data in concept_patterns.items():
            if data["total"] > 1:  # Multiple questions on same concept
                consistency = data["correct"] / data["total"]
                pattern_recognition_ability.append({
                    "concept": concept,
                    "consistency_score": round(consistency, 3),
                    "question_count": data["total"],
                    "pattern_recognition": "strong" if consistency > 0.8 else "moderate" if consistency > 0.6 else "weak"
                })

        # Assess conceptual vs procedural knowledge
        for question in questions:
            question_type = question.get("question_type", "multiple_choice")
            knowledge_type = "conceptual" if question_type in ["scenario_based", "case_study"] else "procedural"
            conceptual_vs_procedural[knowledge_type] += 1
            conceptual_vs_procedural["total"] += 1

        return {
            "cross_domain_connections": cross_domain_connections,
            "pattern_recognition_ability": pattern_recognition_ability,
            "conceptual_vs_procedural_balance": {
                "conceptual_percentage": round(conceptual_vs_procedural["conceptual"] / max(conceptual_vs_procedural["total"], 1), 3),
                "procedural_percentage": round(conceptual_vs_procedural["procedural"] / max(conceptual_vs_procedural["total"], 1), 3),
                "balance_quality": self._assess_knowledge_balance(conceptual_vs_procedural)
            },
            "transfer_learning_score": self._calculate_transfer_learning_score(
                cross_domain_connections, pattern_recognition_ability
            )
        }

    def _analyze_certification_specific_readiness(
        self, questions: List[Dict], answers: Dict, certification_profile: Dict, domain_scores: Dict
    ) -> Dict:
        """Analyze certification-specific readiness and exam strategy."""
        exam_strategy_readiness = []
        industry_context_understanding = []
        domain_interdependency_awareness = []

        passing_score = certification_profile.get("passing_score", 70)
        exam_domains = certification_profile.get("exam_domains", [])

        # Analyze exam strategy (time management, question approach)
        total_questions = len(questions)
        total_time = sum(answers.get(q.get("id"), {}).get("response_time_seconds", 0) for q in questions)
        avg_time_per_question = total_time / max(total_questions, 1)

        # Industry context understanding (real-world scenario performance)
        scenario_questions = [q for q in questions if q.get("question_type") == "scenario_based"]
        scenario_performance = 0
        if scenario_questions:
            scenario_correct = sum(1 for q in scenario_questions if answers.get(q.get("id"), {}).get("is_correct", False))
            scenario_performance = scenario_correct / len(scenario_questions)

        # Domain interdependency analysis
        for domain_info in exam_domains:
            domain_name = domain_info["name"]
            domain_weight = domain_info["weight_percentage"]
            domain_score = domain_scores.get(domain_name, 0)

            readiness_for_domain = {
                "domain": domain_name,
                "weight": domain_weight,
                "current_score": domain_score,
                "readiness_status": "ready" if domain_score >= passing_score else "needs_improvement",
                "contribution_to_overall": (domain_score * domain_weight) / 100
            }
            domain_interdependency_awareness.append(readiness_for_domain)

        overall_weighted_score = sum(item["contribution_to_overall"] for item in domain_interdependency_awareness)

        return {
            "exam_strategy_assessment": {
                "time_management": {
                    "average_time_per_question": round(avg_time_per_question, 1),
                    "time_efficiency": "good" if 30 <= avg_time_per_question <= 120 else "needs_improvement"
                },
                "question_approach_effectiveness": self._assess_question_approach(questions, answers)
            },
            "industry_context_readiness": {
                "scenario_performance": round(scenario_performance, 3),
                "real_world_application_readiness": "strong" if scenario_performance > 0.8 else "moderate" if scenario_performance > 0.6 else "weak"
            },
            "domain_interdependency_awareness": domain_interdependency_awareness,
            "certification_readiness_score": round(overall_weighted_score, 1),
            "exam_readiness_indicators": {
                "meets_passing_threshold": overall_weighted_score >= passing_score,
                "domain_balance": self._assess_domain_balance(domain_scores),
                "confidence_in_certification": "high" if overall_weighted_score >= passing_score + 10 else "moderate"
            }
        }

    def _prepare_google_sheets_export(self, skill_gap_analysis: Dict, domain_gaps: List[Dict], remediation_plan: Dict) -> Dict:
        """Prepare data for Google Sheets export with structured format."""
        return {
            "sheet_name": "Skill_Gap_Analysis",
            "sections": {
                "summary": {
                    "title": "Gap Analysis Summary",
                    "data": [
                        ["Metric", "Score", "Status", "Recommendations"],
                        ["Bloom's Taxonomy Depth", skill_gap_analysis.get("bloom_taxonomy_analysis", {}).get("cognitive_depth_assessment", "N/A"), "Analyze", "Focus on higher-order thinking"],
                        ["Learning Style Match", skill_gap_analysis.get("learning_style_indicators", {}).get("learning_style_recommendations", "Mixed"), "Good", "Continue varied approaches"],
                        ["Metacognitive Awareness", skill_gap_analysis.get("metacognitive_awareness", {}).get("metacognitive_maturity_score", 0), "Developing", "Practice self-assessment"],
                        ["Transfer Learning", skill_gap_analysis.get("transfer_learning_assessment", {}).get("transfer_learning_score", 0), "Good", "Apply concepts across domains"],
                        ["Certification Readiness", skill_gap_analysis.get("certification_specific_insights", {}).get("certification_readiness_score", 0), "In Progress", "Continue preparation"]
                    ]
                },
                "detailed_gaps": {
                    "title": "Detailed Gap Analysis",
                    "data": [["Domain", "Current Score", "Target Score", "Gap Severity", "Priority"]] +
                            [[gap["domain"], gap["current_score"], gap["target_score"], gap["gap_severity"], gap["remediation_priority"]] for gap in domain_gaps]
                },
                "remediation_actions": {
                    "title": "Remediation Plan",
                    "data": [["Action", "Domain", "Priority", "Estimated Hours", "Success Criteria"]] +
                            [[action["description"], action["domain"], action["priority"], action["estimated_duration_hours"], "; ".join(action["success_criteria"])]
                             for action in remediation_plan.get("remediation_actions", [])]
                }
            },
            "charts": [
                {
                    "type": "radar_chart",
                    "title": "Bloom's Taxonomy Performance",
                    "data": skill_gap_analysis.get("bloom_taxonomy_analysis", {}).get("bloom_level_scores", {})
                },
                {
                    "type": "bar_chart",
                    "title": "Domain Performance vs Target",
                    "data": {gap["domain"]: {"current": gap["current_score"], "target": gap["target_score"]} for gap in domain_gaps}
                }
            ]
        }

    # Helper methods for the new functionality
    def _assess_cognitive_depth(self, bloom_scores: Dict) -> str:
        """Assess cognitive depth based on Bloom's taxonomy performance."""
        higher_order = ["analyze", "evaluate", "create"]
        lower_order = ["remember", "understand", "apply"]

        higher_avg = statistics.mean([bloom_scores.get(level, 0) for level in higher_order if level in bloom_scores])
        lower_avg = statistics.mean([bloom_scores.get(level, 0) for level in lower_order if level in bloom_scores])

        if higher_avg > 0.8:
            return "deep_understanding"
        elif higher_avg > 0.6:
            return "developing_depth"
        elif lower_avg > higher_avg:
            return "surface_knowledge"
        else:
            return "mixed_depth"

    def _calculate_knowledge_application_ratio(self, bloom_scores: Dict) -> float:
        """Calculate ratio of knowledge vs application skills."""
        knowledge_levels = ["remember", "understand"]
        application_levels = ["apply", "analyze", "evaluate", "create"]

        knowledge_avg = statistics.mean([bloom_scores.get(level, 0) for level in knowledge_levels if level in bloom_scores])
        application_avg = statistics.mean([bloom_scores.get(level, 0) for level in application_levels if level in bloom_scores])

        return round(application_avg / max(knowledge_avg, 0.1), 3)

    def _generate_bloom_recommendations(self, cognitive_gaps: List[Dict]) -> List[str]:
        """Generate recommendations based on Bloom's taxonomy gaps."""
        recommendations = []
        for gap in cognitive_gaps:
            level = gap["bloom_level"]
            if level in ["remember", "understand"]:
                recommendations.append(f"Review fundamental concepts and definitions for {level} level")
            elif level in ["apply", "analyze"]:
                recommendations.append(f"Practice hands-on exercises and case studies for {level} level")
            else:
                recommendations.append(f"Engage in creative problem-solving and evaluation tasks for {level} level")
        return recommendations

    def _analyze_context_switching(self, context_switching_data: List[Dict]) -> Dict:
        """Analyze context switching performance."""
        if not context_switching_data:
            return {"switches": 0, "average_performance": 0, "adaptation_quality": "insufficient_data"}

        correct_switches = sum(1 for switch in context_switching_data if switch["is_correct"])
        adaptation_rate = correct_switches / len(context_switching_data)

        return {
            "total_switches": len(context_switching_data),
            "successful_adaptations": correct_switches,
            "adaptation_rate": round(adaptation_rate, 3),
            "adaptation_quality": "excellent" if adaptation_rate > 0.8 else "good" if adaptation_rate > 0.6 else "needs_improvement"
        }

    def _recommend_learning_approaches(self, style_preferences: Dict) -> List[str]:
        """Recommend learning approaches based on style preferences."""
        recommendations = []
        best_style = max(style_preferences.items(), key=lambda x: x[1]["efficiency_score"]) if style_preferences else None

        if best_style:
            style_name = best_style[0]
            if style_name == "scenario_based":
                recommendations.append("Focus on case studies and real-world scenarios")
            elif style_name == "practical":
                recommendations.append("Emphasize hands-on practice and labs")
            elif style_name == "theoretical":
                recommendations.append("Study conceptual frameworks and theory")
            else:
                recommendations.append("Continue with mixed question formats")

        return recommendations

    def _assess_retention_patterns(self, questions: List[Dict], answers: Dict) -> Dict:
        """Assess information retention patterns."""
        # Simple retention assessment based on consistency within domains
        domain_consistency = {}
        for question in questions:
            domain = question.get("domain")
            question_id = question.get("id")
            is_correct = answers.get(question_id, {}).get("is_correct", False)

            if domain not in domain_consistency:
                domain_consistency[domain] = {"correct": 0, "total": 0}

            domain_consistency[domain]["total"] += 1
            if is_correct:
                domain_consistency[domain]["correct"] += 1

        avg_consistency = statistics.mean([
            data["correct"] / data["total"] for data in domain_consistency.values() if data["total"] > 0
        ]) if domain_consistency else 0

        return {
            "domain_consistency": {domain: round(data["correct"] / data["total"], 3) for domain, data in domain_consistency.items() if data["total"] > 0},
            "overall_retention_score": round(avg_consistency, 3),
            "retention_quality": "strong" if avg_consistency > 0.8 else "moderate" if avg_consistency > 0.6 else "weak"
        }

    def _assess_knowledge_balance(self, conceptual_vs_procedural: Dict) -> str:
        """Assess balance between conceptual and procedural knowledge."""
        total = conceptual_vs_procedural["total"]
        if total == 0:
            return "insufficient_data"

        conceptual_ratio = conceptual_vs_procedural["conceptual"] / total
        if 0.4 <= conceptual_ratio <= 0.6:
            return "well_balanced"
        elif conceptual_ratio > 0.6:
            return "conceptual_heavy"
        else:
            return "procedural_heavy"

    def _calculate_transfer_learning_score(self, cross_domain_connections: List[Dict], pattern_recognition: List[Dict]) -> float:
        """Calculate overall transfer learning score."""
        if not cross_domain_connections and not pattern_recognition:
            return 0.0

        domain_transfer_avg = statistics.mean([conn["correlation_strength"] for conn in cross_domain_connections]) if cross_domain_connections else 0
        pattern_recog_avg = statistics.mean([pat["consistency_score"] for pat in pattern_recognition]) if pattern_recognition else 0

        return round((domain_transfer_avg + pattern_recog_avg) / 2, 3)

    def _assess_question_approach(self, questions: List[Dict], answers: Dict) -> str:
        """Assess effectiveness of question approach strategy."""
        difficult_questions = [q for q in questions if q.get("difficulty_level") in ["hard", "expert"]]
        if not difficult_questions:
            return "insufficient_difficult_questions"

        difficult_correct = sum(1 for q in difficult_questions if answers.get(q.get("id"), {}).get("is_correct", False))
        difficult_accuracy = difficult_correct / len(difficult_questions)

        return "effective" if difficult_accuracy > 0.6 else "needs_improvement"

    def _assess_domain_balance(self, domain_scores: Dict) -> str:
        """Assess balance across certification domains."""
        if not domain_scores:
            return "no_data"

        scores = list(domain_scores.values())
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0

        if std_dev < 10:
            return "well_balanced"
        elif std_dev < 20:
            return "moderately_balanced"
        else:
            return "unbalanced"

    def _synthesize_skill_profile(self, bloom_analysis: Dict, learning_style: Dict, metacognitive: Dict, transfer_learning: Dict, certification_insights: Dict) -> Dict:
        """Synthesize overall skill profile from all analyses."""
        return {
            "overall_profile_type": self._determine_learner_profile(bloom_analysis, learning_style, metacognitive),
            "strength_areas": self._identify_strength_areas(bloom_analysis, learning_style, transfer_learning),
            "development_priorities": self._identify_development_priorities(bloom_analysis, metacognitive, certification_insights),
            "learning_recommendations": self._generate_comprehensive_recommendations(bloom_analysis, learning_style, metacognitive, transfer_learning, certification_insights)
        }

    def _determine_learner_profile(self, bloom_analysis: Dict, learning_style: Dict, metacognitive: Dict) -> str:
        """Determine overall learner profile type."""
        cognitive_depth = bloom_analysis.get("cognitive_depth_assessment", "mixed_depth")
        metacog_score = metacognitive.get("metacognitive_maturity_score", 0.5)

        if cognitive_depth == "deep_understanding" and metacog_score > 0.8:
            return "advanced_strategic_learner"
        elif cognitive_depth in ["developing_depth", "deep_understanding"] and metacog_score > 0.6:
            return "developing_strategic_learner"
        elif cognitive_depth == "surface_knowledge":
            return "knowledge_focused_learner"
        else:
            return "mixed_profile_learner"

    def _identify_strength_areas(self, bloom_analysis: Dict, learning_style: Dict, transfer_learning: Dict) -> List[str]:
        """Identify key strength areas."""
        strengths = []

        # Check Bloom's strengths
        bloom_scores = bloom_analysis.get("bloom_level_scores", {})
        for level, score in bloom_scores.items():
            if score > 0.8:
                strengths.append(f"Strong {level} skills")

        # Check learning style strengths
        style_prefs = learning_style.get("question_type_preferences", {})
        best_style = max(style_prefs.items(), key=lambda x: x[1]["accuracy"]) if style_prefs else None
        if best_style and best_style[1]["accuracy"] > 0.8:
            strengths.append(f"Excellent {best_style[0]} performance")

        # Check transfer learning
        transfer_score = transfer_learning.get("transfer_learning_score", 0)
        if transfer_score > 0.8:
            strengths.append("Strong transfer learning ability")

        return strengths if strengths else ["Foundational knowledge"]

    def _identify_development_priorities(self, bloom_analysis: Dict, metacognitive: Dict, certification_insights: Dict) -> List[str]:
        """Identify key development priorities."""
        priorities = []

        # Check cognitive gaps
        cognitive_gaps = bloom_analysis.get("cognitive_gaps", [])
        for gap in cognitive_gaps:
            if gap["gap_severity"] > 0.3:
                priorities.append(f"Develop {gap['bloom_level']} skills")

        # Check metacognitive needs
        metacog_score = metacognitive.get("metacognitive_maturity_score", 1.0)
        if metacog_score < 0.6:
            priorities.append("Improve self-assessment accuracy")

        # Check certification readiness
        cert_score = certification_insights.get("certification_readiness_score", 100)
        if cert_score < 70:
            priorities.append("Strengthen certification preparation")

        return priorities if priorities else ["Continue current progress"]

    def _generate_comprehensive_recommendations(self, bloom_analysis: Dict, learning_style: Dict, metacognitive: Dict, transfer_learning: Dict, certification_insights: Dict) -> List[str]:
        """Generate comprehensive learning recommendations."""
        recommendations = []

        # Bloom's recommendations
        recommendations.extend(bloom_analysis.get("recommendations", []))

        # Learning style recommendations
        recommendations.extend(learning_style.get("learning_style_recommendations", []))

        # Metacognitive recommendations
        metacog_score = metacognitive.get("metacognitive_maturity_score", 1.0)
        if metacog_score < 0.7:
            recommendations.append("Practice estimating your confidence before answering questions")
            recommendations.append("Review incorrect answers to improve self-assessment")

        # Transfer learning recommendations
        transfer_score = transfer_learning.get("transfer_learning_score", 1.0)
        if transfer_score < 0.7:
            recommendations.append("Practice applying concepts across different domains")
            recommendations.append("Look for patterns and connections between topics")

        # Certification-specific recommendations
        cert_readiness = certification_insights.get("exam_readiness_indicators", {})
        if not cert_readiness.get("meets_passing_threshold", True):
            recommendations.append("Focus on high-weight certification domains")
            recommendations.append("Practice with exam-format questions")

        return list(set(recommendations))  # Remove duplicates