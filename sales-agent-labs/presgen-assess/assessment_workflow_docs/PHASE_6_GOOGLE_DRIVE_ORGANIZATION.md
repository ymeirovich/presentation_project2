# Phase 6: Google Drive Organization
*System for Automatic Drive File Management and Structure*

## Overview
Automated Google Drive organization system that creates standardized folder structures, manages file permissions, and maintains organized archives of assessment materials and user-generated content.

## 6.1 Drive Structure Management

### 6.1.1 Automated Folder Creation
```python
# /presgen-assess/src/service/google_drive/folder_manager.py
class DriveStructureManager:
    """
    Manages standardized folder structures in Google Drive.
    Creates hierarchical organization for certification content.
    """

    async def create_certification_structure(
        self,
        certification_name: str,
        organization_id: str
    ) -> Dict[str, str]:
        """
        Creates complete folder structure for a new certification.
        Returns mapping of folder types to Google Drive folder IDs.

        Structure:
        /[Organization]/
        ├── Certifications/
        │   └── [Certification_Name]/
        │       ├── Knowledge_Base/
        │       │   ├── Documents/
        │       │   ├── Processed/
        │       │   └── Archive/
        │       ├── Assessments/
        │       │   ├── Generated/
        │       │   ├── Templates/
        │       │   └── Results/
        │       ├── User_Profiles/
        │       │   ├── Active/
        │       │   └── Archived/
        │       └── Reports/
        │           ├── Gap_Analysis/
        │           ├── Progress_Reports/
        │           └── Analytics/
        """
        folder_structure = {
            'root': f"{organization_id}",
            'certifications': f"Certifications",
            'cert_main': f"{certification_name}",
            'knowledge_base': "Knowledge_Base",
            'kb_documents': "Documents",
            'kb_processed': "Processed",
            'kb_archive': "Archive",
            'assessments': "Assessments",
            'assess_generated': "Generated",
            'assess_templates': "Templates",
            'assess_results': "Results",
            'user_profiles': "User_Profiles",
            'profiles_active': "Active",
            'profiles_archived': "Archived",
            'reports': "Reports",
            'reports_gaps': "Gap_Analysis",
            'reports_progress': "Progress_Reports",
            'reports_analytics': "Analytics"
        }

        created_folders = {}
        parent_id = None

        # Create hierarchical structure
        for folder_key, folder_name in folder_structure.items():
            if folder_key == 'root':
                parent_id = await self._get_or_create_folder(
                    folder_name, None
                )
            else:
                parent_folder = self._get_parent_folder(folder_key)
                parent_id = created_folders.get(parent_folder, parent_id)

            folder_id = await self._create_folder_with_permissions(
                folder_name, parent_id, organization_id
            )
            created_folders[folder_key] = folder_id

        return created_folders
```

### 6.1.2 Permission Management System
```python
# /presgen-assess/src/service/google_drive/permissions.py
class DrivePermissionManager:
    """
    Manages Google Drive permissions for different user roles and content types.
    Implements role-based access control with inheritance.
    """

    PERMISSION_TEMPLATES = {
        'organization_admin': {
            'role': 'owner',
            'type': 'user',
            'applies_to': ['root', 'all_subfolders']
        },
        'certification_manager': {
            'role': 'writer',
            'type': 'user',
            'applies_to': ['cert_main', 'knowledge_base', 'assessments']
        },
        'instructor': {
            'role': 'writer',
            'type': 'user',
            'applies_to': ['assessments', 'user_profiles', 'reports']
        },
        'learner': {
            'role': 'reader',
            'type': 'user',
            'applies_to': ['kb_documents', 'assess_results']
        },
        'public_viewer': {
            'role': 'reader',
            'type': 'anyone',
            'applies_to': ['kb_documents']
        }
    }

    async def apply_certification_permissions(
        self,
        folder_structure: Dict[str, str],
        permission_config: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Applies permission templates to certification folder structure.
        Returns summary of permissions applied.
        """
        applied_permissions = {}

        for role, user_emails in permission_config.items():
            if role not in self.PERMISSION_TEMPLATES:
                continue

            template = self.PERMISSION_TEMPLATES[role]
            target_folders = self._resolve_folder_targets(
                template['applies_to'], folder_structure
            )

            for folder_id in target_folders:
                for email in user_emails:
                    permission_id = await self._grant_folder_permission(
                        folder_id, email, template['role'], template['type']
                    )

                    if folder_id not in applied_permissions:
                        applied_permissions[folder_id] = []
                    applied_permissions[folder_id].append(
                        f"{email}:{template['role']}"
                    )

        return applied_permissions
```

