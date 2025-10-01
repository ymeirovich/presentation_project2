"""Service contract schemas for Gap Analysis → Avatar workflow.

Sprint 0 Deliverable: Pydantic schemas for API contracts.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


# Sprint 1: Gap Analysis Schemas

class SkillGap(BaseModel):
    """Individual skill gap identified in assessment."""
    skill_id: str
    skill_name: str
    exam_domain: str
    exam_subsection: Optional[str] = None
    severity: int = Field(..., ge=0, le=10, description="Gap severity 0-10")
    confidence_delta: float = Field(..., description="User confidence vs actual performance")
    question_ids: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "skill_id": "iam_policies",
                "skill_name": "IAM Policies and Permissions",
                "exam_domain": "Security and Compliance",
                "exam_subsection": "Identity and Access Management",
                "severity": 7,
                "confidence_delta": -2.5,
                "question_ids": ["q_001", "q_005", "q_012"]
            }
        }


class GapAnalysisResult(BaseModel):
    """Complete gap analysis results."""
    workflow_id: UUID
    overall_score: float = Field(..., ge=0, le=100)
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    skill_gaps: List[SkillGap]
    performance_by_domain: Dict[str, float]
    text_summary: str
    charts_data: Optional[Dict[str, Any]] = None
    generated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "overall_score": 72.5,
                "total_questions": 24,
                "correct_answers": 17,
                "incorrect_answers": 7,
                "skill_gaps": [],
                "performance_by_domain": {
                    "Security and Compliance": 65.0,
                    "Networking": 80.0,
                    "Compute": 75.0
                },
                "text_summary": "You scored 72.5% overall. Strong performance in Networking...",
                "generated_at": "2025-09-30T12:00:00Z"
            }
        }


class ContentOutlineItem(BaseModel):
    """Content mapped to skill gap via RAG retrieval."""
    skill_id: str
    skill_name: str
    exam_domain: str
    exam_guide_section: str
    content_items: List[Dict[str, Any]] = Field(
        description="List of {topic, source, page_ref, summary}"
    )
    rag_retrieval_score: float = Field(..., ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "skill_id": "iam_policies",
                "skill_name": "IAM Policies and Permissions",
                "exam_domain": "Security and Compliance",
                "exam_guide_section": "1.2 - Define and implement identity and access management",
                "content_items": [
                    {
                        "topic": "IAM Policy Structure",
                        "source": "AWS IAM User Guide",
                        "page_ref": "Chapter 3, p. 45-52",
                        "summary": "IAM policies are JSON documents that define permissions..."
                    }
                ],
                "rag_retrieval_score": 0.89
            }
        }


class RecommendedCourse(BaseModel):
    """Course recommendation for skill gap."""
    id: UUID = Field(..., description="Course database ID")
    workflow_id: UUID = Field(..., description="Associated workflow ID")
    skill_id: str
    skill_name: str
    exam_domain: str
    exam_subsection: Optional[str] = None
    course_title: str
    course_description: str
    estimated_duration_minutes: int
    difficulty_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    learning_objectives: List[str]
    content_outline: Dict[str, Any]
    generation_status: str = Field(default="pending")
    priority: int = Field(default=0, description="Higher = more critical gap")

    class Config:
        json_schema_extra = {
            "example": {
                "skill_id": "iam_policies",
                "skill_name": "IAM Policies and Permissions",
                "exam_domain": "Security and Compliance",
                "course_title": "Mastering AWS IAM Policies",
                "course_description": "Comprehensive guide to IAM policy creation...",
                "estimated_duration_minutes": 45,
                "difficulty_level": "intermediate",
                "learning_objectives": [
                    "Understand IAM policy structure",
                    "Write effective IAM policies"
                ],
                "content_outline": {"sections": []},
                "generation_status": "pending",
                "priority": 7
            }
        }


# Sprint 2: Google Sheets Export Schemas

class SheetsExportRequest(BaseModel):
    """Request to export Gap Analysis to Google Sheets."""
    workflow_id: UUID
    user_id: str
    export_format: str = Field(default="4-tab", pattern="^4-tab$")

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user@example.com",
                "export_format": "4-tab"
            }
        }


class SheetsExportResponse(BaseModel):
    """Response from Google Sheets export."""
    success: bool
    sheet_id: str
    sheet_url: str
    tabs_created: List[str]
    export_time_ms: float

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "sheet_id": "1abc...xyz",
                "sheet_url": "https://docs.google.com/spreadsheets/d/1abc...xyz",
                "tabs_created": ["Answers", "Gap Analysis", "Content Outline", "Presentation"],
                "export_time_ms": 1250.5
            }
        }


# Sprint 3: PresGen-Core Integration Schemas

class PresGenCoreRequest(BaseModel):
    """Request to PresGen-Core for slide generation."""
    course_title: str
    content_outline: Dict[str, Any]
    slide_count: int = Field(..., ge=1, le=40)
    learning_objectives: List[str]
    difficulty_level: str
    rag_context_required: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "course_title": "AWS IAM Deep Dive",
                "content_outline": {"sections": []},
                "slide_count": 20,
                "learning_objectives": ["Understand IAM policies"],
                "difficulty_level": "intermediate",
                "rag_context_required": True
            }
        }


class PresGenCoreResponse(BaseModel):
    """Response from PresGen-Core."""
    success: bool
    presentation_id: str
    presentation_url: str
    slides_generated: int
    generation_time_ms: float

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "presentation_id": "pres_123",
                "presentation_url": "https://drive.google.com/...",
                "slides_generated": 20,
                "generation_time_ms": 5400.2
            }
        }


# Sprint 4: PresGen-Avatar Integration Schemas

class PresGenAvatarRequest(BaseModel):
    """Request to PresGen-Avatar for narrated course generation."""
    course_id: UUID
    presentation_url: str
    narration_script: str
    mode: str = Field(default="presentation-only", pattern="^presentation-only$")

    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "550e8400-e29b-41d4-a716-446655440000",
                "presentation_url": "https://drive.google.com/...",
                "narration_script": "Welcome to AWS IAM Deep Dive...",
                "mode": "presentation-only"
            }
        }


class PresGenAvatarResponse(BaseModel):
    """Response from PresGen-Avatar."""
    success: bool
    course_id: str
    video_url: str
    video_duration_seconds: float
    generation_time_seconds: float

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "course_id": "550e8400-e29b-41d4-a716-446655440000",
                "video_url": "https://storage.googleapis.com/courses/course_123.mp4",
                "video_duration_seconds": 2700.0,
                "generation_time_seconds": 180.5
            }
        }


class CourseGenerationProgress(BaseModel):
    """Progress update for course generation."""
    course_id: UUID
    status: str = Field(..., pattern="^(pending|in_progress|completed|failed)$")
    elapsed_seconds: float
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    current_step: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "in_progress",
                "elapsed_seconds": 45.2,
                "progress_percentage": 35.0,
                "current_step": "Generating narration audio"
            }
        }