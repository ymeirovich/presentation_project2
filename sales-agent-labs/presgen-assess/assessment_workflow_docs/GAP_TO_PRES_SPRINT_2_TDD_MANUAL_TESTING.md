# Sprint 2: Manual TDD Test Plan
## Google Sheets Export (4-Tab On-Demand)

**Sprint Duration**: Weeks 3-4
**Test Plan Version**: 1.0
**Date**: 2025-10-02
**Last Updated**: 2025-10-02

---

## 🎯 Sprint 2 Testing Objectives

Test all Sprint 2 deliverables BEFORE implementation:
1. On-demand Google Sheets export functionality
2. 4-tab sheet generation (Answers, Gap Analysis, Outline, Presentation)
3. RAG content formatting for Outline tab
4. Rate limiter toggle (disabled in development)
5. Database-to-Sheets data flow (not live data)

---

## 📊 Sprint 2 Status Summary

**Overall Progress**: 0% (Pre-implementation testing phase)

| Component | Status | Notes |
|-----------|--------|-------|
| Export Button UI | ⏸️ **PENDING** | Not yet implemented |
| GoogleSheetsExportService | ⏸️ **PENDING** | Service to be created |
| 4-Tab Sheet Generation | ⏸️ **PENDING** | Answers, Gap Analysis, Outline, Presentation |
| RAG Content Formatting | ⏸️ **PENDING** | Depends on Sprint 1 RAG retrieval |
| Rate Limiter Toggle | ⏸️ **PENDING** | Feature flag implementation |

**Prerequisites**: Sprint 1 must be 100% complete before Sprint 2 begins.

---

## 📋 Test Suite Overview

| Test ID | Feature | Priority | Status |
|---------|---------|----------|--------|
| S2-T1 | Export Button & API Endpoint | High | ⏸️ **PENDING** |
| S2-T2 | 4-Tab Sheet Generation | High | ⏸️ **PENDING** |
| S2-T3 | Answers Tab Formatting | High | ⏸️ **PENDING** |
| S2-T4 | Gap Analysis Tab Formatting | High | ⏸️ **PENDING** |
| S2-T5 | Content Outline Tab (RAG) | Medium | ⏸️ **PENDING** |
| S2-T6 | Presentation Tab | Medium | ⏸️ **PENDING** |
| S2-T7 | Rate Limiter Toggle | Medium | ⏸️ **PENDING** |
| S2-T8 | Error Handling & Logging | High | ⏸️ **PENDING** |

---

## Test S2-T1: Export Button & API Endpoint

**Feature**: "Export to Sheets" button triggers on-demand sheet creation
**Prerequisites**:
- Sprint 1 complete (gap analysis data in database)
- Feature flag `ENABLE_SHEETS_EXPORT=true`
- Google Sheets API credentials configured

### Test Case 1.1: Export Button Visibility and Click

**Setup**:
```bash
# Set feature flag
export ENABLE_SHEETS_EXPORT=true

# Start server
uvicorn src.service.app:app --port 8081 --reload
```

**Test Steps**:
1. Navigate to Gap Analysis Dashboard:
```
http://localhost:3000/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis
```

2. Verify "Export to Sheets" button is visible:
   - Button located in dashboard header or actions panel
   - Button text: "Export to Sheets" or "📊 Export to Google Sheets"
   - Button enabled (not disabled/greyed out)

3. Click "Export to Sheets" button

4. Verify export process initiated:
   - Loading spinner or progress indicator appears
   - Button becomes disabled during export
   - User sees "Exporting..." or similar status message

**Expected Results**:
- ✅ Export button visible and clickable
- ✅ Loading state displayed during export
- ✅ API request sent to export endpoint
- ✅ User receives feedback on export progress

**Pass Criteria**:
- [ ] Export button renders correctly
- [ ] Click triggers export API call
- [ ] Loading state displayed
- [ ] Button disabled during export

---

### Test Case 1.2: Export API Endpoint

