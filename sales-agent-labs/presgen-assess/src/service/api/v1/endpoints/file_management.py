"""
File Management API Endpoints for PresGen-Assess

Provides REST API endpoints for file upload, processing, and management
with ChromaDB integration for certification-specific knowledge bases.
"""

import uuid
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import chromadb
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.file_upload_service import (
    FileUploadService, FileMetadata, ProcessingResult,
    file_registry, ResourceType
)
from src.service.chromadb_schema import ChromaDBCollectionManager
from src.models.certification import CertificationProfile
from src.service.database import get_db

router = APIRouter(prefix="/files", tags=["file_management"])

# Initialize services
file_upload_service = FileUploadService()

# Lazy initialize ChromaDB to avoid import errors
chroma_client = None
collection_manager = None

def get_chroma_manager():
    """Lazy load ChromaDB manager"""
    global chroma_client, collection_manager
    if collection_manager is None:
        chroma_client = chromadb.PersistentClient(path="data/chroma")
        collection_manager = ChromaDBCollectionManager(chroma_client)
    return collection_manager


class FileUploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    original_filename: str
    file_size: int
    mime_type: str
    resource_type: str
    upload_timestamp: str
    processing_status: str
    message: str


class FileListResponse(BaseModel):
    """Response for file listing"""
    files: List[FileMetadata]
    total_count: int


class FileProcessingStatus(BaseModel):
    """File processing status response"""
    file_id: str
    status: str
    chunk_count: int
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None
    warnings: List[str] = []


class BulkUploadRequest(BaseModel):
    """Request for bulk file upload"""
    cert_profile_id: str
    resource_mappings: Dict[str, ResourceType]  # filename -> resource_type
    domain_mappings: Optional[Dict[str, str]] = None  # keyword -> domain_name


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    cert_profile_id: str = Form(...),
    resource_type: ResourceType = Form(...),
    process_immediately: bool = Form(True),
    # Authentication disabled for now,
    db: AsyncSession = Depends(get_db)
):
    """Upload a file for certification profile"""

    print("="*80)
    print("🔵 UPLOAD ENDPOINT CALLED")
    print(f"📄 File: {file.filename if file else 'None'}")
    print(f"📋 Profile ID: {cert_profile_id}")
    print(f"🏷️ Resource Type: {resource_type}")
    print(f"⚡ Process Immediately: {process_immediately}")
    print("="*80)

    # Verify certification profile exists (authentication disabled - skip user check)
    # Note: Temporarily allowing uploads without strict profile verification
    # TODO: Re-enable async profile verification when database session works correctly
    cert_profile_name = "temp-profile"  # Placeholder
    print(f"🔧 Using cert_profile_name: {cert_profile_name}")

    try:
        print("📥 Step 1: Saving uploaded file...")
        # Save uploaded file
        file_metadata = await file_upload_service.save_uploaded_file(
            file=file,
            user_id="",  # Authentication disabled - use empty user_id
            cert_profile_id=cert_profile_id,
            resource_type=resource_type
        )
        print(f"✅ Step 1 Complete: File saved with ID: {file_metadata.file_id}")

        # Register file in registry
        print("📝 Step 2: Registering file in database...")
        file_registry.register_file(file_metadata)
        print(f"✅ Step 2 Complete: File registered in database")

        # Process file if requested
        if process_immediately:
            print("⚙️ Step 3: Scheduling background processing...")
            background_tasks.add_task(
                process_file_background,
                file_metadata,
                cert_profile_name,
                "1.0",  # version placeholder
                {}  # domain_mappings, could be extracted from cert_profile
            )
            print("✅ Step 3 Complete: Background task scheduled")
        else:
            print("⏭️ Step 3: Skipped (process_immediately=False)")

        response = FileUploadResponse(
            file_id=file_metadata.file_id,
            original_filename=file_metadata.original_filename,
            file_size=file_metadata.file_size,
            mime_type=file_metadata.mime_type,
            resource_type=file_metadata.resource_type.value,
            upload_timestamp=file_metadata.upload_timestamp,
            processing_status=file_metadata.processing_status,
            message="File uploaded successfully" + (" and processing started" if process_immediately else "")
        )
        print("="*80)
        print(f"✅ UPLOAD SUCCESSFUL: {file_metadata.file_id}")
        print("="*80)
        return response

    except HTTPException as he:
        print(f"❌ HTTP Exception: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {type(e).__name__}")
        print(f"❌ Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {type(e).__name__}: {str(e)}")