## 6.2 File Management Automation

### 6.2.1 Content Organization Engine
```python
# /presgen-assess/src/service/google_drive/content_organizer.py
class ContentOrganizer:
    """
    Automatically organizes uploaded files into appropriate Drive folders.
    Handles file naming conventions and metadata tagging.
    """

    async def organize_knowledge_base_upload(
        self,
        file_id: str,
        certification_name: str,
        file_metadata: Dict[str, Any],
        content_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Organizes knowledge base document uploads.
        Applies intelligent categorization and naming.
        """
        # Analyze file content for categorization
        file_category = await self._categorize_document(
            file_id, content_analysis
        )

        # Generate standardized filename
        standardized_name = self._generate_standard_filename(
            file_metadata['original_name'],
            certification_name,
            file_category,
            file_metadata['upload_date']
        )

        # Determine target folder based on content type
        target_folder_key = self._determine_target_folder(
            file_category, file_metadata['file_type']
        )

        target_folder_id = await self._get_certification_folder(
            certification_name, target_folder_key
        )

        # Move and rename file
        organized_file = await self._move_and_rename_file(
            file_id, target_folder_id, standardized_name
        )

        # Apply content-specific metadata
        await self._apply_file_metadata(
            organized_file['id'],
            {
                'certification': certification_name,
                'category': file_category,
                'processed_date': datetime.utcnow().isoformat(),
                'content_hash': content_analysis.get('content_hash'),
                'version': file_metadata.get('version', '1.0')
            }
        )

        return {
            'organized_file_id': organized_file['id'],
            'final_path': organized_file['path'],
            'category': file_category,
            'target_folder': target_folder_key
        }

    def _generate_standard_filename(
        self,
        original_name: str,
        certification_name: str,
        category: str,
        upload_date: datetime
    ) -> str:
        """
        Generates standardized filename following organizational conventions.
        Format: [CERT]_[CATEGORY]_[DATE]_[ORIGINAL]
        """
        cert_prefix = certification_name.upper().replace(' ', '_')[:10]
        category_prefix = category.upper().replace(' ', '_')[:8]
        date_str = upload_date.strftime('%Y%m%d')

        # Clean original name
        clean_original = re.sub(r'[^\w\-_\.]', '_', original_name)
        clean_original = re.sub(r'_+', '_', clean_original)

        return f"{cert_prefix}_{category_prefix}_{date_str}_{clean_original}"
```

### 6.2.2 Archive Management System
```python
# /presgen-assess/src/service/google_drive/archive_manager.py
class ArchiveManager:
    """
    Manages automated archival of outdated content and version control.
    Implements retention policies and cleanup procedures.
    """

    RETENTION_POLICIES = {
        'knowledge_base_documents': {
            'active_retention_days': 365,
            'archive_retention_days': 1095,  # 3 years
            'version_limit': 5
        },
        'assessment_results': {
            'active_retention_days': 180,
            'archive_retention_days': 730,  # 2 years
            'version_limit': 3
        },
        'user_profiles': {
            'active_retention_days': 730,  # 2 years
            'archive_retention_days': 2555,  # 7 years (compliance)
            'version_limit': 10
        },
        'reports': {
            'active_retention_days': 90,
            'archive_retention_days': 365,
            'version_limit': 3
        }
    }

    async def execute_retention_policy(
        self,
        certification_name: str,
        content_type: str
    ) -> Dict[str, int]:
        """
        Executes retention policy for specified content type.
        Returns counts of files archived and deleted.
        """
        if content_type not in self.RETENTION_POLICIES:
            raise ValueError(f"Unknown content type: {content_type}")

        policy = self.RETENTION_POLICIES[content_type]
        results = {
            'files_archived': 0,
            'files_deleted': 0,
            'versions_cleaned': 0
        }

        # Get active folder for content type
        active_folder_id = await self._get_certification_folder(
            certification_name, f"{content_type}_active"
        )

        archive_folder_id = await self._get_certification_folder(
            certification_name, f"{content_type}_archive"
        )

        # Find files exceeding active retention
        cutoff_date = datetime.utcnow() - timedelta(
            days=policy['active_retention_days']
        )

        old_files = await self._find_files_older_than(
            active_folder_id, cutoff_date
        )

        # Archive old files
        for file_info in old_files:
            await self._move_file_to_archive(
                file_info['id'], archive_folder_id, file_info
            )
            results['files_archived'] += 1

        # Clean up archive based on archive retention
        archive_cutoff = datetime.utcnow() - timedelta(
            days=policy['archive_retention_days']
        )

        expired_files = await self._find_files_older_than(
            archive_folder_id, archive_cutoff
        )

        for file_info in expired_files:
            await self._delete_file_permanently(file_info['id'])
            results['files_deleted'] += 1

        # Version cleanup
        version_cleanup_count = await self._cleanup_file_versions(
            active_folder_id, policy['version_limit']
        )
        results['versions_cleaned'] = version_cleanup_count

        return results
```