**Test Steps**:
1. Trigger export via API:
```bash
curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets -H "Content-Type: application/json"

--
{"success":true,"workflow_id":"19952bd0-9cfe-44bc-9460-c4f521caca89","spreadsheet_id":"1njc1QCJp4V8j3y4soPoQFMsb8ZiVLAcalUCLtNKe2zs","spreadsheet_url":"https://docs.google.com/spreadsheets/d/1njc1QCJp4V8j3y4soPoQFMsb8ZiVLAcalUCLtNKe2zs","spreadsheet_title":"PresGen Gap Analysis 19952bd0-9cfe-44bc-9460-c4f521caca89","export_timestamp":"2025-10-02T18:41:28.076086","mock_response":false,"message":"Export completed","export_summary":{"tabs_count":4,"data_points_exported":61},"additional_exports":{"json_export":{"available":true,"description":"Complete analysis in JSON format","data":{"workflow_id":"19952bd0-9cfe-44bc-9460-c4f521caca89","answers":{"correct_answers":[],"incorrect_answers":[],"total_questions":0,"correct_count":0,"incorrect_count":0},"gap_analysis_summary":{"overall_score":27.0,"total_questions":5,"correct_answers":2,"skill_gaps":[{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_subsection":null,"severity":9,"confidence_delta":0.0,"question_ids":[]},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_subsection":null,"severity":9,"confidence_delta":0.0,"question_ids":[]},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_subsection":null,"severity":9,"confidence_delta":0.0,"question_ids":[]}],"performance_by_domain":{},"text_summary":"You scored 27.0% overall on this AWS Solutions Architect assessment.\n\nYour strongest areas are:\n- Security (0.0%) - Above passing threshold\n- Networking (0.0%) - Above passing threshold\n\nAreas needing improvement:\n- Networking (0.0%) - Below recommended proficiency\n- Compute (0.0%) - Below recommended proficiency\n\nRecommended next steps:\n- Focus study time on areas with lowest scores\n- Review exam guide sections for identified gaps\n- Practice with targeted exercises\n","charts_data":{"bar_chart":{"type":"bar","data":{},"title":"Performance by Domain"},"radar_chart":{"type":"radar","data":{"Security":10,"Networking":10,"Compute":10},"title":"Skill Coverage"},"scatter_plot":{"type":"scatter","data":[],"title":"Confidence vs Performance"}}},"content_outlines":[{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_guide_section":"General","content_items":[{"topic":"Security Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Security in Security."},{"topic":"Security Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Security."}],"rag_retrieval_score":0.75},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_guide_section":"General","content_items":[{"topic":"Networking Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Networking in Networking."},{"topic":"Networking Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Networking."}],"rag_retrieval_score":0.75},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_guide_section":"General","content_items":[{"topic":"Compute Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Compute in Compute."},{"topic":"Compute Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Compute."}],"rag_retrieval_score":0.75},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_guide_section":"General","content_items":[{"topic":"Security Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Security in Security."},{"topic":"Security Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Security."}],"rag_retrieval_score":0.75},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_guide_section":"General","content_items":[{"topic":"Networking Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Networking in Networking."},{"topic":"Networking Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Networking."}],"rag_retrieval_score":0.75},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_guide_section":"General","content_items":[{"topic":"Compute Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Compute in Compute."},{"topic":"Compute Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Compute."}],"rag_retrieval_score":0.75},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_guide_section":"General","content_items":[{"topic":"Security Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Security in Security."},{"topic":"Security Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Security."}],"rag_retrieval_score":0.75},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_guide_section":"General","content_items":[{"topic":"Networking Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Networking in Networking."},{"topic":"Networking Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Networking."}],"rag_retrieval_score":0.75},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_guide_section":"General","content_items":[{"topic":"Compute Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Compute in Compute."},{"topic":"Compute Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Compute."}],"rag_retrieval_score":0.75},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_guide_section":"General","content_items":[{"topic":"Security Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Security in Security."},{"topic":"Security Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Security."}],"rag_retrieval_score":0.75},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_guide_section":"General","content_items":[{"topic":"Networking Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Networking in Networking."},{"topic":"Networking Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Networking."}],"rag_retrieval_score":0.75},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_guide_section":"General","content_items":[{"topic":"Compute Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Compute in Compute."},{"topic":"Compute Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Compute."}],"rag_retrieval_score":0.75},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","exam_guide_section":"General","content_items":[{"topic":"Security Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Security in Security."},{"topic":"Security Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Security."}],"rag_retrieval_score":0.75},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","exam_guide_section":"General","content_items":[{"topic":"Networking Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Networking in Networking."},{"topic":"Networking Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Networking."}],"rag_retrieval_score":0.75},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","exam_guide_section":"General","content_items":[{"topic":"Compute Fundamentals","source":"AWS Solutions Architect Study Guide","page_ref":"Chapter TBD","summary":"Core concepts and principles of Compute in Compute."},{"topic":"Compute Best Practices","source":"Official Documentation","page_ref":"Section TBD","summary":"Industry best practices and common patterns for Compute."}],"rag_retrieval_score":0.75}],"recommended_courses":[{"skill_id":"security","skill_name":"Security","exam_domain":"Security","course_title":"Mastering Security","course_description":"Comprehensive course covering Security concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Security principles","Apply Security in practical scenarios","Master exam topics related to Security"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","course_title":"Mastering Networking","course_description":"Comprehensive course covering Networking concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Networking principles","Apply Networking in practical scenarios","Master exam topics related to Networking"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","course_title":"Mastering Compute","course_description":"Comprehensive course covering Compute concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Compute principles","Apply Compute in practical scenarios","Master exam topics related to Compute"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","course_title":"Mastering Security","course_description":"Comprehensive course covering Security concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Security principles","Apply Security in practical scenarios","Master exam topics related to Security"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","course_title":"Mastering Networking","course_description":"Comprehensive course covering Networking concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Networking principles","Apply Networking in practical scenarios","Master exam topics related to Networking"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","course_title":"Mastering Compute","course_description":"Comprehensive course covering Compute concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Compute principles","Apply Compute in practical scenarios","Master exam topics related to Compute"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","course_title":"Mastering Security","course_description":"Comprehensive course covering Security concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Security principles","Apply Security in practical scenarios","Master exam topics related to Security"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","course_title":"Mastering Networking","course_description":"Comprehensive course covering Networking concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Networking principles","Apply Networking in practical scenarios","Master exam topics related to Networking"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","course_title":"Mastering Compute","course_description":"Comprehensive course covering Compute concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Compute principles","Apply Compute in practical scenarios","Master exam topics related to Compute"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","course_title":"Mastering Security","course_description":"Comprehensive course covering Security concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Security principles","Apply Security in practical scenarios","Master exam topics related to Security"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","course_title":"Mastering Networking","course_description":"Comprehensive course covering Networking concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Networking principles","Apply Networking in practical scenarios","Master exam topics related to Networking"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","course_title":"Mastering Compute","course_description":"Comprehensive course covering Compute concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Compute principles","Apply Compute in practical scenarios","Master exam topics related to Compute"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"security","skill_name":"Security","exam_domain":"Security","course_title":"Mastering Security","course_description":"Comprehensive course covering Security concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Security principles","Apply Security in practical scenarios","Master exam topics related to Security"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"networking","skill_name":"Networking","exam_domain":"Networking","course_title":"Mastering Networking","course_description":"Comprehensive course covering Networking concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Networking principles","Apply Networking in practical scenarios","Master exam topics related to Networking"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9},{"skill_id":"compute","skill_name":"Compute","exam_domain":"Compute","course_title":"Mastering Compute","course_description":"Comprehensive course covering Compute concepts, best practices, and exam-relevant scenarios.","learning_objectives":["Understand core Compute principles","Apply Compute in practical scenarios","Master exam topics related to Compute"],"estimated_duration_minutes":60,"difficulty_level":"beginner","generation_status":"pending","video_url":null,"presentation_url":null,"download_url":null,"priority":9}],"google_sheets_export_data":{"sheet_name":"PresGen_Gap_Analysis","tabs":[{"tab_name":"Answers","title":"📝 Assessment Answers with Explanations","summary":"Total: 0 | Correct: 0 | Incorrect: 0","data":[["Question","Your Answer","Correct Answer","Explanation","Domain","Difficulty","Result"]]},{"tab_name":"Gap Analysis","title":"📊 Gap Analysis with Summary","data":[["📊 Gap Analysis Summary"],[],["Overall Score","27.0%"],["Total Questions","5"],["Correct Answers","2"],[],["📖 Summary"],[],["You scored 27.0% overall on this AWS Solutions Architect assessment.\n\nYour strongest areas are:\n- Security (0.0%) - Above passing threshold\n- Networking (0.0%) - Above passing threshold\n\nAreas needing improvement:\n- Networking (0.0%) - Below recommended proficiency\n- Compute (0.0%) - Below recommended proficiency\n\nRecommended next steps:\n- Focus study time on areas with lowest scores\n- Review exam guide sections for identified gaps\n- Practice with targeted exercises\n"],[],["🔍 Identified Skill Gaps"],[],["Skill","Gap Severity","Priority"],["Security","",""],["Networking","",""],["Compute","",""],[]]},{"tab_name":"Content Outlines","title":"📚 RAG-Retrieved Content Outlines","data":[["Skill","Domain","Content Outline","Source References"],["Security","Security","",""],["Networking","Networking","",""],["Compute","Compute","",""],["Security","Security","",""],["Networking","Networking","",""],["Compute","Compute","",""],["Security","Security","",""],["Networking","Networking","",""],["Compute","Compute","",""],["Security","Security","",""],["Networking","Networking","",""],["Compute","Compute","",""],["Security","Security","",""],["Networking","Networking","",""],["Compute","Compute","",""]]},{"tab_name":"Recommended Courses","title":"🎓 Recommended Courses by Domain","data":[["📖 Compute"],[],["Skill","Priority","Duration (hrs)","Rationale"],["• Compute","","0",""],["• Compute","","0",""],["• Compute","","0",""],["• Compute","","0",""],["• Compute","","0",""],[],["📖 Networking"],[],["Skill","Priority","Duration (hrs)","Rationale"],["• Networking","","0",""],["• Networking","","0",""],["• Networking","","0",""],["• Networking","","0",""],["• Networking","","0",""],[],["📖 Security"],[],["Skill","Priority","Duration (hrs)","Rationale"],["• Security","","0",""],["• Security","","0",""],["• Security","","0",""],["• Security","","0",""],["• Security","","0",""],[]]}],"sections":{"executive_summary":{"title":"🎯 Executive Summary","data":[["Assessment Area","Score/Status","Interpretation","Priority Actions"],["Overall Readiness","0%","Needs Work - Intensive preparation required","Continue preparation"],["Learning Profile","Mixed","Strategic learner assessment","Leverage strengths"],["Priority Gaps",0,"0 areas need improvement","Focus remediation"],["Study Time Needed","0h","Estimated preparation time","Plan schedule"]]},"bloom_taxonomy_analysis":{"title":"🧠 Bloom's Taxonomy Analysis","data":[["No Bloom's taxonomy data available"]]},"learning_style_assessment":{"title":"📚 Learning Style Assessment","data":[["No learning style data available"]]},"metacognitive_analysis":{"title":"🎯 Metacognitive Awareness","data":[["No metacognitive data available"]]},"transfer_learning_assessment":{"title":"🔄 Transfer Learning Ability","data":[["No transfer learning data available"]]},"certification_readiness":{"title":"🏆 Certification Readiness","data":[["No certification readiness data available"]]},"detailed_gaps":{"title":"🔍 Detailed Gap Analysis","data":[["Domain","Current Score","Target Score","Gap Severity","Priority","Remediation Focus"]]},"remediation_actions":{"title":"🛠️ Personalized Remediation Plan","data":[["Action","Domain","Type","Priority","Estimated Hours","Success Criteria"]]},"recommendations":{"title":"💡 Personalized Recommendations","data":[["Category","Recommendation","Rationale"]]}},"charts":[{"type":"radar_chart","title":"Bloom's Taxonomy Performance Profile","data":{}},{"type":"bar_chart","title":"Domain Performance vs Targets","data":{}},{"type":"gauge_chart","title":"Metacognitive Maturity Score","data":{"score":0}},{"type":"scatter_plot","title":"Learning Style Performance Matrix","data":{}}],"summary_stats":{"total_domains_assessed":0,"metrics_analyzed":5,"recommendations_generated":0,"estimated_improvement_potential":0.0}}}},"csv_summary":{"available":true,"description":"Gap analysis summary in CSV format","data":"Domain,Current_Score,Target_Score,Gap_Severity,Priority\r\n"},"markdown_report":{"available":true,"description":"Human-readable markdown report","data":"# Skill Gap Analysis Report\n\nGenerated: 2025-10-02 18:41:28\n\n## Executive Summary\n\n- **Overall Readiness**: 0%\n- **Priority Learning Areas**: 0\n- **Estimated Study Time**: 0 hours\n\n## Key Findings\n\n"}},"instructions":[]}%  
```

