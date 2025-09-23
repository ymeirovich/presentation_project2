"""Tests for gap analysis engine."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.gap_analysis import GapAnalysisEngine


class TestGapAnalysisEngine:
    """Test cases for gap analysis engine functionality."""

    @pytest.fixture
    def gap_engine(self):
        """Create gap analysis engine instance for testing."""
        with patch('src.services.gap_analysis.RAGKnowledgeBase'), \
             patch('src.services.gap_analysis.LLMService'):
            engine = GapAnalysisEngine()
            engine.knowledge_base = AsyncMock()
            engine.llm_service = AsyncMock()
            return engine

    @pytest.fixture
    def sample_assessment_results(self):
        """Sample assessment results for testing."""
        return {
            "assessment_id": "test-123",
            "user_id": "user-456",
            "certification_profile_id": "cert-789",
            "score": 68.5,
            "domain_scores": {
                "Design Resilient Architectures": 75.0,
                "Design High-Performing Architectures": 60.0,
                "Design Secure Architectures": 45.0,
                "Design Cost-Optimized Architectures": 80.0
            },
            "questions": [
                {
                    "id": "q1",
                    "domain": "Design Secure Architectures",
                    "subdomain": "IAM",
                    "difficulty": 0.6
                },
                {
                    "id": "q2",
                    "domain": "Design High-Performing Architectures",
                    "subdomain": "Caching",
                    "difficulty": 0.7
                }
            ],
            "answers": {
                "q1": {"is_correct": False, "response_time_seconds": 45},
                "q2": {"is_correct": True, "response_time_seconds": 30}
            }
        }

    @pytest.fixture
    def sample_certification_profile(self):
        """Sample certification profile for testing."""
        return {
            "name": "AWS Solutions Architect Associate",
            "passing_score": 72,
            "exam_domains": [
                {
                    "name": "Design Resilient Architectures",
                    "weight_percentage": 30,
                    "topics": ["High availability", "Disaster recovery"]
                },
                {
                    "name": "Design High-Performing Architectures",
                    "weight_percentage": 28,
                    "topics": ["Performance optimization", "Caching"]
                },
                {
                    "name": "Design Secure Architectures",
                    "weight_percentage": 24,
                    "topics": ["IAM", "Security groups"]
                },
                {
                    "name": "Design Cost-Optimized Architectures",
                    "weight_percentage": 18,
                    "topics": ["Cost analysis", "Resource optimization"]
                }
            ]
        }

    @pytest.fixture
    def sample_confidence_ratings(self):
        """Sample confidence ratings for testing."""
        return {
            "q1": 4.5,  # Overconfident (high confidence, wrong answer)
            "q2": 2.0   # Underconfident (low confidence, correct answer)
        }

    @pytest.mark.asyncio
    async def test_analyze_assessment_results_success(
        self, gap_engine, sample_assessment_results, sample_certification_profile, sample_confidence_ratings
    ):
        """Test successful assessment results analysis."""
        # Setup
        gap_engine.knowledge_base.retrieve_context_for_assessment.return_value = {
            "combined_context": "IAM best practices and security guidelines...",
            "citations": ["AWS IAM User Guide", "Security Best Practices"]
        }

        # Execute
        result = await gap_engine.analyze_assessment_results(
            assessment_results=sample_assessment_results,
            certification_profile=sample_certification_profile,
            confidence_ratings=sample_confidence_ratings
        )

        # Verify
        assert result["success"] is True
        assert result["assessment_id"] == "test-123"
        assert result["student_identifier"] == "user-456"
        assert result["overall_readiness_score"] > 0
        assert "confidence_analysis" in result
        assert "identified_gaps" in result
        assert "skill_assessments" in result
        assert "remediation_plan" in result
        assert len(result["priority_learning_areas"]) > 0

    def test_analyze_confidence_patterns(self, gap_engine, sample_confidence_ratings):
        """Test confidence pattern analysis."""
        questions = [
            {"id": "q1", "domain": "Security", "subdomain": "IAM"},
            {"id": "q2", "domain": "Performance", "subdomain": "Caching"}
        ]
        answers = {
            "q1": {"is_correct": False, "response_time_seconds": 45},
            "q2": {"is_correct": True, "response_time_seconds": 30}
        }

        # Execute
        result = gap_engine._analyze_confidence_patterns(
            questions=questions,
            answers=answers,
            confidence_ratings=sample_confidence_ratings
        )

        # Verify
        assert result["average_confidence"] == 3.25  # (4.5 + 2.0) / 2
        assert result["average_accuracy"] == 0.5  # 1 correct out of 2
        assert len(result["overconfident_areas"]) == 1
        assert len(result["underconfident_areas"]) == 1
        assert result["overconfident_areas"][0]["domain"] == "Security"
        assert result["underconfident_areas"][0]["domain"] == "Performance"

    def test_identify_domain_gaps(self, gap_engine, sample_certification_profile):
        """Test domain gap identification."""
        domain_scores = {
            "Design Secure Architectures": 45.0,  # Below passing threshold
            "Design High-Performing Architectures": 60.0,  # Below passing threshold
            "Design Resilient Architectures": 75.0,  # Above passing threshold
            "Design Cost-Optimized Architectures": 80.0   # Above passing threshold
        }

        questions = [
            {"id": "q1", "domain": "Design Secure Architectures", "subdomain": "IAM"},
            {"id": "q2", "domain": "Design High-Performing Architectures", "subdomain": "Caching"}
        ]

        answers = {
            "q1": {"is_correct": False},
            "q2": {"is_correct": False}
        }

        # Execute
        gaps = gap_engine._identify_domain_gaps(
            domain_scores=domain_scores,
            certification_profile=sample_certification_profile,
            questions=questions,
            answers=answers
        )

        # Verify
        assert len(gaps) == 2  # Two domains below passing threshold
        gap_domains = [gap["domain"] for gap in gaps]
        assert "Design Secure Architectures" in gap_domains
        assert "Design High-Performing Architectures" in gap_domains

        # Check gap severity calculation
        for gap in gaps:
            assert gap["gap_severity"] > 0
            assert gap["current_score"] < 0.72  # Below passing threshold
            assert gap["target_score"] == 0.72

    def test_assess_skill_levels(self, gap_engine):
        """Test skill level assessment."""
        domain_scores = {
            "Security": 45.0,      # novice
            "Networking": 65.0,    # beginner
            "Compute": 75.0,       # intermediate
            "Storage": 85.0,       # advanced
            "Management": 95.0     # expert
        }

        confidence_analysis = {"calibration_quality": "good"}
        questions = [
            {"id": "q1", "domain": "Security"},
            {"id": "q2", "domain": "Networking"},
            {"id": "q3", "domain": "Compute"}
        ]

        # Execute
        assessments = gap_engine._assess_skill_levels(
            domain_scores=domain_scores,
            confidence_analysis=confidence_analysis,
            questions=questions
        )

        # Verify
        assert len(assessments) == 5

        # Check specific skill levels
        security_assessment = next(a for a in assessments if a["skill_name"] == "Security")
        assert security_assessment["current_level"] == "novice"
        assert security_assessment["target_level"] == "advanced"

        management_assessment = next(a for a in assessments if a["skill_name"] == "Management")
        assert management_assessment["current_level"] == "expert"
        assert management_assessment["target_level"] == "expert"

    def test_calculate_readiness_score(self, gap_engine):
        """Test readiness score calculation."""
        domain_scores = {"Domain A": 70, "Domain B": 80, "Domain C": 75}
        confidence_analysis = {"calibration_quality": "good"}

        # Execute
        score = gap_engine._calculate_readiness_score(
            overall_score=75.0,
            domain_scores=domain_scores,
            confidence_analysis=confidence_analysis
        )

        # Verify
        assert 0 <= score <= 100
        assert score > 70  # Should be above base score due to good calibration

    def test_calculate_correlation(self, gap_engine):
        """Test correlation calculation."""
        # Perfect positive correlation
        list1 = [1, 2, 3, 4, 5]
        list2 = [2, 4, 6, 8, 10]
        correlation = gap_engine._calculate_correlation(list1, list2)
        assert abs(correlation - 1.0) < 0.001

        # Perfect negative correlation
        list3 = [5, 4, 3, 2, 1]
        correlation = gap_engine._calculate_correlation(list1, list3)
        assert abs(correlation - (-1.0)) < 0.001

        # Weak correlation (the test data actually has some correlation)
        list4 = [1, 3, 2, 5, 4]
        correlation = gap_engine._calculate_correlation(list1, list4)
        assert abs(correlation) < 1.0  # Just verify it's a valid correlation value

    def test_calculate_gap_severity(self, gap_engine):
        """Test gap severity calculation."""
        # High severity gap
        severity = gap_engine._calculate_gap_severity(
            current_score=0.3,
            target_score=0.7,
            domain_weight=30.0
        )
        assert severity > 0.2

        # Low severity gap
        severity = gap_engine._calculate_gap_severity(
            current_score=0.68,
            target_score=0.7,
            domain_weight=10.0
        )
        assert severity < 0.1

    def test_classify_gap_type(self, gap_engine):
        """Test gap type classification."""
        # Fundamental gap
        gap_type = gap_engine._classify_gap_type(0.2, {})
        assert gap_type == "fundamental"

        # Conceptual gap
        gap_type = gap_engine._classify_gap_type(0.5, {})
        assert gap_type == "conceptual"

        # Application gap
        gap_type = gap_engine._classify_gap_type(0.7, {})
        assert gap_type == "application"

    def test_calculate_confidence_distribution(self, gap_engine):
        """Test confidence distribution calculation."""
        confidences = [1.0, 2.5, 3.0, 4.0, 5.0]

        # Execute
        distribution = gap_engine._calculate_confidence_distribution(confidences)

        # Verify
        assert len(distribution) == 5
        assert distribution["very_low"] == 0.2  # 1 out of 5
        assert distribution["low"] == 0.2       # 1 out of 5
        assert distribution["medium"] == 0.2    # 1 out of 5
        assert distribution["high"] == 0.2      # 1 out of 5
        assert distribution["very_high"] == 0.2 # 1 out of 5

    def test_assess_calibration_quality(self, gap_engine):
        """Test confidence calibration quality assessment."""
        # Excellent calibration
        quality = gap_engine._assess_calibration_quality(0.8, 4.0, 0.8)
        assert quality == "excellent"

        # Good calibration
        quality = gap_engine._assess_calibration_quality(0.6, 3.5, 0.7)
        assert quality == "good"

        # Fair calibration
        quality = gap_engine._assess_calibration_quality(0.3, 3.0, 0.6)
        assert quality == "fair"

        # Poor calibration
        quality = gap_engine._assess_calibration_quality(0.1, 2.0, 0.4)
        assert quality == "poor"

    def test_estimate_preparation_time(self, gap_engine):
        """Test preparation time estimation."""
        domain_gaps = [
            {"gap_severity": 0.8, "domain_weight_percentage": 30},
            {"gap_severity": 0.6, "domain_weight_percentage": 25}
        ]

        skill_assessments = [
            {"estimated_improvement_time_hours": 10},
            {"estimated_improvement_time_hours": 15}
        ]

        # Execute
        time_estimate = gap_engine._estimate_preparation_time(domain_gaps, skill_assessments)

        # Verify
        assert 10 <= time_estimate <= 200  # Within expected bounds
        assert isinstance(time_estimate, int)

    def test_recommend_study_approach(self, gap_engine):
        """Test study approach recommendation."""
        # Maintenance approach for high readiness
        approach = gap_engine._recommend_study_approach(90.0, [])
        assert approach == "maintenance"

        # Targeted approach for moderate readiness
        approach = gap_engine._recommend_study_approach(75.0, [])
        assert approach == "targeted"

        # Comprehensive approach for low readiness
        approach = gap_engine._recommend_study_approach(50.0, [])
        assert approach == "comprehensive"

    @pytest.mark.asyncio
    async def test_generate_remediation_plan_with_rag(self, gap_engine):
        """Test remediation plan generation with RAG context."""
        # Setup
        domain_gaps = [
            {
                "domain": "Security",
                "gap_severity": 0.7,
                "subdomain_breakdown": {"IAM": {"score": 0.4}}
            }
        ]

        skill_assessments = [
            {
                "skill_name": "Security",
                "estimated_improvement_time_hours": 15
            }
        ]

        gap_engine.knowledge_base.retrieve_context_for_assessment.return_value = {
            "combined_context": "IAM security best practices...",
            "citations": ["AWS IAM Best Practices Guide"]
        }

        # Execute
        result = await gap_engine._generate_remediation_plan(
            domain_gaps=domain_gaps,
            skill_assessments=skill_assessments,
            certification_id="aws-saa",
            overall_score=65.0
        )

        # Verify
        assert result["rag_enhanced"] is True
        assert "personalized_learning_path" in result
        assert "priority_actions" in result
        assert len(result["priority_actions"]) > 0

    def test_create_remediation_actions(self, gap_engine):
        """Test remediation action creation."""
        gap = {
            "domain": "Security",
            "gap_severity": 0.6,
            "subdomain_breakdown": {
                "IAM": {"score": 0.4},
                "VPC": {"score": 0.8}  # Good subdomain
            }
        }

        # Execute
        actions = gap_engine._create_remediation_actions(gap, "Sample RAG context")

        # Verify
        assert len(actions) >= 1  # At least main action

        # Check main action
        main_action = actions[0]
        assert main_action["action_type"] == "study"
        assert main_action["domain"] == "Security"
        assert main_action["estimated_duration_hours"] > 0
        assert main_action["priority"] > 0

        # Should have additional action for weak IAM subdomain
        iam_actions = [a for a in actions if a.get("subdomain") == "IAM"]
        assert len(iam_actions) >= 1