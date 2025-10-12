# Sprint 4 – Phase 10 Report

## Implementation Plan
1. **Enable Outline Regeneration (flag driven)**
   - Add `PRESGEN_REGENERATE_COURSE_OUTLINE` to environment/Settings so operators can toggle new behaviour without breaking existing flows.
2. **Fetch Fresh Inputs at Course Generation**
   - During `generate_skill_course` load the existing `RecommendedCourse`, deserialize its stored JSON (objectives, sections), and pull the resolved presentation prompt.
   - Retrieve assessment/gap-analysis JSON from the workflow record; this gives score summaries and priority learning areas.
   - Collect new RAG context (exam guidelines / transcripts) through `RAGKnowledgeBase.retrieve_context_for_assessment` using the learning objectives or skill focus as queries.
3. **Call LLM for Updated Outline**
   - Extend `LLMService` with `generate_refined_course_outline()` that accepts: recommended course data, prompt, RAG context, assessment + gap-analysis summaries, and target slide count.
   - Build a detailed prompt (existing outline + requirements) and log both the outbound request and inbound JSON response.
   - Parse sections/objectives from the response, fall back gracefully if parsing fails.
4. **Persist & Reuse Regenerated Outline**
   - When successful, replace `RecommendedCourse.learning_objectives` / `content_outline` with the regenerated data (and update `course_title`, etc.) so subsequent runs re-use the latest structure.
5. **Adapt & Send to PresGen-Core**
   - Feed the regenerated outline into `PresentationGenerationService._adapt_content_for_presentation`, log the payload, and continue with Google Slides + PresGen-Core + PresGen-Avatar.
6. **Comprehensive Logging**
   - Emit JSON logs at each major step (context collection, LLM request/response, presentation payload) for observability.

## Completed Tasks
- Added feature flag support (`PRESGEN_REGENERATE_COURSE_OUTLINE`) and deserialization helpers for stored JSON.
- Instantiated `PresentationGenerationService` inside course generation pipeline and created helpers to normalize course data, gather RAG context, and call the LLM.
- Implemented `LLMService.generate_refined_course_outline` with a new prompt builder that combines recommended-course fields, presentation prompt, assessment/gap summaries, and transcript context.
- Hooked regeneration into `generate_skill_course`: when the flag is enabled, the outline gets refreshed, persisted back to the recommended-course record, and logged via `COURSE_OUTLINE_REGENERATED`.
- Added structured JSON logging for regenerated outline inputs/outputs and the final payload sent to PresGen-Core.

## Remaining Work
- Add automated tests (unit/integration) covering outline regeneration, error handling, and logging assertions.
- Validate/adjust prompt tuning for different certification types (ensure transcripts/guidelines are summarized effectively).
- Document the rollout procedure and advise ops on enabling the new flag in staging/production.
- Monitor logs in production to refine prompt size, token usage, and regenerate cadence.