2. Verify response:
```json
{
  "success": true,
  "sheet_id": "1abc...xyz",
  "sheet_url": "https://docs.google.com/spreadsheets/d/1abc...xyz/edit",
  "tabs": ["Answers", "Gap Analysis", "Content Outline", "Presentation"],
  "exported_at": "2025-10-02T10:30:00Z"
}
```

3. Verify database record created:
```bash
sqlite3 test_database.db "SELECT workflow_id, sheet_id, sheet_url, tabs, exported_at FROM google_sheets_exports WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

**Expected Results**:
- ✅ API returns 200 OK
- ✅ Sheet created in Google Drive
- ✅ Response contains sheet_id and sheet_url
- ✅ Export record saved to database

**Pass Criteria**:
- [ ] POST endpoint functional
- [ ] Valid Google Sheet created
- [ ] Response schema matches
- [ ] Database persistence works

---

### Test Case 1.3: Export Error Handling

**Test Steps**:
1. Test export with missing gap analysis data:
```bash
curl -X POST http://localhost:8081/api/v1/workflows/{invalid_workflow_id}/gap-analysis/export-to-sheets -H "Content-Type: application/json"

--
(.venv) yitzchak@MacBookPro presgen-assess % curl -X POST http://localhost:8081/api/v1/workflows/{invalid_workflow_id}/gap-analysis/export-to-sheets -H "Content-Type: application/json"
{"detail":[{"type":"uuid_parsing","loc":["path","workflow_id"],"msg":"Input should be a valid UUID, invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found `i` at 1","input":"invalid_workflow_id","ctx":{"error":"invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found `i` at 1"},"url":"https://errors.pydantic.dev/2.11/v/uuid_parsing"}]}%         
```

**Expected Response**:
```json
{
  "success": false,
  "error": "Gap analysis not found for workflow",
  "status_code": 404
}
```

2. Test export with Google API quota exceeded (simulate):
```bash
# Mock Google API error response
```

**Expected Response**:
```json
{
  "success": false,
  "error": "Google Sheets API quota exceeded. Please try again later.",
  "status_code": 429,
  "retry_after": 60
}
```

**Pass Criteria**:
- [ ] 404 returned for missing workflow
- [ ] 429 returned for quota exceeded
- [ ] Error messages descriptive
- [ ] Logs capture error details

---

## Test S2-T2: 4-Tab Sheet Generation

**Feature**: Generate Google Sheet with 4 tabs from database data

### Test Case 2.1: Sheet Structure Validation

**Test Steps**:
1. Export gap analysis to sheets
2. Open sheet URL in browser
3. Verify 4 tabs exist with correct names:
   - Tab 1: "Answers"
   - Tab 2: "Gap Analysis"
   - Tab 3: "Content Outline"
   - Tab 4: "Presentation"

4. Verify tab order (left to right):
   Answers → Gap Analysis → Content Outline → Presentation

**Expected Results**:
- ✅ All 4 tabs present
- ✅ Tab names match specification
- ✅ Tab order correct
- ✅ Each tab contains headers

**Pass Criteria**:
- [ ] 4 tabs created
- [ ] Tab names correct
- [ ] Tab order correct
- [ ] No empty tabs

---

### Test Case 2.2: Sheet Permissions and Sharing

**Test Steps**:
1. Export sheet
2. Verify sheet permissions:
   - Sheet owned by service account
   - User has edit access
   - Sheet is private (not public)

3. Test sharing:
```bash
# Verify via Google Drive API
curl "https://www.googleapis.com/drive/v3/files/{sheet_id}/permissions" \
  -H "Authorization: Bearer {access_token}"
