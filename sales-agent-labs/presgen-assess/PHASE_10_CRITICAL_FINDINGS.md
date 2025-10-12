# Sprint 4 Phase 10: Critical Findings - Presentation Prompt Issue

**Date**: 2025-10-12
**Status**: 🔴 **CRITICAL ISSUE IDENTIFIED**
**Priority**: HIGH - Blocks proper PresGen-Core integration

---

## 🚨 Critical Issue: Presentation Prompt Mismatch

### Problem Statement

The Phase 10 logging revealed that the **presentation prompt template has 30+ unresolved variables** when sent to PresGen-Core:

```
variables_found_in_template: [
  "course_record",
  "knowledge_base_context",
  "course_record.skill_name",
  "course_record.learning_objectives",
  "course_record.content_outline",
  "course_record.difficulty_level",
  "course_record.estimated_duration_minutes",
  "course_record.course_title",
  "course_record.content_outline.sections",
  "slide_count",
  ...
]

variables_available_for_substitution: ["slide_count", "question_count"]

unsubstituted_variables: [30+ variables]
```

**Result**: `⚠️ Prompt formatting failed; returning original template`

### Root Cause Analysis

The certification profile's `presentation_prompt` field contains an **LLM prompt template** (designed for GPT-4 to generate course outlines), but it's being used as a **PresGen-Core instruction prompt** (simple instructions for slide generation).

#### Evidence from Log (lines 3-163):

The prompt contains JSON structure for LLM output:
```yaml
description: >
  Generate a high-value presentation from a Recommended Course record...

inputs:
  - key: course_record
    required: true
    description: JSON object representing the Recommended Course...
  - key: knowledge_base_context
    required: true
    description: Curated course transcript or RAG-enhanced source content...

roles:
  - role: system
    prompt: |-
      You are an expert instructional designer...
      OBJECTIVE
      - Generate a presentation mapped directly to {course_record.skill_name}
      - Each section must align with {course_record.learning_objectives}
      - Use only relevant content from {knowledge_base_context}

output:
  format: json
  single_object: true
```

This is **not a simple instruction prompt** - it's a **full LLM prompt template**!

### Why This Happens

Looking at the code flow:

1. **Certification Profile**: Stores `presentation_prompt` field
2. **`generate_skill_course`**: Loads prompt from certification profile
3. **`_format_prompt_template`**: Tries to substitute variables
   - Only has: `{slide_count}`, `{question_count}`
   - Needs: `{course_record.*}`, `{knowledge_base_context}`, etc.
4. **Prompt sent to PresGen-Core**: Contains 30+ unresolved variables
5. **PresGen-Core**: Receives prompt with `{course_record.skill_name}` literal text

### Impact

**PresGen-Core receives a prompt like**:
```
Generate a presentation mapped directly to {course_record.skill_name}.
Use only relevant content from {knowledge_base_context}.
Return JSON with {slide_count} slides.
```

Instead of:
```
Generate a presentation about Data Engineering.
Use content from: [actual transcript content].
Return JSON with 10 slides.
```

**This means PresGen-Core:**
- Cannot understand what skill to teach (sees literal `{course_record.skill_name}`)
- Has no RAG context (sees literal `{knowledge_base_context}`)
- May fail or produce generic content

---

## 🔍 Analysis: Two Separate Use Cases

### Use Case 1: LLM Course Outline Generation (Phase 10 Task 3.1)
**Purpose**: Use LLM to regenerate/refine course outlines
**When**: `PRESGEN_REGENERATE_COURSE_OUTLINE=true`
**Input**: Recommended course + RAG context + gap analysis
**Process**: `LLMService.generate_refined_course_outline()`
**Variables Needed**: `{course_record.*}`, `{knowledge_base_context}`, `{slide_count}`
**Substitution**: Done in `_build_refined_outline_prompt()` ✅
**Output**: Refined course outline JSON

### Use Case 2: PresGen-Core Slide Generation (Current Issue)
**Purpose**: Instruct PresGen-Core how to generate slides
**When**: Every course generation (always runs)
**Input**: Slide plans from recommended course
**Process**: `_create_public_presentation()` → PresGen-Core
**Variables Needed**: `{slide_count}` (maybe `{skill_name}` for context)
**Substitution**: Done in `_format_prompt_template()` ⚠️ **INCOMPLETE**
**Output**: Google Slides presentation → narrated video