@router.post("/bulk-upload")
async def bulk_upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    request_data: BulkUploadRequest = Depends(),
    # Authentication disabled for now,
    db: AsyncSession = Depends(get_db)
):
    """Upload multiple files for certification profile"""

    # Verify certification profile (authentication disabled - skip user check)
    cert_profile = db.query(CertificationProfile).filter(
        CertificationProfile.id == request_data.cert_profile_id,
        # CertificationProfile.user_id == current_user.id  # Authentication disabled
    ).first()

    if not cert_profile:
        raise HTTPException(
            status_code=404,
            detail="Certification profile not found"
        )

    uploaded_files = []
    errors = []

    for file in files:
        try:
            # Get resource type for this file
            resource_type = request_data.resource_mappings.get(
                file.filename,
                ResourceType.SUPPLEMENTAL
            )

            # Upload file
            file_metadata = await file_upload_service.save_uploaded_file(
                file=file,
                user_id="",  # Authentication disabled - use empty user_id
                cert_profile_id=request_data.cert_profile_id,
                resource_type=resource_type
            )

            file_registry.register_file(file_metadata)

            # Schedule processing
            background_tasks.add_task(
                process_file_background,
                file_metadata,
                cert_profile.name.lower().replace(' ', '-'),
                cert_profile.version,
                request_data.domain_mappings or {}
            )

            uploaded_files.append({
                "file_id": file_metadata.file_id,
                "filename": file_metadata.original_filename,
                "status": "uploaded"
            })

        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })

    return {
        "uploaded_files": uploaded_files,
        "errors": errors,
        "total_uploaded": len(uploaded_files),
        "total_errors": len(errors)
    }


@router.get("/profile/{cert_profile_id}", response_model=FileListResponse)
async def list_files_for_profile(
    cert_profile_id: str
):
    """List all files for a certification profile"""

    # Get files from registry (loads from database)
    files = file_registry.get_files_for_profile(cert_profile_id)

    return FileListResponse(
        files=files,
        total_count=len(files)
    )


@router.get("/user", response_model=FileListResponse)
async def list_user_files(
    # Authentication disabled for now
):
    """List all files for current user"""

    # Authentication disabled - return all files instead of user-specific
    files = file_registry.get_files_for_user("")  # Empty user_id returns all files

    return FileListResponse(
        files=files,
        total_count=len(files)
    )


