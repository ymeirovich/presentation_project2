"""Processing and analytics utilities for Google Form assessment responses."""

from __future__ import annotations

import asyncio
import statistics
from typing import Any, Dict, List


class FormResponseProcessor:
    """Score responses, analyse trends, and generate learner feedback."""

    async def calculate_assessment_score(
        self,
        *,
        responses: List[Dict[str, Any]],
        answer_key: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        global_points_available = sum(details.get("points", 1) for details in answer_key.values()) or 1
        results: List[Dict[str, Any]] = []

        for response in responses:
            per_question_scores: Dict[str, float] = {}
            total_score = 0.0
            response_points_available = 0.0
            for question_id, metadata in answer_key.items():
                user_answer = (response.get("answers") or {}).get(question_id)
                if metadata.get("rubric") or metadata.get("correct_answer") == "scenario_rubric":
                    scenario_result = await self._score_scenario_response(
                        response=user_answer or "",
                        rubric=metadata.get("rubric", {}),
                    )
                    per_question_scores[question_id] = scenario_result["points"]
                    total_score += scenario_result["points"]
                    if user_answer:
                        response_points_available += metadata.get("points", metadata.get("max_points", 3))
                else:
                    points = metadata.get("points", 1)
                    correct_answer = str(metadata.get("correct_answer", "")).strip().lower()
                    if user_answer is not None and str(user_answer).strip().lower() == correct_answer:
                        per_question_scores[question_id] = points
                        total_score += points
                    else:
                        per_question_scores[question_id] = 0.0
                    if user_answer is not None:
                        response_points_available += points

            denominator = response_points_available or global_points_available
            percentage = round((total_score / denominator) * 100, 2) if denominator else 0.0
            results.append(
                {
                    "response_id": response.get("response_id"),
                    "respondent_email": response.get("respondent_email"),
                    "scores": per_question_scores,
                    "total_score": total_score,
                    "percentage": percentage,
                    "submitted_at": response.get("submitted_at"),
                    "completion_time_seconds": response.get("completion_time_seconds"),
                }
            )

        return {"results": results, "total_available": global_points_available}

    async def _score_scenario_response(self, *, response: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
        response_text = (response or "").lower()
        response_compact = response_text.replace("-", " ")
        keywords = [kw.lower() for kw in rubric.get("keywords", [])]
        matched = []
        for keyword in keywords:
            simplified_keyword = keyword.replace("-", " ")
            if simplified_keyword in response_compact:
                matched.append(keyword)
                continue
            parts = [part for part in simplified_keyword.split() if part]
            if parts and all(part in response_compact for part in parts):
                matched.append(keyword)

        max_points = rubric.get("max_points") or rubric.get("points", 3) or 3
        if not keywords:
            points = max_points if response_text else 0
        else:
            match_ratio = len(matched) / len(keywords)
            if rubric.get("partial_credit", True):
                points = round(max_points * match_ratio, 2)
            else:
                points = max_points if len(matched) == len(keywords) else 0

        return {"points": points, "matched_keywords": matched}

    async def analyze_response_patterns(
        self,
        *,
        responses: List[Dict[str, Any]],
        assessment_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        await asyncio.sleep(0)
        domain_map = assessment_metadata.get("domain_map", {}).copy()
        domains = assessment_metadata.get("domains", [])
        if not domain_map and responses:
            first_response = responses[0].get("answers", {})
            for index, question_id in enumerate(first_response.keys()):
                if index < len(domains):
                    domain_map[question_id] = domains[index]

        domain_stats: Dict[str, Dict[str, Any]] = {
            domain: {"attempts": 0, "correct": 0} for domain in domains
        }
        question_difficulty: Dict[str, Dict[str, Any]] = {}
        completion_times: List[int] = []
        mistake_counter: Dict[str, int] = {}

        for response in responses:
            completion = response.get("completion_time_seconds")
            if completion:
                completion_times.append(int(completion))

            for question_id, answer in (response.get("answers") or {}).items():
                domain = domain_map.get(question_id)
                expected = assessment_metadata.get("answer_key", {}).get(question_id)
                if expected is not None and answer != expected:
                    mistake_counter[question_id] = mistake_counter.get(question_id, 0) + 1

                if domain:
                    domain_entry = domain_stats.setdefault(domain, {"attempts": 0, "correct": 0})
                    domain_entry["attempts"] += 1
                    if expected is not None and answer == expected:
                        domain_entry["correct"] += 1

                difficulty = assessment_metadata.get("difficulty_levels", {}).get(question_id)
                if difficulty is not None:
                    entry = question_difficulty.setdefault(question_id, {"difficulty": difficulty, "answers": []})
                    entry["answers"].append(answer)

        domain_performance = {}
        for domain, values in domain_stats.items():
            attempts = values["attempts"] or 1
            domain_performance[domain] = {
                "attempts": attempts,
                "correct": values["correct"],
                "success_rate": round((values["correct"] / attempts) * 100, 2),
            }

        completion_summary = {}
        if completion_times:
            completion_summary = {
                "average_seconds": round(statistics.mean(completion_times), 2),
                "median_seconds": statistics.median(completion_times),
                "max_seconds": max(completion_times),
            }

        weakness_questions = sorted(mistake_counter, key=mistake_counter.get, reverse=True)
        recommendations = []
        if weakness_questions:
            recommendations.append("Review material for the most frequently missed questions")

        common_mistakes = [{"question_id": qid, "misses": mistake_counter[qid]} for qid in weakness_questions]

        return {
            "domain_performance": domain_performance,
            "question_difficulty_analysis": question_difficulty,
            "completion_time_stats": completion_summary,
            "common_mistakes": common_mistakes,
            "strengths": [domain for domain, info in domain_performance.items() if info["success_rate"] >= 80],
            "weaknesses": [domain for domain, info in domain_performance.items() if info["success_rate"] < 60],
            "recommendations": recommendations,
        }

    async def generate_feedback_report(
        self,
        *,
        user_responses: Dict[str, Any],
        assessment_data: Dict[str, Any],
        performance_analytics: Dict[str, Any],
    ) -> Dict[str, Any]:
        question_lookup = {q.get("id"): q for q in assessment_data.get("questions", [])}

        areas_for_improvement: List[str] = []
        for question_id, score in (user_responses.get("scores") or {}).items():
            if score <= 0 and question_id in question_lookup:
                explanation = question_lookup[question_id].get("explanation")
                if explanation:
                    areas_for_improvement.append(explanation)

        return {
            "overall_performance": {
                "total_score": user_responses.get("total_score", 0),
                "percentage": user_responses.get("percentage", 0),
            },
            "strengths": performance_analytics.get("strengths", []),
            "areas_for_improvement": areas_for_improvement,
            "recommendations": performance_analytics.get("recommendations", []),
        }
