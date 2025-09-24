"""
File Upload Service for PresGen-Assess

Handles file uploads, processing, and integration with ChromaDB
for certification-specific knowledge bases.
"""

import os
import uuid
import hashlib
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

import aiofiles
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel

from src.service.chromadb_schema import (
    ChromaDBCollectionManager, ResourceType, ContentType,
    DifficultyLevel, create_document_metadata
)
from src.service.document_processor import DocumentProcessor


class FileMetadata(BaseModel):
    """Metadata for uploaded files"""
    file_id: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size: int
    mime_type: str
    upload_timestamp: str
    file_hash: str
    user_id: str
    cert_profile_id: str
    resource_type: ResourceType
    processing_status: str = "pending"  # pending, processing, completed, failed
    chunk_count: int = 0
    error_message: Optional[str] = None


class ProcessingResult(BaseModel):
    """Result of file processing"""
    file_id: str
    success: bool
    chunk_count: int
    processing_time_seconds: float
    error_message: Optional[str] = None
    warnings: List[str] = []


class FileUploadService:
    """Service for handling file uploads and processing"""

    def __init__(
        self,
        upload_dir: str = "uploads",
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        allowed_extensions: List[str] = None
    ):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or ['.pdf', '.docx', '.txt', '.md']
        self.processor = DocumentProcessor()

        # Create subdirectories
        self.create_subdirectories()

    def create_subdirectories(self):
        """Create organized subdirectories for uploads"""
        for subdir in ['exam_guides', 'transcripts', 'supplemental', 'temp']:
            (self.upload_dir / subdir).mkdir(exist_ok=True)

    def get_resource_directory(self, resource_type: ResourceType) -> Path:
        """Get directory path for resource type"""
        type_mapping = {
            ResourceType.EXAM_GUIDE: 'exam_guides',
            ResourceType.TRANSCRIPT: 'transcripts',
            ResourceType.SUPPLEMENTAL: 'supplemental'
        }
        return self.upload_dir / type_mapping[resource_type]

    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check file extension
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Supported types: {', '.join(self.allowed_extensions)}"
            )

        # Check file size (approximation from content-length header)
        if hasattr(file, 'size') and file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {self.max_file_size / (1024*1024):.1f}MB"
            )

    async def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def save_uploaded_file(
        self,
        file: UploadFile,
        user_id: str,
        cert_profile_id: str,
        resource_type: ResourceType
    ) -> FileMetadata:
        """Save uploaded file to disk and create metadata"""

        # Validate file
        self.validate_file(file)

        # Generate unique file ID and stored filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{file_extension}"

        # Get resource directory
        resource_dir = self.get_resource_directory(resource_type)
        file_path = resource_dir / stored_filename

        # Save file to disk
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
                file_size = len(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Calculate file hash
        file_hash = await self.calculate_file_hash(file_path)

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        # Create metadata
        metadata = FileMetadata(
            file_id=file_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            upload_timestamp=datetime.utcnow().isoformat(),
            file_hash=file_hash,
            user_id=user_id,
            cert_profile_id=cert_profile_id,
            resource_type=resource_type
        )

        return metadata

    async def process_uploaded_file(
        self,
        file_metadata: FileMetadata,
        cert_id: str,
        bundle_version: str,
        collection_manager: ChromaDBCollectionManager,
        domain_mappings: Optional[Dict[str, str]] = None
    ) -> ProcessingResult:
        """Process uploaded file and add to ChromaDB collection"""

        start_time = datetime.now()
        warnings = []

        try:
            # Update processing status
            file_metadata.processing_status = "processing"

            # Process document into chunks
            chunks = await self.processor.process_file(
                file_path=Path(file_metadata.file_path),
                mime_type=file_metadata.mime_type
            )

            if not chunks:
                return ProcessingResult(
                    file_id=file_metadata.file_id,
                    success=False,
                    chunk_count=0,
                    processing_time_seconds=0,
                    error_message="No content could be extracted from file"
                )

            # Get or create collection
            try:
                collection = collection_manager.get_collection(
                    user_id=file_metadata.user_id,
                    cert_id=cert_id,
                    bundle_version=bundle_version
                )
            except Exception:
                # Collection doesn't exist, this should be created when cert profile is created
                return ProcessingResult(
                    file_id=file_metadata.file_id,
                    success=False,
                    chunk_count=0,
                    processing_time_seconds=0,
                    error_message=f"Collection not found for cert_id: {cert_id}, bundle_version: {bundle_version}"
                )

            # Create document metadata for each chunk
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                # Extract domain from content if domain mappings provided
                domain = ""
                if domain_mappings:
                    for domain_key, domain_name in domain_mappings.items():
                        if domain_key.lower() in chunk.get('content', '').lower():
                            domain = domain_name
                            break

                # Create metadata for chunk
                doc_metadata = create_document_metadata(
                    content=chunk['content'],
                    user_id=file_metadata.user_id,
                    cert_id=cert_id,
                    cert_profile_id=file_metadata.cert_profile_id,
                    bundle_version=bundle_version,
                    resource_type=file_metadata.resource_type,
                    source_file=file_metadata.original_filename,
                    source_uri=file_metadata.file_path,
                    mime_type=file_metadata.mime_type,
                    chunk_index=i,
                    content_type=ContentType.CONCEPT,  # Default, could be enhanced
                    section=chunk.get('section', ''),
                    page=chunk.get('page'),
                    domain=domain,
                    subdomain=chunk.get('subdomain', ''),
                    difficulty_level=DifficultyLevel.INTERMEDIATE,  # Default
                    keywords=chunk.get('keywords', []),
                    concepts=chunk.get('concepts', [])
                )

                documents.append(chunk['content'])
                metadatas.append(doc_metadata)

            # Add documents to collection
            collection_manager.add_documents(
                collection=collection,
                documents=documents,
                metadatas=metadatas
            )

            # Update file metadata
            file_metadata.processing_status = "completed"
            file_metadata.chunk_count = len(chunks)

            processing_time = (datetime.now() - start_time).total_seconds()

            return ProcessingResult(
                file_id=file_metadata.file_id,
                success=True,
                chunk_count=len(chunks),
                processing_time_seconds=processing_time,
                warnings=warnings
            )

        except Exception as e:
            file_metadata.processing_status = "failed"
            file_metadata.error_message = str(e)

            processing_time = (datetime.now() - start_time).total_seconds()

            return ProcessingResult(
                file_id=file_metadata.file_id,
                success=False,
                chunk_count=0,
                processing_time_seconds=processing_time,
                error_message=str(e)
            )

    async def delete_file(self, file_metadata: FileMetadata) -> bool:
        """Delete uploaded file from disk"""
        try:
            file_path = Path(file_metadata.file_path)
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about a file"""
        path = Path(file_path)
        if not path.exists():
            return {}

        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))

        return {
            "filename": path.name,
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "exists": True
        }

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than max_age_hours"""
        temp_dir = self.upload_dir / 'temp'
        if not temp_dir.exists():
            return 0

        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        cleaned_count = 0

        for file_path in temp_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception:
                    pass  # Ignore cleanup errors

        return cleaned_count


class FileRegistry:
    """Registry for tracking uploaded files and their metadata"""

    def __init__(self):
        self._files: Dict[str, FileMetadata] = {}

    def register_file(self, file_metadata: FileMetadata) -> None:
        """Register uploaded file metadata"""
        self._files[file_metadata.file_id] = file_metadata

    def get_file(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID"""
        return self._files.get(file_id)

    def get_files_for_profile(self, cert_profile_id: str) -> List[FileMetadata]:
        """Get all files for a certification profile"""
        return [
            metadata for metadata in self._files.values()
            if metadata.cert_profile_id == cert_profile_id
        ]

    def get_files_for_user(self, user_id: str) -> List[FileMetadata]:
        """Get all files for a user"""
        return [
            metadata for metadata in self._files.values()
            if metadata.user_id == user_id
        ]

    def remove_file(self, file_id: str) -> bool:
        """Remove file from registry"""
        if file_id in self._files:
            del self._files[file_id]
            return True
        return False

    def update_file_status(self, file_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """Update file processing status"""
        if file_id in self._files:
            self._files[file_id].processing_status = status
            if error_message:
                self._files[file_id].error_message = error_message
            return True
        return False


# Global file registry instance
file_registry = FileRegistry()