```

**Expected Results**:
- ✅ Service account is owner
- ✅ User has editor permissions
- ✅ Sheet not publicly accessible

**Pass Criteria**:
- [ ] Correct permissions set
- [ ] User can edit sheet
- [ ] Sheet private by default

---

## Test S2-T3: Answers Tab Formatting

**Feature**: Populate "Answers" tab with assessment responses

### Test Case 3.1: Answers Tab Data Population

**Test Steps**:
1. Export sheet and navigate to "Answers" tab
2. Verify column headers:
   - A: Question #
   - B: Question Text
   - C: User Answer
   - D: Correct Answer
   - E: Result (Correct/Incorrect)
   - F: Skill
   - G: Domain
   - H: Confidence Level

3. Verify data rows populated from database:
```bash
# Check source data
sqlite3 test_database.db "SELECT assessment_data FROM workflow_executions WHERE id='19952bd09cfe44bc9460c4f521caca89';"
```

4. Verify row formatting:
   - Header row: Bold, frozen
   - Correct answers: Green background
   - Incorrect answers: Red background
   - Alternating row colors for readability

**Expected Results**:
- ✅ All question responses present
- ✅ Headers correctly labeled
- ✅ Data matches database
- ✅ Conditional formatting applied

**Pass Criteria**:
- [ ] All columns present
- [ ] Data accurate
- [ ] Formatting applied
- [ ] Headers frozen

---

### Test Case 3.2: Answers Tab Calculations

**Test Steps**:
1. Verify summary calculations at bottom of Answers tab:
   - Total Questions: =COUNTA(A2:A)
   - Correct: =COUNTIF(E:E,"Correct")
   - Incorrect: =COUNTIF(E:E,"Incorrect")
   - Score: =Correct/Total*100

2. Verify calculations match gap analysis data:
```bash
sqlite3 test_database.db "SELECT total_questions, correct_answers, overall_score FROM gap_analysis_results WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