@router.get("/{file_id}/status", response_model=FileProcessingStatus)
async def get_file_status(
    file_id: str,
    # Authentication disabled for now
):
    """Get file processing status"""

    file_metadata = file_registry.get_file(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Authentication disabled - skip user verification
    # if file_metadata.user_id != str(current_user.id):
    #     raise HTTPException(status_code=403, detail="Access denied")

    return FileProcessingStatus(
        file_id=file_metadata.file_id,
        status=file_metadata.processing_status,
        chunk_count=file_metadata.chunk_count,
        error_message=file_metadata.error_message
    )


@router.post("/{file_id}/process")
async def process_file(
    file_id: str,
    background_tasks: BackgroundTasks,
    domain_mappings: Optional[Dict[str, str]] = None,
    # Authentication disabled for now,
    db: AsyncSession = Depends(get_db)
):
    """Process an uploaded file"""

    file_metadata = file_registry.get_file(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Authentication disabled - skip user verification
    # if file_metadata.user_id != str(current_user.id):
    #     raise HTTPException(status_code=403, detail="Access denied")

    # Get certification profile info
    cert_profile = db.query(CertificationProfile).filter(
        CertificationProfile.id == file_metadata.cert_profile_id
    ).first()

    if not cert_profile:
        raise HTTPException(status_code=404, detail="Certification profile not found")

    # Schedule processing
    background_tasks.add_task(
        process_file_background,
        file_metadata,
        cert_profile.name.lower().replace(' ', '-'),
        cert_profile.version,
        domain_mappings or {}
    )

    return {"message": "File processing started", "file_id": file_id}


@router.delete("/{file_id}")
async def delete_file(
    file_id: str
):
    """Delete an uploaded file"""

    file_metadata = file_registry.get_file(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Authentication disabled - skip user verification for now
    # if file_metadata.user_id != str(current_user.id):
    #     raise HTTPException(status_code=403, detail="Access denied")

    try:
        # Delete file from disk (if exists)
        try:
            await file_upload_service.delete_file(file_metadata)
        except Exception as e:
            # File might not exist on disk, continue with registry removal
            print(f"Warning: Could not delete file from disk: {e}")

        # Remove from registry (this removes from database)
        success = file_registry.remove_file(file_id)

        if not success:
            raise HTTPException(status_code=404, detail="File not found in registry")

        # TODO: Remove associated chunks from ChromaDB collection
        # This would require tracking which chunks belong to which file

        return {"message": "File deleted successfully", "file_id": file_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    # Authentication disabled for now
):
    """Download an uploaded file"""

    file_metadata = file_registry.get_file(file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Authentication disabled - skip user verification
    # if file_metadata.user_id != str(current_user.id):
    #     raise HTTPException(status_code=403, detail="Access denied")

    # Check if file exists
    file_info = file_upload_service.get_file_info(file_metadata.file_path)
    if not file_info.get('exists'):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_metadata.file_path,
        filename=file_metadata.original_filename,
        media_type=file_metadata.mime_type
    )


@router.post("/collections/{cert_profile_id}/create")
async def create_knowledge_collection(
    cert_profile_id: str,
    # Authentication disabled for now,
    db: AsyncSession = Depends(get_db)
):
    """Create ChromaDB collection for certification profile"""

    # Verify certification profile (authentication disabled - skip user check)
    cert_profile = db.query(CertificationProfile).filter(
        CertificationProfile.id == cert_profile_id,
        # CertificationProfile.user_id == current_user.id  # Authentication disabled
    ).first()

    if not cert_profile:
        raise HTTPException(
            status_code=404,
            detail="Certification profile not found"
        )

    try:
        # Create collection
        collection = collection_manager.create_collection(
            user_id="",  # Authentication disabled - use empty user_id
            cert_id=cert_profile.name.lower().replace(' ', '-'),
            cert_name=cert_profile.name,
            bundle_version=cert_profile.version
        )

        collection_name = collection.name

        return {
            "message": "Collection created successfully",
            "collection_name": collection_name,
            "cert_profile_id": cert_profile_id
        }

    except Exception as e:
        # Collection might already exist
        if "already exists" in str(e).lower():
            return {
                "message": "Collection already exists",
                "cert_profile_id": cert_profile_id
            }
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.delete("/collections/{cert_profile_id}")
async def delete_knowledge_collection(
    cert_profile_id: str,
    # Authentication disabled for now,
    db: AsyncSession = Depends(get_db)
):
    """Delete ChromaDB collection for certification profile"""

    # Verify certification profile (authentication disabled - skip user check)
    cert_profile = db.query(CertificationProfile).filter(
        CertificationProfile.id == cert_profile_id,
        # CertificationProfile.user_id == current_user.id  # Authentication disabled
    ).first()

    if not cert_profile:
        raise HTTPException(
            status_code=404,
            detail="Certification profile not found"
        )

    try:
        # Delete collection
        success = collection_manager.delete_collection(
            user_id="",  # Authentication disabled - use empty user_id
            cert_id=cert_profile.name.lower().replace(' ', '-'),
            bundle_version=cert_profile.version
        )

        if success:
            return {
                "message": "Collection deleted successfully",
                "cert_profile_id": cert_profile_id
            }
        else:
            return {
                "message": "Collection not found or already deleted",
                "cert_profile_id": cert_profile_id
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


@router.get("/collections/user")
async def list_user_collections(
    # Authentication disabled for now
):
    """List all ChromaDB collections for current user"""

    try:
        # Authentication disabled - return all collections instead of user-specific
        collections = collection_manager.list_user_collections("")  # Empty user_id returns all
        return {
            "collections": collections,
            "total_count": len(collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


# Background task functions
async def process_file_background(
    file_metadata: FileMetadata,
    cert_id: str,
    bundle_version: str,
    domain_mappings: Dict[str, str]
):
    """Background task to process uploaded file"""
    try:
        result = await file_upload_service.process_uploaded_file(
            file_metadata=file_metadata,
            cert_id=cert_id,
            bundle_version=bundle_version,
            collection_manager=collection_manager,
            domain_mappings=domain_mappings
        )

        # Update file registry with results
        if result.success:
            file_registry.update_file_status(
                file_metadata.file_id,
                "completed",
                None
            )
        else:
            file_registry.update_file_status(
                file_metadata.file_id,
                "failed",
                result.error_message
            )

    except Exception as e:
        file_registry.update_file_status(
            file_metadata.file_id,
            "failed",
            str(e)
        )


# Health check endpoints
@router.get("/health")
async def health_check():
    """Health check for file management service"""
    stats = file_upload_service.processor.get_processing_stats()
    return {
        "status": "healthy",
        "processing_stats": stats,
        "total_files_in_registry": len(file_registry._files)
    }


@router.post("/cleanup")
async def cleanup_temp_files(
    max_age_hours: int = 24,
    # Authentication disabled for now
):
    """Clean up temporary files (admin only)"""
    # TODO: Add admin role check
    cleaned_count = await file_upload_service.cleanup_temp_files(max_age_hours)
    return {
        "message": f"Cleaned up {cleaned_count} temporary files",
        "max_age_hours": max_age_hours
    }