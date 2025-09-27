"""Workflow orchestration service for coordinating assessment workflow phases."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.models.workflow import WorkflowExecution, WorkflowStatus
from src.models.certification import CertificationProfile
from src.services.google_forms_service import GoogleFormsService
from src.services.assessment_forms_mapper import AssessmentFormsMapper
from src.services.form_response_processor import FormResponseProcessor
from src.services.response_ingestion_service import ResponseIngestionService
from src.service.database import get_db_session as get_async_session
from src.common.enhanced_logging import get_enhanced_logger


class WorkflowOrchestrator:
    """Orchestrates end-to-end assessment workflow execution."""

    def __init__(self):
        self.logger = get_enhanced_logger(__name__)
        self.google_forms_service = GoogleFormsService()
        self.assessment_mapper = AssessmentFormsMapper()
        self.response_processor = FormResponseProcessor()
        self.response_ingestion = ResponseIngestionService()

    async def execute_assessment_to_form_workflow(
        self,
        certification_profile_id: UUID,
        user_id: str,
        assessment_data: Dict[str, Any],
        form_settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute the complete assessment-to-form workflow."""
        correlation_id = f"workflow_{certification_profile_id}"

        self.logger.info("Starting assessment-to-form workflow", extra={
            "certification_profile_id": str(certification_profile_id),
            "user_id": user_id,
            "correlation_id": correlation_id,
            "question_count": len(assessment_data.get("questions", []))
        })

        try:
            # Create workflow execution record
            workflow = await self._create_workflow_execution(
                certification_profile_id=certification_profile_id,
                user_id=user_id,
                assessment_data=assessment_data
            )

            # Phase 1: Generate Google Form
            form_result = await self._create_google_form_phase(
                workflow=workflow,
                assessment_data=assessment_data,
                form_settings=form_settings or {}
            )

            if not form_result["success"]:
                await self._mark_workflow_error(workflow.id, form_result["error"])
                return form_result

            # Phase 2: Configure form and set to awaiting responses
            await self._configure_form_phase(workflow, form_result)

            # Phase 3: Start async response collection
            await self._start_response_collection_phase(workflow)

            return {
                "success": True,
                "workflow_id": str(workflow.id),
                "form_id": form_result["form_id"],
                "form_url": form_result["form_url"],
                "status": WorkflowStatus.AWAITING_COMPLETION,
                "message": "Assessment form created and deployed. Awaiting responses."
            }

        except Exception as e:
            self.logger.error("Workflow execution failed", extra={
                "certification_profile_id": str(certification_profile_id),
                "user_id": user_id,
                "error": str(e),
                "correlation_id": correlation_id
            })
            return {
                "success": False,
                "error": f"Workflow execution failed: {str(e)}"
            }

    async def _create_workflow_execution(
        self,
        certification_profile_id: UUID,
        user_id: str,
        assessment_data: Dict[str, Any]
    ) -> WorkflowExecution:
        """Create initial workflow execution record."""
        async with get_async_session() as session:
            workflow = WorkflowExecution(
                user_id=user_id,
                certification_profile_id=certification_profile_id,
                current_step="create_form",
                execution_status=WorkflowStatus.INITIATED,
                assessment_data=assessment_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            session.add(workflow)
            await session.commit()
            await session.refresh(workflow)

            self.logger.info("Created workflow execution", extra={
                "workflow_id": str(workflow.id),
                "certification_profile_id": str(certification_profile_id),
                "user_id": user_id
            })

            return workflow

    async def _create_google_form_phase(
        self,
        workflow: WorkflowExecution,
        assessment_data: Dict[str, Any],
        form_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Google Form creation phase."""
        self.logger.info("Starting Google Form creation phase", extra={
            "workflow_id": str(workflow.id)
        })

        try:
            # Generate form title and description
            form_title = self._generate_form_title(assessment_data)
            form_description = self._generate_form_description(assessment_data)

            # Create Google Form
            form_result = await self.google_forms_service.create_assessment_form(
                assessment_data=assessment_data,
                form_title=form_title,
                form_description=form_description,
                settings=form_settings
            )

            if form_result["success"]:
                # Update workflow with form information
                await self._update_workflow_status(
                    workflow.id,
                    WorkflowStatus.DEPLOYED_TO_GOOGLE,
                    "configure_form",
                    form_metadata={
                        "form_id": form_result["form_id"],
                        "form_url": form_result["form_url"],
                        "form_title": form_title
                    }
                )

            return form_result

        except Exception as e:
            self.logger.error("Google Form creation failed", extra={
                "workflow_id": str(workflow.id),
                "error": str(e)
            })
            return {"success": False, "error": str(e)}

    def _generate_form_title(self, assessment_data: Dict[str, Any]) -> str:
        """Generate appropriate form title from assessment data."""
        metadata = assessment_data.get("metadata", {})
        cert_name = metadata.get("certification_name", "Assessment")
        version = metadata.get("certification_version", "")

        title = f"{cert_name} Assessment"
        if version:
            title += f" ({version})"

        return title

    def _generate_form_description(self, assessment_data: Dict[str, Any]) -> str:
        """Generate form description from assessment data."""
        metadata = assessment_data.get("metadata", {})
        question_count = len(assessment_data.get("questions", []))
        duration = metadata.get("estimated_duration_minutes", "N/A")

        description = f"This assessment contains {question_count} questions "
        if duration != "N/A":
            description += f"and should take approximately {duration} minutes to complete."
        else:
            description += "covering key topics in the certification area."

        description += "\n\nPlease answer all questions to the best of your ability."

        return description

    async def _configure_form_phase(
        self,
        workflow: WorkflowExecution,
        form_result: Dict[str, Any]
    ):
        """Configure additional form settings and permissions."""
        form_id = form_result["form_id"]

        self.logger.info("Configuring form settings", extra={
            "workflow_id": str(workflow.id),
            "form_id": form_id
        })

        # TODO: Add Drive folder organization here if needed
        # TODO: Configure form permissions and sharing settings

        # Update workflow with Google Form ID
        async with get_async_session() as session:
            await session.execute(
                update(WorkflowExecution)
                .where(WorkflowExecution.id == workflow.id)
                .values(
                    google_form_id=form_id,
                    updated_at=datetime.utcnow()
                )
            )
            await session.commit()

    async def _start_response_collection_phase(self, workflow: WorkflowExecution):
        """Start the async response collection phase."""
        self.logger.info("Starting response collection phase", extra={
            "workflow_id": str(workflow.id),
            "form_id": workflow.google_form_id
        })

        # Update workflow to awaiting completion status
        await self._update_workflow_status(
            workflow.id,
            WorkflowStatus.AWAITING_COMPLETION,
            "collect_responses",
            additional_data={
                "paused_at": datetime.utcnow().isoformat(),
                "collection_started": True
            }
        )

    async def _update_workflow_status(
        self,
        workflow_id: UUID,
        status: WorkflowStatus,
        current_step: str,
        form_metadata: Optional[Dict] = None,
        additional_data: Optional[Dict] = None
    ):
        """Update workflow status and metadata."""
        async with get_async_session() as session:
            update_values = {
                "execution_status": status,
                "current_step": current_step,
                "updated_at": datetime.utcnow()
            }

            if form_metadata:
                if form_metadata.get("form_id"):
                    update_values["google_form_id"] = form_metadata["form_id"]

                # Store form metadata in workflow data
                update_values["generated_content_urls"] = {
                    "form_url": form_metadata.get("form_url"),
                    "form_edit_url": form_metadata.get("form_edit_url", ""),
                    "form_title": form_metadata.get("form_title", "")
                }

            if additional_data:
                if additional_data.get("paused_at"):
                    update_values["paused_at"] = datetime.fromisoformat(
                        additional_data["paused_at"].replace("Z", "+00:00")
                    )

            await session.execute(
                update(WorkflowExecution)
                .where(WorkflowExecution.id == workflow_id)
                .values(**update_values)
            )
            await session.commit()

            self.logger.info("Updated workflow status", extra={
                "workflow_id": str(workflow_id),
                "new_status": status,
                "current_step": current_step
            })

    async def _mark_workflow_error(self, workflow_id: UUID, error_message: str):
        """Mark workflow as failed with error message."""
        await self._update_workflow_status(
            workflow_id,
            WorkflowStatus.ERROR,
            "error",
            additional_data={"error_message": error_message}
        )

    async def process_completed_responses(self, workflow_id: UUID) -> Dict[str, Any]:
        """Process responses when collection phase is complete."""
        async with get_async_session() as session:
            result = await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()

            if not workflow:
                return {"success": False, "error": "Workflow not found"}

            if workflow.execution_status != WorkflowStatus.RESULTS_ANALYZED:
                return {"success": False, "error": "Workflow not ready for processing"}

            self.logger.info("Processing completed responses", extra={
                "workflow_id": str(workflow_id),
                "response_count": len(workflow.collected_responses or [])
            })

            try:
                # Process responses using FormResponseProcessor
                responses = workflow.collected_responses or []
                if not responses:
                    return {"success": False, "error": "No responses to process"}

                # Extract answer key from assessment data
                answer_key = self._extract_answer_key(workflow.assessment_data)

                # Calculate scores and analytics
                scoring_results = await self.response_processor.calculate_assessment_score(
                    responses=responses,
                    answer_key=answer_key
                )

                # Update workflow with results
                await self._store_analysis_results(workflow_id, scoring_results)

                # Transition to next phase
                await self._update_workflow_status(
                    workflow_id,
                    WorkflowStatus.TRAINING_PLAN_GENERATED,
                    "generate_training_plan"
                )

                return {
                    "success": True,
                    "workflow_id": str(workflow_id),
                    "results": scoring_results,
                    "message": "Response processing completed"
                }

            except Exception as e:
                self.logger.error("Response processing failed", extra={
                    "workflow_id": str(workflow_id),
                    "error": str(e)
                })
                await self._mark_workflow_error(workflow_id, str(e))
                return {"success": False, "error": str(e)}

    def _extract_answer_key(self, assessment_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Extract answer key from assessment data for scoring."""
        answer_key = {}

        for question in assessment_data.get("questions", []):
            question_id = question.get("id")
            if question_id:
                answer_key[question_id] = {
                    "correct_answer": question.get("correct_answer"),
                    "points": 1,  # Default scoring
                    "question_type": question.get("question_type"),
                    "domain": question.get("domain"),
                    "difficulty": question.get("difficulty", 0.5)
                }

                # Handle scenario questions with rubrics
                if question.get("question_type") == "scenario":
                    answer_key[question_id]["rubric"] = question.get("rubric", {})
                    answer_key[question_id]["max_points"] = 3

        return answer_key

    async def _store_analysis_results(
        self,
        workflow_id: UUID,
        analysis_results: Dict[str, Any]
    ):
        """Store analysis results in workflow."""
        async with get_async_session() as session:
            await session.execute(
                update(WorkflowExecution)
                .where(WorkflowExecution.id == workflow_id)
                .values(
                    gap_analysis_results=analysis_results,
                    updated_at=datetime.utcnow()
                )
            )
            await session.commit()

    async def get_workflow_status(self, workflow_id: UUID) -> Dict[str, Any]:
        """Get current workflow status and progress."""
        async with get_async_session() as session:
            result = await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()

            if not workflow:
                return {"success": False, "error": "Workflow not found"}

            return {
                "success": True,
                "workflow_id": str(workflow.id),
                "status": workflow.execution_status,
                "current_step": workflow.current_step,
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                "google_form_id": workflow.google_form_id,
                "form_urls": workflow.generated_content_urls,
                "response_count": len(workflow.collected_responses or []),
                "paused_at": workflow.paused_at.isoformat() if workflow.paused_at else None,
                "resumed_at": workflow.resumed_at.isoformat() if workflow.resumed_at else None
            }

    async def list_active_workflows(self) -> Dict[str, Any]:
        """List all active workflows with their current status."""
        async with get_async_session() as session:
            result = await session.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.execution_status != WorkflowStatus.COMPLETED)
                .where(WorkflowExecution.execution_status != WorkflowStatus.ERROR)
                .order_by(WorkflowExecution.updated_at.desc())
            )
            workflows = result.scalars().all()

            workflow_list = []
            for workflow in workflows:
                workflow_list.append({
                    "workflow_id": str(workflow.id),
                    "user_id": workflow.user_id,
                    "status": workflow.execution_status,
                    "current_step": workflow.current_step,
                    "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                    "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
                    "google_form_id": workflow.google_form_id,
                    "response_count": len(workflow.collected_responses or [])
                })

            return {
                "success": True,
                "workflows": workflow_list,
                "total_count": len(workflow_list)
            }