**Expected Results**:
- ✅ Formulas calculate correctly
- ✅ Summary matches database
- ✅ Percentage formatted properly

**Pass Criteria**:
- [ ] Summary row present
- [ ] Calculations correct
- [ ] Matches database values

---

## Test S2-T4: Gap Analysis Tab Formatting

**Feature**: Populate "Gap Analysis" tab with skill gaps and performance data

### Test Case 4.1: Gap Analysis Tab Structure

**Test Steps**:
1. Navigate to "Gap Analysis" tab
2. Verify sections:
   - **Section 1: Overall Performance**
     - Overall Score
     - Total Questions
     - Correct Answers
     - Incorrect Answers

   - **Section 2: Performance by Domain**
     - Domain | Score | Target | Gap | Status

   - **Section 3: Identified Skill Gaps**
     - Skill Name | Domain | Severity | Questions Missed | Confidence Delta

3. Verify data matches database:
```bash
sqlite3 test_database.db "SELECT overall_score, performance_by_domain, skill_gaps FROM gap_analysis_results WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

**Expected Results**:
- ✅ 3 sections present
- ✅ Data populated from database
- ✅ Sections clearly labeled
- ✅ Headers formatted (bold)

**Pass Criteria**:
- [ ] All sections present
- [ ] Data accurate
- [ ] Clear section separation
- [ ] Formatting applied

---

### Test Case 4.2: Gap Analysis Text Summary

**Test Steps**:
1. Verify text summary section at top of tab
2. Text should include:
   - Overall score and performance
   - Strongest areas
   - Areas needing improvement
   - Critical skill gaps
   - Recommended next steps

3. Compare with database text_summary:
```bash
sqlite3 test_database.db "SELECT text_summary FROM gap_analysis_results WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

**Expected Results**:
- ✅ Text summary displayed
- ✅ Matches database content
- ✅ Readable formatting (wrapped text)
- ✅ Includes all key elements

**Pass Criteria**:
- [ ] Summary cell present
- [ ] Text matches database
- [ ] Proper formatting
- [ ] All elements included

---

### Test Case 4.3: Performance Charts (Images)

**Test Steps**:
1. Verify chart images embedded in Gap Analysis tab:
   - Bar chart: Performance by Domain
   - Radar chart: Skill Coverage
   - Scatter plot: Confidence Calibration

