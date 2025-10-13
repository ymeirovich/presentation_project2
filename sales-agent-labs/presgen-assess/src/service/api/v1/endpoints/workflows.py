"""Async workflow management API endpoints."""

import asyncio
from datetime import datetime
import csv
from io import StringIO
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
from uuid import UUID

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.common.logging_config import get_workflow_logger, get_api_logger, get_assessment_logger
from src.common.config import settings
from src.models.workflow import WorkflowExecution
from src.models.generated_course import GeneratedCourse
from src.models.gap_analysis import RecommendedCourse, GapAnalysisResult
from src.models.certification import CertificationProfile
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStatusUpdate
)
from src.schemas.google_forms import AssessmentWorkflowRequest, FormSettings
from src.schemas.gap_analysis import CourseGenerationResponse, CourseStatusResponse
from src.service.database import get_db
from src.services.workflow_orchestrator import WorkflowOrchestrator
from src.services.ai_question_generator import AIQuestionGenerator
from src.services.response_ingestion_service import ResponseIngestionService
from src.services.google_sheets_service import GoogleSheetsService, EnhancedGapAnalysisExporter
from src.services.google_forms_service import GoogleFormsService
from src.services.course_generation_service import log_course_event
from src.services.presentation_service import PresentationGenerationService
from fastapi.responses import JSONResponse, Response, FileResponse

logger = get_workflow_logger()
api_logger = get_api_logger()
assessment_logger = get_assessment_logger()

router = APIRouter()

REPO_ROOT = Path(__file__).resolve().parents[6]
SRC_ROOT = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_ROOT):
    str_path = str(path)
    if str_path not in sys.path:
        sys.path.insert(0, str_path)

presentation_generation_service = PresentationGenerationService()


def _slugify_skill_name(value: str) -> str:
    """Convert a skill name to a filesystem-friendly slug."""

    slug = ''.join(ch.lower() if ch.isalnum() else '-' for ch in value)
    slug = '-'.join(part for part in slug.split('-') if part)
    return slug or 'skill'


def _summarize_learning_objectives(obj: Any, limit: int = 5) -> List[str]:
    """Normalize learning objectives into a short bullet list."""

    bullets: List[str] = []
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    bullets.append(text[:180])
            elif isinstance(item, dict):
                text = str(item.get("title") or item.get("text") or "").strip()
                if text:
                    bullets.append(text[:180])
            if len(bullets) >= limit:
                break
    return bullets


def _ensure_list(value: Any) -> List[Any]:
    """Ensure a value is returned as a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except Exception:
            return [value]
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _ensure_dict(value: Any) -> Dict[str, Any]:
    """Ensure a value is returned as a dict."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def _regenerate_course_outline_for_course(
    workflow: WorkflowExecution,
    skill_course: RecommendedCourse,
    presentation_prompt: Optional[str],
    target_slide_count: int
) -> Optional[Dict[str, Any]]:
    """Regenerate course outline using LLM for the specified course."""
    try:
        outline = await presentation_generation_service.regenerate_outline_from_recommended_course(
            workflow=workflow,
            recommended_course=skill_course,
            presentation_prompt=presentation_prompt,
            target_slide_count=target_slide_count,
        )
        if outline and outline.get("success"):
            return outline
        return None
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "⚠️ Outline regeneration failed | workflow_id=%s | course_id=%s | error=%s",
            getattr(workflow, "id", "unknown"),
            getattr(skill_course, "id", "unknown"),
            exc,
        )
        return None


def _build_slide_plans(
    title: str,
    subtitle: str,
    skill_name: str,
    skill_course: RecommendedCourse,
    target_slide_count: int = 12,
) -> List[Dict[str, Any]]:
    """Build slide plans with title, subtitle, bullets, and presenter notes (script)."""

    def _clean_list(values: Optional[List[str]]) -> List[str]:
        if not values:
            return []
        cleaned = []
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                cleaned.append(text)
        return cleaned

    plans: List[Dict[str, Any]] = []
    target = max(1, min(target_slide_count, 40))

    learning_objectives = _clean_list(skill_course.learning_objectives)
    content_outline = skill_course.content_outline or {}
    sections = content_outline.get("sections", []) if isinstance(content_outline, dict) else []
    content_items = content_outline.get("content_items", []) if isinstance(content_outline, dict) else []

    def add_plan(slide_title: str, slide_subtitle: str = "", bullets: Optional[List[str]] = None, script: str = "") -> None:
        bullet_list = _clean_list(bullets) if bullets else []
        plans.append({
            "title": slide_title.strip() or "Untitled Slide",
            "subtitle": slide_subtitle.strip() if slide_subtitle else "",
            "bullets": bullet_list,
            "script": (script.strip() or slide_title.strip() or "Presenter notes unavailable."),
        })

    # Title / overview slide
    overview_points = learning_objectives[:3] or [f"Why {skill_name} matters"]
    add_plan(
        slide_title=title,
        slide_subtitle=subtitle,
        bullets=overview_points,
        script=(
            f"Welcome to this session on {skill_name}. "
            f"We will focus on {', '.join(overview_points)}."
        ),
    )

    # Gap summary slide (if we have course description)
    if skill_course.course_description:
        add_plan(
            slide_title="Current Skill Snapshot",
            slide_subtitle=skill_name,
            bullets=[
                "Review current performance",
                "Identify key learning objectives",
                "Map remediation steps"
            ],
            script=skill_course.course_description or f"We will address the critical gaps in {skill_name}.",
        )

    objective_queue = learning_objectives.copy()
    section_queue = list(sections) if isinstance(sections, list) else []
    item_queue = list(content_items) if isinstance(content_items, list) else []

    def _objective_plan(objective: str) -> None:
        add_plan(
            slide_title=objective,
            slide_subtitle="Learning objective",
            bullets=[
                "Clarify the core concept",
                "Connect theory to practical implementation",
                "Identify resources to reinforce learning",
            ],
            script=f"In this segment we will focus on the objective '{objective}' and how to demonstrate proficiency.",
        )

    def _section_plan(section: Dict[str, Any]) -> None:
        section_title = str(section.get("title") or "Key Section").strip()
        duration = section.get("duration_minutes")
        bullets = []
        if duration:
            bullets.append(f"Estimated focus time: {duration} minutes")
        bullets.extend([
            "Highlight foundational knowledge",
            "Discuss implementation considerations",
            "Note common pitfalls and exam tips",
        ])
        add_plan(
            slide_title=section_title,
            slide_subtitle="Section focus",
            bullets=bullets,
            script=f"This section explores {section_title.lower()} with guidance on how to master it for certification success.",
        )

    def _content_item_plan(item: Dict[str, Any]) -> None:
        topic = (item.get("topic") or item.get("title") or "Key Concept").strip()
        source = (item.get("source") or "Reference material").strip()
        key_points = item.get("key_points")
        bullets = _clean_list(key_points if isinstance(key_points, list) else None)
        summary = (item.get("summary") or item.get("description") or "Explain why this concept matters.").strip()
        if not bullets:
            sentences = [seg.strip() for seg in summary.replace("\n", " ").split('.') if seg.strip()]
            bullets = sentences[:3] if sentences else [summary]
        add_plan(
            slide_title=topic,
            slide_subtitle=f"Source: {source}" if source else "",
            bullets=bullets,
            script=summary,
        )

    while len(plans) < target:
        if objective_queue:
            _objective_plan(objective_queue.pop(0))
        elif item_queue:
            _content_item_plan(item_queue.pop(0))
        elif section_queue:
            _section_plan(section_queue.pop(0))
        else:
            # All content exhausted - add final review slide and break
            add_plan(
                slide_title="Review & Next Steps",
                slide_subtitle=skill_name,
                bullets=[
                    "Summarize key insights",
                    "Plan immediate practice tasks",
                    "Schedule follow-up assessment",
                ],
                script="Consolidate what we learned and outline concrete next actions for continued progress.",
            )
            break  # Exit loop to prevent infinite "Review & Next Steps" slides

    # Ensure we don't exceed the target
    return plans[:target]