## 6.3 Integration Points

### 6.3.1 Knowledge Base Integration
```python
# /presgen-assess/src/schemas/drive_integration.py
class DriveKnowledgeBaseConfig(BaseModel):
    """Configuration for Drive-Knowledge Base integration."""

    auto_organize: bool = True
    auto_process: bool = True
    notification_webhooks: List[str] = []
    content_analysis_enabled: bool = True
    duplicate_detection: bool = True

class DriveUploadEvent(BaseModel):
    """Event triggered when files are uploaded to Drive."""

    file_id: str
    folder_id: str
    certification_name: str
    uploader_email: str
    file_metadata: Dict[str, Any]
    timestamp: datetime

class DriveOrganizationResult(BaseModel):
    """Result of Drive organization operations."""

    success: bool
    organized_file_id: str
    final_path: str
    category: str
    processing_actions: List[str]
    error_details: Optional[str] = None
```

### 6.3.2 Assessment Integration
```python
# /presgen-assess/src/service/api/v1/endpoints/drive_assessment.py
@router.post("/assessments/{assessment_id}/save-to-drive")
async def save_assessment_to_drive(
    assessment_id: UUID,
    drive_config: DriveAssessmentSaveConfig,
    db: AsyncSession = Depends(get_db)
) -> DriveAssessmentSaveResponse:
    """
    Saves assessment results and artifacts to organized Drive structure.
    Creates links between database records and Drive files.
    """
    assessment = await get_assessment_by_id(assessment_id, db)
    if not assessment:
        raise HTTPException(404, "Assessment not found")

    # Create assessment package in Drive
    drive_package = await drive_manager.create_assessment_package(
        assessment_id=assessment_id,
        certification_name=assessment.certification_name,
        user_profile_id=assessment.user_profile_id,
        results_data=assessment.results,
        artifacts=drive_config.include_artifacts
    )

    # Update assessment record with Drive links
    assessment.drive_folder_id = drive_package['folder_id']
    assessment.drive_results_file_id = drive_package['results_file_id']

    await db.commit()

    return DriveAssessmentSaveResponse(
        success=True,
        drive_folder_id=drive_package['folder_id'],
        drive_folder_url=drive_package['folder_url'],
        saved_files=drive_package['saved_files']
    )
```

## 6.4 Monitoring and Analytics

### 6.4.1 Drive Usage Analytics
```python
# /presgen-assess/src/service/analytics/drive_analytics.py
class DriveAnalyticsCollector:
    """
    Collects and analyzes Drive usage patterns for optimization.
    Provides insights for storage management and user behavior.
    """

    async def collect_usage_metrics(
        self,
        certification_name: str,
        time_range: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """
        Collects comprehensive Drive usage metrics.
        """
        start_date, end_date = time_range

        metrics = {
            'storage_usage': await self._calculate_storage_usage(
                certification_name, start_date, end_date
            ),
            'file_activity': await self._analyze_file_activity(
                certification_name, start_date, end_date
            ),
            'access_patterns': await self._analyze_access_patterns(
                certification_name, start_date, end_date
            ),
            'organization_efficiency': await self._measure_organization_efficiency(
                certification_name
            )
        }

        return metrics

    async def _calculate_storage_usage(
        self,
        certification_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Calculate storage usage by category and time period."""
        folder_structure = await self._get_certification_folders(
            certification_name
        )

        usage_by_category = {}

        for category, folder_id in folder_structure.items():
            if category.startswith('_'):  # Skip internal keys
                continue

            folder_size = await self._calculate_folder_size(
                folder_id, start_date, end_date
            )
            usage_by_category[category] = {
                'total_bytes': folder_size['total_bytes'],
                'file_count': folder_size['file_count'],
                'avg_file_size': folder_size['avg_file_size']
            }

        return usage_by_category
```