2. Verify charts generated from charts_data JSON:
```bash
sqlite3 test_database.db "SELECT charts_data FROM gap_analysis_results WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

3. Verify chart images:
   - Proper size (not too large)
   - Clear labels and legends
   - Positioned correctly in sheet

**Expected Results**:
- ✅ 3 chart images present
- ✅ Charts match database data
- ✅ Clear and readable
- ✅ Proper positioning

**Pass Criteria**:
- [ ] All charts present
- [ ] Charts accurate
- [ ] Readable size
- [ ] Correct placement

---

## Test S2-T5: Content Outline Tab (RAG)

**Feature**: Populate "Content Outline" tab with RAG-retrieved learning resources

### Test Case 5.1: Content Outline Tab Structure

**Test Steps**:
1. Navigate to "Content Outline" tab
2. Verify column headers:
   - A: Skill Name
   - B: Domain
   - C: Exam Guide Section
   - D: Topic
   - E: Source
   - F: Page Reference
   - G: Summary
   - H: Relevance Score

3. Verify data populated from content_outlines table:
```bash
sqlite3 test_database.db "SELECT skill_name, exam_domain, exam_guide_section, content_items, rag_retrieval_score FROM content_outlines WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

4. Verify content items unpacked from JSON:
   - Each content item gets its own row
   - Skill name repeated for each item
   - Relevance score displayed

**Expected Results**:
- ✅ All skill gaps have content outlines
- ✅ Content items properly unpacked
- ✅ Data matches database
- ✅ Headers formatted

**Pass Criteria**:
- [ ] All columns present
- [ ] Data accurate
- [ ] JSON unpacked correctly
- [ ] Formatting applied

---

### Test Case 5.2: RAG Content Formatting

**Test Steps**:
1. Verify RAG content formatting:
   - Topic: Concise title (< 100 chars)
   - Source: Full citation
   - Page Reference: Clear location
   - Summary: Readable paragraph (< 500 chars)

2. Verify relevance score:
   - Range: 0.0 to 1.0
   - Displayed as percentage (e.g., "85%")
   - Color-coded:
     - Green: ≥ 0.7
     - Yellow: 0.5-0.69
     - Red: < 0.5

3. Verify content quality:
   - No truncated text
   - Proper line wrapping
   - Citations complete

**Expected Results**:
- ✅ All content properly formatted
- ✅ Relevance scores color-coded
- ✅ Text readable and complete
- ✅ Citations accurate

**Pass Criteria**:
- [ ] Content formatted correctly
- [ ] Scores color-coded
- [ ] Text not truncated
- [ ] Citations complete

---

### Test Case 5.3: Content Outline Grouping

**Test Steps**:
1. Verify content grouped by skill:
   - All items for Skill A together
   - Followed by all items for Skill B
   - Etc.

2. Verify skill sections separated:
   - Blank row or border between skills
   - Skill name highlighted or bold
   - Domain label clear

3. Verify sort order:
   - Skills ordered by severity (highest first)
   - Within skill, items ordered by relevance score (highest first)

**Expected Results**:
- ✅ Clear skill grouping
- ✅ Visual separation
- ✅ Logical sort order
- ✅ Easy to scan

**Pass Criteria**:
- [ ] Skills grouped correctly
- [ ] Clear separation
- [ ] Proper sort order
- [ ] Readable layout

---

## Test S2-T6: Presentation Tab

**Feature**: Populate "Presentation" tab with course links and metadata

### Test Case 6.1: Presentation Tab Structure

**Test Steps**:
1. Navigate to "Presentation" tab
2. Verify column headers:
   - A: Course Title
   - B: Domain
   - C: Skills Covered
   - D: Status
   - E: Presentation URL
   - F: Download URL
   - G: Duration (seconds)
   - H: Generated At

3. Verify data populated from recommended_courses table:
```bash
sqlite3 test_database.db "SELECT course_title, exam_domain, skills_covered, generation_status, video_url, download_url, duration_seconds FROM recommended_courses WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

**Expected Results**:
- ✅ All recommended courses listed
- ✅ Data matches database
- ✅ Headers formatted
- ✅ Status indicators clear

**Pass Criteria**:
- [ ] All columns present
- [ ] Data accurate
- [ ] Formatting applied
- [ ] Status clear

---

### Test Case 6.2: Course Status Indicators

**Test Steps**:
1. Verify status values and formatting:
   - "pending": Yellow background, "Not Generated"
   - "generating": Orange background, "In Progress..."
   - "completed": Green background, "✓ Complete"
   - "failed": Red background, "✗ Failed"

2. Verify hyperlinks:
   - Presentation URL: Clickable link if status = "completed"
   - Download URL: Clickable link if status = "completed"
   - URLs disabled/greyed if status ≠ "completed"

3. Verify duration formatting:
   - Convert seconds to MM:SS or HH:MM:SS
   - Display as readable format (e.g., "3:45" or "1:23:45")

**Expected Results**:
- ✅ Status color-coded correctly
- ✅ Hyperlinks functional
- ✅ Duration readable
- ✅ Conditional formatting works

**Pass Criteria**:
- [ ] Status color-coded
- [ ] Links functional
- [ ] Duration formatted
- [ ] Conditional logic correct

---

### Test Case 6.3: Presentation Tab Updates

**Test Steps**:
1. Verify initial state (all courses "pending"):
```bash
sqlite3 test_database.db "UPDATE recommended_courses SET generation_status='pending', video_url=NULL WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89';"
```

2. Export to sheets and verify "pending" status

3. Update course status to "completed":
```bash
sqlite3 test_database.db "UPDATE recommended_courses SET generation_status='completed', video_url='https://drive.google.com/file/d/abc123', duration_seconds=225 WHERE id='{course_id}';"
```

4. Re-export to sheets (or update existing sheet)

5. Verify updated values:
   - Status = "✓ Complete" (green)
   - Presentation URL clickable
   - Duration = "3:45"

**Expected Results**:
- ✅ Initial export shows pending
- ✅ Updates reflected on re-export
- ✅ Links become active
- ✅ Data stays synchronized

**Pass Criteria**:
- [ ] Initial state correct
- [ ] Updates reflected
- [ ] Links activate correctly
- [ ] Data synchronized

---

## Test S2-T7: Rate Limiter Toggle

**Feature**: Feature flag to enable/disable Google API rate limiting

### Test Case 7.1: Rate Limiter Disabled (Development)

**Setup**:
```bash
export ENABLE_GOOGLE_RATE_LIMITER=false
uvicorn src.service.app:app --port 8081 --reload
```

**Test Steps**:
1. Trigger multiple rapid exports:
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets &
done
```