### The Mismatch

**The certification profile's `presentation_prompt` is a Use Case 1 prompt (LLM template), but it's being used for Use Case 2 (PresGen-Core instructions)!**

---

## 💡 Solution Options

### Option 1: Separate Prompts (RECOMMENDED)

**Create two distinct prompt fields in `CertificationProfile`:**

```python
class CertificationProfile(Base):
    # Existing fields...

    # Option 1A: Add new field for PresGen-Core instructions
    presentation_prompt = Column(Text)  # Existing: LLM outline generation
    presgen_instructions = Column(Text)  # NEW: PresGen-Core slide generation
```

**Then**:
- `presentation_prompt` → Used by `generate_refined_course_outline()` (LLM)
- `presgen_instructions` → Used by `_format_prompt_template()` (PresGen-Core)

**Benefits**:
- Clean separation of concerns
- Each prompt optimized for its use case
- No variable collision issues

**Migration**:
```sql
-- Add new column
ALTER TABLE certification_profiles ADD COLUMN presgen_instructions TEXT;

-- Copy existing prompts (temporary)
UPDATE certification_profiles SET presgen_instructions = presentation_prompt;

-- Then manually simplify presgen_instructions to remove LLM-specific content
```

---

### Option 2: Substitute All Variables (COMPLEX)

**Modify `_format_prompt_template()` to substitute all course variables:**

```python
def _format_prompt_template(template: Optional[str]) -> Optional[str]:
    if not template:
        return template

    # Collect RAG context (expensive!)
    rag_context = await _get_rag_context_for_skill(skill_course)

    values = _SafeDict({
        "slide_count": requested_slide_count,
        "question_count": question_count,
        # NEW: Course variables
        "course_record.skill_name": skill_course.skill_name,
        "course_record.course_title": skill_course.course_title,
        "course_record.learning_objectives": json.dumps(skill_course.learning_objectives),
        "course_record.content_outline": json.dumps(skill_course.content_outline),
        "course_record.difficulty_level": skill_course.difficulty_level,
        "course_record.estimated_duration_minutes": skill_course.estimated_duration_minutes,
        # NEW: RAG context
        "knowledge_base_context": rag_context,  # Could be 10KB+ of text!
    })

    return template.format_map(values)
```

**Issues**:
- Makes function async (complex refactor)
- RAG retrieval is slow (~1-2 seconds)
- Large RAG context in prompt may confuse PresGen-Core
- Still using LLM prompt template for PresGen-Core (design smell)

---

### Option 3: Simplify Prompt Template (QUICK FIX)

**Update the certification profile to use a simpler prompt:**

```yaml
# OLD (LLM template - too complex for PresGen-Core)
description: >
  Generate a high-value presentation from a Recommended Course record...
inputs:
  - key: course_record
  - key: knowledge_base_context
roles:
  - role: system
    prompt: |-
      You are an expert instructional designer...
      Use {course_record.skill_name} and {knowledge_base_context}...

# NEW (Simple instructions for PresGen-Core)
Generate a professional training presentation with {slide_count} slides.
Focus on clarity, practical examples, and learner engagement.
Each slide should have 3-5 bullet points and instructor notes.
Narration should be ≤ 75 seconds per slide.
```

**Benefits**:
- Immediate fix (no code changes)
- Removes variable dependency
- Simpler prompt likely works better with PresGen-Core

**Drawbacks**:
- Loses rich context from LLM template
- May produce less customized presentations

---

### Option 4: Use Default Prompt (TEMPORARY WORKAROUND)

**Set `presentation_prompt` to NULL in certification profile:**

```python
# In _format_prompt_template()
if not template:
    # Return a sensible default
    return f"Generate a {requested_slide_count}-slide presentation on the given topic."
```

**Use this while deciding on Option 1, 2, or 3.**

---

## 📋 Recommendations

### Immediate Action (Today)