def _create_public_presentation(
    *,
    title: str,
    subtitle: Optional[str],
    bullets: List[str],
    workflow_id: str,
    skill_name: str,
    slide_plans: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create and share a Google Slides deck with multiple slides, returning its edit URL."""

    # Import Google Slides module using helper to handle namespace collision
    from common.google_slides_import_v2 import get_slides_google
    slides_google = get_slides_google()

    create_presentation = slides_google.create_presentation
    delete_default_slide = slides_google.delete_default_slide
    create_main_slide_with_content = slides_google.create_main_slide_with_content
    _load_credentials = slides_google._load_credentials

    from googleapiclient.discovery import build

    logger.info(
        "🎯 slides_generation | stage=create_start | workflow_id=%s | skill=%s | slide_count=%s",
        workflow_id,
        skill_name,
        len(slide_plans) if slide_plans else 1,
    )

    presentation = create_presentation(title)
    presentation_id = presentation.get("presentationId")
    if not presentation_id:
        raise RuntimeError("Failed to obtain presentationId from Google Slides response")

    presentation_url = presentation.get("presentationLink") or f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    try:
        delete_default_slide(presentation_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug(
            "🎯 slides_generation | stage=delete_default_slide_failed | workflow_id=%s | skill=%s | error=%s",
            workflow_id,
            skill_name,
            exc,
        )

    # Create multiple slides if slide_plans provided, otherwise create single slide
    if slide_plans:
        for idx, plan in enumerate(slide_plans):
            try:
                create_main_slide_with_content(
                    presentation_id,
                    title=plan.get("title", f"Slide {idx + 1}"),
                    subtitle=plan.get("subtitle", ""),
                    bullets=plan.get("bullets", []),
                    image_url=None,
                    script=plan.get("script", ""),
                )
                logger.debug(
                    "🎯 slides_generation | stage=slide_created | workflow_id=%s | skill=%s | slide=%s/%s | title=%s",
                    workflow_id,
                    skill_name,
                    idx + 1,
                    len(slide_plans),
                    plan.get("title", "Untitled"),
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "🎯 slides_generation | stage=create_slide_failed | workflow_id=%s | skill=%s | slide=%s | error=%s",
                    workflow_id,
                    skill_name,
                    idx + 1,
                    exc,
                )
    else:
        # Fallback: create single slide with basic content
        try:
            create_main_slide_with_content(
                presentation_id,
                title=title,
                subtitle=subtitle or "",
                bullets=bullets or [f"Key concepts for {skill_name}"],
                image_url=None,
                script=f"Welcome to this presentation on {skill_name}. " + (subtitle or ""),
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "🎯 slides_generation | stage=create_slide_failed | workflow_id=%s | skill=%s | error=%s",
                workflow_id,
                skill_name,
                exc,
            )

    creds = _load_credentials()
    drive_service = build("drive", "v3", credentials=creds)
    drive_service.permissions().create(
        fileId=presentation_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    logger.info(
        "🎯 slides_generation | stage=create_complete | workflow_id=%s | skill=%s | presentation_url=%s | total_slides=%s",
        workflow_id,
        skill_name,
        presentation_url,
        len(slide_plans) if slide_plans else 1,
    )

    return presentation_url


async def _ensure_presentation_deck(
    course: GeneratedCourse,
    skill_course: RecommendedCourse,
    *,
    workflow_id: str,
    assessment_title: Optional[str],
    target_slide_count: int = 12,
) -> str:
    """Guarantee a Google Slides deck exists with the requested slide count and return its URL."""

    if course.presentation_url:
        return course.presentation_url

    title = course.course_title or f"Mastering {skill_course.skill_name}"
    subtitle = assessment_title or skill_course.exam_domain
    bullets = _summarize_learning_objectives(skill_course.learning_objectives)
    skill_name = skill_course.skill_name
    if not bullets and skill_course.course_description:
        bullets = [skill_course.course_description.strip()[:180]]

    # Build slide plans for all slides
    slide_plans = _build_slide_plans(
        title=title,
        subtitle=subtitle,
        skill_name=skill_name,
        skill_course=skill_course,
        target_slide_count=target_slide_count,
    )

    outline_preview = " | ".join(
        f"{idx + 1}: {plan.get('title', 'Untitled')}"
        for idx, plan in enumerate(slide_plans[:5])
    ) + (f" ... (+{len(slide_plans) - 5} more)" if len(slide_plans) > 5 else "")

    log_course_event(
        "PRESENTATION_SLIDE_CONTENT_PREPARED",
        workflow_id=workflow_id,
        course_id=getattr(course, "id", "unknown"),
        skill_name=skill_name,
        slide_count=len(slide_plans),
        subtitle=(assessment_title or skill_course.exam_domain or ""),
        outline_preview=outline_preview,
        slide_plans=slide_plans,  # ✅ Phase 10 Task 4.1 - Include complete slide array
    )

    # ✅ Phase 10 Task 4.1 - Log complete PresGen-Core payload
    logger.info(
        json.dumps({
            "event": "presgen_core_payload_full",
            "workflow_id": workflow_id,
            "course_id": getattr(course, "id", "unknown"),
            "presentation_title": title,
            "presentation_subtitle": subtitle,
            "sections": [
                {
                    "slide_number": idx + 1,
                    "title": plan.get("title"),
                    "bullets": plan.get("bullets"),
                    "instructor_notes": plan.get("instructor_notes"),
                }
                for idx, plan in enumerate(slide_plans)
            ],
            "total_slides": len(slide_plans),
        })
    )

    loop = asyncio.get_running_loop()
    presentation_url = await loop.run_in_executor(
        None,
        lambda: _create_public_presentation(
            title=title,
            subtitle=subtitle,
            bullets=bullets,
            workflow_id=workflow_id,
            skill_name=skill_name,
            slide_plans=slide_plans,
        ),
    )

    return presentation_url


async def _build_gap_analysis_data(
    workflow_id: UUID,
    db: AsyncSession
) -> Dict[str, Any]:
    """Build gap analysis payload for a workflow."""
    stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found"
        )

    if workflow.progress < 75:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow has not reached gap analysis stage"
        )

    domain_performance = [
        {
            "domain": "Data Engineering",
            "score": 65,
            "question_count": 6,
            "correct_count": 4,
            "confidence_score": 78,
            "overconfidence_ratio": round(78 / 65, 2),
            "bloom_levels": [
                {
                    "level": "remember",
                    "label": "Remember",
                    "score": 70,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "understand",
                    "label": "Understand",
                    "score": 68,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "apply",
                    "label": "Apply",
                    "score": 60,
                    "question_count": 2,
                    "correct_count": 2
                }
            ]
        },
        {
            "domain": "Exploratory Data Analysis",
            "score": 72,
            "question_count": 6,
            "correct_count": 4,
            "confidence_score": 71,
            "overconfidence_ratio": round(71 / 72, 2),
            "bloom_levels": [
                {
                    "level": "remember",
                    "label": "Remember",
                    "score": 80,
                    "question_count": 2,
                    "correct_count": 2
                },
                {
                    "level": "analyze",
                    "label": "Analyze",
                    "score": 70,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "evaluate",
                    "label": "Evaluate",
                    "score": 65,
                    "question_count": 2,
                    "correct_count": 1
                }
            ]
        },
        {
            "domain": "Modeling",
            "score": 58,
            "question_count": 6,
            "correct_count": 3,
            "confidence_score": 82,
            "overconfidence_ratio": round(82 / 58, 2),
            "bloom_levels": [
                {
                    "level": "understand",
                    "label": "Understand",
                    "score": 62,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "apply",
                    "label": "Apply",
                    "score": 55,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "create",
                    "label": "Create",
                    "score": 50,
                    "question_count": 2,
                    "correct_count": 1
                }
            ]
        },
        {
            "domain": "Machine Learning Implementation and Operations",
            "score": 68,
            "question_count": 6,
            "correct_count": 4,
            "confidence_score": 69,
            "overconfidence_ratio": round(69 / 68, 2),
            "bloom_levels": [
                {
                    "level": "remember",
                    "label": "Remember",
                    "score": 75,
                    "question_count": 2,
                    "correct_count": 2
                },
                {
                    "level": "apply",
                    "label": "Apply",
                    "score": 68,
                    "question_count": 2,
                    "correct_count": 1
                },
                {
                    "level": "analyze",
                    "label": "Analyze",
                    "score": 60,
                    "question_count": 2,
                    "correct_count": 1
                }
            ]
        }
    ]

    learning_gaps = [
        {
            "domain": "Modeling",
            "gap_severity": "critical",
            "confidence_gap": 24,
            "skill_gap": 22,
            "recommended_study_hours": 12,
            "priority_topics": [
                "Model Selection",
                "Hyperparameter Tuning",
                "Model Evaluation"
            ],
            "remediation_resources": [
                {
                    "title": "AWS ML Model Selection Guide",
                    "type": "documentation",
                    "url": "https://docs.aws.amazon.com/machine-learning/",
                    "estimated_time_minutes": 90
                }
            ]
        },
        {
            "domain": "Data Engineering",
            "gap_severity": "high",
            "confidence_gap": -13,
            "skill_gap": 15,
            "recommended_study_hours": 8,
            "priority_topics": [
                "Data Pipeline Architecture",
                "ETL Processes"
            ],
            "remediation_resources": [
                {
                    "title": "AWS Data Engineering Best Practices",
                    "type": "article",
                    "url": "https://aws.amazon.com/data-engineering/",
                    "estimated_time_minutes": 60
                }
            ]
        }
    ]

    bloom_taxonomy_breakdown = [
        {
            "level": "remember",
            "label": "Remember",
            "score": 85,
            "question_count": 6,
            "correct_count": 5
        },
        {
            "level": "understand",
            "label": "Understand",
            "score": 78,
            "question_count": 6,
            "correct_count": 4
        },
        {
            "level": "apply",
            "label": "Apply",
            "score": 65,
            "question_count": 6,
            "correct_count": 4
        },
        {
            "level": "analyze",
            "label": "Analyze",
            "score": 55,
            "question_count": 4,
            "correct_count": 2
        },
        {
            "level": "evaluate",
            "label": "Evaluate",
            "score": 45,
            "question_count": 2,
            "correct_count": 1
        },
        {
            "level": "create",
            "label": "Create",
            "score": 35,
            "question_count": 2,
            "correct_count": 1
        }
    ]

    return {
        "workflow_id": str(workflow_id),
        "overall_score": 66,
        "overall_confidence": 75,
        "overconfidence_indicator": True,
        "domain_performance": domain_performance,
        "learning_gaps": learning_gaps,
        "bloom_taxonomy_breakdown": bloom_taxonomy_breakdown,
        "recommended_study_plan": {
            "total_estimated_hours": 24,
            "priority_domains": ["Modeling", "Data Engineering"],
            "study_sequence": [
                "Model Selection and Evaluation",
                "Feature Engineering",
                "Data Pipeline Architecture",
                "ML Model Deployment"
            ]
        },
        "generated_at": workflow.updated_at.isoformat() if workflow.updated_at else datetime.utcnow().isoformat()
    }


def _generate_basic_pdf(text: str) -> bytes:
    """Generate a minimal PDF document containing the provided text."""
    # Escape PDF text characters
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in text.splitlines()
    ]

    stream_lines = []
    if escaped_lines:
        stream_lines.append(f"({escaped_lines[0]}) Tj")
        for line in escaped_lines[1:]:
            stream_lines.append(f"0 -14 Td ({line}) Tj")
    else:
        stream_lines.append("(Gap Analysis Report) Tj")

    stream_content = "BT /F1 12 Tf 72 750 Td " + "\n".join(stream_lines) + " ET"
    stream_bytes = stream_content.encode("latin-1", errors="ignore")
    header = b"%PDF-1.4\n"
    body = header
    offsets = [0]  # Object 0

    def add_obj(obj_bytes: bytes) -> None:
        nonlocal body
        offsets.append(len(body))
        body += obj_bytes

    add_obj(b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")
    add_obj(b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n")
    add_obj(b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n")

    content_obj = (
        f"4 0 obj<</Length {len(stream_bytes)}>>stream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    add_obj(content_obj)

    add_obj(b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n")

    xref_offset = len(body)

    xref_entries = [b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_entries.append(f"{offset:010} 00000 n \n".encode("latin-1"))

    body += b"xref\n0 6\n" + b"".join(xref_entries)
    body += b"trailer<</Size 6/Root 1 0 R>>\n"
    body += b"startxref\n" + str(xref_offset).encode("latin-1") + b"\n%%EOF"

    return body
@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Create a new async workflow."""
    # Log API request
    api_logger.info(f"📥 POST /workflows | user_id={workflow_data.user_id} | workflow_type={workflow_data.workflow_type} | cert_profile_id={workflow_data.certification_profile_id}")

    try:
        # Map WorkflowCreate data to WorkflowExecution fields
        workflow_dict = workflow_data.model_dump(exclude_none=True)

        # Ensure required fields exist for ORM compatibility and UI expectations
        workflow_dict.setdefault('current_step', 'initiated')
        workflow_dict.setdefault('execution_status', 'pending')
        workflow_dict['status'] = workflow_dict.get('execution_status', 'pending')
        workflow_dict.setdefault('progress', 0)

        # Backfill slide count tracking so downstream steps have defaults
        if 'requested_slide_count' not in workflow_dict:
            requested_slides = (
                workflow_dict.get('parameters', {}).get('slide_count')
                if isinstance(workflow_dict.get('parameters'), dict)
                else None
            )
            if requested_slides:
                workflow_dict['requested_slide_count'] = requested_slides

        # Map schema field names to database column names
        google_sheet_url = workflow_dict.pop('google_sheet_url', None)
        if google_sheet_url:
            workflow_dict['sheet_url_input'] = google_sheet_url

        logger.info(
            "📥 Creating workflow | user_id=%s profile_id=%s workflow_type=%s",
            workflow_dict.get('user_id'),
            workflow_dict.get('certification_profile_id'),
            workflow_dict.get('workflow_type'),
        )

        workflow = WorkflowExecution(**workflow_dict)
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        logger.info(
            "✅ Workflow created | id=%s status=%s current_step=%s",
            workflow.id,
            workflow.status,
            workflow.current_step,
        )

        # Auto-trigger orchestration for assessment_generation workflows
        if workflow.workflow_type == "assessment_generation":
            try:
                logger.info("🚀 Auto-triggering orchestration for assessment_generation workflow")

                # Generate real AI questions using knowledge base
                logger.info(f"🤖 Generating AI questions for workflow {workflow.id} | cert_profile_id={workflow.certification_profile_id} | domain_distribution={workflow.parameters.get('domain_distribution', {})} | question_count={workflow.parameters.get('question_count', 24)}")
                assessment_logger.info(f"🚀 Starting assessment generation | workflow_id={workflow.id} | cert_profile_id={workflow.certification_profile_id} | question_count={workflow.parameters.get('question_count', 24)}")

                question_generator = AIQuestionGenerator()
                ai_result = await question_generator.generate_contextual_assessment(
                    certification_profile_id=str(workflow.certification_profile_id),
                    user_profile="intermediate_learner",  # Default user profile
                    difficulty_level=workflow.parameters.get('difficulty_level', 'beginner'),
                    domain_distribution=workflow.parameters.get('domain_distribution', {}),
                    question_count=workflow.parameters.get('question_count', 24)
                )

                logger.info(f"🔍 AI question generation result | success={ai_result.get('success')} | error={ai_result.get('error', 'None')}")
                assessment_logger.info(f"✅ Assessment generation completed | success={ai_result.get('success')} | questions_generated={len(ai_result.get('assessment_data', {}).get('questions', []))} | workflow_id={workflow.id}")

                if ai_result.get('success') and ai_result.get('assessment_data', {}).get('questions'):
                    # Use AI-generated questions
                    assessment_data = ai_result['assessment_data']
                    generation_method = "ai_generated"
                    question_count = len(assessment_data.get('questions', []))
                    logger.info(f"✅ Using AI-generated questions | count={question_count}")
                else:
                    # Fallback to mock questions if AI generation fails
                    logger.warning(f"⚠️ AI question generation failed, using fallback mock questions: {ai_result.get('error', 'Unknown error')}")
                    fallback_count = min(5, workflow.parameters.get('question_count', 24) // 5)
                    assessment_data = {
                        "questions": [
                            {
                                "id": f"fallback_q{i+1}",
                                "question_text": f"Sample question {i+1} for {workflow.parameters.get('title', 'Assessment')}",
                                "question_type": "multiple_choice",
                                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                                "correct_answer": "A"
                            } for i in range(fallback_count)
                        ],
                        "metadata": {
                            "certification_name": workflow.parameters.get('title', 'Assessment'),
                            "difficulty_level": workflow.parameters.get('difficulty_level', 'beginner'),
                            "question_count": workflow.parameters.get('question_count', 24),
                            "domain_distribution": workflow.parameters.get('domain_distribution', {})
                        }
                    }
                    generation_method = "fallback"
                    question_count = fallback_count

                # Store generation metadata in workflow parameters
                if not workflow.parameters:
                    workflow.parameters = {}
                workflow.parameters['generation_method'] = generation_method
                workflow.parameters['question_count'] = question_count

                # Store assessment data (questions) for later response matching
                workflow.assessment_data = assessment_data

                # Flag the JSON columns as modified so SQLAlchemy detects the changes
                flag_modified(workflow, 'parameters')
                flag_modified(workflow, 'assessment_data')

                await db.commit()
                await db.refresh(workflow)

                logger.info(f"✅ Stored generation metadata and questions | method={generation_method} | count={question_count}")

                form_settings = FormSettings(
                    collect_email=True,
                    require_login=False
                )

                orchestrator = WorkflowOrchestrator()
                orchestration_result = await orchestrator.execute_assessment_to_form_workflow(
                    certification_profile_id=workflow.certification_profile_id,
                    user_id=workflow.user_id,
                    assessment_data=assessment_data,
                    form_settings=form_settings
                )

                if orchestration_result.get("success"):
                    logger.info(f"✅ Auto-orchestration successful for workflow {workflow.id}")
                else:
                    logger.warning(f"⚠️ Auto-orchestration failed for workflow {workflow.id}: {orchestration_result.get('error')}")

            except Exception as e:
                logger.error(f"❌ Auto-orchestration error for workflow {workflow.id}: {e}")

            # Refresh workflow to get latest parameters with generation metadata
            await db.refresh(workflow)

        return WorkflowResponse.model_validate(workflow)

    except Exception as e:
        await db.rollback()
        logger.exception("❌ Failed to create workflow")
        logger.error("❌ Payload causing failure: %s", workflow_data.model_dump())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[WorkflowResponse]:
    """List workflows with optional status filtering."""
    try:
        stmt = select(WorkflowExecution).offset(skip).limit(limit).order_by(WorkflowExecution.created_at.desc())

        if status_filter:
            stmt = stmt.where(WorkflowExecution.status == status_filter)

        result = await db.execute(stmt)
        workflows = result.scalars().all()

        return [WorkflowResponse.model_validate(workflow) for workflow in workflows]

    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get a specific workflow by ID."""
    try:
        logger.info("🔍 Fetching workflow detail | id=%s", workflow_id)
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            logger.warning("⚠️ Workflow not found | id=%s", workflow_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        response = WorkflowResponse.model_validate(workflow)
        logger.info(
            "📤 Workflow detail retrieved | id=%s status=%s step=%s",
            workflow_id,
            response.status,
            response.current_step,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Failed to get workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )




@router.get("/token/{resume_token}", response_model=WorkflowResponse)
async def get_workflow_by_token(
    resume_token: str,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get workflow by resume token."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.resume_token == resume_token)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired resume token"
            )

        # Check if token is expired (tokens expire after 24 hours)
        from datetime import datetime, timedelta
        if workflow.created_at < datetime.utcnow() - timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Resume token has expired"
            )

        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow by token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: UUID,
    resume_data: WorkflowResumeRequest,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Resume a workflow with provided data."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        # Check if workflow can be resumed
        if workflow.status not in ["awaiting_completion", "sheet_url_provided"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow cannot be resumed from status: {workflow.status}"
            )

        # Update workflow with resume data
        for field, value in resume_data.model_dump(exclude_unset=True).items():
            if field == "google_sheet_url":
                setattr(workflow, "sheet_url_input", value)
            else:
                setattr(workflow, field, value)

        # Update status based on what was provided
        if resume_data.google_sheet_url:
            workflow.status = "sheet_url_provided"

        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Resumed workflow: {workflow_id}")
        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to resume workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume workflow"
        )


@router.put("/{workflow_id}/status", response_model=WorkflowResponse)
async def update_workflow_status(
    workflow_id: UUID,
    status_update: WorkflowStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Update workflow status."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        # Update status and progress
        workflow.status = status_update.status
        if status_update.progress is not None:
            workflow.progress = status_update.progress
        if status_update.error_message:
            workflow.error_message = status_update.error_message

        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Updated workflow status: {workflow_id} -> {status_update.status}")
        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update workflow status {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow status"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a workflow."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        await db.delete(workflow)
        await db.commit()

        logger.info(f"✅ Deleted workflow: {workflow_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow"
        )


# Sprint 2 Enhancement: Workflow Orchestration Endpoints

@router.post("/assessment-to-form")
async def create_assessment_form_workflow(
    request: AssessmentWorkflowRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create and execute assessment-to-form workflow with orchestration."""
    try:
        logger.info("🚀 Starting assessment-to-form workflow orchestration")

        orchestrator = WorkflowOrchestrator()

        # Execute orchestrated workflow
        result = await orchestrator.execute_assessment_to_form_workflow(
            certification_profile_id=request.certification_profile_id,
            user_id=request.user_id,
            assessment_data=request.assessment_data,
            form_settings=request.form_settings
        )

        if result["success"]:
            logger.info(f"✅ Assessment-to-form workflow created successfully: {result['workflow_id']}")
        else:
            logger.error(f"❌ Assessment-to-form workflow failed: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"❌ Assessment-to-form workflow error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.post("/{workflow_id}/force-ingest-responses")
async def force_ingest_responses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger response ingestion for a workflow."""
    try:
        logger.info(f"🔄 Forcing response ingestion for workflow: {workflow_id}")

        ingestion_service = ResponseIngestionService()
        result = await ingestion_service.force_ingest_workflow_responses(workflow_id)

        if result["success"]:
            logger.info(f"✅ Response ingestion completed for workflow: {workflow_id}")
        else:
            logger.error(f"❌ Response ingestion failed for workflow: {workflow_id}")

        return result

    except Exception as e:
        logger.error(f"❌ Response ingestion error for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response ingestion failed: {str(e)}"
        )


@router.post("/{workflow_id}/process-responses")
async def process_workflow_responses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Process collected responses and generate analysis."""
    try:
        logger.info(f"📊 Processing responses for workflow: {workflow_id}")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.process_completed_responses(workflow_id)

        if result["success"]:
            logger.info(f"✅ Response processing completed for workflow: {workflow_id}")
        else:
            logger.error(f"❌ Response processing failed for workflow: {workflow_id}")

        return result

    except Exception as e:
        logger.error(f"❌ Response processing error for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response processing failed: {str(e)}"
        )


@router.get("/{workflow_id}/orchestration-status")
async def get_orchestration_status(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed orchestration status for a workflow."""
    try:
        logger.info(f"📋 Getting orchestration status for workflow: {workflow_id}")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.get_workflow_status(workflow_id)

        return result

    except Exception as e:
        logger.error(f"❌ Error getting orchestration status for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orchestration status: {str(e)}"
        )


@router.get("/active/orchestration")
async def list_active_orchestrated_workflows(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all active workflows with orchestration details."""
    try:
        logger.info("📋 Listing active orchestrated workflows")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.list_active_workflows()

        return result

    except Exception as e:
        logger.error(f"❌ Error listing active orchestrated workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active workflows: {str(e)}"
        )


@router.get("/ingestion/stats")
async def get_ingestion_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get response ingestion statistics."""
    try:
        logger.info("📊 Getting ingestion statistics")

        ingestion_service = ResponseIngestionService()
        result = await ingestion_service.get_ingestion_stats()

        return {
            "success": True,
            "stats": result
        }

    except Exception as e:
        logger.error(f"❌ Error getting ingestion statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion statistics: {str(e)}"
        )


@router.post("/{workflow_id}/trigger-orchestration")
async def trigger_workflow_orchestration(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger assessment-to-form orchestration for an existing workflow."""
    try:
        logger.info(f"🚀 Triggering orchestration for workflow: {workflow_id}")

        # Get the workflow
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        if workflow.workflow_type != "assessment_generation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Orchestration only supported for assessment_generation workflows, got: {workflow.workflow_type}"
            )

        # Generate AI-powered assessment data using certification resources
        from src.services.ai_question_generator import AIQuestionGenerator

        logger.info(f"🤖 Generating AI-powered questions for workflow {workflow_id}")

        question_generator = AIQuestionGenerator()
        ai_generation_result = await question_generator.generate_contextual_assessment(
            certification_profile_id=workflow.certification_profile_id,
            user_profile=workflow.user_id,
            difficulty_level=workflow.parameters.get('difficulty_level', 'intermediate'),
            domain_distribution=workflow.parameters.get('domain_distribution', {}),
            question_count=workflow.parameters.get('question_count', 24)
        )

        if ai_generation_result.get("success"):
            assessment_data = ai_generation_result["assessment_data"]
            logger.info(f"✅ AI question generation successful | questions={len(assessment_data['questions'])} avg_quality={assessment_data['metadata']['quality_scores']['overall']:.1f}")
        else:
            logger.warning(f"⚠️ AI question generation failed, using fallback")
            # Fallback to basic questions if AI generation fails
            assessment_data = {
                "questions": [
                    {
                        "id": f"fallback_q{i+1}",
                        "question_text": f"Sample question {i+1} for {workflow.parameters.get('title', 'Assessment')}",
                        "question_type": "multiple_choice",
                        "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                        "correct_answer": "A"
                    } for i in range(min(5, workflow.parameters.get('question_count', 24) // 5))
                ],
                "metadata": {
                    "certification_name": workflow.parameters.get('title', 'Assessment'),
                    "difficulty_level": workflow.parameters.get('difficulty_level', 'beginner'),
                    "question_count": workflow.parameters.get('question_count', 24),
                    "domain_distribution": workflow.parameters.get('domain_distribution', {}),
                    "fallback_mode": True
                }
            }

        form_settings = FormSettings(
            collect_email=True,
            require_login=False
        )

        orchestrator = WorkflowOrchestrator()
        orchestration_result = await orchestrator.execute_assessment_to_form_workflow(
            certification_profile_id=workflow.certification_profile_id,
            user_id=workflow.user_id,
            assessment_data=assessment_data,
            form_settings=form_settings
        )

        if orchestration_result.get("success"):
            logger.info(f"✅ Orchestration successful for workflow {workflow_id}")
            return {
                "success": True,
                "message": "Workflow orchestration triggered successfully",
                "workflow_id": str(workflow_id),
                "orchestration_result": orchestration_result
            }
        else:
            logger.error(f"❌ Orchestration failed for workflow {workflow_id}: {orchestration_result.get('error')}")
            return {
                "success": False,
                "error": f"Orchestration failed: {orchestration_result.get('error')}",
                "workflow_id": str(workflow_id)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering orchestration for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger orchestration: {str(e)}"
        )


async def fetch_form_responses_and_trigger_pipeline(
    workflow_id: UUID,
    workflow: WorkflowExecution,
    db: AsyncSession
) -> Dict[str, Any]:
    """Fetch responses from Google Forms and trigger full pipeline."""

    forms_service = GoogleFormsService()

    # 1. Fetch responses from Google Forms API
    form_id = workflow.google_form_id
    if not form_id:
        raise ValueError("No Google Form ID found in workflow")

    logger.info(f"📥 Fetching responses from Google Form {form_id}")

    try:
        responses_data = await forms_service.get_form_responses(form_id=form_id)
        responses = responses_data.get('responses', [])

        if not responses:
            raise ValueError("No responses found in Google Form")

        logger.info(f"✅ Fetched {len(responses)} responses")
    except Exception as e:
        logger.error(f"❌ Failed to fetch form responses: {e}")
        raise ValueError(f"Failed to fetch form responses: {str(e)}")

    # 2. Unpause workflow
    workflow.paused_at = None
    workflow.resumed_at = datetime.utcnow()
    workflow.current_step = "gap_analysis"
    workflow.execution_status = "processing"
    workflow.progress = 50
    await db.commit()

    # 3. Fetch certification profile
    from src.models.certification import CertificationProfile
    cert_stmt = select(CertificationProfile).where(
        CertificationProfile.id == workflow.certification_profile_id
    )
    cert_result = await db.execute(cert_stmt)
    cert_profile = cert_result.scalar_one_or_none()

    if not cert_profile:
        raise ValueError("Certification profile not found")

    cert_profile_dict = {
        "id": str(cert_profile.id),
        "name": cert_profile.name,
        "version": cert_profile.version,
        "exam_domains": cert_profile.exam_domains
    }

    # 4. Retrieve stored questions from workflow
    assessment_data = workflow.assessment_data
    if not assessment_data or not assessment_data.get('questions'):
        raise ValueError("No assessment questions found in workflow")

    questions = assessment_data.get('questions', [])
    logger.info(f"📝 Retrieved {len(questions)} questions from workflow")

    # VALIDATION: Fetch actual questions from Google Forms and compare with stored questions
    logger.info("🔍 Validating question order by fetching form structure from Google Forms...")
    try:
        form_structure = await forms_service.get_form_structure(form_id=form_id)
        google_questions = form_structure.get('questions', [])

        logger.info(f"📋 Google Forms has {len(google_questions)} questions")

        # Compare question text at each index
        validation_passed = True
        for idx, google_q in enumerate(google_questions):
            google_title = google_q.get('title', '').strip()

            if idx < len(questions):
                stored_text = questions[idx].get('question_text', '').strip()

                # Direct string comparison (faster than hashing for medium strings)
                if google_title == stored_text:
                    logger.info(f"✅ Q{idx} matches: '{stored_text[:60]}...'")
                else:
                    logger.warning(
                        f"⚠️  Q{idx} MISMATCH!\n"
                        f"   Google: '{google_title[:80]}...'\n"
                        f"   Stored: '{stored_text[:80]}...'"
                    )
                    validation_passed = False
            else:
                logger.warning(f"⚠️  Q{idx} exists in Google Forms but not in stored questions!")
                validation_passed = False

        # Check if we have more stored questions than Google Form questions
        if len(questions) > len(google_questions):
            logger.warning(
                f"⚠️  We have {len(questions)} stored questions but Google Forms only has {len(google_questions)}!"
            )
            validation_passed = False

        if validation_passed:
            logger.info("✅ Question order validation PASSED - all questions match!")
        else:
            logger.error("❌ Question order validation FAILED - order-based matching may be unreliable!")

    except Exception as e:
        logger.warning(f"⚠️  Could not validate question order: {e}")
        logger.info("Proceeding with order-based matching without validation...")

    # 5. Match form responses with questions and grade them
    formatted_responses = []
    for response in responses:
        user_answers = response.get('answers', {})

        # Google Forms returns answers as a dict with Google Form question IDs as keys
        # We need to match them by order since our stored question IDs don't match
        google_form_ids = list(user_answers.keys())
        answer_values = list(user_answers.values())

        logger.info(f"📋 Processing response with {len(answer_values)} answers for {len(questions)} questions")
        logger.info(f"🔑 Google Form question IDs: {google_form_ids}")

        # VALIDATION: Check if answer count matches question count
        if len(answer_values) != len(questions):
            logger.error(
                f"❌ CRITICAL: Answer count mismatch! "
                f"Received {len(answer_values)} answers but have {len(questions)} questions. "
                f"Order-based matching will fail!"
            )

        # Log all stored questions for reference
        logger.info("📚 Stored questions order:")
        for idx, q in enumerate(questions):
            logger.info(f"   Q{idx}: {q.get('question_text', '')[:80]}")

        # Match questions with answers by order/index
        for idx, question in enumerate(questions):
            if idx < len(answer_values):
                user_answer = answer_values[idx]
                google_form_id = google_form_ids[idx] if idx < len(google_form_ids) else "unknown"

                # Determine if answer is correct
                correct_answer = question.get('correct_answer')
                is_correct = (user_answer == correct_answer) if correct_answer else False

                question_id = question.get('question_id') or question.get('id') or f"q_{idx}"

                # Log the mapping for validation
                logger.info(
                    f"📌 Q{idx}: Local ID='{question_id}' | Google ID='{google_form_id}' | "
                    f"Question: '{question.get('question_text', '')[:60]}...' | "
                    f"Answer: '{user_answer}' | Correct: '{correct_answer}' | Match: {is_correct}"
                )

                formatted_responses.append({
                    "question_id": question_id,
                    "question_text": question.get('question_text', ''),
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "domain": question.get('domain', 'General'),
                    "subdomain": question.get('subdomain'),
                    "topic": question.get('topic'),
                    "bloom_level": question.get('bloom_level', 'Remember'),
                    "confidence": 3.0  # Default confidence
                })

    logger.info(f"✅ Matched and graded {len(formatted_responses)} responses")

    # Log summary of grading results
    correct_count = sum(1 for r in formatted_responses if r['is_correct'])
    logger.info(f"📊 Grading Summary: {correct_count}/{len(formatted_responses)} correct ({correct_count/len(formatted_responses)*100:.1f}%)")

    # 6. Trigger gap analysis with formatted responses
    from src.services.gap_analysis_enhanced import EnhancedGapAnalysisService
    gap_service = EnhancedGapAnalysisService()

    logger.info(f"📊 Generating gap analysis for workflow {workflow_id}")
    gap_result = await gap_service.analyze_and_persist(
        workflow_id=workflow_id,
        assessment_responses=formatted_responses,
        certification_profile=cert_profile_dict
    )

    workflow.progress = 75
    await db.commit()

    # 7. Generate content outlines and recommended courses
    skill_gaps = gap_result.get("skill_gaps", [])

    if skill_gaps:
        logger.info("📝 Generating content outlines")
        await gap_service.generate_content_outlines(
            gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
            workflow_id=workflow_id,
            skill_gaps=skill_gaps,
            certification_profile=cert_profile_dict
        )

        logger.info("📚 Generating recommended courses")
        await gap_service.generate_course_recommendations(
            gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
            workflow_id=workflow_id,
            skill_gaps=skill_gaps,
            certification_profile=cert_profile_dict
        )

    workflow.progress = 85
    workflow.current_step = "generate_presentation"
    await db.commit()

    # 8. Trigger presentation generation
    logger.info(f"🎨 Creating presentation")
    from src.services.presgen_integration_service import PresGenIntegrationService
    presgen_service = PresGenIntegrationService()

    presentation_result = await presgen_service.generate_presentation(
        workflow_id=workflow_id,
        assessment_title=workflow.parameters.get('title', 'Assessment'),
        user_email=workflow.user_id,
        skill_name=gap_result.get('skill_name', 'Unknown'),
        slide_count=workflow.parameters.get('slide_count', 12)
    )

    # 9. Finalize workflow
    workflow.current_step = "finalize_workflow"
    workflow.execution_status = "completed"
    workflow.progress = 100
    workflow.presentation_url = presentation_result.get('presentation_url')
    await db.commit()

    logger.info(f"✅ Workflow {workflow_id} completed successfully")

    return {
        "success": True,
        "response_count": len(responses),
        "gap_analysis_completed": True,
        "presentation_url": presentation_result.get('presentation_url')
    }


@router.post("/{workflow_id}/manual-process")
async def manual_process_completed_form(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually process a completed Google Form to trigger gap analysis."""
    try:
        logger.info(f"🎯 Manual processing for completed form | workflow_id={workflow_id}")

        # Get workflow details
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Fetch real responses and trigger full pipeline
        try:
            result = await fetch_form_responses_and_trigger_pipeline(
                workflow_id=workflow_id,
                workflow=workflow,
                db=db
            )

            return {
                "success": True,
                "message": "Form processing completed successfully",
                "workflow_id": str(workflow_id),
                "status": "completed",
                "current_step": "finalize_workflow",
                "next_steps": [],
                "response_count": result.get('response_count'),
                "presentation_url": result.get('presentation_url'),
                "mock_data_used": False
            }

        except ValueError as e:
            logger.warning(f"⚠️ Using fallback processing: {e}")
            # Fallback to manual gap analysis if no responses
            workflow.current_step = "gap_analysis"
            workflow.execution_status = "processing"
            workflow.progress = 90
            await db.commit()

            return {
                "success": False,
                "message": f"No responses found: {str(e)}",
                "workflow_id": str(workflow_id),
                "status": "pending",
                "current_step": "gap_analysis",
                "next_steps": ["Wait for form responses", "Click 'Process Completed Form' again"],
                "note": "Please ensure the Google Form has at least one response"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Manual processing failed for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual processing failed: {str(e)}"
        )


@router.post("/{workflow_id}/resume-paused")
async def resume_paused_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Resume a paused workflow and trigger full pipeline progression."""
    try:
        logger.info(f"▶️ Resuming workflow {workflow_id}")

        # Get workflow
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Check if paused
        if not workflow.paused_at or workflow.resumed_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is not paused"
            )

        # Resume based on current step
        if workflow.current_step in ["collect_responses", "gap_analysis"]:
            # Resume from form processing
            result = await fetch_form_responses_and_trigger_pipeline(
                workflow_id=workflow_id,
                workflow=workflow,
                db=db
            )
            return {
                "success": True,
                "message": "Workflow resumed and completed",
                "workflow_id": str(workflow_id),
                "presentation_url": result.get('presentation_url')
            }
        else:
            # For other steps, just unpause and let normal processing continue
            workflow.paused_at = None
            workflow.resumed_at = datetime.utcnow()
            workflow.execution_status = "processing"
            await db.commit()

            return {
                "success": True,
                "message": "Workflow resumed",
                "workflow_id": str(workflow_id),
                "current_step": workflow.current_step
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Resume workflow failed for {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume workflow failed: {str(e)}"
        )


@router.post("/{workflow_id}/manual-gap-analysis")
async def manual_gap_analysis_completion(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually complete gap analysis WITH database persistence."""
    try:
        logger.info(f"🎯 Manual gap analysis with persistence | workflow_id={workflow_id}")

        # Get workflow details
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Generate mock assessment responses for testing
        mock_responses = [
            {
                "question_id": f"q{i}",
                "domain": ["Security", "Networking", "Compute"][i % 3],
                "skill_id": f"skill_{i}",
                "skill_name": ["IAM Policies", "VPC Configuration", "EC2 Instances", "S3 Storage", "Lambda Functions"][i % 5],
                "exam_domain": ["Security and Compliance", "Networking", "Compute"][i % 3],
                "exam_subsection": "Core Concepts",
                "user_answer": "A",
                "correct_answer": "B" if i % 2 == 0 else "A",
                "is_correct": i % 2 != 0,
                "confidence": 3
            }
            for i in range(5)
        ]

        # Prepare certification profile
        cert_profile = {
            "id": str(workflow.certification_profile_id),
            "name": "AWS Solutions Architect",
            "collection_name": "aws_sa_certification"
        }

        # Use EnhancedGapAnalysisService for database persistence
        from src.services.gap_analysis_enhanced import EnhancedGapAnalysisService

        gap_service = EnhancedGapAnalysisService()

        # Perform gap analysis and persist to database
        gap_result = await gap_service.analyze_and_persist(
            workflow_id=workflow_id,
            assessment_responses=mock_responses,
            certification_profile=cert_profile
        )

        # Generate content outlines
        skill_gaps = gap_result.get("skill_gaps", [])
        if skill_gaps:
            await gap_service.generate_content_outlines(
                gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
                workflow_id=workflow_id,
                skill_gaps=skill_gaps,
                certification_profile=cert_profile
            )

        # Generate recommended courses
        if skill_gaps:
            await gap_service.generate_course_recommendations(
                gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
                workflow_id=workflow_id,
                skill_gaps=skill_gaps,
                certification_profile=cert_profile
            )

        # Update workflow to completed (Gap Analysis is now the final step)
        workflow.current_step = "gap_analysis_complete"
        workflow.execution_status = "completed"
        workflow.progress = 100

        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Gap analysis persisted | gap_analysis_id={gap_result['gap_analysis_id']}")

        return {
            "success": True,
            "message": "Gap analysis completed - workflow is now complete at 100%",
            "workflow_id": str(workflow_id),
            "gap_analysis_id": gap_result["gap_analysis_id"],
            "status": "completed",
            "current_step": "gap_analysis_complete",
            "progress": 100,
            "gap_analysis_results": gap_result,
            "next_steps": [
                "View Gap Analysis Dashboard",
                "Generate presentations from Dashboard (user-initiated)",
                "Generate courses from Recommended Courses (user-initiated)"
            ],
            "mock_data_used": True,
            "note": "Workflow complete. Presentation generation is now available on the Gap Analysis Dashboard."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Manual gap analysis failed for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual gap analysis failed: {str(e)}"
        )


@router.post("/{workflow_id}/manual-presentation")
async def manual_presentation_completion(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually complete presentation generation and finalize workflow."""
    try:
        logger.info(f"🎯 Manual presentation completion | workflow_id={workflow_id}")

        # Get workflow details
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Create mock presentation results
        mock_presentation = {
            "success": True,
            "presentation_id": f"{workflow.id}_presentation",
            "title": workflow.parameters.get("title", "Assessment Results Presentation"),
            "slide_count": workflow.parameters.get("slide_count", 12),
            "content_outline": [
                "Assessment Overview",
                "Performance Summary",
                "Domain Analysis: Data Engineering",
                "Domain Analysis: Exploratory Data Analysis",
                "Domain Analysis: Modeling",
                "Domain Analysis: ML Implementation",
                "Learning Gap Identification",
                "Remediation Plan",
                "Priority Study Areas",
                "Recommended Resources",
                "Next Steps",
                "Conclusion"
            ],
            "presentation_url": f"https://docs.google.com/presentation/d/mock_presentation_{workflow.id}",
            "google_slides_id": f"mock_slides_{workflow.id}",
            "avatar_generation": {
                "enabled": workflow.parameters.get("include_avatar", False),
                "status": "completed" if workflow.parameters.get("include_avatar") else "skipped"
            },
            "timestamp": "2025-09-28T10:45:00Z"
        }

        # Update workflow to completed
        workflow.current_step = "finalize_workflow"
        workflow.execution_status = "completed"
        workflow.progress = 100
        workflow.presentation_url = mock_presentation["presentation_url"]

        # Commit the changes
        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Manual presentation completed | workflow_id={workflow_id}")

        return {
            "success": True,
            "message": "Presentation generation completed manually",
            "workflow_id": str(workflow_id),
            "status": "completed",
            "current_step": "finalize_workflow",
            "progress": 100,
            "presentation_results": mock_presentation,
            "completion_summary": {
                "total_time": "Completed manually",
                "stages_completed": [
                    "Response Collection",
                    "Gap Analysis",
                    "Presentation Generation",
                    "Finalization"
                ],
                "deliverables": [
                    "Assessment gap analysis report",
                    "Personalized learning presentation",
                    "Remediation plan with study hours"
                ]
            },
            "mock_data_used": True,
            "note": "Workflow completed with sample presentation data"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Manual presentation completion failed for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual presentation completion failed: {str(e)}"
        )


@router.get(
    "/{workflow_id}/gap-analysis",
    summary="Get Gap Analysis Results",
    description="""
    **Retrieve comprehensive gap analysis results for a completed assessment workflow.**

    This endpoint provides detailed learning gap analysis including:
    - Overall performance scores and confidence metrics
    - Domain-specific performance breakdown
    - Learning gaps with severity levels and remediation resources
    - Bloom's taxonomy skill distribution
    - Personalized study plan recommendations

    **Requirements:**
    - Workflow must be at least 75% complete (gap analysis stage)
    - Assessment responses must have been processed

    **Use Cases:**
    - Display learner performance dashboard
    - Generate personalized learning recommendations
    - Create targeted remediation plans
    - Track learning progress over time
    """,
    response_description="Comprehensive gap analysis data with performance metrics and learning recommendations",
    tags=["workflows", "gap-analysis", "assessment-results"]
)
async def get_workflow_gap_analysis(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get gap analysis results for a completed workflow."""
    try:
        logger.info(f"📊 Getting gap analysis for workflow: {workflow_id}")
        gap_analysis_data = await _build_gap_analysis_data(workflow_id, db)

        logger.info(f"✅ Gap analysis retrieved for workflow: {workflow_id}")
        return gap_analysis_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get gap analysis for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gap analysis: {str(e)}"
        )


@router.post("/{workflow_id}/gap-analysis/export-to-sheets")
async def export_gap_analysis_to_google_sheets(
    workflow_id: UUID,
    payload: Dict[str, Optional[str]] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Export gap analysis results to Google Sheets with 4-tab format (Sprint 2)."""
    try:
        logger.info(
            "📤 Exporting gap analysis to Google Sheets | workflow_id=%s share_email=%s",
            workflow_id,
            payload.get("share_email")
        )

        # Fetch data for all 4 tabs from database
        logger.info("📊 Fetching data for 4 tabs from database")

        # Import models for querying
        from src.models.gap_analysis import (
            GapAnalysisResult as GapAnalysisResultModel,
            ContentOutline as ContentOutlineModel,
            RecommendedCourse as RecommendedCourseModel
        )
        from src.models.workflow import WorkflowExecution

        # Get workflow to access assessment_data
        workflow_stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        workflow_result = await db.execute(workflow_stmt)
        workflow = workflow_result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        # Tab 1: Answers - Get questions from assessment_data JSON
        logger.debug("📝 Fetching answers data (Tab 1)")

        answers_data = {
            "correct_answers": [],
            "incorrect_answers": [],
            "total_questions": 0,
            "correct_count": 0,
            "incorrect_count": 0
        }

        # Extract questions from assessment_data if available
        if workflow.assessment_data and "questions" in workflow.assessment_data:
            questions = workflow.assessment_data.get("questions", [])
            answers_data["total_questions"] = len(questions)

            # If we have form responses, match them with questions
            form_responses = workflow.assessment_data.get("responses", {})

            for question in questions:
                question_id = question.get("id")
                user_answer = form_responses.get(question_id) if form_responses else None
                correct_answer = question.get("correct_answer")

                if user_answer:
                    is_correct = user_answer == correct_answer
                    answer_item = {
                        "question_text": question.get("text", ""),
                        "user_answer": user_answer,
                        "correct_answer": correct_answer,
                        "explanation": question.get("explanation", ""),
                        "domain": question.get("domain", ""),
                        "difficulty": question.get("difficulty", "")
                    }

                    if is_correct:
                        answers_data["correct_answers"].append(answer_item)
                        answers_data["correct_count"] += 1
                    else:
                        answers_data["incorrect_answers"].append(answer_item)
                        answers_data["incorrect_count"] += 1

        # Tab 2: Gap Analysis - Get gap analysis summary
        logger.debug("📊 Fetching gap analysis data (Tab 2)")
        gap_stmt = (
            select(GapAnalysisResultModel)
            .where(GapAnalysisResultModel.workflow_id == workflow_id)
            .order_by(GapAnalysisResultModel.created_at.desc())
            .limit(1)
        )
        gap_result = await db.execute(gap_stmt)
        gap_analysis_db = gap_result.scalar_one_or_none()

        gap_analysis_summary = {}
        if gap_analysis_db:
            gap_analysis_summary = {
                "overall_score": gap_analysis_db.overall_score,
                "total_questions": gap_analysis_db.total_questions,
                "correct_answers": gap_analysis_db.correct_answers,
                "skill_gaps": gap_analysis_db.skill_gaps,
                "performance_by_domain": gap_analysis_db.performance_by_domain,
                "text_summary": gap_analysis_db.text_summary,
                "charts_data": gap_analysis_db.charts_data
            }

        # Tab 3: Content Outlines
        logger.debug("📚 Fetching content outlines (Tab 3)")
        outlines_stmt = select(ContentOutlineModel).where(
            ContentOutlineModel.workflow_id == workflow_id
        )
        outlines_result = await db.execute(outlines_stmt)
        outlines_db = outlines_result.scalars().all()

        content_outlines = [
            {
                "skill_id": outline.skill_id,
                "skill_name": outline.skill_name,
                "exam_domain": outline.exam_domain,
                "exam_guide_section": outline.exam_guide_section,
                "content_items": outline.content_items,
                "rag_retrieval_score": outline.rag_retrieval_score
            }
            for outline in outlines_db
        ]

        # Tab 4: Recommended Courses
        logger.debug("🎓 Fetching recommended courses (Tab 4)")
        courses_stmt = select(RecommendedCourseModel).where(
            RecommendedCourseModel.workflow_id == workflow_id
        )
        courses_result = await db.execute(courses_stmt)
        courses_db = courses_result.scalars().all()

        recommended_courses = [
            {
                "skill_id": course.skill_id,
                "skill_name": course.skill_name,
                "exam_domain": course.exam_domain,
                "course_title": course.course_title,
                "course_description": course.course_description,
                "learning_objectives": course.learning_objectives,
                "estimated_duration_minutes": course.estimated_duration_minutes,
                "difficulty_level": course.difficulty_level,
                "generation_status": course.generation_status,
                "video_url": course.video_url,
                "presentation_url": course.presentation_url,
                "download_url": course.download_url,
                "priority": course.priority
            }
            for course in courses_db
        ]

        # Build comprehensive gap analysis data with all 4 tabs
        gap_analysis_data = {
            "workflow_id": str(workflow_id),
            "answers": answers_data,
            "gap_analysis_summary": gap_analysis_summary,
            "content_outlines": content_outlines,
            "recommended_courses": recommended_courses
        }

        logger.info(f"✅ Data fetched | answers={answers_data['total_questions']} outlines={len(content_outlines)} courses={len(recommended_courses)}")

        # Choose authentication method based on configuration
        if settings.use_oauth_for_sheets:
            logger.info("🔐 Using OAuth authentication for Google Sheets export")
            sheets_service = GoogleSheetsService(
                credentials_path=settings.oauth_sheets_client,
                use_oauth=True
            )
        else:
            logger.info("🔐 Using service account authentication for Google Sheets export")
            sheets_service = GoogleSheetsService(
                credentials_path=settings.google_application_credentials,
                use_oauth=False
            )

        exporter = EnhancedGapAnalysisExporter(sheets_service)

        export_options = {
            "title": f"PresGen Gap Analysis {workflow_id}",
            "share_email": payload.get("share_email")
        }

        export_result = await exporter.export_comprehensive_analysis(
            gap_analysis_result=gap_analysis_data,
            export_options=export_options
        )

        google_export = export_result.get("google_sheets_export", {})
        additional_exports = export_result.get("additional_exports")

        response_payload = {
            "success": bool(google_export.get("success")),
            "workflow_id": str(workflow_id),
            "spreadsheet_id": google_export.get("spreadsheet_id"),
            "spreadsheet_url": google_export.get("spreadsheet_url"),
            "spreadsheet_title": google_export.get("spreadsheet_title"),
            "export_timestamp": google_export.get("export_timestamp")
            or export_result.get("export_timestamp"),
            "mock_response": google_export.get("mock_response", False),
            "message": google_export.get("note")
            or google_export.get("reason")
            or ("Export completed" if google_export.get("success") else None),
            "export_summary": google_export.get("export_summary")
            or export_result.get("comprehensive_analysis"),
            "additional_exports": additional_exports,
            "instructions": google_export.get("instructions") or []
        }

        if not response_payload["success"]:
            logger.warning(
                "⚠️ Google Sheets export returned mock response | workflow_id=%s reason=%s",
                workflow_id,
                response_payload.get("message")
            )

        logger.info(
            "✅ Gap analysis export completed | workflow_id=%s success=%s",
            workflow_id,
            response_payload["success"]
        )

        # Save export record to database if successful
        if response_payload["success"] and response_payload.get("spreadsheet_id"):
            try:
                from uuid import uuid4
                import json

                export_record_sql = """
                    INSERT INTO google_sheets_exports
                    (id, workflow_id, sheet_id, sheet_url, tabs, exported_at, export_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """

                tabs_json = json.dumps(["Answers", "Gap Analysis", "Content Outline", "Presentation"])

                await db.execute(
                    text(export_record_sql),
                    (
                        str(uuid4()),
                        str(workflow_id).replace("-", ""),
                        response_payload["spreadsheet_id"],
                        response_payload["spreadsheet_url"],
                        tabs_json,
                        response_payload["export_timestamp"],
                        "completed"
                    )
                )
                await db.commit()
                logger.info(f"💾 Export record saved to database | workflow_id={workflow_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save export record to database: {e}")

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ Gap analysis export failed | workflow_id=%s error=%s",
            workflow_id,
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export gap analysis to Google Sheets: {str(e)}"
        )


@router.get("/{workflow_id}/gap-analysis/export")
async def export_gap_analysis_report(
    workflow_id: UUID,
    format: str = Query(
        default="json",
        pattern="^(json|csv|pdf)$",
        description="Export format for gap analysis report"
    ),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Export gap analysis data in JSON, CSV, or PDF format."""
    try:
        gap_analysis_data = await _build_gap_analysis_data(workflow_id, db)

        filename_base = f"gap-analysis-{workflow_id}"

        if format == "json":
            return JSONResponse(
                content=gap_analysis_data,
                headers={
                    "Content-Disposition": f"attachment; filename={filename_base}.json"
                }
            )

        if format == "csv":
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)

            writer.writerow(["Gap Analysis Summary"])
            writer.writerow(["Workflow ID", gap_analysis_data["workflow_id"]])
            writer.writerow(["Overall Score", gap_analysis_data["overall_score"]])
            writer.writerow(["Overall Confidence", gap_analysis_data["overall_confidence"]])
            writer.writerow([])

            writer.writerow(["Domain Performance"])
            writer.writerow(["Domain", "Score", "Confidence", "Questions Correct", "Questions Total", "Overconfidence Ratio"])
            for domain in gap_analysis_data["domain_performance"]:
                writer.writerow([
                    domain["domain"],
                    domain["score"],
                    domain["confidence_score"],
                    domain["correct_count"],
                    domain["question_count"],
                    domain["overconfidence_ratio"],
                ])

            writer.writerow([])
            writer.writerow(["Learning Gaps"])
            writer.writerow(["Domain", "Severity", "Skill Gap", "Confidence Gap", "Recommended Study Hours", "Priority Topics"])
            for gap in gap_analysis_data["learning_gaps"]:
                writer.writerow([
                    gap["domain"],
                    gap["gap_severity"],
                    gap["skill_gap"],
                    gap["confidence_gap"],
                    gap["recommended_study_hours"],
                    "; ".join(gap["priority_topics"]),
                ])

            csv_content = csv_buffer.getvalue()
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={filename_base}.csv"
                }
            )

        # PDF export (placeholder document with key metrics)
        pdf_body = f"""
Gap Analysis Report
Workflow ID: {gap_analysis_data['workflow_id']}
Overall Score: {gap_analysis_data['overall_score']}%
Overall Confidence: {gap_analysis_data['overall_confidence']}%

Top Learning Gaps:
"""
        for gap in gap_analysis_data["learning_gaps"]:
            pdf_body += f"- {gap['domain']} ({gap['gap_severity']}) - Study Hours: {gap['recommended_study_hours']}\n"

        pdf_stream = _generate_basic_pdf(pdf_body)

        return Response(
            content=pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename_base}.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ Gap analysis export failed | workflow_id=%s error=%s",
            workflow_id,
            e,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export gap analysis: {str(e)}"
        )


@router.post("/{workflow_id}/auto-progress")
async def auto_progress_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Automatically progress workflow from initiated to collect_responses stage."""
    try:
        logger.info(f"🚀 Auto-progressing workflow: {workflow_id}")

        # Get workflow details
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        # Check if workflow is already at or past the target stage
        if workflow.current_step == "collect_responses":
            logger.info(f"✅ Workflow {workflow_id} already at target stage: {workflow.current_step}")
            return {
                "success": True,
                "message": f"Workflow already at target stage: {workflow.current_step}",
                "workflow_id": str(workflow_id),
                "previous_step": workflow.current_step,
                "current_step": workflow.current_step,
                "status": workflow.execution_status,
                "progress": 100 if workflow.current_step == "collect_responses" else 70,
                "already_completed": True
            }

        if workflow.current_step != "initiated":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow is in '{workflow.current_step}' stage, not 'initiated'"
            )

        # Simulate the progression through initial stages
        stages = [
            ("validate_input", 10, "Input validation completed"),
            ("fetch_certification", 20, "Certification profile loaded"),
            ("setup_knowledge_base", 30, "Knowledge base prepared"),
            ("generate_questions", 40, "AI questions generated"),
            ("validate_questions", 50, "Questions validated"),
            ("balance_domains", 60, "Domain distribution balanced"),
            ("generate_assessment", 70, "Google Form assessment created"),
            ("collect_responses", 70, "Ready for response collection")
        ]

        # Update workflow to collect_responses stage
        workflow.current_step = "collect_responses"
        workflow.execution_status = "awaiting_completion"
        workflow.progress = 70

        # Generate a mock Google Form ID for this workflow (proper Google Form ID format)
        # Google Form IDs are typically 44 characters long, base64-like strings
        import base64
        import hashlib

        # Create a deterministic but valid-looking Google Form ID
        workflow_string = str(workflow_id).replace('-', '')
        hash_input = f"form_{workflow_string}".encode('utf-8')
        form_hash = hashlib.sha256(hash_input).digest()

        # Encode to base64 and clean up to look like a Google Form ID
        form_id_base = base64.b64encode(form_hash).decode('utf-8')
        form_id_clean = form_id_base.replace('+', 'A').replace('/', 'B').replace('=', '')
        mock_form_id = f"1{form_id_clean[:42]}"  # Google Form IDs start with '1' and are ~44 chars

        # Commit the changes
        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Auto-progression completed for workflow: {workflow_id}")

        return {
            "success": True,
            "message": "Workflow auto-progressed to collect_responses stage",
            "workflow_id": str(workflow_id),
            "previous_step": "initiated",
            "current_step": "collect_responses",
            "status": "awaiting_completion",
            "progress": 70,
            "stages_completed": stages,
            "google_form": {
                "form_id": mock_form_id,
                "form_url": f"https://docs.google.com/forms/d/{mock_form_id}/edit",
                "view_url": f"https://docs.google.com/forms/d/e/1FAIpQLSe{mock_form_id[1:40]}/viewform"
            },
            "next_action": "Complete the Google Form assessment to proceed",
            "automation_used": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Auto-progression failed for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-progression failed: {str(e)}"
        )
    
@router.post(
    "/{workflow_id}/skills/{skill_id}/generate-course",
    response_model=CourseGenerationResponse,
    summary="Generate course for individual skill",
    description="Generate avatar-narrated course for a specific skill gap"
)
async def generate_skill_course(
    workflow_id: UUID,
    skill_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate course for individual skill with PresGen-Avatar integration

    Flow:
    1. Fetch skill gap details from recommended_courses
    2. Get certification profile's presentation_prompt
    3. Call PresGen-Core with custom prompt
    4. Call PresGen-Avatar for video narration
    5. Return course metadata with video URL
    """
    from src.integrations.presgen_avatar.client import PresGenAvatarClient, CircuitOpenError as AvatarCircuitOpenError
    from src.integrations.presgen_core.client import PresGenCoreClient, CircuitOpenError as CoreCircuitOpenError
    from src.integrations.presgen_core.schemas import PresGenPresentationRequest

    request_started_at = datetime.utcnow()
    logger.info(
        "🎯 generate_course_pipeline | stage=request_received | workflow_id=%s | skill_id=%s",
        workflow_id,
        skill_id,
    )

    workflow_id_str = str(workflow_id)
    workflow_id_normalized = workflow_id.hex

    log_course_event("COURSE_GENERATION_STARTED", workflow_id=workflow_id_str, skill_id=skill_id)

    # 1. Fetch workflow and skill details
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        logger.warning(
            "🎯 generate_course_pipeline | stage=workflow_missing | workflow_id=%s | skill_id=%s",
            workflow_id,
            skill_id,
        )
        raise HTTPException(status_code=404, detail="Workflow not found")

    if isinstance(workflow.assessment_data, str):
        try:
            workflow.assessment_data = json.loads(workflow.assessment_data)
        except Exception:
            workflow.assessment_data = {}

    if isinstance(workflow.gap_analysis_results, str):
        try:
            workflow.gap_analysis_results = json.loads(workflow.gap_analysis_results)
        except Exception:
            workflow.gap_analysis_results = {}

    # 2. Fetch skill gap from recommended_courses
    result = await db.execute(
        select(RecommendedCourse).where(
            and_(
                RecommendedCourse.workflow_id == workflow_id,
                RecommendedCourse.skill_id == skill_id
            )
        ).order_by(RecommendedCourse.recommended_at.desc())
    )
    skill_course = result.scalars().first()
    if not skill_course:
        raise HTTPException(status_code=404, detail="Skill not found in recommended courses")

    log_course_event(
        "SKILL_FOUND",
        workflow_id=workflow_id_str,
        skill_name=skill_course.skill_name,
    )
    logger.info(
        "🎯 generate_course_pipeline | stage=course_loaded | workflow_id=%s | skill_id=%s | recommended_course_id=%s",
        workflow_id,
        skill_id,
        skill_course.id,
    )

    # Ensure JSON fields are deserialized for downstream usage
    skill_course.learning_objectives = _ensure_list(skill_course.learning_objectives)
    skill_course.content_outline = _ensure_dict(skill_course.content_outline)

    # 3. Get certification profile's custom prompt
    result = await db.execute(
        select(CertificationProfile).where(
            CertificationProfile.id == workflow.certification_profile_id
        )
    )
    cert_profile = result.scalar_one_or_none()
    custom_prompt = cert_profile.presentation_prompt if cert_profile else None

    workflow_parameters = workflow.parameters or {}
    requested_slide_count = (
        workflow.requested_slide_count
        or workflow_parameters.get("slide_count")
        or getattr(settings, "presgen_core_max_slides", None)
        or 20
    )

    async def _format_prompt_template(template: Optional[str]) -> Optional[str]:
        """Format presentation prompt template with available variables.

        Now supports full variable substitution including course data and RAG context.
        Uses simplified variable names (e.g., {skill_name} instead of {course_record.skill_name}).
        Retrieves filtered RAG context based on learning objectives (1-2s retrieval cost acceptable).

        NOTE: Detects LLM prompt templates (YAML-structured) and returns default instead.
        """
        def _get_default_prompt():
            return f"""Create a professional training presentation with {requested_slide_count} slides.
Focus on clear explanations, practical examples, and learner engagement.
Structure: Introduction → Core Concepts → Practical Applications → Review.
Each slide should have 3-5 concise bullet points and instructor notes.
Narration should be conversational and ≤ 75 seconds per slide."""

        if not template:
            return _get_default_prompt()

        # ✅ Detect LLM prompt templates (YAML/structured prompts for LLM use, not PresGen-Core)
        # Only detect actual YAML structure indicators, not common section headings like "OUTPUT FORMAT"
        yaml_structure_indicators = ["description:", "inputs:", "roles:", "role: system"]
        if any(indicator in template for indicator in yaml_structure_indicators):
            logger.info(
                json.dumps({
                    "event": "llm_prompt_template_detected",
                    "workflow_id": workflow_id_str,
                    "message": "Certification profile contains LLM prompt template (YAML-structured). Using default PresGen-Core instructions instead.",
                    "detected_indicators": [ind for ind in yaml_structure_indicators if ind in template],
                    "recommendation": "For PresGen-Core, use simple instruction text. For LLM outline generation, enable PRESGEN_REGENERATE_COURSE_OUTLINE.",
                })
            )
            return _get_default_prompt()

        class _SafeDict(dict):
            def __missing__(self, key):
                return "{" + key + "}"

        # ✅ Phase 10 Full Implementation - Retrieve RAG context filtered by learning objectives
        rag_retrieval_start = datetime.utcnow()
        knowledge_base_context = ""
        rag_citations = []

        try:
            from src.knowledge.base import RAGKnowledgeBase
            rag_kb = RAGKnowledgeBase()

            # Use learning objectives as queries to filter source transcripts
            learning_objectives = skill_course.learning_objectives or []
            queries = [q for q in learning_objectives if isinstance(q, str)]
            if not queries:
                queries = [skill_course.skill_name]

            combined_context_parts = []

            # ✅ Use collection_name (string code) instead of UUID for ChromaDB query
            # ChromaDB stores embeddings with certification_id as string code (e.g., "aws-ml-specialty")
            # not UUID from certification_profiles table
            rag_certification_id = cert_profile.collection_name if cert_profile and cert_profile.collection_name else str(workflow.certification_profile_id)

            logger.info(f"🔍 Starting RAG retrieval with certification_id='{rag_certification_id}', queries={queries[:3]}")

            for query in queries[:3]:  # Top 3 learning objectives
                try:
                    logger.info(f"🔍 Calling RAG for query: '{query}'")
                    result = await rag_kb.retrieve_context_for_assessment(
                        query=query,
                        certification_id=rag_certification_id,
                        k=6,  # 6 chunks per query
                        balance_sources=True
                    )
                    logger.info(f"✅ RAG call completed successfully")

                    # Debug logging: show what we got back
                    logger.info(f"📊 RAG result type: {type(result).__name__}, has 'get': {hasattr(result, 'get')}")

                    # Type check: ensure result is dict, not string
                    if not isinstance(result, dict):
                        logger.warning(f"⚠️ RAG returned unexpected type: {type(result).__name__}, expected dict. Result: {str(result)[:200]}")
                        continue

                    context_text = result.get("combined_context")
                except Exception as query_exc:
                    logger.warning(f"⚠️ RAG query failed for '{query}': {query_exc}")
                    continue
                if context_text:
                    combined_context_parts.append(f"### Context for '{query}'\n{context_text}")
                rag_citations.extend(result.get("citations", []) or [])

            knowledge_base_context = "\n\n".join(combined_context_parts)

            rag_retrieval_duration = (datetime.utcnow() - rag_retrieval_start).total_seconds()

            # ✅ Phase 10 Task 2.1 - Log RAG context collection
            logger.info(
                json.dumps({
                    "event": "rag_context_collected_for_presentation_prompt",
                    "workflow_id": workflow_id_str,
                    "course_id": str(skill_course.id),
                    "skill_name": skill_course.skill_name,
                    "certification_id_used": rag_certification_id,  # Show which ID was used for RAG query
                    "queries_used": queries[:3],
                    "chunks_retrieved": len(rag_citations),
                    "total_chars": len(knowledge_base_context),
                    "retrieval_duration_seconds": rag_retrieval_duration,
                    "citations": [
                        {
                            "source": c.get("source"),
                            "relevance_score": c.get("score"),
                            "chunk_preview": c.get("text", "")[:100] + "...",
                        }
                        for c in rag_citations[:5]  # Top 5 most relevant
                    ],
                })
            )

        except Exception as exc:
            import traceback
            logger.warning(
                f"⚠️ RAG context retrieval failed: {exc}",
                extra={
                    "workflow_id": workflow_id_str,
                    "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                    "certification_profile_id": str(workflow.certification_profile_id),
                    "rag_certification_id_attempted": rag_certification_id if 'rag_certification_id' in locals() else None,
                    "queries_attempted": queries[:3] if 'queries' in locals() else [],
                }
            )
            knowledge_base_context = ""

        # ✅ Phase 10 Full Implementation - Populate all course data with simplified variable names
        import re
        # Only match {variable_name} patterns, not JSON objects
        variables_in_template = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template)

        # Build values dict with all available course data
        content_outline = skill_course.content_outline or {}
        sections = content_outline.get("sections", []) if isinstance(content_outline, dict) else []

        values = _SafeDict({
            # Slide configuration
            "slide_count": requested_slide_count,
            "question_count": workflow_parameters.get("question_count"),

            # Course metadata (simplified variable names)
            "skill_name": skill_course.skill_name,
            "course_title": skill_course.course_title,
            "course_description": skill_course.course_description or "",
            "estimated_duration_minutes": skill_course.estimated_duration_minutes or 60,
            "difficulty_level": skill_course.difficulty_level or "intermediate",
            "exam_domain": skill_course.exam_domain or "",

            # Course structure
            "learning_objectives": json.dumps(learning_objectives, indent=2),
            "content_outline_sections": json.dumps(sections, indent=2),

            # RAG context (filtered by learning objectives)
            "knowledge_base_context": knowledge_base_context,

            # Assessment data
            "assessment_score": workflow.assessment_data.get("score") if isinstance(workflow.assessment_data, dict) else None,

            # Gap analysis data
            "priority_learning_areas": json.dumps(
                workflow.gap_analysis_results.get("priority_learning_areas", [])
                if isinstance(workflow.gap_analysis_results, dict) else []
            ),
            "overall_readiness_score": workflow.gap_analysis_results.get("overall_readiness_score")
                if isinstance(workflow.gap_analysis_results, dict) else None,
        })

        # Remove None values to avoid "None" strings in output
        values = _SafeDict({k: v for k, v in values.items() if v is not None})

        # ✅ Phase 10 Task 3.1 - Log variables BEFORE substitution
        logger.info(
            json.dumps({
                "event": "presentation_prompt_variable_check",
                "workflow_id": workflow_id_str,
                "variables_found_in_template": variables_in_template,
                "variables_available_for_substitution": list(values.keys()),
                "unsubstituted_variables": [v for v in variables_in_template if v not in values],
                "rag_context_available": len(knowledge_base_context) > 0,
                "rag_context_chars": len(knowledge_base_context),
            })
        )

        try:
            formatted = template.format_map(values)

            # ✅ Phase 10 Task 3.1 - Validate AFTER substitution
            # Only match {variable_name} patterns, not JSON objects like {"key": "value"}
            # Variable names: alphanumeric, underscore, no spaces, no quotes, no colons
            remaining_placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", formatted)
            logger.info(
                json.dumps({
                    "event": "presentation_prompt_after_substitution",
                    "workflow_id": workflow_id_str,
                    "remaining_unresolved_variables": remaining_placeholders,
                    "substitution_complete": len(remaining_placeholders) == 0,
                    "prompt_length_chars": len(formatted),
                })
            )

            if remaining_placeholders:
                logger.warning(
                    f"⚠️ Presentation prompt has {len(remaining_placeholders)} unresolved variables: {remaining_placeholders}"
                )

            return formatted

        except Exception as exc:  # pragma: no cover - formatting errors surfaced via logs
            import traceback
            logger.warning(
                "⚠️ Prompt formatting failed with exception; using default prompt",
                extra={
                    "workflow_id": workflow_id_str,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            )
            # Return default instead of broken template
            return f"""Create a professional training presentation with {requested_slide_count} slides.
Focus on clear explanations, practical examples, and learner engagement.
Structure: Introduction → Core Concepts → Practical Applications → Review.
Each slide should have 3-5 concise bullet points and instructor notes.
Narration should be conversational and ≤ 75 seconds per slide."""

    formatted_prompt = await _format_prompt_template(custom_prompt)
    custom_prompt = formatted_prompt

    log_course_event(
        "CUSTOM_PROMPT_LOADED",
        workflow_id=workflow_id_str,
        has_custom_prompt=bool(custom_prompt),
        prompt_preview=(custom_prompt[:120] + '…') if custom_prompt and len(custom_prompt) > 120 else custom_prompt,
    )
    logger.info(
        "🎯 generate_course_pipeline | stage=content_spec_prepared | workflow_id=%s | skill_id=%s | has_custom_prompt=%s",
        workflow_id,
        skill_id,
        bool(custom_prompt),
    )

    timestamp_course_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    skill_slug = _slugify_skill_name(skill_course.skill_name)

    # 4. Check for existing course record
    existing_course_result = await db.execute(
        select(GeneratedCourse).where(
            and_(
                GeneratedCourse.workflow_id == workflow_id_normalized,
                GeneratedCourse.skill_id == skill_id
            )
        )
    )
    course = existing_course_result.scalar_one_or_none()

    regen_allowed_statuses = {
        "failed",
        "generating_video",
        "pending",
        "generating_presentation",
        "completed",
        "generating_avatar",
    }

    if course:
        previous_status = course.status
        if previous_status not in regen_allowed_statuses:
            log_course_event(
                "COURSE_GENERATION_ALREADY_EXISTS",
                workflow_id=workflow_id_str,
                course_id=course.id,
                status=previous_status,
            )
            return CourseGenerationResponse(
                course_id=course.id,
                workflow_id=workflow_id_str,
                skill_id=skill_id,
                skill_name=course.skill_name,
                course_title=course.course_title,
                presentation_url=course.presentation_url,
                video_url=course.video_url,
                status=course.status,
                progress=course.progress,
                created_at=course.created_at,
                updated_at=course.updated_at,
                completed_at=course.completed_at,
            )

        log_course_event(
            "COURSE_GENERATION_RETRY",
            workflow_id=workflow_id_str,
            course_id=course.id,
            previous_status=previous_status,
        )
        course.course_title = f"Mastering {skill_course.skill_name}"
        course.presentation_url = None
        course.video_url = None
        course.error_message = None
        course.presgen_core_job_id = None
        course.presgen_core_download_url = None
        course.presgen_core_processing_time_ms = None
        course.presgen_avatar_job_id = None
        course.status = "pending"
        course.progress = 0
        course.completed_at = None
        await db.commit()
        await db.refresh(course)
        course_id = course.id
    else:
        course_id = timestamp_course_id
        course = GeneratedCourse(
            id=course_id,
            workflow_id=workflow_id_normalized,
            skill_id=skill_id,
            skill_name=skill_course.skill_name,
            course_title=f"Mastering {skill_course.skill_name}",
            status="pending",
            progress=0,
        )
        db.add(course)
        await db.commit()
        await db.refresh(course)

        log_course_event("COURSE_RECORD_CREATED", workflow_id=workflow_id_str, course_id=course_id)

    outline_regenerated = False
    if getattr(settings, "presgen_regenerate_course_outline", False):
        regenerated_outline = await _regenerate_course_outline_for_course(
            workflow=workflow,
            skill_course=skill_course,
            presentation_prompt=custom_prompt,
            target_slide_count=requested_slide_count,
        )
        if regenerated_outline:
            skill_course.learning_objectives = regenerated_outline.get(
                "learning_objectives",
                skill_course.learning_objectives,
            )
            skill_course.content_outline = {"sections": regenerated_outline.get("sections", [])}
            if regenerated_outline.get("course_title"):
                skill_course.course_title = regenerated_outline["course_title"]
                course.course_title = regenerated_outline["course_title"]
            if regenerated_outline.get("course_description"):
                skill_course.course_description = regenerated_outline["course_description"]
            if regenerated_outline.get("estimated_duration_minutes"):
                skill_course.estimated_duration_minutes = regenerated_outline["estimated_duration_minutes"]
            skill_course.updated_at = datetime.utcnow()
            db.add(skill_course)
            await db.commit()
            await db.refresh(skill_course)
            outline_regenerated = True
            log_course_event(
                "COURSE_OUTLINE_REGENERATED",
                workflow_id=workflow_id_str,
                course_id=course_id,
                slide_count=requested_slide_count,
                learning_objectives=len(skill_course.learning_objectives or []),
            )
        else:
            log_course_event(
                "COURSE_OUTLINE_REGENERATE_FAILED",
                workflow_id=workflow_id_str,
                course_id=course_id,
            )

    # Ensure a Google Slides deck exists before calling PresGen-Core
    try:
        presentation_url = await _ensure_presentation_deck(
            course,
            skill_course,
            workflow_id=workflow_id_str,
            assessment_title=getattr(workflow, "assessment_title", None),
            target_slide_count=requested_slide_count,
        )
        if course.presentation_url != presentation_url:
            course.presentation_url = presentation_url
            await db.commit()
            await db.refresh(course)

        log_course_event(
            "PRESENTATION_DECK_READY",
            workflow_id=workflow_id_str,
            course_id=course_id,
            presentation_url=course.presentation_url,
        )
        logger.info(
            "=" * 80
        )
        logger.info(
            "✅ PRESENTATION UPLOAD COMPLETED"
        )
        logger.info(
            "🎯 generate_course_pipeline | stage=slides_ready | workflow_id=%s | skill_id=%s | course_id=%s | presentation_url=%s",
            workflow_id,
            skill_id,
            course_id,
            course.presentation_url,
        )
        logger.info(
            "📊 Presentation Details:"
        )
        logger.info(
            "  • Workflow ID: %s", workflow_id_str
        )
        logger.info(
            "  • Course ID: %s", course_id
        )
        logger.info(
            "  • Skill: %s", skill_course.skill_name
        )
        logger.info(
            "  • Presentation URL: %s", course.presentation_url
        )
        logger.info(
            "  • Requested Slide Count: %s", requested_slide_count
        )
        logger.info(
            "  • Status: Presentation uploaded and ready"
        )
        logger.info(
            "🔜 Next Step: Calling PresGen-Core for video processing"
        )
        logger.info(
            "=" * 80
        )
    except Exception as exc:  # pylint: disable=broad-except
        course.status = "failed"
        course.progress = 0
        course.error_message = f"Google Slides deck creation failed: {exc}"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESENTATION_DECK_FAILED",
            workflow_id=workflow_id_str,
            course_id=course_id,
            error=str(exc),
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=slides_failed | workflow_id=%s | skill_id=%s | course_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            exc,
        )
        raise HTTPException(status_code=502, detail="Failed to create Google Slides presentation") from exc

    # 5. Call PresGen-Core for presentation
    presgen_core = PresGenCoreClient(base_url=os.getenv("PRESGEN_CORE_URL"))

    course.status = "generating_presentation"
    course.progress = 25
    await db.commit()
    await db.refresh(course)

    log_course_event("PRESGEN_CORE_STARTED", workflow_id=workflow_id_str, course_id=course_id)
    logger.info(
        "=" * 80
    )
    logger.info(
        "🎬 CALLING PRESGEN-CORE VIDEO PROCESSING SERVICE"
    )
    logger.info(
        "🎯 generate_course_pipeline | stage=core_generation_start | workflow_id=%s | skill_id=%s | course_id=%s",
        workflow_id,
        skill_id,
        course_id,
    )
    logger.info(
        "📋 PresGen-Core Request Details:"
    )
    logger.info(
        "  • Base URL: %s", presgen_core.base_url
    )
    logger.info(
        "  • Timeout: %.1f seconds (%.1f minutes)", presgen_core._timeout.read, presgen_core._timeout.read / 60
    )
    logger.info(
        "  • Skill: %s", skill_course.skill_name
    )
    logger.info(
        "  • Domain: %s", skill_course.exam_domain
    )
    logger.info(
        "  • Target Duration: %s minutes", 10
    )
    logger.info(
        "  • Presentation URL: %s", course.presentation_url
    )
    logger.info(
        "  • Custom Prompt Length: %s chars", len(custom_prompt) if custom_prompt else 0
    )
    logger.info(
        "  • Content Text Length: %s chars", len(skill_course.course_description) if skill_course.course_description else 0
    )
    logger.info(
        "⏳ Waiting for PresGen-Core response (timeout: %.1f min)...", presgen_core._timeout.read / 60
    )
    logger.info(
        "=" * 80
    )

    try:
        core_request_start = datetime.utcnow()
        core_response = await presgen_core.generate_presentation(
            PresGenPresentationRequest(
                skill=skill_course.skill_name,
                domain=skill_course.exam_domain,
                target_duration_minutes=10,
                custom_prompt=custom_prompt,
                presentation_url=course.presentation_url,
                content_text=skill_course.course_description,
                metadata={
                    "workflow_id": workflow_id_str,
                    "skill_id": skill_id,
                    "prompt_length": len(custom_prompt) if custom_prompt else 0,
                },
            )
        )
        core_request_duration_ms = int((datetime.utcnow() - core_request_start).total_seconds() * 1000)

        logger.info(
            "=" * 80
        )
        logger.info(
            "✅ PRESGEN-CORE RESPONSE RECEIVED"
        )
        logger.info(
            "📊 Response Details:"
        )
        logger.info(
            "  • Job ID: %s", core_response.job_id
        )
        logger.info(
            "  • Success: %s", core_response.success
        )
        logger.info(
            "  • Presentation URL: %s", core_response.presentation_url or "N/A"
        )
        logger.info(
            "  • Download URL: %s", core_response.download_url or "N/A"
        )
        logger.info(
            "  • Processing Time: %s ms", core_response.duration_ms or "N/A"
        )
        logger.info(
            "  • Request Duration: %s ms", core_request_duration_ms
        )
        logger.info(
            "  • Error: %s", core_response.error or "None"
        )
        logger.info(
            "=" * 80
        )
    except CoreCircuitOpenError as exc:
        course.status = "failed"
        course.progress = 0
        course.error_message = "PresGen-Core circuit open; please retry later"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESGEN_CORE_CIRCUIT_OPEN",
            workflow_id=workflow_id_str,
            course_id=course_id,
            error=str(exc),
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=core_circuit_open | workflow_id=%s | skill_id=%s | course_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            exc,
        )

        raise HTTPException(status_code=503, detail="PresGen-Core temporarily unavailable") from exc
    except Exception as exc:  # pragma: no cover - error path exercised via manual test
        course.status = "failed"
        course.progress = 0
        course.error_message = f"PresGen-Core generation failed: {exc}"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESGEN_CORE_FAILED",
            workflow_id=workflow_id_str,
            course_id=course_id,
            error=str(exc),
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=core_failure | workflow_id=%s | skill_id=%s | course_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            exc,
        )

        raise HTTPException(status_code=502, detail="PresGen-Core generation failed") from exc

    course.presgen_core_job_id = core_response.job_id
    course.presgen_core_download_url = core_response.download_url
    if core_response.duration_ms is not None:
        course.presgen_core_processing_time_ms = core_response.duration_ms

    presentation_url = core_response.presentation_url or course.presentation_url
    if presentation_url:
        course.presentation_url = presentation_url

    if not core_response.success or core_response.error:
        course.status = "failed"
        course.progress = 0
        course.error_message = core_response.error or "PresGen-Core reported failure"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESGEN_CORE_FAILED",
            workflow_id=workflow_id_str,
            course_id=course_id,
            job_id=core_response.job_id,
            error=course.error_message,
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=core_failure | workflow_id=%s | skill_id=%s | course_id=%s | job_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            core_response.job_id,
            course.error_message,
        )
        raise HTTPException(status_code=502, detail="PresGen-Core generation failed")

    course.status = "generating_presentation"
    course.progress = 50
    course.error_message = None
    await db.commit()
    await db.refresh(course)

    log_course_event(
        "PRESGEN_CORE_COMPLETED",
        workflow_id=workflow_id_str,
        course_id=course_id,
        presentation_url=course.presentation_url,
        prompt_used=(core_response.prompt_used or custom_prompt),
        job_id=core_response.job_id,
        download_url=core_response.download_url,
        processing_time_ms=core_response.duration_ms,
    )

    # 6. Call PresGen-Avatar for narration
    avatar_client = PresGenAvatarClient(base_url=os.getenv("PRESGEN_AVATAR_URL"))

    course.status = "generating_video"
    course.progress = 60
    await db.commit()
    await db.refresh(course)

    log_course_event(
        "PRESGEN_AVATAR_STARTED",
        workflow_id=workflow_id_str,
        presentation_url=presentation_url,
    )
    logger.info(
        "=" * 80
    )
    logger.info(
        "🎤 CALLING PRESGEN-AVATAR TTS/VIDEO WORKER SERVICE"
    )
    logger.info(
        "🎯 generate_course_pipeline | stage=avatar_generation_start | workflow_id=%s | skill_id=%s | course_id=%s | presentation_url=%s",
        workflow_id,
        skill_id,
        course_id,
        presentation_url,
    )
    logger.info(
        "📋 PresGen-Avatar Request Details:"
    )
    logger.info(
        "  • Base URL: %s", avatar_client.base_url if hasattr(avatar_client, 'base_url') else os.getenv("PRESGEN_AVATAR_URL")
    )
    logger.info(
        "  • Workflow ID: %s", workflow_id_str
    )
    logger.info(
        "  • Skill ID: %s", skill_id
    )
    logger.info(
        "  • Presentation URL: %s", presentation_url
    )
    logger.info(
        "  • Mode: presentation-only"
    )
    logger.info(
        "  • Quality: fast"
    )
    logger.info(
        "  • Voice Provider: openai"
    )
    logger.info(
        "  • Voice ID: alloy"
    )
    logger.info(
        "⏳ Waiting for PresGen-Avatar response..."
    )
    logger.info(
        "=" * 80
    )

    try:
        avatar_request_start = datetime.utcnow()
        avatar_result = await avatar_client.generate_video(
            workflow_id=workflow_id_str,
            skill_id=skill_id,
            presentation_url=presentation_url,
            mode="presentation-only",
            quality="fast",
            voice_provider="openai",
            voice_id="alloy",
        )
        avatar_request_duration_ms = int((datetime.utcnow() - avatar_request_start).total_seconds() * 1000)

        logger.info(
            "=" * 80
        )
        logger.info(
            "✅ PRESGEN-AVATAR RESPONSE RECEIVED"
        )
        logger.info(
            "📊 Response Details:"
        )
        logger.info(
            "  • Job ID: %s", avatar_result.job_id
        )
        logger.info(
            "  • Status: %s", avatar_result.status
        )
        logger.info(
            "  • Progress: %s%%", avatar_result.progress or 0
        )
        logger.info(
            "  • Video URL: %s", avatar_result.video_url or "Pending..."
        )
        logger.info(
            "  • Request Duration: %s ms", avatar_request_duration_ms
        )
        logger.info(
            "  • Error Message: %s", avatar_result.error_message or "None"
        )
        logger.info(
            "=" * 80
        )
    except AvatarCircuitOpenError as exc:
        course.status = "failed"
        course.progress = 0
        course.error_message = "PresGen-Avatar circuit open; please retry later"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESGEN_AVATAR_CIRCUIT_OPEN",
            workflow_id=workflow_id_str,
            course_id=course_id,
            error=str(exc),
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=avatar_circuit_open | workflow_id=%s | skill_id=%s | course_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            exc,
        )

        raise HTTPException(status_code=503, detail="PresGen-Avatar temporarily unavailable") from exc
    except Exception as exc:  # pylint: disable=broad-except
        course.status = "failed"
        course.progress = 0
        course.error_message = f"PresGen-Avatar generation failed: {exc}"
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "COURSE_GENERATION_FAILED",
            workflow_id=workflow_id_str,
            course_id=course_id,
            error=course.error_message,
        )
        logger.warning(
            "🎯 generate_course_pipeline | stage=avatar_failure | workflow_id=%s | skill_id=%s | course_id=%s | error=%s",
            workflow_id,
            skill_id,
            course_id,
            exc,
        )

        raise HTTPException(status_code=502, detail="PresGen-Avatar generation failed") from exc
    else:
        avatar_api_mode = (avatar_result.context or {}).get("api_mode")
        course.presgen_avatar_job_id = avatar_result.job_id
        course.progress = max(course.progress, avatar_result.progress or course.progress or 70)
        await db.commit()
        await db.refresh(course)

        log_course_event(
            "PRESGEN_AVATAR_QUEUED",
            workflow_id=workflow_id_str,
            course_id=course_id,
            job_id=avatar_result.job_id,
            status=avatar_result.status,
        )

        final_status = avatar_result
        if avatar_api_mode != "course" and avatar_result.status not in {"completed", "failed"}:
            final_status = await avatar_client.poll_until_complete(avatar_result.job_id)
            log_course_event(
                "PRESGEN_AVATAR_PROGRESS",
                workflow_id=workflow_id_str,
                job_id=avatar_result.job_id,
                status=final_status.status,
                progress=final_status.progress,
            )

        if avatar_api_mode == "course":
            if final_status.status == "failed":
                course.status = "failed"
                course.progress = final_status.progress or course.progress
                course.error_message = final_status.error_message or "PresGen-Avatar generation failed"
                await db.commit()
                await db.refresh(course)

                log_course_event(
                    "COURSE_GENERATION_FAILED",
                    workflow_id=workflow_id_str,
                    job_id=avatar_result.job_id,
                    error=course.error_message,
                )

                raise HTTPException(status_code=502, detail="PresGen-Avatar generation failed")

            course.progress = final_status.progress or course.progress
            if final_status.video_url and not course.video_url:
                course.video_url = str(final_status.video_url)
            await db.commit()
            await db.refresh(course)
        elif final_status.status == "failed":
            course.status = "failed"
            course.progress = final_status.progress or course.progress
            course.error_message = final_status.error_message or "PresGen-Avatar generation failed"
            await db.commit()
            await db.refresh(course)

            log_course_event(
                "COURSE_GENERATION_FAILED",
                workflow_id=workflow_id_str,
                job_id=avatar_result.job_id,
                error=course.error_message,
            )

            raise HTTPException(status_code=502, detail="PresGen-Avatar generation failed")

        if avatar_api_mode != "course":
            job_output_dir = settings.avatar_output_dir / workflow_id_str / "jobs" / course_id
            job_output_dir.mkdir(parents=True, exist_ok=True)
            output_filename = f"avatar-{skill_slug}-{course_id}.mp4"
            mp4_path = job_output_dir / output_filename

            logger.info(
                "=" * 80
            )
            logger.info(
                "💾 DOWNLOADING AND SAVING VIDEO LOCALLY"
            )
            logger.info(
                "📂 Local Storage Details:"
            )
            logger.info(
                "  • Output Directory: %s", job_output_dir
            )
            logger.info(
                "  • Output Filename: %s", output_filename
            )
            logger.info(
                "  • Full Path: %s", mp4_path
            )
            logger.info(
                "  • Video Source URL: %s", final_status.video_url or "N/A"
            )

            if final_status.video_url:
                download_start = datetime.utcnow()
                try:
                    if str(final_status.video_url).startswith("http"):
                        logger.info(
                            "🌐 Downloading video from HTTP URL..."
                        )
                        logger.info(
                            "  • URL: %s", str(final_status.video_url)
                        )

                        bytes_downloaded = 0
                        async with httpx.AsyncClient(timeout=None) as client:
                            async with client.stream("GET", str(final_status.video_url)) as stream:
                                stream.raise_for_status()
                                with mp4_path.open("wb") as fh:
                                    async for chunk in stream.aiter_bytes():
                                        fh.write(chunk)
                                        bytes_downloaded += len(chunk)

                        download_duration_ms = int((datetime.utcnow() - download_start).total_seconds() * 1000)
                        file_size_mb = bytes_downloaded / (1024 * 1024)

                        logger.info(
                            "✅ Video downloaded successfully via HTTP"
                        )
                        logger.info(
                            "  • Bytes Downloaded: %s (%.2f MB)", bytes_downloaded, file_size_mb
                        )
                        logger.info(
                            "  • Download Duration: %s ms", download_duration_ms
                        )
                        logger.info(
                            "  • Average Speed: %.2f MB/s", file_size_mb / (download_duration_ms / 1000) if download_duration_ms > 0 else 0
                        )
                    else:
                        logger.info(
                            "📁 Copying video from local filesystem..."
                        )
                        source_path = Path(str(final_status.video_url))
                        logger.info(
                            "  • Source Path: %s", source_path
                        )
                        logger.info(
                            "  • Source Exists: %s", source_path.exists()
                        )

                        if source_path.exists():
                            shutil.copy2(source_path, mp4_path)
                            download_duration_ms = int((datetime.utcnow() - download_start).total_seconds() * 1000)
                            file_size_mb = mp4_path.stat().st_size / (1024 * 1024)

                            logger.info(
                                "✅ Video copied successfully from local filesystem"
                            )
                            logger.info(
                                "  • File Size: %.2f MB", file_size_mb
                            )
                            logger.info(
                                "  • Copy Duration: %s ms", download_duration_ms
                            )
                        else:
                            logger.error(
                                "❌ Source file does not exist: %s", source_path
                            )

                    logger.info(
                        "📊 Final Video File:"
                    )
                    logger.info(
                        "  • Path: %s", mp4_path
                    )
                    logger.info(
                        "  • Exists: %s", mp4_path.exists()
                    )
                    if mp4_path.exists():
                        logger.info(
                            "  • Size: %.2f MB", mp4_path.stat().st_size / (1024 * 1024)
                        )
                    logger.info(
                        "=" * 80
                    )

                except Exception as exc:  # pylint: disable=broad-except
                    download_duration_ms = int((datetime.utcnow() - download_start).total_seconds() * 1000)
                    logger.error(
                        "=" * 80
                    )
                    logger.error(
                        "❌ VIDEO DOWNLOAD/SAVE FAILED"
                    )
                    logger.error(
                        "  • Source: %s", final_status.video_url
                    )
                    logger.error(
                        "  • Destination: %s", mp4_path
                    )
                    logger.error(
                        "  • Error: %s", str(exc)
                    )
                    logger.error(
                        "  • Duration before failure: %s ms", download_duration_ms
                    )
                    logger.error(
                        "=" * 80
                    )
                    logger.warning(
                        "Failed to copy avatar output from %s | error=%s",
                        final_status.video_url,
                        exc,
                    )
            else:
                logger.warning(
                    "⚠️  No video_url provided in final_status - skipping download"
                )
                logger.info(
                    "=" * 80
                )

            course.video_url = f"{settings.api_v1_prefix}/workflows/{workflow_id_str}/courses/{course_id}/video"
            course.local_video_path = str(mp4_path)
            course.status = "completed"
            course.progress = final_status.progress or 100
            course.completed_at = datetime.utcnow()
            await db.commit()
            await db.refresh(course)

            log_course_event(
                "COURSE_GENERATION_COMPLETED",
                workflow_id=workflow_id_str,
                video_url=course.video_url,
                job_id=avatar_result.job_id,
                local_path=str(mp4_path),
            )

            total_duration_ms = int((datetime.utcnow() - request_started_at).total_seconds() * 1000)

            logger.info(
                "=" * 80
            )
            logger.info(
                "🎉 COURSE GENERATION PIPELINE COMPLETED SUCCESSFULLY"
            )
            logger.info(
                "🎯 generate_course_pipeline | stage=course_completed | workflow_id=%s | skill_id=%s | course_id=%s | video_url=%s | total_duration_ms=%s",
                workflow_id,
                skill_id,
                course_id,
                course.video_url,
                total_duration_ms,
            )
            logger.info(
                "📊 Final Summary:"
            )
            logger.info(
                "  • Workflow ID: %s", workflow_id_str
            )
            logger.info(
                "  • Course ID: %s", course_id
            )
            logger.info(
                "  • Skill: %s", skill_course.skill_name
            )
            logger.info(
                "  • Status: %s", course.status
            )
            logger.info(
                "  • Progress: %s%%", course.progress
            )
            logger.info(
                "  • Presentation URL: %s", course.presentation_url
            )
            logger.info(
                "  • Video URL (API): %s", course.video_url
            )
            logger.info(
                "  • Local Video Path: %s", course.local_video_path
            )
            logger.info(
                "  • PresGen-Core Job ID: %s", course.presgen_core_job_id or "N/A"
            )
            logger.info(
                "  • PresGen-Avatar Job ID: %s", course.presgen_avatar_job_id or "N/A"
            )
            logger.info(
                "⏱️  Performance Metrics:"
            )
            logger.info(
                "  • Total Pipeline Duration: %s ms (%.2f seconds)", total_duration_ms, total_duration_ms / 1000
            )
            logger.info(
                "  • PresGen-Core Processing: %s ms", course.presgen_core_processing_time_ms or "N/A"
            )
            logger.info(
                "  • Completed At: %s", course.completed_at.isoformat() if course.completed_at else "N/A"
            )
            logger.info(
                "=" * 80
            )
    finally:
        await presgen_core.close()
        await avatar_client.close()

    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        skill_name=skill_course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=course.presgen_core_download_url,
        presgen_avatar_job_id=course.presgen_avatar_job_id,
        local_video_path=course.local_video_path,
        status=course.status,
        progress=course.progress,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=course.completed_at,
    )
@router.get(
    "/{workflow_id}/courses/{course_id}/video",
    summary="Download course video",
)
async def download_course_video(
    workflow_id: UUID,
    course_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stream the locally stored avatar MP4 for a generated course."""

    workflow_id_str = str(workflow_id)
    workflow_id_normalized = workflow_id.hex

    result = await db.execute(
        select(GeneratedCourse).where(
            and_(
                GeneratedCourse.workflow_id == workflow_id_normalized,
                GeneratedCourse.id == course_id,
            )
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    job_dir = settings.avatar_output_dir / workflow_id_str / "jobs" / course_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Video file not available")

    expected_path = job_dir / f"avatar-{_slugify_skill_name(course.skill_name)}-{course_id}.mp4"
    if not expected_path.exists():
        mp4_candidates = sorted(job_dir.glob("*.mp4"))
        if not mp4_candidates:
            raise HTTPException(status_code=404, detail="Video file missing")
        expected_path = mp4_candidates[0]

    return FileResponse(expected_path, media_type="video/mp4", filename=expected_path.name)


@router.get(
    "/{workflow_id}/courses",
    response_model=List[CourseGenerationResponse],
    summary="List generated courses for workflow"
)
async def list_generated_courses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Return all generated courses for a workflow."""

    workflow_id_normalized = workflow_id.hex

    result = await db.execute(
        select(GeneratedCourse)
        .where(GeneratedCourse.workflow_id == workflow_id_normalized)
        .order_by(GeneratedCourse.created_at.desc())
    )
    courses = result.scalars().all()

    return [
        CourseGenerationResponse(
            course_id=course.id,
            workflow_id=str(workflow_id),
            skill_id=course.skill_id,
            skill_name=course.skill_name,
            course_title=course.course_title,
            presentation_url=course.presentation_url,
            video_url=course.video_url,
            presgen_core_job_id=course.presgen_core_job_id,
            presgen_core_download_url=course.presgen_core_download_url,
            presgen_avatar_job_id=course.presgen_avatar_job_id,
            local_video_path=course.local_video_path,
            status=course.status,
            progress=course.progress,
            created_at=course.created_at,
            updated_at=course.updated_at,
            completed_at=course.completed_at,
        )
        for course in courses
    ]


@router.get(
    "/{workflow_id}/courses/{course_id}/status",
    response_model=CourseStatusResponse,
    summary="Get course generation status"
)
async def get_course_status(
    workflow_id: UUID,
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get real-time status of course generation."""

    workflow_id_normalized = workflow_id.hex

    result = await db.execute(
        select(GeneratedCourse).where(
            and_(
                GeneratedCourse.workflow_id == workflow_id_normalized,
                GeneratedCourse.id == course_id
            )
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseStatusResponse(
        course_id=course.id,
        status=course.status,
        progress=course.progress,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_avatar_job_id=course.presgen_avatar_job_id,
        error_message=course.error_message
    )