2. Verify all requests succeed:
   - No rate limit errors
   - All 10 exports complete
   - No "429 Too Many Requests" responses

3. Check logs:
```bash
grep "rate_limit" src/logs/workflows.log
```

**Expected Results**:
- ✅ All requests succeed
- ✅ No rate limiting applied
- ✅ Logs show rate limiter disabled

**Pass Criteria**:
- [ ] All requests succeed
- [ ] No 429 errors
- [ ] Logs confirm disabled

---

### Test Case 7.2: Rate Limiter Enabled (Production)

**Setup**:
```bash
export ENABLE_GOOGLE_RATE_LIMITER=true
export GOOGLE_RATE_LIMIT_CALLS=5
export GOOGLE_RATE_LIMIT_WINDOW_SECONDS=60
uvicorn src.service.app:app --port 8081 --reload
```

**Test Steps**:
1. Trigger 10 rapid exports (exceeds limit of 5 per 60 seconds):
```bash
for i in {1..10}; do
  curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets
done
```

2. Verify rate limiting:
   - First 5 requests succeed (200 OK)
   - Requests 6-10 fail with 429 status
   - Response includes "Retry-After" header

3. Verify error response:
```json
{
  "success": false,
  "error": "Rate limit exceeded. Please try again in 45 seconds.",
  "status_code": 429,
  "retry_after": 45
}
```

4. Wait 60 seconds and retry:
```bash
sleep 60
curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets
```

**Expected Results**:
- ✅ First 5 requests succeed
- ✅ Subsequent requests rate limited
- ✅ Retry-After header present
- ✅ Rate limit resets after window

**Pass Criteria**:
- [ ] Rate limiting enforced
- [ ] 429 status returned
- [ ] Retry-After header correct
- [ ] Rate limit resets

---

### Test Case 7.3: Rate Limiter Configuration Validation

**Test Steps**:
1. Verify rate limiter configuration loaded:
```bash
curl http://localhost:8081/api/v1/config/rate-limiter
```

**Expected Response**:
```json
{
  "enabled": true,
  "max_calls": 5,
  "window_seconds": 60,
  "scope": "google_api"
}
```

2. Test invalid configuration:
```bash
export GOOGLE_RATE_LIMIT_CALLS=0  # Invalid
uvicorn src.service.app:app --port 8081
```

**Expected Results**:
- ✅ Server fails to start with error
- ✅ Error message: "Invalid rate limit configuration"

**Pass Criteria**:
- [ ] Config loads correctly
- [ ] Invalid config rejected
- [ ] Error messages clear

---

## Test S2-T8: Error Handling & Logging

**Feature**: Comprehensive error handling and structured logging for sheet export

### Test Case 8.1: Export Logging

**Test Steps**:
1. Enable enhanced logging:
```bash
export ENABLE_ENHANCED_LOGGING=true
```

2. Trigger export:
```bash
curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets
```

3. Verify logs:
```bash
grep "sheets_export" src/logs/workflows.log
```

**Expected Log Events**:
```json
{
  "event": "sheets_export_start",
  "workflow_id": "...",
  "correlation_id": "...",
  "timestamp": "2025-10-02T10:30:00Z"
}

{
  "event": "sheets_export_tab_created",
  "tab_name": "Answers",
  "row_count": 24,
  "correlation_id": "..."
}

{
  "event": "sheets_export_complete",
  "workflow_id": "...",
  "sheet_id": "...",
  "duration_ms": 3500,
  "correlation_id": "..."
}
```

**Pass Criteria**:
- [ ] Export start logged
- [ ] Tab creation logged
- [ ] Export complete logged
- [ ] Correlation ID tracked

---

### Test Case 8.2: Export Error Scenarios

**Test Steps**:
1. Test Google API authentication failure (invalid credentials):
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/invalid/path
curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets
```

**Expected Response**:
```json
{
  "success": false,
  "error": "Google Sheets authentication failed",
  "status_code": 500
}
```

2. Test missing gap analysis data:
```bash
curl -X POST http://localhost:8081/api/v1/workflows/{workflow_id_no_data}/gap-analysis/export-to-sheets
```

**Expected Response**:
```json
{
  "success": false,
  "error": "Gap analysis not found for workflow",
  "status_code": 404
}
```

3. Test network timeout (mock):
```bash
# Simulate network delay
curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets \
  --max-time 5
