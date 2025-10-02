# PresGen-Assess Gemini Migration Plan

## Objectives
- Replace OpenAI GPT-4 usage in PresGen-Assess with Gemini 2.0 Flash (and optional Gemini 1.5 Pro fallback) to reduce LLM costs while maintaining output quality.
- Introduce Google Cloud Text-to-Speech as the secondary narration engine in PresGen-Training2, keeping ElevenLabs as primary.
- Enhance observability and documentation to support rollout and comparison testing.

## Prerequisites
- Google Cloud project ready with Vertex AI and Text-to-Speech APIs enabled.
- Service account or API key with permissions for Vertex AI and TTS, stored locally via `GOOGLE_API_KEY` / `GOOGLE_APPLICATION_CREDENTIALS`.
- Existing OpenAI keys retained for fallback and benchmarking.

## Workstream A: PresGen-Assess LLM Migration
1. **Config Updates**
   - Extend `presgen-assess/src/common/config.py` with `ASSESS_LLM_PROVIDER`, `ASSESS_LLM_MODEL`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_REGION`.
   - Update `.env` and `.env.example` to include new variables with defaults (`gemini-2.0-flash-001`).

2. **Gemini Client Implementation**
   - Create an async Gemini client wrapper mirroring OpenAI usage (handle retries, JSON parsing, system prompts).
   - Wire the wrapper into `LLMService` so provider selection happens at initialization based on config.

3. **Prompt & Schema Tweaks**
   - Rewrite system message to detail required JSON schema and output rules for Gemini.
   - Add few-shot examples demonstrating valid responses.
   - Adjust RAG prompt builder to trim context lengths for Gemini limits.

4. **Feature Toggles**
   - Implement runtime toggle to switch between `gemini-2.0-flash-001` and `gemini-1.5-pro-latest` via `.env` change.
   - Keep OpenAI path available via `ASSESS_LLM_PROVIDER=openai` for rollback.

5. **Testing & Validation**
   - Add unit tests mocking Gemini responses for success/error paths.
   - Create comparison script to run sampled assessments through both providers and log quality notes.
   - Capture token usage and cost estimates for before/after runs.

## Workstream B: Google Cloud Text-to-Speech Integration
1. **Dependency & Config**
   - Add `google-cloud-texttospeech` to `requirements.txt` / `poetry` file.
   - Update `.env` for `GOOGLE_TTS_VOICE`, `GOOGLE_APPLICATION_CREDENTIALS` path.

2. **Voice Manager Enhancements**
   - Implement `_generate_google_tts_speech` in `presgen-training2/src/core/voice/voice_manager.py` using WaveNet/Studio voices.
   - Update engine selection logic to use ElevenLabs → Google TTS → OpenAI.
   - Persist metadata for Google TTS profiles.

3. **Audio Handling**
   - Ensure synthesized audio saves to WAV; add conversions if needed.
   - Add tests covering Google TTS path with mocked client.

## Workstream C: Observability & Documentation
1. **Logging**
   - Add structured logs in LLM service capturing provider, model, token counts, latency, cost estimates.
   - Log TTS engine usage, character counts, and errors in voice manager.

2. **Dashboards/Monitoring**
   - Define metrics (e.g., successes, failures, latency) and integrate with existing monitoring if available.

3. **Documentation**
   - Create migration guide summarizing setup steps, env vars, rollback plan.
   - Update `OAUTH_TOKEN_STANDARDIZATION.md` or related docs with new Gemini/TTS requirements.

## Rollout Checklist
1. Complete code changes and tests.
2. Regenerate unified OAuth token with Slides/Drive/Script scopes (already done) and verify new Google credentials.
3. Deploy to staging with `ASSESS_LLM_PROVIDER=gemini` and run regression suite.
4. Evaluate assessment output quality vs. GPT-4/gpt-4o baseline; adjust prompts if necessary.
5. Enable Google TTS fallback in staging and run narration workflows.
6. Review logs for cost/latency impacts.
7. After approval, update production `.env` toggles and monitor.

## Open Questions / Risks
- Need to confirm Gemini JSON adherence on larger prompts; may require additional validation or fallback logic.
- Google TTS quota and voice selection must be sized for expected workload.
- Ensure compliance and data handling policies cover new Google APIs.

