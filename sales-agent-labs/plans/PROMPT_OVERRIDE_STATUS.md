# Prompt Override Status (October 2025)

## Current Behaviour
- **Fixed prompts** – PresGen Core/Data rely on the hardcoded `MULTI_SLIDE_SYSTEM_PROMPT` & `SYSTEM_PROMPT` defined in `src/agent/prompts.py`. End users cannot view or tweak these instructions.
- **Hidden configuration** – The UI forms (Core `CoreForm.tsx`, Data `DataForm.tsx`) have no field exposing the current LLM instructions. Override experiments require editing Python directly.
- **Back-end expectations** – `/render` and `/data/ask` only accept narrative inputs (report text, questions). They cannot accept custom prompt strings without code changes.
- **Caching assumptions** – LLM cache keys currently depend on report text + slide count. Any future prompt overrides must participate in the cache key to avoid cross-contamination.

## Motivation for Change
1. Give power users visibility into the prompt that generates slides.
2. Allow per-run overrides without redeploying PresGen Core/Data.
3. Maintain deterministic fallbacks when no override is supplied.

## Risks / Constraints
- Changing the LLM prompts alters cached results; versioning strategy must include prompt in cache key.
- UI forms must stay approachable—prompt editing is an advanced feature, so UX should default to pre-filled templates.
- Backwards compatibility: existing API clients that omit a prompt must continue working.

## Success Criteria
- Default prompt is visible and editable in the UI; clearing the field reverts to the system default on reload.
- Submissions include optional `report_prompt` fields; when omitted or blank, the previous hardcoded behaviour persists.
- LLM cache/fallback logic respects override vs default distinctions (no stale prompt reuse).