```

**Expected Response**:
```json
{
  "success": false,
  "error": "Google Sheets API timeout. Please try again.",
  "status_code": 504
}
```

**Pass Criteria**:
- [ ] Auth errors handled
- [ ] Missing data handled
- [ ] Timeout handled
- [ ] Error messages descriptive

---

### Test Case 8.3: Export Performance Metrics

**Test Steps**:
1. Export sheet and measure timing:
```bash
time curl -X POST http://localhost:8081/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/gap-analysis/export-to-sheets
```

2. Verify performance logs:
```bash
grep "sheets_export_complete" src/logs/workflows.log | grep "duration_ms"
```

**Performance Targets**:
- Total export time: < 60 seconds
- Tab creation (per tab): < 10 seconds
- Data formatting: < 5 seconds
- API calls: < 3 seconds each

3. Verify performance metrics in response:
```json
{
  "success": true,
  "sheet_id": "...",
  "performance": {
    "total_duration_ms": 45000,
    "tab_creation_ms": 30000,
    "formatting_ms": 10000,
    "api_calls_ms": 5000
  }
}
```

**Pass Criteria**:
- [ ] Export completes in < 60s
- [ ] Tab creation < 10s each
- [ ] Performance logged
- [ ] Metrics in response

---

## 🎯 Sprint 2 Success Criteria

### Critical Path (Must Pass)
- [ ] S2-T1.1: Export button functional
- [ ] S2-T1.2: Export API endpoint works
- [ ] S2-T2.1: 4-tab sheet structure correct
- [ ] S2-T3.1: Answers tab populated
- [ ] S2-T4.1: Gap Analysis tab populated
- [ ] S2-T5.1: Content Outline tab populated
- [ ] S2-T6.1: Presentation tab structure correct

### Important (Should Pass)
- [ ] S2-T3.2: Answers calculations correct
- [ ] S2-T4.2: Gap Analysis text summary present
- [ ] S2-T5.2: RAG content formatted
- [ ] S2-T6.2: Course status indicators work
- [ ] S2-T7.1: Rate limiter toggles correctly

### Nice to Have (May Pass)
- [ ] S2-T4.3: Charts embedded in sheet
- [ ] S2-T5.3: Content outline grouping
- [ ] S2-T6.3: Presentation tab updates
- [ ] S2-T8.3: Performance metrics tracked

---

## 📊 Test Execution Tracking

**Date**: ___________
**Tester**: ___________

| Test ID | Status | Pass/Fail | Notes |
|---------|--------|-----------|-------|
| S2-T1.1 | | | |
| S2-T1.2 | | | |
| S2-T1.3 | | | |
| S2-T2.1 | | | |
| S2-T2.2 | | | |
| S2-T3.1 | | | |
| S2-T3.2 | | | |
| S2-T4.1 | | | |
| S2-T4.2 | | | |
| S2-T4.3 | | | |
| S2-T5.1 | | | |
| S2-T5.2 | | | |
| S2-T5.3 | | | |
| S2-T6.1 | | | |
| S2-T6.2 | | | |
| S2-T6.3 | | | |
| S2-T7.1 | | | |
| S2-T7.2 | | | |
| S2-T7.3 | | | |
| S2-T8.1 | | | |
| S2-T8.2 | | | |
| S2-T8.3 | | | |

---

## 📝 Notes and Issues

_Document any issues, blockers, or observations during testing:_

---

## 🔧 Database Schema Requirements

Sprint 2 requires the following table for export tracking:

```sql
-- Google Sheets Export Tracking
CREATE TABLE IF NOT EXISTS google_sheets_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    sheet_id VARCHAR(255) NOT NULL,
    sheet_url TEXT NOT NULL,
    tabs JSONB NOT NULL DEFAULT '[]'::jsonb,
    exported_at TIMESTAMP DEFAULT NOW(),
    export_duration_ms INTEGER,
    export_status VARCHAR(50) DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sheets_workflow ON google_sheets_exports(workflow_id);
CREATE INDEX idx_sheets_status ON google_sheets_exports(export_status);
```

---

## 🚨 Sprint 2 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Google API quota exceeded | HIGH | Rate limiter; exponential backoff; quota monitoring |
| Sheet creation timeout | MEDIUM | Async export; background job queue; retry logic |
| RAG content formatting errors | MEDIUM | Content validation; fallback to plain text |
| Large dataset export failures | MEDIUM | Batch processing; pagination; chunking |

---

## 📋 Prerequisites Checklist

Before starting Sprint 2 testing:

- [ ] Sprint 1 100% complete
- [ ] Gap analysis data in database
- [ ] Content outlines populated (RAG retrieval done)
- [ ] Recommended courses created
- [ ] Google Sheets API credentials configured
- [ ] Feature flag `ENABLE_SHEETS_EXPORT` available
- [ ] Enhanced logging enabled

---

**Test Plan Ready for Sprint 2 Implementation**
