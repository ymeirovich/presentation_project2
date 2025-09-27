"""Google Drive folder organization and management service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from src.services.google_auth_manager import GoogleAuthManager
from src.common.enhanced_logging import get_enhanced_logger


class DriveFolderManager:
    """Manages Google Drive folder organization for assessment workflows."""

    def __init__(self):
        self.logger = get_enhanced_logger(__name__)
        self.auth_manager = GoogleAuthManager()
        self.drive_service = None
        self._folder_cache: Dict[str, str] = {}  # folder_path -> folder_id

    async def _get_drive_service(self):
        """Get authenticated Google Drive service."""
        if not self.drive_service:
            credentials = self.auth_manager.get_service_credentials()
            self.drive_service = build('drive', 'v3', credentials=credentials)
        return self.drive_service

    async def create_assessment_folder_structure(
        self,
        workflow_id: UUID,
        certification_name: str,
        user_id: str,
        parent_folder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create organized folder structure for assessment workflow."""
        try:
            drive_service = await self._get_drive_service()

            # Create main assessment folder
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            main_folder_name = f"{certification_name}_Assessment_{timestamp}"

            main_folder = await self._create_folder(
                drive_service,
                main_folder_name,
                parent_folder_id,
                description=f"Assessment workflow {workflow_id} for user {user_id}"
            )

            main_folder_id = main_folder["id"]

            # Create subfolders
            subfolders = {}

            # Forms subfolder
            forms_folder = await self._create_folder(
                drive_service,
                "Forms",
                main_folder_id,
                description="Google Forms and related files"
            )
            subfolders["forms"] = forms_folder["id"]

            # Responses subfolder
            responses_folder = await self._create_folder(
                drive_service,
                "Responses",
                main_folder_id,
                description="Response data and analysis"
            )
            subfolders["responses"] = responses_folder["id"]

            # Analysis subfolder
            analysis_folder = await self._create_folder(
                drive_service,
                "Analysis",
                main_folder_id,
                description="Gap analysis and assessment results"
            )
            subfolders["analysis"] = analysis_folder["id"]

            # Reports subfolder
            reports_folder = await self._create_folder(
                drive_service,
                "Reports",
                main_folder_id,
                description="Generated reports and presentations"
            )
            subfolders["reports"] = reports_folder["id"]

            # Set folder permissions
            await self._configure_folder_permissions(
                drive_service,
                main_folder_id,
                user_id
            )

            folder_structure = {
                "main_folder_id": main_folder_id,
                "main_folder_name": main_folder_name,
                "main_folder_url": f"https://drive.google.com/drive/folders/{main_folder_id}",
                "subfolders": subfolders,
                "subfolder_urls": {
                    name: f"https://drive.google.com/drive/folders/{folder_id}"
                    for name, folder_id in subfolders.items()
                }
            }

            self.logger.info("Created assessment folder structure", extra={
                "workflow_id": str(workflow_id),
                "main_folder_id": main_folder_id,
                "main_folder_name": main_folder_name,
                "subfolder_count": len(subfolders),
                "user_id": user_id
            })

            return {
                "success": True,
                "folder_structure": folder_structure
            }

        except Exception as e:
            self.logger.error("Failed to create folder structure", extra={
                "workflow_id": str(workflow_id),
                "certification_name": certification_name,
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def _create_folder(
        self,
        drive_service,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a folder in Google Drive."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]

        if description:
            folder_metadata['description'] = description

        try:
            folder = drive_service.files().create(
                body=folder_metadata,
                fields='id,name,webViewLink'
            ).execute()

            self.logger.debug("Created Drive folder", extra={
                "folder_name": folder_name,
                "folder_id": folder.get("id"),
                "parent_folder_id": parent_folder_id
            })

            return folder

        except HttpError as e:
            self.logger.error("Failed to create Drive folder", extra={
                "folder_name": folder_name,
                "parent_folder_id": parent_folder_id,
                "error": str(e)
            })
            raise

    async def _configure_folder_permissions(
        self,
        drive_service,
        folder_id: str,
        user_id: str
    ):
        """Configure appropriate permissions for assessment folders."""
        try:
            # Give the user full access
            user_permission = {
                'type': 'user',
                'role': 'writer',
                'emailAddress': user_id if '@' in user_id else f"{user_id}@example.com"
            }

            try:
                drive_service.permissions().create(
                    fileId=folder_id,
                    body=user_permission,
                    sendNotificationEmail=False
                ).execute()

                self.logger.debug("Set user permissions", extra={
                    "folder_id": folder_id,
                    "user_id": user_id
                })

            except HttpError as e:
                # Permission setting may fail if user doesn't exist
                self.logger.warning("Could not set user permissions", extra={
                    "folder_id": folder_id,
                    "user_id": user_id,
                    "error": str(e)
                })

        except Exception as e:
            self.logger.error("Failed to configure folder permissions", extra={
                "folder_id": folder_id,
                "user_id": user_id,
                "error": str(e)
            })

    async def organize_form_in_folder(
        self,
        form_id: str,
        forms_folder_id: str,
        workflow_id: UUID
    ) -> Dict[str, Any]:
        """Move or copy a Google Form to the appropriate folder."""
        try:
            drive_service = await self._get_drive_service()

            # Get current form parents
            form_file = drive_service.files().get(
                fileId=form_id,
                fields='parents,name'
            ).execute()

            # Move form to forms folder
            previous_parents = ",".join(form_file.get('parents', []))

            updated_file = drive_service.files().update(
                fileId=form_id,
                addParents=forms_folder_id,
                removeParents=previous_parents,
                fields='id,parents,webViewLink'
            ).execute()

            self.logger.info("Organized form in folder", extra={
                "form_id": form_id,
                "forms_folder_id": forms_folder_id,
                "workflow_id": str(workflow_id),
                "form_name": form_file.get('name')
            })

            return {
                "success": True,
                "form_id": form_id,
                "new_location": forms_folder_id,
                "form_url": updated_file.get('webViewLink')
            }

        except Exception as e:
            self.logger.error("Failed to organize form in folder", extra={
                "form_id": form_id,
                "forms_folder_id": forms_folder_id,
                "workflow_id": str(workflow_id),
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def create_analysis_spreadsheet(
        self,
        analysis_folder_id: str,
        workflow_id: UUID,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a Google Sheets spreadsheet with analysis results."""
        try:
            drive_service = await self._get_drive_service()

            # Create spreadsheet
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            sheet_name = f"Assessment_Analysis_{timestamp}"

            sheet_metadata = {
                'name': sheet_name,
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [analysis_folder_id]
            }

            spreadsheet = drive_service.files().create(
                body=sheet_metadata,
                fields='id,name,webViewLink'
            ).execute()

            # TODO: Populate spreadsheet with analysis data using Sheets API
            # This would require additional Sheets API integration

            self.logger.info("Created analysis spreadsheet", extra={
                "spreadsheet_id": spreadsheet.get("id"),
                "spreadsheet_name": sheet_name,
                "analysis_folder_id": analysis_folder_id,
                "workflow_id": str(workflow_id)
            })

            return {
                "success": True,
                "spreadsheet_id": spreadsheet.get("id"),
                "spreadsheet_name": sheet_name,
                "spreadsheet_url": spreadsheet.get("webViewLink"),
                "folder_id": analysis_folder_id
            }

        except Exception as e:
            self.logger.error("Failed to create analysis spreadsheet", extra={
                "analysis_folder_id": analysis_folder_id,
                "workflow_id": str(workflow_id),
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def cleanup_old_folders(
        self,
        retention_days: int = 90,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old assessment folders based on retention policy."""
        try:
            drive_service = await self._get_drive_service()

            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            cutoff_iso = cutoff_date.isoformat() + 'Z'

            # Search for old assessment folders
            query = (
                f"mimeType='application/vnd.google-apps.folder' "
                f"and name contains 'Assessment' "
                f"and createdTime < '{cutoff_iso}'"
            )

            results = drive_service.files().list(
                q=query,
                fields='files(id,name,createdTime,description)',
                pageSize=100
            ).execute()

            old_folders = results.get('files', [])
            cleanup_results = []

            for folder in old_folders:
                folder_info = {
                    "folder_id": folder["id"],
                    "folder_name": folder["name"],
                    "created_time": folder["createdTime"],
                    "description": folder.get("description", "")
                }

                if not dry_run:
                    try:
                        drive_service.files().delete(fileId=folder["id"]).execute()
                        folder_info["status"] = "deleted"
                    except HttpError as e:
                        folder_info["status"] = "failed"
                        folder_info["error"] = str(e)
                else:
                    folder_info["status"] = "would_delete"

                cleanup_results.append(folder_info)

            self.logger.info("Completed folder cleanup", extra={
                "retention_days": retention_days,
                "dry_run": dry_run,
                "folders_found": len(old_folders),
                "folders_processed": len(cleanup_results)
            })

            return {
                "success": True,
                "cleanup_results": cleanup_results,
                "dry_run": dry_run,
                "retention_days": retention_days,
                "cutoff_date": cutoff_date.isoformat()
            }

        except Exception as e:
            self.logger.error("Failed to cleanup old folders", extra={
                "retention_days": retention_days,
                "dry_run": dry_run,
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def get_folder_structure_info(self, main_folder_id: str) -> Dict[str, Any]:
        """Get information about an existing folder structure."""
        try:
            drive_service = await self._get_drive_service()

            # Get main folder info
            main_folder = drive_service.files().get(
                fileId=main_folder_id,
                fields='id,name,description,createdTime,webViewLink'
            ).execute()

            # Get subfolders
            subfolders_query = f"'{main_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
            subfolders_result = drive_service.files().list(
                q=subfolders_query,
                fields='files(id,name,description,webViewLink)'
            ).execute()

            subfolders = {}
            for subfolder in subfolders_result.get('files', []):
                subfolders[subfolder['name'].lower()] = {
                    "id": subfolder['id'],
                    "name": subfolder['name'],
                    "url": subfolder.get('webViewLink'),
                    "description": subfolder.get('description', '')
                }

            # Count files in each subfolder
            for folder_name, folder_info in subfolders.items():
                files_query = f"'{folder_info['id']}' in parents"
                files_result = drive_service.files().list(
                    q=files_query,
                    fields='files(id,name,mimeType)'
                ).execute()
                folder_info["file_count"] = len(files_result.get('files', []))

            return {
                "success": True,
                "main_folder": {
                    "id": main_folder['id'],
                    "name": main_folder['name'],
                    "description": main_folder.get('description', ''),
                    "created_time": main_folder.get('createdTime'),
                    "url": main_folder.get('webViewLink')
                },
                "subfolders": subfolders,
                "total_subfolders": len(subfolders)
            }

        except Exception as e:
            self.logger.error("Failed to get folder structure info", extra={
                "main_folder_id": main_folder_id,
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }

    async def export_folder_contents_list(
        self,
        folder_id: str,
        include_subfolders: bool = True
    ) -> Dict[str, Any]:
        """Export a list of all contents in a folder structure."""
        try:
            drive_service = await self._get_drive_service()

            contents = []

            def _scan_folder(current_folder_id: str, folder_path: str = ""):
                """Recursively scan folder contents."""
                query = f"'{current_folder_id}' in parents"
                results = drive_service.files().list(
                    q=query,
                    fields='files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink)',
                    pageSize=1000
                ).execute()

                for file_item in results.get('files', []):
                    file_info = {
                        "id": file_item['id'],
                        "name": file_item['name'],
                        "mime_type": file_item['mimeType'],
                        "size": file_item.get('size', 0),
                        "created_time": file_item.get('createdTime'),
                        "modified_time": file_item.get('modifiedTime'),
                        "url": file_item.get('webViewLink'),
                        "folder_path": folder_path,
                        "is_folder": file_item['mimeType'] == 'application/vnd.google-apps.folder'
                    }
                    contents.append(file_info)

                    # Recursively scan subfolders if requested
                    if (include_subfolders and
                        file_item['mimeType'] == 'application/vnd.google-apps.folder'):
                        subfolder_path = f"{folder_path}/{file_item['name']}" if folder_path else file_item['name']
                        _scan_folder(file_item['id'], subfolder_path)

            _scan_folder(folder_id)

            # Calculate statistics
            total_files = len([c for c in contents if not c['is_folder']])
            total_folders = len([c for c in contents if c['is_folder']])
            total_size = sum(int(c.get('size', 0)) for c in contents if c.get('size'))

            return {
                "success": True,
                "contents": contents,
                "statistics": {
                    "total_files": total_files,
                    "total_folders": total_folders,
                    "total_size_bytes": total_size,
                    "total_items": len(contents)
                }
            }

        except Exception as e:
            self.logger.error("Failed to export folder contents", extra={
                "folder_id": folder_id,
                "include_subfolders": include_subfolders,
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e)
            }