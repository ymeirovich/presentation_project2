"""
API endpoints for report prompt templates.
Provides default prompt templates for the UI.
"""

from fastapi import APIRouter

router = APIRouter()


DEFAULT_REPORT_PROMPT = """You are a technical assessment analyst. Based on the candidate's responses and assessment results, generate a comprehensive technical assessment report.

The report should include:

1. **Executive Summary**
   - Overall assessment outcome
   - Key strengths identified
   - Critical areas for improvement
   - Recommendation (Pass/Fail/Conditional Pass)

2. **Technical Knowledge Assessment**
   - Core competencies evaluated
   - Proficiency levels demonstrated
   - Specific technical skills verified
   - Knowledge gaps identified

3. **Practical Skills Evaluation**
   - Hands-on capabilities demonstrated
   - Problem-solving approach
   - Best practices application
   - Tool and technology proficiency

4. **Gap Analysis**
   - Skills that meet certification requirements
   - Skills requiring improvement
   - Recommended training areas
   - Estimated time to readiness

5. **Detailed Recommendations**
   - Specific learning resources
   - Practice exercises suggested
   - Focus areas for development
   - Next steps for certification preparation

Format the report in clear, professional language with specific examples from the assessment where applicable.
"""


@router.get(
    "/report",
    summary="Get default report prompt",
    description="Retrieve the default prompt template for generating assessment reports"
)
async def get_report_prompt():
    """
    Get the default report generation prompt template.

    Returns:
        dict: Contains the default prompt template
    """
    return {
        "prompt": DEFAULT_REPORT_PROMPT.strip(),
        "type": "report_generation",
        "version": "1.0"
    }