### 6.4.2 Automated Optimization
```python
# /presgen-assess/src/service/google_drive/optimizer.py
class DriveOptimizer:
    """
    Automated optimization for Drive organization and performance.
    Implements smart cleanup and restructuring recommendations.
    """

    async def analyze_optimization_opportunities(
        self,
        certification_name: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyzes Drive structure for optimization opportunities.
        Returns actionable recommendations.
        """
        opportunities = {
            'duplicate_files': [],
            'oversized_files': [],
            'unused_files': [],
            'permission_issues': [],
            'structure_improvements': []
        }

        # Detect duplicate files
        duplicates = await self._find_duplicate_files(certification_name)
        for duplicate_group in duplicates:
            opportunities['duplicate_files'].append({
                'type': 'duplicate_content',
                'files': duplicate_group,
                'potential_savings_bytes': duplicate_group['total_duplicate_size'],
                'recommended_action': 'keep_latest_delete_others'
            })

        # Identify oversized files
        large_files = await self._find_oversized_files(certification_name)
        for file_info in large_files:
            opportunities['oversized_files'].append({
                'type': 'large_file',
                'file_id': file_info['id'],
                'size_bytes': file_info['size'],
                'recommended_action': 'compress_or_archive'
            })

        # Find unused files
        unused_files = await self._find_unused_files(certification_name)
        for file_info in unused_files:
            opportunities['unused_files'].append({
                'type': 'unused_file',
                'file_id': file_info['id'],
                'last_accessed': file_info['last_accessed'],
                'recommended_action': 'archive_or_delete'
            })

        return opportunities

    async def execute_optimization_plan(
        self,
        certification_name: str,
        optimization_plan: Dict[str, List[str]],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Executes approved optimization actions.
        Returns summary of changes made.
        """
        if dry_run:
            return await self._simulate_optimization(
                certification_name, optimization_plan
            )

        execution_results = {
            'files_deleted': 0,
            'files_compressed': 0,
            'files_archived': 0,
            'storage_freed_bytes': 0,
            'errors': []
        }

        # Execute each optimization action
        for action_type, file_ids in optimization_plan.items():
            for file_id in file_ids:
                try:
                    result = await self._execute_optimization_action(
                        action_type, file_id
                    )

                    execution_results[f"files_{action_type}"] += 1
                    execution_results['storage_freed_bytes'] += result.get(
                        'bytes_freed', 0
                    )

                except Exception as e:
                    execution_results['errors'].append({
                        'file_id': file_id,
                        'action': action_type,
                        'error': str(e)
                    })

        return execution_results
```

## 6.5 Configuration and Deployment

### 6.5.1 Drive Service Configuration
```yaml
# /presgen-assess/config/drive_config.yaml
google_drive:
  service_account_path: "${GOOGLE_APPLICATION_CREDENTIALS}"
  project_id: "${GOOGLE_CLOUD_PROJECT}"

  organization:
    auto_folder_creation: true
    permission_inheritance: true
    default_sharing_domain: "organization.com"

  retention_policies:
    knowledge_base:
      active_days: 365
      archive_days: 1095
      version_limit: 5
    assessments:
      active_days: 180
      archive_days: 730
      version_limit: 3

  optimization:
    auto_cleanup_enabled: true
    cleanup_schedule: "0 2 * * 0"  # Weekly at 2 AM
    duplicate_detection: true
    compression_threshold_mb: 50

  monitoring:
    usage_analytics: true
    performance_monitoring: true
    webhook_notifications: true
```

### 6.5.2 Database Integration
```sql
-- /presgen-assess/migrations/013_drive_integration.sql
CREATE TABLE drive_folder_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certification_name VARCHAR(100) NOT NULL,
    folder_type VARCHAR(50) NOT NULL,
    drive_folder_id VARCHAR(100) NOT NULL UNIQUE,
    parent_folder_id VARCHAR(100),
    folder_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(certification_name, folder_type)
);

CREATE TABLE drive_file_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drive_file_id VARCHAR(100) NOT NULL UNIQUE,
    original_filename VARCHAR(500) NOT NULL,
    standardized_filename VARCHAR(500) NOT NULL,
    certification_name VARCHAR(100) NOT NULL,
    content_category VARCHAR(100),
    folder_mapping_id UUID REFERENCES drive_folder_mappings(id),
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    content_hash VARCHAR(64),
    upload_date TIMESTAMP WITH TIME ZONE,
    last_accessed TIMESTAMP WITH TIME ZONE,
    archive_date TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_drive_files_cert_category (certification_name, content_category),
    INDEX idx_drive_files_hash (content_hash),
    INDEX idx_drive_files_upload_date (upload_date)
);

CREATE TABLE drive_optimization_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certification_name VARCHAR(100) NOT NULL,
    optimization_type VARCHAR(50) NOT NULL,
    files_affected INTEGER DEFAULT 0,
    storage_freed_bytes BIGINT DEFAULT 0,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_drive_optimization_cert_date (certification_name, executed_at)
);
```

