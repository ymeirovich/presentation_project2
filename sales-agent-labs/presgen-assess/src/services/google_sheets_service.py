"""Google Sheets integration service for exporting skill gap analysis results."""

import logging
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

try:
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for exporting skill gap analysis to Google Sheets.

    Supports both service account and OAuth user authentication.
    """

    def __init__(self, credentials_path: Optional[str] = None, use_oauth: bool = False):
        """Initialize Google Sheets service with credentials.

        Args:
            credentials_path: Path to service account JSON (if use_oauth=False)
                            or OAuth client JSON (if use_oauth=True)
            use_oauth: If True, use OAuth flow instead of service account
        """
        self.credentials_path = credentials_path
        self.use_oauth = use_oauth
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]

        if GOOGLE_SHEETS_AVAILABLE and credentials_path:
            try:
                self._initialize_service()
            except Exception as e:
                logger.warning(f"⚠️ Google Sheets service initialization failed: {e}")

    def _initialize_service(self):
        """Initialize Google Sheets API service with OAuth or service account."""
        try:
            if self.use_oauth:
                logger.info(f"🔐 Initializing Google Sheets with OAuth authentication")
                credentials = self._get_oauth_credentials()
                logger.info(f"✅ OAuth credentials obtained successfully")
            else:
                logger.info(f"🔐 Initializing Google Sheets with service account: {self.credentials_path}")
                credentials = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.scopes
                )
                logger.info(f"✅ Service account credentials loaded successfully")

            logger.debug(f"📋 Scopes: {', '.join(self.scopes)}")

            # Build Sheets API service
            self.service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)

            logger.info("✅ Google Sheets API service initialized successfully")

        except FileNotFoundError as e:
            logger.error(f"❌ Credentials file not found: {self.credentials_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets service: {e}", exc_info=True)
            raise

    def _get_oauth_credentials(self):
        """Get OAuth credentials, refreshing or authenticating as needed.

        Returns:
            OAuth credentials object
        """
        # Determine token path (same dir as oauth client, but named token_*.json)
        creds_dir = os.path.dirname(self.credentials_path)
        creds_filename = os.path.basename(self.credentials_path)
        token_filename = creds_filename.replace('oauth_', 'token_').replace('_client', '')
        token_path = os.path.join(creds_dir, token_filename)

        logger.debug(f"📁 OAuth client: {self.credentials_path}")
        logger.debug(f"📁 Token path: {token_path}")

        creds = None

        # Check if token exists
        if os.path.exists(token_path):
            logger.debug(f"📋 Loading existing OAuth token")
            creds = OAuthCredentials.from_authorized_user_file(token_path, self.scopes)

        # If no valid credentials, do OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing expired OAuth token")
                creds.refresh(Request())
                logger.info("✅ OAuth token refreshed successfully")
            else:
                logger.info("🔐 Starting OAuth flow (browser will open for authentication)")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("✅ OAuth authentication completed successfully")

            # Save token for future use
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"✅ OAuth token saved to: {token_path}")

        return creds

    async def export_skill_gap_analysis(
        self,
        gap_analysis_data: Dict,
        spreadsheet_title: Optional[str] = None,
        share_with_email: Optional[str] = None
    ) -> Dict:
        """Export skill gap analysis to Google Sheets with 4-tab format."""
        export_start_time = datetime.now()
        logger.info("📊 Starting Google Sheets export | title=%s share_email=%s", spreadsheet_title, share_with_email)

        try:
            if not GOOGLE_SHEETS_AVAILABLE:
                logger.warning("⚠️ Google Sheets libraries not available")
                return self._create_mock_export_response("Google Sheets libraries not available")

            if not self.service:
                logger.error("❌ Google Sheets service not initialized")
                return self._create_mock_export_response("Google Sheets service not initialized")

            # Create or get spreadsheet
            spreadsheet_title = spreadsheet_title or f"Skill_Gap_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            logger.info(f"📝 Creating spreadsheet: {spreadsheet_title}")

            spreadsheet = await self._create_spreadsheet(spreadsheet_title)

            if not spreadsheet:
                logger.error("❌ Spreadsheet creation returned None")
                return self._create_mock_export_response("Failed to create spreadsheet")

            spreadsheet_id = spreadsheet['spreadsheetId']
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            logger.info(f"✅ Spreadsheet created | id={spreadsheet_id} url={spreadsheet_url}")

            # Prepare export data
            export_data = gap_analysis_data.get("google_sheets_export_data", {})
            tabs = export_data.get("tabs", [])
            logger.info(f"📋 Export data prepared | tabs={len(tabs)}")

            # Create 4 tabs
            tabs_created = []
            for i, tab in enumerate(tabs, 1):
                tab_name = tab.get("tab_name", f"Tab{i}")
                logger.info(f"📄 Creating Tab {i}: {tab_name}")

                tab_result = await self._create_tab_from_data(
                    spreadsheet_id=spreadsheet_id,
                    tab_name=tab_name,
                    tab_data=tab,
                    is_first_tab=(i == 1)
                )

                if tab_result.get("success"):
                    tabs_created.append(tab_name)
                    logger.info(f"✅ Tab {i} ({tab_name}) created successfully")
                else:
                    logger.warning(f"⚠️ Tab {i} ({tab_name}) creation failed: {tab_result.get('error')}")

            # Share spreadsheet if email provided
            sharing_result = None
            if share_with_email:
                logger.info(f"🔗 Sharing spreadsheet with {share_with_email}")
                sharing_result = await self._share_spreadsheet(spreadsheet_id, share_with_email)
                logger.info(f"✅ Sharing completed | success={sharing_result.get('success')}")

            export_duration = (datetime.now() - export_start_time).total_seconds()
            logger.info(f"✅ Successfully exported skill gap analysis to Google Sheets | duration={export_duration:.2f}s url={spreadsheet_url}")

            return {
                "success": True,
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
                "spreadsheet_title": spreadsheet_title,
                "tabs_created": tabs_created,
                "export_timestamp": datetime.now().isoformat(),
                "sharing_status": sharing_result,
                "export_summary": {
                    "tabs_count": len(tabs_created),
                    "data_points_exported": sum(len(tab.get("data", [])) for tab in tabs)
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to export to Google Sheets: {e}")
            return self._create_mock_export_response(f"Export failed: {str(e)}")

    async def _create_tab_from_data(
        self,
        spreadsheet_id: str,
        tab_name: str,
        tab_data: Dict,
        is_first_tab: bool = False
    ) -> Dict:
        """Create a tab from structured tab data."""
        try:
            logger.debug(f"📝 Creating tab: {tab_name} | is_first={is_first_tab}")

            # Create new sheet (unless it's the first tab which already exists)
            sheet_id = 0
            if not is_first_tab:
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': tab_name,
                            'gridProperties': {
                                'rowCount': 1000,
                                'columnCount': 20
                            }
                        }
                    }
                }]

                batch_update_request = {'requests': requests}
                response = self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=batch_update_request
                ).execute()

                sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
                logger.debug(f"✅ New sheet created | sheet_id={sheet_id}")
            else:
                # Rename first sheet
                requests = [{
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': 0,
                            'title': tab_name
                        },
                        'fields': 'title'
                    }
                }]

                batch_update_request = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=batch_update_request
                ).execute()
                logger.debug(f"✅ First sheet renamed to: {tab_name}")

            # Add title and data
            updates = []
            current_row = 1

            # Add title
            title = tab_data.get("title", tab_name)
            updates.append({
                'range': f'{tab_name}!A{current_row}',
                'values': [[title]]
            })
            current_row += 1

            # Add summary if exists
            summary = tab_data.get("summary")
            if summary:
                current_row += 1
                updates.append({
                    'range': f'{tab_name}!A{current_row}',
                    'values': [[summary]]
                })
                current_row += 2

            # Add data rows
            data_rows = tab_data.get("data", [])
            if data_rows:
                updates.append({
                    'range': f'{tab_name}!A{current_row}',
                    'values': data_rows
                })

            # Batch update all data
            if updates:
                logger.debug(f"📤 Sending batch update for {tab_name} | total_updates={len(updates)}")
                body = {
                    'valueInputOption': 'RAW',
                    'data': [
                        {
                            'range': update['range'],
                            'values': update['values']
                        } for update in updates
                    ]
                }

                result = self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                logger.debug(f"✅ Batch update completed for {tab_name}")

                # Apply formatting
                await self._apply_formatting(spreadsheet_id, sheet_id)

            return {"success": True, "tab_name": tab_name, "updates": len(updates)}

        except Exception as e:
            logger.error(f"❌ Failed to create tab {tab_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _create_spreadsheet(self, title: str) -> Optional[Dict]:
        """Create a new Google Spreadsheet."""
        try:
            logger.debug(f"🔨 Creating spreadsheet with title: {title}")
            spreadsheet_body = {
                'properties': {
                    'title': title
                }
            }

            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()

            logger.debug(f"✅ Spreadsheet created successfully | id={spreadsheet.get('spreadsheetId')}")
            return spreadsheet

        except HttpError as e:
            logger.error(f"❌ Failed to create spreadsheet: {e}", exc_info=True)
            return None

    async def _create_skill_gap_tab(self, spreadsheet_id: str, export_data: Dict) -> Dict:
        """Create and populate the skill gap analysis tab."""
        try:
            logger.debug(f"📝 Preparing skill gap tab data | spreadsheet_id={spreadsheet_id}")

            # Prepare all data for batch update
            updates = []
            sections = export_data.get("sections", {})
            logger.debug(f"📊 Processing {len(sections)} sections")

            current_row = 1

            # Add title
            updates.append({
                'range': f'A{current_row}',
                'values': [['🎯 Skill Gap Analysis Report']]
            })
            current_row += 2

            # Add timestamp
            updates.append({
                'range': f'A{current_row}',
                'values': [[f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}']]
            })
            current_row += 3

            # Add summary section
            if 'summary' in sections:
                summary_section = sections['summary']
                updates.append({
                    'range': f'A{current_row}',
                    'values': [[f"📊 {summary_section.get('title', 'Summary')}"]]
                })
                current_row += 1

                summary_data = summary_section.get('data', [])
                if summary_data:
                    updates.append({
                        'range': f'A{current_row}',
                        'values': summary_data
                    })
                    current_row += len(summary_data) + 2

            # Add detailed gaps section
            if 'detailed_gaps' in sections:
                gaps_section = sections['detailed_gaps']
                updates.append({
                    'range': f'A{current_row}',
                    'values': [[f"🔍 {gaps_section.get('title', 'Detailed Gaps')}"]]
                })
                current_row += 1

                gaps_data = gaps_section.get('data', [])
                if gaps_data:
                    updates.append({
                        'range': f'A{current_row}',
                        'values': gaps_data
                    })
                    current_row += len(gaps_data) + 2

            # Add remediation actions section
            if 'remediation_actions' in sections:
                remediation_section = sections['remediation_actions']
                updates.append({
                    'range': f'A{current_row}',
                    'values': [[f"🛠️ {remediation_section.get('title', 'Remediation Plan')}"]]
                })
                current_row += 1

                remediation_data = remediation_section.get('data', [])
                if remediation_data:
                    updates.append({
                        'range': f'A{current_row}',
                        'values': remediation_data
                    })
                    current_row += len(remediation_data) + 2

            # Batch update all data
            if updates:
                logger.debug(f"📤 Sending batch update | total_updates={len(updates)}")
                body = {
                    'valueInputOption': 'RAW',
                    'data': [
                        {
                            'range': update['range'],
                            'values': update['values']
                        } for update in updates
                    ]
                }

                result = self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                logger.debug(f"✅ Batch update completed | updated_ranges={result.get('totalUpdatedRows', 0)}")

                # Apply formatting
                logger.debug("🎨 Applying formatting to skill gap tab")
                await self._apply_formatting(spreadsheet_id, 0)  # Sheet ID 0 for first sheet
                logger.debug("✅ Formatting applied")

                return {"success": True, "updates": len(updates)}

        except Exception as e:
            logger.error(f"❌ Failed to create skill gap tab: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _create_charts_tab(self, spreadsheet_id: str, export_data: Dict) -> Dict:
        """Create a tab with charts and visualizations."""
        try:
            logger.debug(f"📊 Creating charts tab | spreadsheet_id={spreadsheet_id}")

            # Add new sheet for charts
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': 'Charts_and_Visualizations',
                        'gridProperties': {
                            'rowCount': 100,
                            'columnCount': 20
                        }
                    }
                }
            }]

            batch_update_request = {'requests': requests}
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_request
            ).execute()

            new_sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
            logger.debug(f"✅ Charts sheet created | sheet_id={new_sheet_id}")

            # Add chart data and descriptions
            charts = export_data.get("charts", [])
            logger.debug(f"📊 Processing {len(charts)} charts")
            updates = []
            current_row = 1

            # Add charts header
            updates.append({
                'range': f'Charts_and_Visualizations!A{current_row}',
                'values': [['📈 Skill Gap Visualizations']]
            })
            current_row += 3

            # Add chart descriptions and data
            for i, chart in enumerate(charts):
                logger.debug(f"📊 Processing chart {i+1}/{len(charts)} | type={chart.get('type', 'unknown')}")
                chart_title = chart.get("title", f"Chart {i+1}")
                chart_type = chart.get("type", "unknown")
                chart_data = chart.get("data", {})

                # Chart title
                updates.append({
                    'range': f'Charts_and_Visualizations!A{current_row}',
                    'values': [[f"{chart_title} ({chart_type})"]]
                })
                current_row += 1

                # Chart data
                if isinstance(chart_data, dict):
                    data_rows = [["Category", "Value"]]
                    for key, value in chart_data.items():
                        if isinstance(value, dict):
                            # Handle nested data (e.g., current vs target)
                            for sub_key, sub_value in value.items():
                                data_rows.append([f"{key} ({sub_key})", sub_value])
                        else:
                            data_rows.append([key, value])

                    updates.append({
                        'range': f'Charts_and_Visualizations!A{current_row}',
                        'values': data_rows
                    })
                    current_row += len(data_rows) + 3

            # Batch update chart data
            if updates:
                logger.debug(f"📤 Sending chart batch update | total_updates={len(updates)}")
                body = {
                    'valueInputOption': 'RAW',
                    'data': [
                        {
                            'range': update['range'],
                            'values': update['values']
                        } for update in updates
                    ]
                }

                result = self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                logger.debug(f"✅ Chart batch update completed | updated_ranges={result.get('totalUpdatedRows', 0)}")

                # Apply formatting to charts sheet
                logger.debug("🎨 Applying formatting to charts tab")
                await self._apply_formatting(spreadsheet_id, new_sheet_id)
                logger.debug("✅ Charts tab formatting applied")

                return {"success": True, "charts_created": len(charts)}

        except Exception as e:
            logger.error(f"❌ Failed to create charts tab: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _apply_formatting(self, spreadsheet_id: str, sheet_id: int) -> Dict:
        """Apply formatting to the spreadsheet."""
        try:
            logger.debug(f"🎨 Applying formatting | sheet_id={sheet_id}")
            requests = [
                # Header formatting
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9},
                                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                                'horizontalAlignment': 'CENTER'
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)'
                    }
                },
                # Auto-resize columns
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': sheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': 10
                        }
                    }
                }
            ]

            batch_update_request = {'requests': requests}
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_request
            ).execute()

            logger.debug(f"✅ Formatting applied successfully | replies={len(response.get('replies', []))}")
            return {"success": True, "formatting_applied": True}

        except Exception as e:
            logger.error(f"❌ Failed to apply formatting: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _share_spreadsheet(self, spreadsheet_id: str, email: str) -> Dict:
        """Share spreadsheet with specified email."""
        try:
            logger.debug(f"🔗 Attempting to share spreadsheet with {email}")
            # This would require Drive API integration
            # For now, return a placeholder response
            logger.warning("⚠️ Sharing functionality requires Drive API integration - returning placeholder")
            return {
                "success": True,
                "shared_with": email,
                "permission": "reader",
                "note": "Sharing functionality requires Drive API integration"
            }

        except Exception as e:
            logger.error(f"❌ Failed to share spreadsheet: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _count_data_points(self, export_data: Dict) -> int:
        """Count total data points in export data."""
        total_points = 0
        sections = export_data.get("sections", {})

        for section_name, section_data in sections.items():
            data = section_data.get("data", [])
            total_points += len(data) * len(data[0]) if data and len(data) > 0 else 0

        charts = export_data.get("charts", [])
        for chart in charts:
            chart_data = chart.get("data", {})
            if isinstance(chart_data, dict):
                total_points += len(chart_data)

        return total_points

    def _create_mock_export_response(self, reason: str) -> Dict:
        """Create mock response when Google Sheets is not available."""
        mock_id = str(uuid4())
        mock_url = f"https://docs.google.com/spreadsheets/d/{mock_id}"

        return {
            "success": False,
            "mock_response": True,
            "reason": reason,
            "spreadsheet_id": mock_id,
            "spreadsheet_url": mock_url,
            "spreadsheet_title": f"Mock_Skill_Gap_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "tabs_created": ["Skill_Gap_Analysis", "Charts_and_Visualizations"],
            "export_timestamp": datetime.now().isoformat(),
            "note": "This is a mock response. Enable Google Sheets integration for actual export.",
            "instructions": [
                "1. Set up Google Cloud project with Sheets API enabled",
                "2. Create service account and download credentials JSON",
                "3. Configure GOOGLE_SHEETS_CREDENTIALS_PATH environment variable",
                "4. Install google-api-python-client package",
                "5. Restart service to enable Google Sheets integration"
            ]
        }


class EnhancedGapAnalysisExporter:
    """Enhanced exporter combining gap analysis with Google Sheets integration."""

    def __init__(self, google_sheets_service: GoogleSheetsService):
        """Initialize enhanced exporter with Google Sheets service."""
        self.sheets_service = google_sheets_service

    async def export_comprehensive_analysis(
        self,
        gap_analysis_result: Dict,
        export_options: Optional[Dict] = None
    ) -> Dict:
        """Export comprehensive gap analysis with enhanced formatting."""

        export_options = export_options or {}
        logger.info(f"📊 Starting comprehensive analysis export | options={export_options}")

        try:
            # Enhanced data preparation
            logger.info("🔄 Preparing enhanced export data")
            enhanced_export_data = self._prepare_enhanced_export_data(gap_analysis_result)
            logger.info(f"✅ Export data prepared | sections={len(enhanced_export_data.get('sections', {}))} charts={len(enhanced_export_data.get('charts', []))}")

            # Update gap analysis with enhanced export data
            gap_analysis_result["google_sheets_export_data"] = enhanced_export_data

            # Export to Google Sheets
            logger.info("📤 Exporting to Google Sheets")
            sheets_result = await self.sheets_service.export_skill_gap_analysis(
                gap_analysis_data=gap_analysis_result,
                spreadsheet_title=export_options.get("title"),
                share_with_email=export_options.get("share_email")
            )
            logger.info(f"✅ Google Sheets export completed | success={sheets_result.get('success')}")

            # Generate additional export formats
            logger.info("📝 Generating additional export formats")
            additional_exports = self._generate_additional_exports(
                gap_analysis_result, export_options
            )
            logger.info(f"✅ Additional exports generated | formats={list(additional_exports.keys())}")

            result = {
                "google_sheets_export": sheets_result,
                "additional_exports": additional_exports,
                "comprehensive_analysis": {
                    "metrics_analyzed": 5,
                    "visualization_charts": len(enhanced_export_data.get("charts", [])),
                    "actionable_recommendations": len(self._extract_recommendations(gap_analysis_result)),
                    "export_formats": ["google_sheets", "json", "csv", "markdown"]
                },
                "export_timestamp": datetime.now().isoformat()
            }

            logger.info(f"✅ Comprehensive analysis export completed successfully | metrics={result['comprehensive_analysis']['metrics_analyzed']} charts={result['comprehensive_analysis']['visualization_charts']}")
            return result

        except Exception as e:
            logger.error(f"❌ Comprehensive export failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "fallback_data": gap_analysis_result.get("google_sheets_export_data", {})
            }

    def _prepare_enhanced_export_data(self, gap_analysis_result: Dict) -> Dict:
        """Prepare enhanced export data with 4-tab format for Sprint 2.

        Tab 1: Answers - Correct/incorrect with explanations
        Tab 2: Gap Analysis - Charts, scores, skill gaps + text summary
        Tab 3: Content Outline - RAG-retrieved content
        Tab 4: Recommended Courses - Categorized by Domain → Skills
        """
        logger.debug("📋 Preparing 4-tab export data structure")

        enhanced_skill_gap = gap_analysis_result.get("enhanced_skill_gap_analysis", {})
        domain_gaps = gap_analysis_result.get("identified_gaps", [])
        remediation_plan = gap_analysis_result.get("remediation_plan", {})

        # Extract data for 4 tabs
        answers_data = gap_analysis_result.get("answers", {})
        gap_analysis_data = gap_analysis_result.get("gap_analysis_summary", {})
        content_outlines = gap_analysis_result.get("content_outlines", [])
        recommended_courses = gap_analysis_result.get("recommended_courses", [])

        logger.debug(f"📋 Building 4 tabs | answers={answers_data.get('total_questions', 0)} gaps={len(gap_analysis_data.get('skill_gaps', []))} outlines={len(content_outlines)} courses={len(recommended_courses)}")

        # Format 4 tabs
        tabs = [
            self._format_tab1_answers(answers_data),
            self._format_tab2_gap_analysis(gap_analysis_data),
            self._format_tab3_content_outlines(content_outlines),
            self._format_tab4_recommended_courses(recommended_courses)
        ]

        return {
            "sheet_name": "PresGen_Gap_Analysis",
            "tabs": tabs,
            # Keep legacy sections for backward compatibility
            "sections": {
                "executive_summary": {
                    "title": "🎯 Executive Summary",
                    "data": [
                        ["Assessment Area", "Score/Status", "Interpretation", "Priority Actions"],
                        ["Overall Readiness", f"{gap_analysis_result.get('overall_readiness_score', 0)}%",
                         self._interpret_readiness_score(gap_analysis_result.get('overall_readiness_score', 0)),
                         "Continue preparation"],
                        ["Learning Profile", enhanced_skill_gap.get("overall_skill_profile", {}).get("overall_profile_type", "Mixed"),
                         "Strategic learner assessment", "Leverage strengths"],
                        ["Priority Gaps", len(domain_gaps), f"{len(domain_gaps)} areas need improvement", "Focus remediation"],
                        ["Study Time Needed", f"{gap_analysis_result.get('estimated_preparation_time_hours', 0)}h",
                         "Estimated preparation time", "Plan schedule"]
                    ]
                },
                "bloom_taxonomy_analysis": {
                    "title": "🧠 Bloom's Taxonomy Analysis",
                    "data": self._format_bloom_analysis(enhanced_skill_gap.get("bloom_taxonomy_analysis", {}))
                },
                "learning_style_assessment": {
                    "title": "📚 Learning Style Assessment",
                    "data": self._format_learning_style(enhanced_skill_gap.get("learning_style_indicators", {}))
                },
                "metacognitive_analysis": {
                    "title": "🎯 Metacognitive Awareness",
                    "data": self._format_metacognitive_analysis(enhanced_skill_gap.get("metacognitive_awareness", {}))
                },
                "transfer_learning_assessment": {
                    "title": "🔄 Transfer Learning Ability",
                    "data": self._format_transfer_learning(enhanced_skill_gap.get("transfer_learning_assessment", {}))
                },
                "certification_readiness": {
                    "title": "🏆 Certification Readiness",
                    "data": self._format_certification_readiness(enhanced_skill_gap.get("certification_specific_insights", {}))
                },
                "detailed_gaps": {
                    "title": "🔍 Detailed Gap Analysis",
                    "data": [["Domain", "Current Score", "Target Score", "Gap Severity", "Priority", "Remediation Focus"]] +
                            [[gap["domain"], f"{gap['current_score']:.1%}", f"{gap['target_score']:.1%}",
                              gap["gap_severity"], gap["remediation_priority"], gap.get("gap_type", "general")]
                             for gap in domain_gaps]
                },
                "remediation_actions": {
                    "title": "🛠️ Personalized Remediation Plan",
                    "data": [["Action", "Domain", "Type", "Priority", "Estimated Hours", "Success Criteria"]] +
                            [[action["description"], action["domain"], action["action_type"],
                              action["priority"], action["estimated_duration_hours"],
                              "; ".join(action["success_criteria"][:2])]  # Limit criteria for readability
                             for action in remediation_plan.get("remediation_actions", [])]
                },
                "recommendations": {
                    "title": "💡 Personalized Recommendations",
                    "data": [["Category", "Recommendation", "Rationale"]] +
                            [[rec["category"], rec["recommendation"], rec["rationale"]]
                             for rec in self._generate_categorized_recommendations(gap_analysis_result)]
                }
            },
            "charts": [
                {
                    "type": "radar_chart",
                    "title": "Bloom's Taxonomy Performance Profile",
                    "data": enhanced_skill_gap.get("bloom_taxonomy_analysis", {}).get("bloom_level_scores", {})
                },
                {
                    "type": "bar_chart",
                    "title": "Domain Performance vs Targets",
                    "data": {gap["domain"]: {"current": gap["current_score"], "target": gap["target_score"]}
                             for gap in domain_gaps}
                },
                {
                    "type": "gauge_chart",
                    "title": "Metacognitive Maturity Score",
                    "data": {"score": enhanced_skill_gap.get("metacognitive_awareness", {}).get("metacognitive_maturity_score", 0)}
                },
                {
                    "type": "scatter_plot",
                    "title": "Learning Style Performance Matrix",
                    "data": enhanced_skill_gap.get("learning_style_indicators", {}).get("question_type_preferences", {})
                }
            ],
            "summary_stats": {
                "total_domains_assessed": len(domain_gaps),
                "metrics_analyzed": 5,
                "recommendations_generated": len(self._extract_recommendations(gap_analysis_result)),
                "estimated_improvement_potential": self._calculate_improvement_potential(domain_gaps)
            }
        }

    def _format_bloom_analysis(self, bloom_data: Dict) -> List[List]:
        """Format Bloom's taxonomy analysis for spreadsheet."""
        if not bloom_data:
            return [["No Bloom's taxonomy data available"]]

        scores = bloom_data.get("bloom_level_scores", {})
        gaps = bloom_data.get("cognitive_gaps", [])

        data = [["Cognitive Level", "Score", "Performance", "Gap Severity", "Recommendations"]]

        for level, score in scores.items():
            performance = "Strong" if score > 0.8 else "Good" if score > 0.6 else "Needs Work"
            gap_info = next((gap for gap in gaps if gap["bloom_level"] == level), None)
            gap_severity = gap_info["gap_severity"] if gap_info else 0
            recommendation = f"Focus on {level} skills" if gap_severity > 0.3 else "Maintain current level"

            data.append([level.title(), f"{score:.1%}", performance, f"{gap_severity:.1%}", recommendation])

        return data

    def _format_learning_style(self, learning_data: Dict) -> List[List]:
        """Format learning style analysis for spreadsheet."""
        if not learning_data:
            return [["No learning style data available"]]

        preferences = learning_data.get("question_type_preferences", {})
        context_switching = learning_data.get("context_switching_ability", {})

        data = [["Question Type", "Accuracy", "Avg Time (s)", "Efficiency", "Recommendation"]]

        for q_type, metrics in preferences.items():
            accuracy = metrics.get("accuracy", 0)
            avg_time = metrics.get("average_time_seconds", 0)
            efficiency = metrics.get("efficiency_score", 0)
            recommendation = "Leverage strength" if efficiency > 0.8 else "Practice more"

            data.append([q_type.replace("_", " ").title(), f"{accuracy:.1%}",
                        f"{avg_time:.1f}", f"{efficiency:.2f}", recommendation])

        # Add context switching info
        switching_quality = context_switching.get("adaptation_quality", "unknown")
        data.append(["Context Switching", switching_quality.replace("_", " ").title(),
                    "", "", "Practice domain transitions" if switching_quality == "needs_improvement" else "Good flexibility"])

        return data

    def _format_metacognitive_analysis(self, metacog_data: Dict) -> List[List]:
        """Format metacognitive analysis for spreadsheet."""
        if not metacog_data:
            return [["No metacognitive data available"]]

        self_assessment = metacog_data.get("self_assessment_accuracy", {})
        uncertainty = metacog_data.get("uncertainty_recognition", {})
        strategy = metacog_data.get("strategy_adaptation", {})
        maturity_score = metacog_data.get("metacognitive_maturity_score", 0)

        data = [
            ["Metacognitive Aspect", "Score/Quality", "Assessment", "Development Need"],
            ["Self-Assessment Accuracy", f"{1 - self_assessment.get('average_gap', 1):.1%}",
             self_assessment.get("calibration_quality", "unknown").replace("_", " ").title(),
             "Practice confidence estimation" if self_assessment.get('average_gap', 1) > 0.3 else "Good calibration"],
            ["Uncertainty Recognition", f"{uncertainty.get('recognition_rate', 0):.1%}",
             uncertainty.get("quality", "unknown").replace("_", " ").title(),
             "Learn to identify knowledge gaps" if uncertainty.get('recognition_rate', 0) < 0.7 else "Good awareness"],
            ["Strategy Adaptation", f"{strategy.get('appropriate_time_allocation_rate', 0):.1%}",
             strategy.get("adaptation_quality", "unknown").replace("_", " ").title(),
             "Improve time management" if strategy.get('appropriate_time_allocation_rate', 0) < 0.7 else "Good strategy"],
            ["Overall Maturity", f"{maturity_score:.1%}",
             "Advanced" if maturity_score > 0.8 else "Developing" if maturity_score > 0.6 else "Beginner",
             "Continue developing metacognitive skills" if maturity_score < 0.8 else "Maintain awareness"]
        ]

        return data

    def _format_transfer_learning(self, transfer_data: Dict) -> List[List]:
        """Format transfer learning analysis for spreadsheet."""
        if not transfer_data:
            return [["No transfer learning data available"]]

        cross_domain = transfer_data.get("cross_domain_connections", [])
        pattern_recognition = transfer_data.get("pattern_recognition_ability", [])
        balance = transfer_data.get("conceptual_vs_procedural_balance", {})
        transfer_score = transfer_data.get("transfer_learning_score", 0)

        data = [
            ["Transfer Learning Aspect", "Score/Status", "Quality", "Development Focus"],
            ["Overall Transfer Score", f"{transfer_score:.1%}",
             "Strong" if transfer_score > 0.8 else "Moderate" if transfer_score > 0.6 else "Developing",
             "Practice cross-domain applications" if transfer_score < 0.7 else "Leverage existing ability"],
            ["Knowledge Balance",
             f"Conceptual: {balance.get('conceptual_percentage', 0):.1%}, Procedural: {balance.get('procedural_percentage', 0):.1%}",
             balance.get("balance_quality", "unknown").replace("_", " ").title(),
             "Balance conceptual and practical knowledge" if balance.get("balance_quality") != "well_balanced" else "Good balance"]
        ]

        # Add top domain connections
        if cross_domain:
            top_connections = sorted(cross_domain, key=lambda x: x.get("correlation_strength", 0), reverse=True)[:3]
            for i, conn in enumerate(top_connections):
                data.append([f"Domain Connection {i+1}", conn["domain_pair"],
                           conn["transfer_potential"].replace("_", " ").title(),
                           "Strengthen connection" if conn["transfer_potential"] == "low" else "Leverage connection"])

        return data

    def _format_certification_readiness(self, cert_data: Dict) -> List[List]:
        """Format certification readiness analysis for spreadsheet."""
        if not cert_data:
            return [["No certification readiness data available"]]

        readiness_score = cert_data.get("certification_readiness_score", 0)
        exam_indicators = cert_data.get("exam_readiness_indicators", {})
        industry_context = cert_data.get("industry_context_readiness", {})
        exam_strategy = cert_data.get("exam_strategy_assessment", {})

        data = [
            ["Readiness Aspect", "Score/Status", "Assessment", "Preparation Focus"],
            ["Overall Certification Readiness", f"{readiness_score}%",
             "Ready" if readiness_score >= 80 else "Nearly Ready" if readiness_score >= 70 else "Needs Preparation",
             "Final review" if readiness_score >= 80 else "Continue focused study"],
            ["Meets Passing Threshold",
             "Yes" if exam_indicators.get("meets_passing_threshold", False) else "No",
             exam_indicators.get("confidence_in_certification", "moderate").title(),
             "Maintain preparation" if exam_indicators.get("meets_passing_threshold") else "Intensive study needed"],
            ["Domain Balance", exam_indicators.get("domain_balance", "unknown").replace("_", " ").title(),
             "Good" if exam_indicators.get("domain_balance") == "well_balanced" else "Needs Work",
             "Focus on weak domains" if exam_indicators.get("domain_balance") != "well_balanced" else "Maintain balance"],
            ["Industry Application", industry_context.get("real_world_application_readiness", "unknown").title(),
             "Strong" if industry_context.get("scenario_performance", 0) > 0.8 else "Developing",
             "Practice real-world scenarios" if industry_context.get("scenario_performance", 0) < 0.7 else "Good application skills"],
            ["Exam Strategy", exam_strategy.get("time_management", {}).get("time_efficiency", "unknown").replace("_", " ").title(),
             "Effective" if exam_strategy.get("question_approach_effectiveness") == "effective" else "Needs Work",
             "Practice exam techniques" if exam_strategy.get("question_approach_effectiveness") != "effective" else "Good exam strategy"]
        ]

        return data

    def _generate_categorized_recommendations(self, gap_analysis_result: Dict) -> List[Dict]:
        """Generate categorized recommendations for better organization."""
        enhanced_analysis = gap_analysis_result.get("enhanced_skill_gap_analysis", {})
        recommendations = []

        # Cognitive development recommendations
        bloom_recs = enhanced_analysis.get("bloom_taxonomy_analysis", {}).get("recommendations", [])
        for rec in bloom_recs:
            recommendations.append({
                "category": "Cognitive Development",
                "recommendation": rec,
                "rationale": "Based on Bloom's taxonomy performance gaps"
            })

        # Learning strategy recommendations
        learning_recs = enhanced_analysis.get("learning_style_indicators", {}).get("learning_style_recommendations", [])
        for rec in learning_recs:
            recommendations.append({
                "category": "Learning Strategy",
                "recommendation": rec,
                "rationale": "Based on learning style and retention patterns"
            })

        # Metacognitive recommendations
        metacog_score = enhanced_analysis.get("metacognitive_awareness", {}).get("metacognitive_maturity_score", 1.0)
        if metacog_score < 0.7:
            recommendations.extend([
                {
                    "category": "Self-Awareness",
                    "recommendation": "Practice estimating confidence before answering questions",
                    "rationale": "Low metacognitive maturity score indicates need for better self-assessment"
                },
                {
                    "category": "Self-Awareness",
                    "recommendation": "Review incorrect answers to understand reasoning gaps",
                    "rationale": "Improve calibration between confidence and actual performance"
                }
            ])

        # Certification-specific recommendations
        cert_insights = enhanced_analysis.get("certification_specific_insights", {})
        if not cert_insights.get("exam_readiness_indicators", {}).get("meets_passing_threshold", True):
            recommendations.append({
                "category": "Certification Prep",
                "recommendation": "Focus on high-weight certification domains",
                "rationale": "Current performance below passing threshold for certification"
            })

        return recommendations

    def _generate_additional_exports(self, gap_analysis_result: Dict, export_options: Dict) -> Dict:
        """Generate additional export formats."""
        return {
            "json_export": {
                "available": True,
                "description": "Complete analysis in JSON format",
                "data": gap_analysis_result
            },
            "csv_summary": {
                "available": True,
                "description": "Gap analysis summary in CSV format",
                "data": self._create_csv_summary(gap_analysis_result)
            },
            "markdown_report": {
                "available": True,
                "description": "Human-readable markdown report",
                "data": self._create_markdown_report(gap_analysis_result)
            }
        }

    def _create_csv_summary(self, gap_analysis_result: Dict) -> str:
        """Create CSV summary of gap analysis."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(["Domain", "Current_Score", "Target_Score", "Gap_Severity", "Priority"])

        # Write domain gaps
        for gap in gap_analysis_result.get("identified_gaps", []):
            writer.writerow([
                gap["domain"],
                gap["current_score"],
                gap["target_score"],
                gap["gap_severity"],
                gap["remediation_priority"]
            ])

        return output.getvalue()

    def _create_markdown_report(self, gap_analysis_result: Dict) -> str:
        """Create markdown report of gap analysis."""
        report = f"""# Skill Gap Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Overall Readiness**: {gap_analysis_result.get('overall_readiness_score', 0)}%
