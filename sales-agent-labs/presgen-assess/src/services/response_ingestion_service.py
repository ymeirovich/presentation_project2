"""Async response ingestion service for Google Forms assessment responses."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.models.workflow import WorkflowExecution, WorkflowStatus
from src.services.google_forms_service import GoogleFormsService
from src.services.form_response_processor import FormResponseProcessor
from src.service.database import get_db_session as get_async_session
from src.common.enhanced_logging import get_enhanced_logger


class ResponseIngestionService:
    """Async service for ingesting and processing Google Forms responses."""

    def __init__(self):
        self.logger = get_enhanced_logger(__name__)
        self.google_forms_service = GoogleFormsService()
        self.response_processor = FormResponseProcessor()
        self._processed_responses: Set[str] = set()  # Deduplication cache

    async def start_ingestion_worker(self, poll_interval_seconds: int = 60):
        """Start the async response ingestion worker."""
        self.logger.info("Starting response ingestion worker", extra={
            "poll_interval_seconds": poll_interval_seconds
        })

        while True:
            try:
                await self._poll_and_ingest_responses()
                await asyncio.sleep(poll_interval_seconds)

            except Exception as e:
                self.logger.error("Error in ingestion worker", extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                # Continue running even if individual poll fails
                await asyncio.sleep(poll_interval_seconds)

    async def _poll_and_ingest_responses(self):
        """Poll all active workflows for new responses."""
        async with get_async_session() as session:
            # Find workflows awaiting completion
            result = await session.execute(
                select(WorkflowExecution).where(
                    WorkflowExecution.execution_status == WorkflowStatus.AWAITING_COMPLETION
                ).where(
                    WorkflowExecution.google_form_id.isnot(None)
                )
            )
            workflows = result.scalars().all()

            self.logger.info("Polling workflows for responses", extra={
                "workflow_count": len(workflows)
            })

            for workflow in workflows:
                try:
                    await self._process_workflow_responses(session, workflow)
                except Exception as e:
                    self.logger.error("Error processing workflow responses", extra={
                        "workflow_id": str(workflow.id),
                        "form_id": workflow.google_form_id,
                        "error": str(e)
                    })

    async def _process_workflow_responses(
        self,
        session: AsyncSession,
        workflow: WorkflowExecution
    ):
        """Process responses for a specific workflow."""
        if not workflow.google_form_id:
            return

        correlation_id = f"workflow_{workflow.id}"

        # Fetch responses from Google Forms
        responses_result = await self.google_forms_service.get_form_responses(
            form_id=workflow.google_form_id,
            include_empty=False
        )

        if not responses_result.get("success"):
            self.logger.warning("Failed to fetch form responses", extra={
                "workflow_id": str(workflow.id),
                "form_id": workflow.google_form_id,
                "error": responses_result.get("error")
            })
            return

        raw_responses = responses_result.get("responses", [])
        new_responses = self._filter_new_responses(raw_responses)

        if not new_responses:
            self.logger.debug("No new responses found", extra={
                "workflow_id": str(workflow.id),
                "form_id": workflow.google_form_id
            })
            return

        self.logger.info("Processing new responses", extra={
            "workflow_id": str(workflow.id),
            "form_id": workflow.google_form_id,
            "response_count": len(new_responses),
            "correlation_id": correlation_id
        })

        # Normalize and store responses
        normalized_responses = await self._normalize_responses(
            new_responses,
            workflow
        )

        # Update workflow with response data
        await self._update_workflow_responses(
            session,
            workflow,
            normalized_responses
        )

        # Process responses if we have enough
        await self._evaluate_completion_criteria(
            session,
            workflow,
            normalized_responses
        )

    def _filter_new_responses(self, responses: List[Dict]) -> List[Dict]:
        """Filter out already processed responses."""
        new_responses = []
        for response in responses:
            response_id = response.get("response_id") or response.get("responseId")
            if response_id and response_id not in self._processed_responses:
                new_responses.append(response)
                self._processed_responses.add(response_id)
        return new_responses

    async def _normalize_responses(
        self,
        raw_responses: List[Dict],
        workflow: WorkflowExecution
    ) -> List[Dict]:
        """Normalize raw Google Forms responses to standard format."""
        normalized = []

        for response in raw_responses:
            try:
                normalized_response = {
                    "response_id": response.get("responseId") or response.get("response_id"),
                    "workflow_id": str(workflow.id),
                    "respondent_email": response.get("respondentEmail"),
                    "submitted_at": self._parse_timestamp(
                        response.get("lastSubmittedTime") or response.get("submitted_at")
                    ),
                    "answers": self._normalize_answers(response.get("answers", {})),
                    "completion_time_seconds": response.get("completion_time_seconds"),
                    "metadata": {
                        "form_id": workflow.google_form_id,
                        "raw_create_time": response.get("createTime"),
                        "ingested_at": datetime.utcnow().isoformat()
                    }
                }
                normalized.append(normalized_response)

            except Exception as e:
                self.logger.error("Error normalizing response", extra={
                    "workflow_id": str(workflow.id),
                    "response_id": response.get("responseId"),
                    "error": str(e)
                })

        return normalized

    def _normalize_answers(self, answers: Dict) -> Dict:
        """Normalize answer format from Google Forms API."""
        normalized = {}

        for question_id, answer_data in answers.items():
            if isinstance(answer_data, dict):
                # Handle different answer types from Google Forms API
                if "textAnswers" in answer_data:
                    text_answers = answer_data["textAnswers"].get("answers", [])
                    if text_answers:
                        normalized[question_id] = text_answers[0].get("value", "")
                elif "fileUploadAnswers" in answer_data:
                    # Handle file uploads (future enhancement)
                    normalized[question_id] = "FILE_UPLOAD"
                else:
                    # Fallback to string representation
                    normalized[question_id] = str(answer_data)
            else:
                normalized[question_id] = str(answer_data)

        return normalized

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp from Google Forms API format."""
        if not timestamp_str:
            return None

        try:
            # Handle ISO format with timezone
            if timestamp_str.endswith('Z'):
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            self.logger.warning("Failed to parse timestamp", extra={
                "timestamp": timestamp_str
            })
            return None

    async def _update_workflow_responses(
        self,
        session: AsyncSession,
        workflow: WorkflowExecution,
        responses: List[Dict]
    ):
        """Update workflow with new response data."""
        if not responses:
            return

        # Update collected responses in workflow data
        current_responses = workflow.collected_responses or []
        current_responses.extend(responses)

        await session.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == workflow.id)
            .values(
                collected_responses=current_responses,
                updated_at=datetime.utcnow()
            )
        )

        await session.commit()

        self.logger.info("Updated workflow with responses", extra={
            "workflow_id": str(workflow.id),
            "new_response_count": len(responses),
            "total_response_count": len(current_responses)
        })

    async def _evaluate_completion_criteria(
        self,
        session: AsyncSession,
        workflow: WorkflowExecution,
        new_responses: List[Dict]
    ):
        """Evaluate if workflow should proceed to analysis phase."""
        total_responses = len(workflow.collected_responses or [])

        # Simple completion criteria - can be enhanced based on requirements
        min_responses = 1  # Minimum responses to proceed
        max_wait_hours = 24  # Maximum hours to wait for responses

        should_proceed = (
            total_responses >= min_responses or
            self._should_timeout_and_proceed(workflow, max_wait_hours)
        )

        if should_proceed:
            self.logger.info("Workflow ready for analysis", extra={
                "workflow_id": str(workflow.id),
                "response_count": total_responses,
                "reason": "min_responses" if total_responses >= min_responses else "timeout"
            })

            # Trigger analysis phase
            await self._transition_to_analysis(session, workflow)

    def _should_timeout_and_proceed(
        self,
        workflow: WorkflowExecution,
        max_wait_hours: int
    ) -> bool:
        """Check if workflow should timeout and proceed with available responses."""
        if not workflow.paused_at:
            return False

        wait_duration = datetime.utcnow() - workflow.paused_at
        return wait_duration > timedelta(hours=max_wait_hours)

    async def _transition_to_analysis(
        self,
        session: AsyncSession,
        workflow: WorkflowExecution
    ):
        """Transition workflow to analysis phase."""
        await session.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == workflow.id)
            .values(
                execution_status=WorkflowStatus.RESULTS_ANALYZED,
                current_step="analyze_responses",
                resumed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        )

        await session.commit()

        self.logger.info("Transitioned workflow to analysis", extra={
            "workflow_id": str(workflow.id),
            "new_status": WorkflowStatus.RESULTS_ANALYZED
        })

        # TODO: Trigger response analysis service here
        # await self._trigger_response_analysis(workflow)

    async def force_ingest_workflow_responses(self, workflow_id: UUID) -> Dict[str, Any]:
        """Manually trigger response ingestion for a specific workflow."""
        async with get_async_session() as session:
            result = await session.execute(
                select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()

            if not workflow:
                return {"success": False, "error": "Workflow not found"}

            if not workflow.google_form_id:
                return {"success": False, "error": "No Google Form associated with workflow"}

            try:
                await self._process_workflow_responses(session, workflow)
                return {
                    "success": True,
                    "message": "Response ingestion completed",
                    "workflow_id": str(workflow_id)
                }
            except Exception as e:
                self.logger.error("Manual ingestion failed", extra={
                    "workflow_id": str(workflow_id),
                    "error": str(e)
                })
                return {"success": False, "error": str(e)}

    async def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get statistics about response ingestion."""
        async with get_async_session() as session:
            # Count workflows by status
            result = await session.execute(
                select(WorkflowExecution.execution_status,
                       func.count(WorkflowExecution.id))
                .group_by(WorkflowExecution.execution_status)
            )
            status_counts = dict(result.all())

            return {
                "processed_response_ids": len(self._processed_responses),
                "workflow_status_counts": status_counts,
                "awaiting_completion": status_counts.get(WorkflowStatus.AWAITING_COMPLETION, 0)
            }