## 6.6 Testing Strategy

### 6.6.1 Drive Integration Tests
```python
# /presgen-assess/tests/test_drive_integration.py
class TestDriveIntegration:
    """
    Integration tests for Google Drive organization system.
    Tests folder creation, file management, and permissions.
    """

    @pytest.mark.asyncio
    async def test_certification_folder_creation(self):
        """Test complete certification folder structure creation."""
        drive_manager = DriveStructureManager()

        folder_structure = await drive_manager.create_certification_structure(
            certification_name="AWS_Solutions_Architect",
            organization_id="test_org_123"
        )

        # Verify all required folders were created
        required_folders = [
            'root', 'certifications', 'cert_main', 'knowledge_base',
            'assessments', 'user_profiles', 'reports'
        ]

        for folder_key in required_folders:
            assert folder_key in folder_structure
            assert folder_structure[folder_key] is not None

        # Verify folder hierarchy
        assert await self._verify_folder_parent(
            folder_structure['cert_main'],
            folder_structure['certifications']
        )

    @pytest.mark.asyncio
    async def test_file_organization_workflow(self):
        """Test complete file upload and organization workflow."""
        organizer = ContentOrganizer()

        # Simulate file upload
        test_file_id = await self._upload_test_file(
            "test_certification_guide.pdf"
        )

        organization_result = await organizer.organize_knowledge_base_upload(
            file_id=test_file_id,
            certification_name="Test_Certification",
            file_metadata={
                'original_name': 'certification_guide.pdf',
                'file_type': 'application/pdf',
                'upload_date': datetime.utcnow()
            },
            content_analysis={
                'content_hash': 'abc123',
                'detected_topics': ['exam_objectives', 'study_guide']
            }
        )

        assert organization_result['success'] is True
        assert 'organized_file_id' in organization_result
        assert organization_result['category'] in ['study_guide', 'exam_prep']

    @pytest.mark.asyncio
    async def test_retention_policy_execution(self):
        """Test automated retention policy execution."""
        archive_manager = ArchiveManager()

        # Create test files with different ages
        old_file_id = await self._create_test_file_with_age(days_old=400)
        recent_file_id = await self._create_test_file_with_age(days_old=30)

        retention_results = await archive_manager.execute_retention_policy(
            certification_name="Test_Certification",
            content_type="knowledge_base_documents"
        )

        assert retention_results['files_archived'] >= 1

        # Verify old file was moved to archive
        file_location = await self._get_file_location(old_file_id)
        assert 'archive' in file_location['folder_path'].lower()

        # Verify recent file remains in active folder
        recent_location = await self._get_file_location(recent_file_id)
        assert 'archive' not in recent_location['folder_path'].lower()
```

This completes Phase 6 - Google Drive Organization. Moving to Phase 7.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create detailed Phase 1 document - Google APIs Foundation", "status": "completed", "activeForm": "Creating detailed Phase 1 document - Google APIs Foundation"}, {"content": "Create detailed Phase 2 document - Google Forms Automation", "status": "completed", "activeForm": "Creating detailed Phase 2 document - Google Forms Automation"}, {"content": "Create detailed Phase 3 document - Response Collection Pipeline", "status": "completed", "activeForm": "Creating detailed Phase 3 document - Response Collection Pipeline"}, {"content": "Create detailed Phase 4 document - PresGen-Core Integration", "status": "completed", "activeForm": "Creating detailed Phase 4 document - PresGen-Core Integration"}, {"content": "Create detailed Phase 5 document - PresGen-Avatar Integration", "status": "completed", "activeForm": "Creating detailed Phase 5 document - PresGen-Avatar Integration"}, {"content": "Create detailed Phase 6 document - Google Drive Organization", "status": "completed", "activeForm": "Creating detailed Phase 6 document - Google Drive Organization"}, {"content": "Create detailed Phase 7 document - End-to-End Integration", "status": "in_progress", "activeForm": "Creating detailed Phase 7 document - End-to-End Integration"}]