- **Priority Learning Areas**: {len(gap_analysis_result.get('priority_learning_areas', []))}
- **Estimated Study Time**: {gap_analysis_result.get('estimated_preparation_time_hours', 0)} hours

## Key Findings

"""

        enhanced_analysis = gap_analysis_result.get("enhanced_skill_gap_analysis", {})

        # Add Bloom's taxonomy findings
        bloom_data = enhanced_analysis.get("bloom_taxonomy_analysis", {})
        if bloom_data:
            report += f"### Cognitive Development\n"
            report += f"- **Cognitive Depth**: {bloom_data.get('cognitive_depth_assessment', 'Unknown')}\n"
            report += f"- **Knowledge/Application Ratio**: {bloom_data.get('knowledge_vs_application_ratio', 'N/A')}\n\n"

        # Add learning style findings
        learning_data = enhanced_analysis.get("learning_style_indicators", {})
        if learning_data:
            report += f"### Learning Style\n"
            context_switching = learning_data.get("context_switching_ability", {})
            report += f"- **Context Switching**: {context_switching.get('adaptation_quality', 'Unknown')}\n\n"

        # Add recommendations
        all_recs = self._extract_recommendations(gap_analysis_result)
        if all_recs:
            report += f"## Recommendations\n\n"
            for i, rec in enumerate(all_recs[:10], 1):  # Top 10 recommendations
                report += f"{i}. {rec}\n"

        return report

    def _extract_recommendations(self, gap_analysis_result: Dict) -> List[str]:
        """Extract all recommendations from gap analysis."""
        recommendations = []
        enhanced_analysis = gap_analysis_result.get("enhanced_skill_gap_analysis", {})

        # Extract from all analysis sections
        for section_key in ["bloom_taxonomy_analysis", "learning_style_indicators"]:
            section_data = enhanced_analysis.get(section_key, {})
            section_recs = section_data.get("recommendations", [])
            recommendations.extend(section_recs)

        # Extract from overall skill profile
        skill_profile = enhanced_analysis.get("overall_skill_profile", {})
        learning_recs = skill_profile.get("learning_recommendations", [])
        recommendations.extend(learning_recs)

        return list(set(recommendations))  # Remove duplicates

    def _interpret_readiness_score(self, score: float) -> str:
        """Interpret readiness score."""
        if score >= 85:
            return "Excellent - Ready for certification"
        elif score >= 75:
            return "Good - Minor preparation needed"
        elif score >= 65:
            return "Fair - Moderate preparation needed"
        else:
            return "Needs Work - Intensive preparation required"

    def _calculate_improvement_potential(self, domain_gaps: List[Dict]) -> float:
        """Calculate improvement potential percentage."""
        if not domain_gaps:
            return 0.0

        total_potential = sum(gap["gap_severity"] for gap in domain_gaps)
        return round(total_potential / len(domain_gaps) * 100, 1)

    def _format_tab1_answers(self, answers_data: Dict) -> Dict:
        """Format Tab 1: Answers with correct/incorrect and explanations."""
        logger.debug("📝 Formatting Tab 1: Answers")

        correct_answers = answers_data.get("correct_answers", [])
        incorrect_answers = answers_data.get("incorrect_answers", [])

        # Build data rows
        data_rows = [["Question", "Your Answer", "Correct Answer", "Explanation", "Domain", "Difficulty", "Result"]]

        # Add correct answers
        for answer in correct_answers:
            data_rows.append([
                answer.get("question_text", ""),
                answer.get("user_answer", ""),
                answer.get("correct_answer", ""),
                answer.get("explanation", ""),
                answer.get("domain", ""),
                answer.get("difficulty", ""),
                "✓ Correct"
            ])

        # Add incorrect answers
        for answer in incorrect_answers:
            data_rows.append([
                answer.get("question_text", ""),
                answer.get("user_answer", ""),
                answer.get("correct_answer", ""),
                answer.get("explanation", ""),
                answer.get("domain", ""),
                answer.get("difficulty", ""),
                "✗ Incorrect"
            ])

        return {
            "tab_name": "Answers",
            "title": "📝 Assessment Answers with Explanations",
            "summary": f"Total: {answers_data.get('total_questions', 0)} | Correct: {answers_data.get('correct_count', 0)} | Incorrect: {answers_data.get('incorrect_count', 0)}",
            "data": data_rows
        }

    def _format_tab2_gap_analysis(self, gap_data: Dict) -> Dict:
        """Format Tab 2: Gap Analysis with scores, skill gaps, and text summary."""
        logger.debug("📊 Formatting Tab 2: Gap Analysis")

        data_rows = []

        # Add summary section
        data_rows.append(["📊 Gap Analysis Summary"])
        data_rows.append([])
        data_rows.append(["Overall Score", f"{gap_data.get('overall_score', 0)}%"])
        data_rows.append(["Total Questions", str(gap_data.get('total_questions', 0))])
        data_rows.append(["Correct Answers", str(gap_data.get('correct_answers', 0))])
        data_rows.append([])

        # Add text summary
        text_summary = gap_data.get('text_summary', '')
        if text_summary:
            data_rows.append(["📖 Summary"])
            data_rows.append([])
            data_rows.append([text_summary])
            data_rows.append([])

        # Add skill gaps
        skill_gaps = gap_data.get('skill_gaps', [])
        if skill_gaps:
            data_rows.append(["🔍 Identified Skill Gaps"])
            data_rows.append([])
            data_rows.append(["Skill", "Gap Severity", "Priority"])
            for gap in skill_gaps:
                data_rows.append([
                    gap.get('skill_name', ''),
                    gap.get('gap_severity', ''),
                    gap.get('priority', '')
                ])
            data_rows.append([])

        # Add performance by domain
        performance = gap_data.get('performance_by_domain', [])
        if performance:
            data_rows.append(["📈 Performance by Domain"])
            data_rows.append([])
            data_rows.append(["Domain", "Score", "Questions", "Correct"])
            for perf in performance:
                data_rows.append([
                    perf.get('domain', ''),
                    f"{perf.get('score', 0)}%",
                    str(perf.get('total_questions', 0)),
                    str(perf.get('correct_count', 0))
                ])

        return {
            "tab_name": "Gap Analysis",
            "title": "📊 Gap Analysis with Summary",
            "data": data_rows
        }

    def _format_tab3_content_outlines(self, outlines: List[Dict]) -> Dict:
        """Format Tab 3: Content Outlines (RAG-retrieved content)."""
        logger.debug("📚 Formatting Tab 3: Content Outlines")

        data_rows = [["Skill", "Domain", "Content Outline", "Source References"]]

        for outline in outlines:
            data_rows.append([
                outline.get("skill_name", ""),
                outline.get("exam_domain", ""),
                outline.get("outline_text", ""),
                ", ".join(outline.get("source_references", []))
            ])

        return {
            "tab_name": "Content Outlines",
            "title": "📚 RAG-Retrieved Content Outlines",
            "data": data_rows
        }

    def _format_tab4_recommended_courses(self, courses: List[Dict]) -> Dict:
        """Format Tab 4: Recommended Courses categorized by Domain → Skills."""
        logger.debug("🎓 Formatting Tab 4: Recommended Courses by Domain")

        # Group courses by domain
        courses_by_domain = {}
        for course in courses:
            domain = course.get("exam_domain", "Other")
            if domain not in courses_by_domain:
                courses_by_domain[domain] = []
            courses_by_domain[domain].append(course)

        # Build data rows with domain grouping
        data_rows = []

        for domain, domain_courses in sorted(courses_by_domain.items()):
            # Domain header
            data_rows.append([f"📖 {domain}"])
            data_rows.append([])

            # Add skills for this domain as bullet points
            data_rows.append(["Skill", "Priority", "Duration (hrs)", "Rationale"])
            for course in domain_courses:
                skill_bullet = f"• {course.get('skill_name', '')}"
                data_rows.append([
                    skill_bullet,
                    course.get("priority_level", ""),
                    str(course.get("estimated_duration_hours", 0)),
                    course.get("rationale", "")
                ])

            data_rows.append([])  # Spacing between domains

        return {
            "tab_name": "Recommended Courses",
            "title": "🎓 Recommended Courses by Domain",
            "data": data_rows
        }