**Option 4 (Temporary Workaround)**:
1. Set `presentation_prompt = NULL` for test certification profile
2. Add default prompt in `_format_prompt_template()`
3. Test course generation - should work without variable errors
4. Log output will show `substitution_complete: true`

### Short Term (This Week)

**Option 1 (Separate Prompts)** - Implement properly:
1. Add `presgen_instructions` column to `certification_profiles` table
2. Create migration: `alembic revision -m "add_presgen_instructions"`
3. Update `_format_prompt_template()` to use `presgen_instructions` instead of `presentation_prompt`
4. Keep `presentation_prompt` for future LLM outline regeneration feature
5. Update UI to manage both prompts separately

### Medium Term (Next Sprint)

**Clarify prompt architecture**:
1. Document what each prompt is for
2. Provide example prompts for each use case
3. Add validation to detect LLM templates vs. instruction prompts
4. Consider templating system (Jinja2) for complex variable substitution

---

## 🧪 Testing Plan

### Test Case 1: NULL Prompt (Workaround)
```python
# Set presentation_prompt = NULL
cert_profile.presentation_prompt = None

# Expected log output:
{
  "event": "presentation_prompt_variable_check",
  "variables_found_in_template": [],  # No variables in default prompt
  "variables_available_for_substitution": ["slide_count"],
  "unsubstituted_variables": []
}

{
  "event": "presentation_prompt_after_substitution",
  "remaining_unresolved_variables": [],
  "substitution_complete": true  # ✅ SUCCESS
}
```

### Test Case 2: Simplified Prompt (Option 3)
```yaml
# Simple prompt template
prompt: "Generate a {slide_count}-slide presentation. Focus on clarity and examples."

# Expected log output:
{
  "variables_found_in_template": ["slide_count"],
  "variables_available_for_substitution": ["slide_count"],
  "unsubstituted_variables": []
}

{
  "remaining_unresolved_variables": [],
  "substitution_complete": true  # ✅ SUCCESS
}
```

### Test Case 3: Separate Prompts (Option 1)
```python
# Use new presgen_instructions field
presgen_instructions: str = "Create professional slides with {slide_count} slides."
presentation_prompt: str = "[Complex LLM template]"  # Not used by PresGen-Core

# Code uses presgen_instructions for PresGen-Core
# Code uses presentation_prompt for LLM outline regeneration

# Expected: Both use cases work correctly ✅
```

---

## 📊 Decision Matrix

| Option | Complexity | Time | Correctness | Maintenance |
|--------|-----------|------|-------------|-------------|
| **1. Separate Prompts** | Medium | 2-3 hours | ✅ Best | ✅ Clean |
| **2. Substitute All** | High | 4-6 hours | ⚠️ Complex | ❌ Brittle |
| **3. Simplify Prompt** | Low | 10 minutes | ⚠️ Loses context | ⚠️ Manual update |
| **4. NULL/Default** | Low | 5 minutes | ⚠️ Temporary | ⚠️ Not production-ready |

**Recommendation**: **Option 4 → Option 1**
1. Implement Option 4 today (unblock testing)
2. Implement Option 1 this week (proper fix)
3. Document prompts for future maintainers

---

## 🔗 Related Files

- **Code**: [src/service/api/v1/endpoints/workflows.py:2653-2710](src/service/api/v1/endpoints/workflows.py#L2653-2710)
- **Model**: [src/models/certification.py](src/models/certification.py) - `CertificationProfile.presentation_prompt`
- **LLM Service**: [src/services/llm_service.py:622-718](src/services/llm_service.py#L622-718) - Correct variable substitution
- **Logs**: [logs/course_generation.log](logs/course_generation.log) - Shows unresolved variables

---

## 📝 Next Steps

1. ✅ Document findings (this document)
2. ⏳ Choose solution option (recommend Option 4 → Option 1)
3. ⏳ Implement chosen solution
4. ⏳ Test with course generation
5. ⏳ Verify logs show `substitution_complete: true`
6. ⏳ Update Phase 10 status document

---

**Document Status**: Analysis Complete
**Last Updated**: 2025-10-12
**Decision Required**: Choose solution option (recommend Option 4 → Option 1)
**Owner**: Development Team
