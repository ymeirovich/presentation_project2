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

        print(f"📥 FileUploadService: Saving file '{file.filename}'")
        print(f"  Profile: {cert_profile_id}")
        print(f"  Resource Type: {resource_type}")

        # Validate file
        print(f"  Validating file...")
        self.validate_file(file)
        print(f"  ✅ File validation passed")

        # Generate unique file ID and stored filename
        file_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{file_extension}"
        print(f"  Generated File ID: {file_id}")
        print(f"  Stored filename: {stored_filename}")

        # Get resource directory
        resource_dir = self.get_resource_directory(resource_type)
        file_path = resource_dir / stored_filename
        print(f"  Storage path: {file_path}")

        # Save file to disk
        try:
            print(f"  Writing file to disk...")
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
                file_size = len(content)
            print(f"  ✅ File written: {file_size} bytes")
        except Exception as e:
            print(f"  ❌ File write failed: {type(e).__name__}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Calculate file hash
        print(f"  Calculating file hash...")
        file_hash = await self.calculate_file_hash(file_path)
        print(f"  ✅ File hash: {file_hash[:16]}...")

        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = "application/octet-stream"
        print(f"  MIME type: {mime_type}")

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

        print(f"✅ FileUploadService: File saved successfully")
        print(f"  File ID: {file_id}")
        print(f"  Size: {file_size} bytes")
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
    """Registry for tracking uploaded files and their metadata - DATABASE-BACKED"""

    def __init__(self, db_session=None):
        # Keep in-memory cache for performance, but sync with database
        self._files: Dict[str, FileMetadata] = {}
        self._db_session = db_session

    def _get_db(self):
        """Get database session"""
        if self._db_session:
            return self._db_session

        # Create synchronous SQLite session for file registry
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.models.base import Base

        # Use SQLite database
        db_path = 'test_database.db'
        engine = create_engine(f'sqlite:///{db_path}', echo=False)

        # Ensure tables exist in SQLite database
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        return Session()

    def _save_to_database(self, file_metadata: FileMetadata) -> None:
        """Persist file metadata to database"""
        from src.models.certification import KnowledgeBaseDocument
        from sqlalchemy.exc import IntegrityError
        from uuid import UUID

        print(f"    💾 _save_to_database: Starting database save")
        db = self._get_db()
        print(f"    ✅ Database session obtained")

        try:
            # Convert string UUIDs to UUID objects if needed
            file_uuid = UUID(file_metadata.file_id) if isinstance(file_metadata.file_id, str) else file_metadata.file_id
            profile_uuid = UUID(file_metadata.cert_profile_id) if isinstance(file_metadata.cert_profile_id, str) else file_metadata.cert_profile_id
            print(f"    ✅ UUIDs converted: file={file_uuid}, profile={profile_uuid}")

            # Check if document already exists
            print(f"    Checking for existing document...")
            existing = db.query(KnowledgeBaseDocument).filter_by(id=file_uuid).first()

            if existing:
                print(f"    📝 Updating existing record")
                # Update existing record
                existing.original_filename = file_metadata.original_filename
                existing.stored_path = file_metadata.file_path
                existing.document_type = file_metadata.mime_type
                existing.content_classification = file_metadata.resource_type.value
                existing.file_size_bytes = file_metadata.file_size
                existing.processing_status = file_metadata.processing_status
                existing.chunk_count = file_metadata.chunk_count
                existing.checksum = file_metadata.file_hash
            else:
                print(f"    ➕ Creating new database record")
                # Create new record
                db_record = KnowledgeBaseDocument(
                    id=file_uuid,
                    certification_profile_id=profile_uuid,
                    original_filename=file_metadata.original_filename,
                    stored_path=file_metadata.file_path,
                    document_type=file_metadata.mime_type,
                    content_classification=file_metadata.resource_type.value,
                    file_size_bytes=file_metadata.file_size,
                    processing_status=file_metadata.processing_status,
                    chunk_count=file_metadata.chunk_count,
                    checksum=file_metadata.file_hash
                )
                db.add(db_record)
                print(f"    ✅ Record added to session")

            print(f"    Committing transaction...")
            db.commit()
            print(f"    ✅ Database commit successful")
        except IntegrityError as ie:
            print(f"    ⚠️ IntegrityError (duplicate?): {str(ie)}")
            db.rollback()
        except Exception as e:
            print(f"    ❌ Database save failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
            raise

    def _load_from_database(self, cert_profile_id: str = None, user_id: str = None) -> List[FileMetadata]:
        """Load file metadata from database"""
        from src.models.certification import KnowledgeBaseDocument
        from uuid import UUID

        db = self._get_db()
        query = db.query(KnowledgeBaseDocument)

        if cert_profile_id:
            # Convert string UUID to UUID object if needed
            profile_uuid = UUID(cert_profile_id) if isinstance(cert_profile_id, str) else cert_profile_id
            query = query.filter_by(certification_profile_id=profile_uuid)

        documents = query.all()

        file_metadatas = []
        for doc in documents:
            # Convert database record to FileMetadata
            try:
                file_metadata = FileMetadata(
                    file_id=str(doc.id),
                    original_filename=doc.original_filename,
                    stored_filename=Path(doc.stored_path).name,
                    file_path=doc.stored_path,
                    file_size=doc.file_size_bytes,
                    mime_type=doc.document_type or 'application/octet-stream',
                    upload_timestamp=doc.created_at.isoformat() if doc.created_at else datetime.now().isoformat(),
                    file_hash=doc.checksum or '',
                    user_id=user_id or '',  # Note: user_id not stored in KnowledgeBaseDocument
                    cert_profile_id=str(doc.certification_profile_id),
                    resource_type=ResourceType(doc.content_classification) if doc.content_classification else ResourceType.SUPPLEMENTAL,
                    processing_status=doc.processing_status or 'pending',
                    chunk_count=doc.chunk_count or 0,
                    error_message=None
                )
                file_metadatas.append(file_metadata)
            except Exception as e:
                print(f"Error converting database record to FileMetadata: {e}")
                continue

        return file_metadatas

    def register_file(self, file_metadata: FileMetadata) -> None:
        """Register uploaded file metadata - persists to database"""
        print(f"📝 FileRegistry: Registering file {file_metadata.file_id}")
        print(f"  Filename: {file_metadata.original_filename}")
        print(f"  Profile: {file_metadata.cert_profile_id}")
        print(f"  Resource Type: {file_metadata.resource_type}")

        self._files[file_metadata.file_id] = file_metadata
        print(f"  ✅ Added to in-memory cache")

        print(f"  Saving to database...")
        self._save_to_database(file_metadata)
        print(f"✅ FileRegistry: File registered successfully")

    def get_file(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID - checks cache first, then database"""
        from uuid import UUID

        # Check in-memory cache first
        if file_id in self._files:
            return self._files[file_id]

        # Load from database
        from src.models.certification import KnowledgeBaseDocument
        db = self._get_db()

        # Convert string UUID to UUID object if needed
        uuid_obj = UUID(file_id) if isinstance(file_id, str) else file_id
        doc = db.query(KnowledgeBaseDocument).filter_by(id=uuid_obj).first()

        if doc:
            file_metadatas = self._load_from_database()
            for fm in file_metadatas:
                if fm.file_id == file_id:
                    self._files[file_id] = fm  # Cache it
                    return fm

        return None

    def get_files_for_profile(self, cert_profile_id: str) -> List[FileMetadata]:
        """Get all files for a certification profile - loads from database"""
        # Load from database to ensure we have latest data
        file_metadatas = self._load_from_database(cert_profile_id=cert_profile_id)

        # Update cache
        for fm in file_metadatas:
            self._files[fm.file_id] = fm

        return file_metadatas

    def get_files_for_user(self, user_id: str) -> List[FileMetadata]:
        """Get all files for a user - loads from database"""
        # Load from database
        file_metadatas = self._load_from_database(user_id=user_id)

        # Update cache
        for fm in file_metadatas:
            self._files[fm.file_id] = fm

        return file_metadatas

    def remove_file(self, file_id: str) -> bool:
        """Remove file from registry - removes from database"""
        from src.models.certification import KnowledgeBaseDocument
        from uuid import UUID

        db = self._get_db()
        try:
            # Convert string UUID to UUID object if needed
            uuid_obj = UUID(file_id) if isinstance(file_id, str) else file_id

            # Remove from database
            doc = db.query(KnowledgeBaseDocument).filter_by(id=uuid_obj).first()
            if doc:
                db.delete(doc)
                db.commit()

            # Remove from cache (use string key)
            if file_id in self._files:
                del self._files[file_id]

            return True
        except Exception as e:
            db.rollback()
            print(f"Error removing file from registry: {e}")
            return False

    def update_file_status(
        self,
        file_id: str,
        status: str,
        error_message: Optional[str] = None,
        chunk_count: Optional[int] = None
    ) -> bool:
        """Update file processing status - updates database"""
        from src.models.certification import KnowledgeBaseDocument
        from uuid import UUID

        db = self._get_db()
        try:
            # Convert string UUID to UUID object if needed
            uuid_obj = UUID(file_id) if isinstance(file_id, str) else file_id

            # Update database
            doc = db.query(KnowledgeBaseDocument).filter_by(id=uuid_obj).first()
            if doc:
                doc.processing_status = status
                if chunk_count is not None:
                    doc.chunk_count = chunk_count
                    doc.processed_at = datetime.utcnow()
                db.commit()

            # Update cache (use string key)
            if file_id in self._files:
                self._files[file_id].processing_status = status
                if chunk_count is not None:
                    self._files[file_id].chunk_count = chunk_count
                if error_message:
                    self._files[file_id].error_message = error_message

            return True
        except Exception as e:
            db.rollback()
            print(f"Error updating file status: {e}")
            return False


# Global file registry instance
file_registry = FileRegistry()
