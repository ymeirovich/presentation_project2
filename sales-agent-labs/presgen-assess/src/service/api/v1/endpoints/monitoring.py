"""Monitoring and health check API endpoints for production readiness."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logging_config import get_workflow_logger
from src.service.database import get_db
from src.services.monitoring_service import MonitoringService
from src.services.presgen_integration_service import PresGenIntegrationService

logger = get_workflow_logger()
router = APIRouter()


@router.get("/health")
async def health_check(
    include_details: bool = Query(default=True, description="Include detailed health check results"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Comprehensive health check endpoint for production monitoring."""
    try:
        logger.info("🏥 Performing health check", extra={"include_details": include_details})

        monitoring_service = MonitoringService()
        health_result = await monitoring_service.comprehensive_health_check()

        if not include_details:
            # Return simplified health status
            return {
                "status": health_result["overall_status"],
                "timestamp": health_result["timestamp"],
                "summary": health_result.get("summary", {})
            }

        logger.info("✅ Health check completed", extra={
            "overall_status": health_result["overall_status"],
            "checks_count": len(health_result.get("checks", []))
        })

        return health_result

    except Exception as e:
        logger.error("❌ Health check failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, str]:
    """Simple health check for load balancer health probes."""
    try:
        # Basic application responsiveness check
        return {
            "status": "healthy",
            "timestamp": str(datetime.utcnow())
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable"
        )


@router.get("/metrics")
async def get_system_metrics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed system metrics for monitoring dashboards."""
    try:
        logger.info("📊 Retrieving system metrics")

        monitoring_service = MonitoringService()
        metrics_result = await monitoring_service.get_system_metrics()

        if not metrics_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=metrics_result["error"]
            )

        logger.info("✅ System metrics retrieved")
        return metrics_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get system metrics", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@router.get("/health/history")
async def get_health_history(
    limit: int = Query(default=24, ge=1, le=100, description="Number of recent health checks to return"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get historical health check data."""
    try:
        logger.info("📈 Retrieving health history", extra={"limit": limit})

        monitoring_service = MonitoringService()
        history_result = await monitoring_service.get_health_history(limit)

        if not history_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=history_result["error"]
            )

        logger.info("✅ Health history retrieved", extra={
            "returned_records": history_result["returned_records"]
        })

        return history_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get health history", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health history: {str(e)}"
        )


@router.get("/alerts")
async def get_active_alerts(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get current system alerts."""
    try:
        logger.info("🚨 Checking for active alerts")

        monitoring_service = MonitoringService()
        alerts = await monitoring_service.check_alerts()

        alert_summary = {
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a.get("severity") == "critical"]),
            "warning_alerts": len([a for a in alerts if a.get("severity") == "warning"]),
            "info_alerts": len([a for a in alerts if a.get("severity") == "info"])
        }

        logger.info("✅ Alerts checked", extra=alert_summary)

        return {
            "success": True,
            "alerts": alerts,
            "summary": alert_summary,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("❌ Failed to check alerts", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check alerts: {str(e)}"
        )


@router.get("/presgen/status")
async def get_presgen_integration_status(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get PresGen integration status and statistics."""
    try:
        logger.info("🎯 Checking PresGen integration status")

        presgen_service = PresGenIntegrationService()
        stats_result = await presgen_service.get_integration_statistics()

        if not stats_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=stats_result["error"]
            )

        logger.info("✅ PresGen status retrieved")
        return stats_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get PresGen status", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PresGen status: {str(e)}"
        )


@router.get("/presgen/jobs/{job_id}/status")
async def get_presgen_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get status of a specific PresGen job."""
    try:
        logger.info("🔍 Getting PresGen job status", extra={"job_id": job_id})

        presgen_service = PresGenIntegrationService()
        status_result = await presgen_service.get_presgen_job_status(job_id)

        if not status_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=status_result["error"]
            )

        logger.info("✅ PresGen job status retrieved", extra={
            "job_id": job_id,
            "status": status_result.get("status")
        })

        return status_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get PresGen job status", extra={
            "job_id": job_id,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get PresGen job status: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/trigger-presgen")
async def trigger_presgen_generation(
    workflow_id: UUID,
    presentation_requirements: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger PresGen presentation and video generation for a workflow."""
    try:
        logger.info("🚀 Triggering PresGen generation", extra={
            "workflow_id": str(workflow_id),
            "has_requirements": presentation_requirements is not None
        })

        # TODO: Get workflow data from database
        # This would typically fetch the workflow, gap analysis, and certification profile
        # For now, we'll return a placeholder structure

        presgen_service = PresGenIntegrationService()

        # Placeholder data - would be fetched from workflow
        assessment_data = {"placeholder": "assessment_data"}
        gap_analysis_results = {"gap_areas": []}
        certification_profile = {"certification_name": "Sample Certification"}

        result = await presgen_service.trigger_presgen_workflow(
            workflow_id=workflow_id,
            assessment_data=assessment_data,
            gap_analysis_results=gap_analysis_results,
            certification_profile=certification_profile,
            presentation_requirements=presentation_requirements
        )

        if result["success"]:
            logger.info("✅ PresGen generation triggered", extra={
                "workflow_id": str(workflow_id),
                "presgen_job_id": result.get("presgen_job_id")
            })
        else:
            logger.error("❌ PresGen generation failed", extra={
                "workflow_id": str(workflow_id),
                "error": result.get("error")
            })

        return result

    except Exception as e:
        logger.error("❌ Failed to trigger PresGen generation", extra={
            "workflow_id": str(workflow_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger PresGen generation: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/generate-learning-content")
async def generate_learning_content(
    workflow_id: UUID,
    content_format: str = Query(default="slides", description="Content format: slides, modules, or comprehensive"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate personalized learning content based on gap analysis."""
    try:
        logger.info("📚 Generating learning content", extra={
            "workflow_id": str(workflow_id),
            "content_format": content_format
        })

        presgen_service = PresGenIntegrationService()

        # TODO: Fetch actual gap analysis and certification profile from workflow
        # Placeholder data for now
        gap_analysis_results = {"gap_areas": []}
        certification_profile = {"certification_name": "Sample Certification"}

        result = await presgen_service.generate_learning_content_from_gaps(
            gap_analysis_results=gap_analysis_results,
            certification_profile=certification_profile,
            content_format=content_format
        )

        if result["success"]:
            logger.info("✅ Learning content generated", extra={
                "workflow_id": str(workflow_id),
                "content_format": content_format,
                "module_count": result.get("learning_plan", {}).get("total_modules", 0)
            })
        else:
            logger.error("❌ Learning content generation failed", extra={
                "workflow_id": str(workflow_id),
                "error": result.get("error")
            })

        return result

    except Exception as e:
        logger.error("❌ Failed to generate learning content", extra={
            "workflow_id": str(workflow_id),
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate learning content: {str(e)}"
        )


# Add missing import
from datetime import datetime