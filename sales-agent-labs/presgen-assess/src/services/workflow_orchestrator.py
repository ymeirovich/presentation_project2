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
from src.services.ai_question_generator import AIQuestionGenerator  # Sprint 1
from src.services.gap_analysis_enhanced import EnhancedGapAnalysisService  # Sprint 1
from src.service.database import get_db_session as get_async_session
from src.common.enhanced_logging import (
    get_enhanced_logger,
    log_workflow_stage_start,
    log_form_question_generation
)
from src.common.feature_flags import is_feature_enabled  # Sprint 0
from src.common.structured_logger import StructuredLogger  # Sprint 0


class WorkflowOrchestrator:
    """Orchestrates end-to-end assessment workflow execution.

    Sprint 1: Added AI question generation integration.
    """

    def __init__(self):
        self.logger = get_enhanced_logger(__name__)
        self.structured_logger = StructuredLogger("workflow_orchestrator")  # Sprint 0
        self.google_forms_service = GoogleFormsService()
        self.assessment_mapper = AssessmentFormsMapper()
        self.response_processor = FormResponseProcessor()
        self.response_ingestion = ResponseIngestionService()
        self.ai_question_generator = AIQuestionGenerator()  # Sprint 1
        self.gap_analysis_service = EnhancedGapAnalysisService()  # Sprint 1

    async def execute_assessment_to_form_workflow(
        self,
        certification_profile_id: UUID,
        user_id: str,
        assessment_data: Dict[str, Any],
        form_settings: Optional[Dict] = None,
        use_ai_generation: bool = True  # Sprint 1: NEW parameter
    ) -> Dict[str, Any]:
        """Execute the complete assessment-to-form workflow.

        Sprint 1: Added AI question generation support via use_ai_generation parameter.

        Args:
            certification_profile_id: UUID of certification profile
            user_id: User identifier
            assessment_data: Assessment data (questions or generation params)
            form_settings: Optional form configuration
            use_ai_generation: If True and feature enabled, use AI to generate questions

        Returns:
            Dict with workflow results including generation_method
        """
        correlation_id = f"workflow_{certification_profile_id}"

        self.logger.info("Starting assessment-to-form workflow", extra={
            "certification_profile_id": str(certification_profile_id),
            "user_id": user_id,
            "correlation_id": correlation_id,
            "use_ai_generation": use_ai_generation,
            "question_count": len(assessment_data.get("questions", []))
        })

        # Enhanced Stage 1 Logging
        log_workflow_stage_start(
            correlation_id=correlation_id,
            stage="form_generation",
            certification_profile=str(certification_profile_id),
            resource_count=len(assessment_data.get("resources", [])),
            timestamp=datetime.utcnow().isoformat(),
            logger=self.logger
        )

        try:
            # Create workflow execution record
            workflow = await self._create_workflow_execution(
                certification_profile_id=certification_profile_id,
                user_id=user_id,
                assessment_data=assessment_data
            )

            # Sprint 1: STEP 1 - AI Question Generation (if enabled)
            generation_method = "manual"
            if use_ai_generation and is_feature_enabled("enable_ai_question_generation"):
                self.structured_logger.log_ai_generation_start(
                    workflow_id=str(workflow.id),
                    certification_profile_id=str(certification_profile_id),
                    question_count=assessment_data.get("question_count", 24),
                    difficulty=assessment_data.get("difficulty", "intermediate")
                )

                try:
                    start_time = asyncio.get_event_loop().time()

                    # Generate questions using AI
                    generation_result = await self.ai_question_generator.generate_contextual_assessment(
                        certification_profile_id=certification_profile_id,
                        user_profile=user_id,
                        difficulty_level=assessment_data.get("difficulty", "intermediate"),
                        domain_distribution=assessment_data.get("domain_distribution", {}),
                        question_count=assessment_data.get("question_count", 24)
                    )

                    generation_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

                    if not generation_result.get("success", False):
                        # AI generation failed, log and fall back to manual questions
                        error_msg = generation_result.get("error", "Unknown error")
                        self.structured_logger.log_ai_generation_error(
                            workflow_id=str(workflow.id),
                            error=error_msg,
                            fallback_used=True
                        )
                        self.logger.warning(f"AI generation failed, using manual questions: {error_msg}")
                    else:
                        # AI generation succeeded
                        questions = generation_result["assessment_data"]["questions"]
                        quality_scores = generation_result["assessment_data"]["metadata"].get("quality_scores", {})

                        # Update assessment_data with generated questions
                        if "metadata" not in assessment_data:
                            assessment_data["metadata"] = {}

                        assessment_data["questions"] = questions
                        assessment_data["metadata"]["generation_method"] = "ai_generated"
                        assessment_data["metadata"]["quality_scores"] = quality_scores
                        generation_method = "ai_generated"

                        avg_quality = quality_scores.get("overall", 0.0)
                        self.structured_logger.log_ai_generation_complete(
                            workflow_id=str(workflow.id),
                            questions_generated=len(questions),
                            quality_score=avg_quality,
                            generation_time_ms=generation_time_ms
                        )

                        self.logger.info(f"AI generated {len(questions)} questions with quality {avg_quality:.2f}")

                except Exception as e:
                    self.structured_logger.log_ai_generation_error(
                        workflow_id=str(workflow.id),
                        error=str(e),
                        fallback_used=True
                    )
                    self.logger.error(f"AI generation exception: {e}", exc_info=True)
                    # Continue with manual questions from assessment_data

            else:
                self.logger.info(f"Using manual questions (AI generation {'disabled' if not is_feature_enabled('enable_ai_question_generation') else 'not requested'})")
                if "metadata" not in assessment_data:
                    assessment_data["metadata"] = {}
                assessment_data["metadata"]["generation_method"] = "manual"

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
                "generation_method": generation_method,  # Sprint 1: NEW field
                "question_count": len(assessment_data.get("questions", [])),  # Sprint 1: NEW field
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
        """Create or continue existing workflow execution record."""
        async with get_async_session() as session:
            # Check for existing workflow for this user and certification
            result = await session.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.user_id == user_id)
                .where(WorkflowExecution.certification_profile_id == certification_profile_id)
                .where(WorkflowExecution.execution_status != WorkflowStatus.COMPLETED)
                .where(WorkflowExecution.execution_status != WorkflowStatus.ERROR)
                .order_by(WorkflowExecution.created_at.desc())
            )
            existing_workflows = result.scalars().all()

            # Handle case where multiple non-completed workflows exist
            if len(existing_workflows) > 1:
                self.logger.warning(
                    "Multiple active workflows found for user=%s profile=%s, using most recent",
                    user_id, certification_profile_id,
                    extra={"workflow_count": len(existing_workflows)}
                )
                # Mark older workflows as completed to avoid future conflicts
                for old_workflow in existing_workflows[1:]:
                    old_workflow.execution_status = WorkflowStatus.COMPLETED
                    old_workflow.current_step = "auto_completed_duplicate"
                    self.logger.info(
                        "Auto-completing duplicate workflow id=%s to prevent conflicts",
                        old_workflow.id
                    )
                await session.commit()

            existing_workflow = existing_workflows[0] if existing_workflows else None

            if existing_workflow:
                # Continue existing workflow
                self.logger.info("Continuing existing workflow execution", extra={
                    "workflow_id": str(existing_workflow.id),
                    "certification_profile_id": str(certification_profile_id),
                    "user_id": user_id,
                    "current_step": existing_workflow.current_step,
                    "current_status": existing_workflow.execution_status
                })
                return existing_workflow

            # Create new workflow if none exists
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

            self.logger.info("Created new workflow execution", extra={
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
                # Enhanced logging for form generation
                log_form_question_generation(
                    correlation_id=f"workflow_{workflow.id}",
                    question_count=len(assessment_data.get("questions", [])),
                    skill_mappings=assessment_data.get("skill_mappings", {}),
                    generation_time_seconds=45.2,  # This would be calculated from actual timing
                    logger=self.logger
                )

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
                    paused_at_value = additional_data["paused_at"]
                    # Handle different data types for paused_at
                    if isinstance(paused_at_value, str):
                        update_values["paused_at"] = datetime.fromisoformat(
                            paused_at_value.replace("Z", "+00:00")
                        )
                    elif isinstance(paused_at_value, (int, float)):
                        # Assume it's a timestamp
                        update_values["paused_at"] = datetime.fromtimestamp(paused_at_value)
                    elif isinstance(paused_at_value, datetime):
                        # Already a datetime object
                        update_values["paused_at"] = paused_at_value

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

                # Sprint 1: Perform Gap Analysis with Database Persistence
                if is_feature_enabled("enable_gap_dashboard_enhancements"):
                    gap_analysis_result = await self._perform_gap_analysis(
                        workflow_id=workflow_id,
                        workflow=workflow,
                        responses=responses,
                        scoring_results=scoring_results
                    )

                    if gap_analysis_result["success"]:
                        self.logger.info("Gap analysis completed and persisted", extra={
                            "workflow_id": str(workflow_id),
                            "gap_analysis_id": gap_analysis_result.get("gap_analysis_id")
                        })

                # Workflow completes at Gap Analysis (100%)
                await self._update_workflow_status(
                    workflow_id,
                    WorkflowStatus.COMPLETED,
                    "gap_analysis_complete"
                )

                # Update progress to 100%
                async with get_async_session() as session:
                    await session.execute(
                        update(WorkflowExecution)
                        .where(WorkflowExecution.id == workflow_id)
                        .values(progress=100)
                    )
                    await session.commit()

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
    async def _perform_gap_analysis(
        self,
        workflow_id: UUID,
        workflow: WorkflowExecution,
        responses: List[Dict[str, Any]],
        scoring_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform enhanced gap analysis with database persistence.
        
        Sprint 1: Integrates EnhancedGapAnalysisService into workflow.
        """
        try:
            # Get certification profile
            async with get_async_session() as session:
                cert_result = await session.execute(
                    select(CertificationProfile)
                    .where(CertificationProfile.id == workflow.certification_profile_id)
                )
                cert_profile = cert_result.scalar_one_or_none()
                
                if not cert_profile:
                    self.logger.error(f"Certification profile not found: {workflow.certification_profile_id}")
                    return {"success": False, "error": "Certification profile not found"}
                
                # Convert to dict for service
                cert_profile_dict = {
                    "id": str(cert_profile.id),
                    "name": cert_profile.name,
                    "description": cert_profile.description
                }
            
            # Format responses for gap analysis
            assessment_responses = self._format_responses_for_gap_analysis(
                responses,
                workflow.assessment_data
            )
            
            # Perform gap analysis and persist
            gap_result = await self.gap_analysis_service.analyze_and_persist(
                workflow_id=workflow_id,
                assessment_responses=assessment_responses,
                certification_profile=cert_profile_dict
            )
            
            if not gap_result["success"]:
                return gap_result
            
            # Generate content outlines (placeholder for Sprint 2 full RAG)
            skill_gaps = gap_result.get("skill_gaps", [])
            if skill_gaps:
                content_outline_ids = await self.gap_analysis_service.generate_content_outlines(
                    gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
                    workflow_id=workflow_id,
                    skill_gaps=skill_gaps,
                    certification_profile=cert_profile_dict
                )
                
                # Generate course recommendations
                course_ids = await self.gap_analysis_service.generate_course_recommendations(
                    gap_analysis_id=UUID(gap_result["gap_analysis_id"]),
                    workflow_id=workflow_id,
                    skill_gaps=skill_gaps,
                    certification_profile=cert_profile_dict
                )
                
                gap_result["content_outline_count"] = len(content_outline_ids)
                gap_result["recommended_course_count"] = len(course_ids)
            
            return gap_result
            
        except Exception as e:
            self.logger.error(f"Gap analysis failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _format_responses_for_gap_analysis(
        self,
        responses: List[Dict[str, Any]],
        assessment_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format workflow responses for gap analysis service."""
        formatted_responses = []
        questions = assessment_data.get("questions", [])
        question_map = {q.get("id"): q for q in questions}
        
        for response in responses:
            question_id = response.get("question_id")
            question = question_map.get(question_id, {})
            
            formatted_responses.append({
                "question_id": question_id,
                "user_answer": response.get("answer"),
                "correct_answer": question.get("correct_answer"),
                "is_correct": response.get("answer") == question.get("correct_answer"),
                "domain": question.get("domain", "General"),
                "skill_id": question.get("skill_id", "unknown"),
                "confidence": response.get("confidence", 3.0)
            })
        
        return formatted_responses
