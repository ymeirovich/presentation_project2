# Sprint 4 Phase 11: RAG Context Enhancement & Presentation Quality Improvement

**Date:** October 14, 2025
**Status:** Planning Complete - Ready for Implementation
**Priority:** High - Addresses core presentation quality issues

---

## Executive Summary

Phase 11 addresses the root cause of low-quality presentation generation: **unstructured RAG context delivery** to small language models. The current system retrieves relevant content but delivers it as a flat text blob, causing gpt-4o-mini to produce generic, unfocused slides despite having access to quality source material.

**Problem Statement:**
- ✅ RAG retrieval works correctly (returns relevant chunks)
- ❌ Context formatting fails (flat concatenation without structure)
- ❌ LLM comprehension fails (60K token blob exceeds effective attention)
- ❌ Output quality suffers (40% relevance, generic content)

**Solution Strategy:**
- **Tier 1 (Immediate):** Prompt enhancement + configuration (zero code changes)
- **Tier 2 (Short-term):** RAG context restructuring (2 files, 80 lines)
- **Tier 3 (Optional):** Model upgrade path (configuration-driven)
- **Tier 4 (Future):** Domain-aware ingestion (200 lines, significant quality boost)

**Expected Outcomes:**
- Tier 1: 40% → 60% quality (+50% improvement)
- Tier 2: 60% → 75% quality (+25% improvement)
- Tier 3: 75% → 85% quality (+13% improvement)
- Tier 4: 85% → 90%+ quality (+6% improvement)

---

## Table of Contents

1. [Problem Analysis](#problem-analysis)
2. [Architecture Overview](#architecture-overview)
3. [Tier 1: Prompt Enhancement](#tier-1-prompt-enhancement-immediate-win)
4. [Tier 2: RAG Context Structuring](#tier-2-rag-context-structuring-high-impact)
5. [Tier 3: Model Upgrade Path](#tier-3-model-upgrade-path-optional)
6. [Tier 4: Domain-Aware Ingestion](#tier-4-domain-aware-ingestion-future-enhancement)
7. [Implementation Checklist](#implementation-checklist)
8. [Testing Strategy](#testing-strategy)
9. [Key Learnings & Recommendations](#key-learnings--recommendations)
10. [Cost-Benefit Analysis](#cost-benefit-analysis)

---

## Problem Analysis

### Current RAG Pipeline Flow

```
User Assessment → Gap Analysis → Recommended Courses
                                        ↓
                            RecommendedCourse {
                                skill_name: "Data Engineering",
                                exam_domain: "Data Engineering",
                                learning_objectives: [
                                    "Understand core Data Engineering principles",
                                    "Apply ETL workflows with AWS Glue",
                                    "Design data pipelines for ML"
                                ]
                            }
                                        ↓
    workflows.py:2700-2740: _format_prompt_template()
                                        ↓
    Use learning_objectives as RAG queries (top 3)
                                        ↓
    base.py:128-174: retrieve_context_for_assessment()
        - Query: "Understand core Data Engineering principles"
        - certification_id: "aws-ml-specialty"
        - k=6 (3 exam guide + 3 transcript chunks)
        - balance_sources=True
                                        ↓
    embeddings.py:148-190: retrieve_context()
        - Semantic search in exam_guides_collection
        - Semantic search in transcripts_collection
        - Sort by relevance (cosine distance)
        - Return top-k chunks
                                        ↓
    base.py:186-211: _format_combined_context()
        ❌ PROBLEM: Flat concatenation without structure

        Output format:
        """
        === OFFICIAL EXAM GUIDE CONTENT ===
        [Source 1: Exam Guide: AWS ML Specialty Exam Guide (Section 12, Page 3)]
        Choose appropriate AWS storage solutions for ML workloads...

        [Source 2: Exam Guide: AWS ML Specialty Exam Guide (Section 15, Page 4)]
        Understand data transformation requirements...

        === COURSE TRANSCRIPT CONTENT ===
        [Source 1: Course Transcript: AWS ML Module 3 (Segment 42)]
        Amazon S3 provides eleven nines of durability for ML data lakes...

        [Source 2: Course Transcript: AWS ML Module 5 (Segment 78)]
        AWS Glue is a serverless ETL service for data preparation...
        """

        Total: ~15K-60K chars of flat text
                                        ↓
    workflows.py:2826-2844: values["knowledge_base_context"] = knowledge_base_context
                                        ↓
    Substitute into CLEANED_CERTIFICATION_PROMPT.md
                                        ↓
    Send to gpt-4o-mini (128K context window)
        ❌ PROBLEM: 60K+ tokens exceed effective attention budget (~16K tokens)
        ❌ RESULT: Model ignores 80% of middle content
                                        ↓
    Generate presentation outline (generic, low-quality)
```

### Root Causes Identified

#### 1. Unstructured Context Delivery
**Current format:**
```
=== OFFICIAL EXAM GUIDE CONTENT ===
[Source 1: citation]
{raw_text_800_words}
[Source 2: citation]
{raw_text_800_words}
=== COURSE TRANSCRIPT CONTENT ===
[Source 1: citation]
{raw_text_800_words}
...
```

**Why it fails:**
- No semantic boundaries between chunks
- No domain/topic metadata for filtering
- No relevance scores visible to LLM
- Raw text without compression or summarization
- Model can't identify which chunks apply to current slide

#### 2. Token Budget Overflow
**Context window vs Effective attention:**
```
gpt-4o-mini specs:
- Context window: 128K tokens (~500K chars)
- Effective attention: ~16K tokens (~64K chars) for middle content
- Attention pattern: Strong on first 10% and last 10%, weak on middle 80%

Current input:
- Prompt: ~2K tokens
- Structured course data: ~3K tokens
- RAG context: ~15K-60K tokens ← PROBLEM
- Total: ~20K-65K tokens

Result: Middle 80% of RAG context gets effectively ignored
```

#### 3. Weak Prompt Directives
**Current prompt (CLEANED_CERTIFICATION_PROMPT.md):**
- Focus: "You are an AI instructional designer..." (role description)
- Structure: OUTPUT FORMAT, slide architecture, JSON schema
- Missing: Quality constraints, evaluation criteria, grounding requirements

**Why it fails:**
- Small models optimize for format compliance, not content quality
- No explicit instruction to verify facts against context
- No penalty for fabricating content
- No relevance scoring mechanism

#### 4. Model Capacity Limitations
**gpt-4o-mini characteristics:**
```
Strengths:
- Fast (250ms response time)
- Cheap ($0.15 input / $0.60 output per 1M tokens)
- Good at following JSON schemas
- Handles simple reasoning tasks

Weaknesses:
- Poor long-context reasoning (effective window ~16K tokens)
- Weak semantic filtering (can't isolate relevant chunks from blob)
- Tendency toward generic responses
- Limited ability to synthesize across multiple sources
```

---

## Architecture Overview

### Proposed Solution: Multi-Tier Enhancement Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ Tier 1: Prompt Enhancement (Zero Code Changes)                 │
│ - Enhanced system role with quality rubric                      │
│ - Explicit grounding requirements                               │
│ - Self-evaluation checklist                                     │
│ Expected: 40% → 60% quality (+50% improvement)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tier 2: RAG Context Structuring (2 files, ~80 lines)           │
│ - Domain/topic tags on each chunk                              │
│ - Relevance scores exposed to LLM                              │
│ - Chunk compression (800 words → 150 words)                    │
│ - Semantic boundaries with markdown headers                     │
│ Expected: 60% → 75% quality (+25% improvement)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tier 3: Model Upgrade Path (Configuration-Driven)              │
│ - Option A: gpt-4o ($0.068/course, 85% quality)               │
│ - Option B: claude-3.5-haiku ($0.008/course, 75% quality)     │
│ - Fallback: gpt-4o-mini ($0.004/course, 60% quality)          │
│ Expected: 75% → 85% quality (+13% improvement)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tier 4: Domain-Aware Ingestion (Future, ~200 lines)            │
│ - Classify chunks by domain/topic/skill at upload              │
│ - Store taxonomy metadata in ChromaDB                          │
│ - Retrieve with hierarchical filters                           │
│ Expected: 85% → 90%+ quality (+6% improvement)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Prompt Enhancement (Immediate Win)

**Impact:** High
**Effort:** Low (1-2 hours)
**Files Changed:** 1 (CLEANED_CERTIFICATION_PROMPT.md)
**Code Changes:** 0
**Cost:** $0

### Changes Required

#### 1. Update CLEANED_CERTIFICATION_PROMPT.md

**File:** `presgen-assess/CLEANED_CERTIFICATION_PROMPT.md`

```markdown
# Enhanced Certification Prompt Template (Tier 1)

## SYSTEM ROLE (Enhanced)

You are an **AI Certification Course Architect** specializing in evidence-based instructional design for technical certification preparation.

### Primary Directive

Create slide-ready learning content that meets these **mandatory quality standards**:

1. **Grounding Requirement** - Every technical statement MUST cite or paraphrase content from the provided {knowledge_base_context}. If context is insufficient for a learning objective, output: "_[Insufficient context - requires additional source material]_" rather than fabricating content.

2. **Domain Alignment** - All content must directly relate to {exam_domain} and {skill_name}. Filter out tangential information even if present in context.

3. **Technical Accuracy** - Maintain certification exam-level precision. Use exact terminology from the exam guide and transcript sources. Avoid oversimplification or generic analogies not found in sources.

4. **Appropriate Depth** - Calibrate explanation depth to {difficulty_level} using Bloom's taxonomy:
   - **Beginner**: Define, list, describe (Knowledge/Comprehension)
   - **Intermediate**: Apply, demonstrate, interpret (Application/Analysis)
   - **Advanced**: Evaluate, design, optimize (Synthesis/Evaluation)

### Context Structure Interpretation

The {knowledge_base_context} variable contains RAG-retrieved passages formatted as:

```
### Domain: [Domain Name] | Source: [exam_guide|transcript] | Relevance: [0.00-1.00]
**Learning Objective**: [Specific objective this chunk addresses]
**Task**: [Exam guide task reference, if applicable]
{chunk_text}
---
```

**How to use this structure:**
- Prioritize chunks with **Relevance ≥ 0.75** (high semantic match to learning objectives)
- Weight **transcript** sources for explanations and examples
- Weight **exam_guide** sources for task definitions and scope
- Match chunk **Domain** tags to current section's focus area
- Cross-reference **Learning Objective** tags with {learning_objectives} array

### Quality Enforcement Rules

**MUST DO:**
- ✅ Cite specific sources for technical claims (e.g., "As noted in the exam guide, Task 1.1...")
- ✅ Use examples and terminology found in transcript context
- ✅ Align each slide to specific learning objectives from {learning_objectives}
- ✅ Maintain factual consistency across slides (no contradictions)
- ✅ Keep narration ≤ 75 seconds per slide (~150 words)

**MUST NOT DO:**
- ❌ Fabricate AWS service names, features, or best practices not in context
- ❌ Include generic definitions or analogies not grounded in sources
- ❌ Copy-paste raw context text (synthesize and paraphrase)
- ❌ Drift to adjacent topics outside {exam_domain} scope
- ❌ Use placeholder content like "To be determined" or "Example needed"

---

## INTERNAL QUALITY CHECKLIST

Before generating final JSON output, mentally verify:

1. ✅ **Grounding Check**: Each slide's key points map to specific chunks in {knowledge_base_context}
2. ✅ **Relevance Check**: Content focuses on {skill_name} and {exam_domain}, not tangential topics
3. ✅ **Depth Check**: Explanation complexity matches {difficulty_level} expectations
4. ✅ **Coverage Check**: All items in {learning_objectives} are addressed across slides
5. ✅ **Consistency Check**: No contradictions between slides or with source material
6. ✅ **Completeness Check**: Every section in {content_outline_sections} has substantive content

If any check fails, revise content before output.

---

## OBJECTIVE

Generate a course-specific educational presentation that:
- Maps precisely to {skill_name} and {exam_domain}
- Aligns all slides to {learning_objectives} and {content_outline_sections}
- Uses **only** relevant excerpts from {knowledge_base_context} with Relevance ≥ 0.75
- Matches {difficulty_level} using Bloom's taxonomy verbs
- Fits within {estimated_duration_minutes} total duration
- Ensures each slide's narration script is ≤ 75 seconds (~150 words)

---

## DESIGN FRAMEWORK

### 1. Content Filtering & Mapping (ENHANCED)

Use this **strict hierarchy** for selecting and structuring content:

**Level 1: Domain Filter**
- Extract chunks from {knowledge_base_context} where Domain tag matches {exam_domain}
- Example: If {exam_domain} = "Data Engineering", only use chunks tagged "Domain: Data Engineering"

**Level 2: Objective Filter**
- For each item in {learning_objectives}, find chunks where Learning Objective tag matches
- Example: Objective "Apply ETL workflows" → Use chunks tagged with that objective

**Level 3: Relevance Filter**
- Among matched chunks, prioritize those with Relevance ≥ 0.75
- If <3 high-relevance chunks available, note gap: "_[Limited context for this objective]_"

**Level 4: Source Balance**
- For explanatory content: Weight transcript chunks 70%, exam guide 30%
- For task definitions: Weight exam guide chunks 70%, transcript 30%
- For examples: Use transcript chunks exclusively

**Level 5: Section Alignment**
- Map chunks to {content_outline_sections} by topic similarity
- Allocate slides proportionally to section duration_minutes
- Ensure each section has ≥2 distinct source chunks

### 2. Slide Count Allocation (UNCHANGED)

Distribute slides across sections based on their duration:
- Review {content_outline_sections} to see each section's duration_minutes
- Allocate slides proportionally to duration
- Total slides should be approximately {slide_count}
- Each section: minimum 2 slides, maximum 10 slides

### 3. Slide Architecture (ENHANCED)

Each section from {content_outline_sections} becomes a presentation section:

| Section | Content Focus | Typical Slides | Source Emphasis |
|---------|---------------|----------------|-----------------|
| Introduction | Context, objectives, key terms | 2–3 slides | Exam guide (task scope) |
| Core Concepts | Conceptual explanations, frameworks | 5–7 slides | Transcript (explanations) |
| Practical Applications | Hands-on examples, workflows | 4–6 slides | Transcript (examples) |
| Review and Practice | Summary, sample question, recap | 2–3 slides | Mixed sources |

Each slide contains:
- **title** — Concise and descriptive (≤10 words)
- **bullets** — 3–5 short learning points (≤12 words each)
- **instructor_notes** — Narration script ≤75 seconds (~150 words), synthesizing 2-3 relevant chunks

**Slide Construction Template:**
```
Title: [Concept from high-relevance chunk]
Bullets:
  - [Key point 1 from chunk A, Relevance 0.92]
  - [Key point 2 from chunk A, rephrased]
  - [Key point 3 from chunk B, Relevance 0.85]
  - [Example from chunk C, Relevance 0.78]

Instructor Notes:
"As covered in [source citation], [synthesis of chunk A + chunk B].
For example, [paraphrase of chunk C example].
This aligns with [exam task reference from chunk metadata]..."
```

### 4. Difficulty Calibration (ENHANCED)

Adjust tone and depth to {difficulty_level} using Bloom's taxonomy:

| Level | Cognitive Verbs | Content Approach | Example |
|-------|----------------|------------------|---------|
| **Beginner** | Define, list, describe, identify | Foundational concepts with analogies | "Define what S3 is" |
| **Intermediate** | Apply, demonstrate, interpret, compare | Workflows and trade-offs | "Demonstrate S3 bucket configuration for ML" |
| **Advanced** | Analyze, evaluate, design, optimize | Architecture decisions and edge cases | "Evaluate S3 vs EFS for real-time inference" |

**Implementation:**
- Beginner: Use chunks tagged with foundational tasks (Task X.1 intro tasks)
- Intermediate: Use chunks with procedural content and comparisons
- Advanced: Use chunks discussing optimization, troubleshooting, architecture

### 5. Alignment with Duration (UNCHANGED)

Total presentation length (spoken) should match {estimated_duration_minutes} ±10%.
Each slide should average ~1.5 minutes total learning time (narration + visual review).

---

## OUTPUT REQUIREMENTS (UNCHANGED)

[Keep existing JSON schema specification]

---

## EXAMPLE OUTPUT STRUCTURE (ENHANCED)

```json
{
  "presentation_type": "course_remediation",
  "skill_name": "Data Engineering",
  "course_title": "Data Engineering Foundations for ML",
  "difficulty_level": "intermediate",
  "estimated_duration_minutes": 30,
  "slide_count": 12,
  "sections": [
    {
      "title": "Data Storage Solutions for ML",
      "slides": [
        {
          "title": "Amazon S3 as ML Data Lake Foundation",
          "bullets": [
            "Eleven nines (99.999999999%) durability for ML datasets",
            "Automatic scaling eliminates capacity planning",
            "Native integration with SageMaker, Glue, and Athena",
            "Cost-effective storage tiers for different access patterns"
          ],
          "instructor_notes": "As noted in the AWS ML Specialty exam guide Task 1.1, choosing appropriate storage is foundational. Amazon S3 serves as the primary data lake for most ML workloads due to its exceptional durability and seamless integration with AWS ML services. The transcript from Module 3 emphasizes three key considerations: First, use S3 buckets organized by environment and data stage. Second, implement bucket policies for access control and versioning for data lineage. Third, leverage S3 Select for efficient querying without moving data. This architecture supports both batch training workflows and streaming inference pipelines, as we'll explore in the next slide."
        }
      ]
    }
  ],
  "metadata": {
    "rag_context_chunks_used": 12,
    "high_relevance_chunks": 9,
    "low_context_warnings": 0,
    "source_distribution": {
      "exam_guide": 4,
      "transcript": 8
    }
  }
}
```

---

## SUMMARY OF BEHAVIOR

When executed, this enhanced prompt instructs the LLM to:

1. ✅ **Strict grounding**: Only use content from {knowledge_base_context}, citing sources
2. ✅ **Semantic filtering**: Prioritize chunks with Domain tag matching {exam_domain} and Relevance ≥ 0.75
3. ✅ **Quality self-evaluation**: Run internal checklist before generating output
4. ✅ **Source-aware composition**: Balance exam guide (scope) vs transcript (depth) appropriately
5. ✅ **Bloom's-aligned depth**: Calibrate cognitive complexity to {difficulty_level}
6. ✅ **Gap transparency**: Explicitly note when context is insufficient rather than fabricating

---

## USAGE NOTES

- All variable placeholders will be substituted with actual values before sending to LLM
- {knowledge_base_context} now contains **structured, tagged chunks** with:
  - Domain/topic metadata
  - Relevance scores
  - Learning objective alignment
  - Source type (exam_guide vs transcript)
- {content_outline_sections} is provided as JSON array with section titles and durations
- {learning_objectives} is provided as JSON array of learning goal strings
- Variable substitution is handled automatically by the workflow engine

---

## VERSION HISTORY

- **v1.0** (Oct 13, 2025): Initial cleaned certification prompt
- **v2.0** (Oct 14, 2025): **Tier 1 Enhancement** - Added quality rubric, grounding requirements, and structured context interpretation
```

#### 2. Add Environment Configuration

**File:** `presgen-assess/.env`

```bash
# ============================================
# RAG Context Configuration (Tier 1)
# ============================================

# Retrieval Parameters (Universal - applies to all learning domains)
RAG_RETRIEVAL_K_PER_SECTION=3          # Top-k chunks per learning objective (default: 3)
RAG_MAX_TOTAL_CHUNKS=15                # Max total chunks to prevent token overflow (default: 15)
RAG_RELEVANCE_THRESHOLD=0.75           # Minimum relevance score for chunk inclusion (default: 0.75)

# Context Formatting (Tier 2 preparation)
RAG_ENABLE_DOMAIN_TAGS=false           # Add domain/topic tags to chunks (Tier 2 feature)
RAG_INCLUDE_RELEVANCE_SCORES=false     # Show relevance scores in context (Tier 2 feature)
RAG_CHUNK_COMPRESSION=false            # Summarize chunks before insertion (future)

# Source Balancing
RAG_TRANSCRIPT_WEIGHT=0.6              # Weight for transcript sources (0.0-1.0, default: 0.6)
RAG_EXAM_GUIDE_WEIGHT=0.4              # Weight for exam guide sources (0.0-1.0, default: 0.4)
```

**Note:** Tier 1 environment variables are **declarative only** - they document intended behavior but don't require code changes yet. They prepare the configuration layer for Tier 2 implementation.

### Testing Tier 1

**Test Case:** Generate presentation for existing "Data Engineering" recommended course

```bash
# Prerequisites
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess

# 1. Verify prompt updated in database
python3 << 'EOF'
import asyncio
from sqlalchemy import select
from src.service.database import get_db_session  # or: from src.service.database import AsyncSessionLocal
from src.models.certification import CertificationProfile

async def check_prompt():
    async with get_db_session() as session:
        result = await session.execute(
            select(CertificationProfile).where(
                CertificationProfile.collection_name == "aws-ml-specialty"
            )
        )
        cert = result.scalar_one_or_none()
        if cert and cert.presentation_prompt:
            print("✅ Custom prompt found, length:", len(cert.presentation_prompt))
            print("First 200 chars:", cert.presentation_prompt[:200])
        else:
            print("⚠️ No custom prompt - will use default")

asyncio.run(check_prompt())
EOF

# 2. Generate test presentation
# Use existing workflow or create new one
# Monitor logs for quality improvements
tail -f logs/workflow_*.log | grep -E "(event|quality|relevance|grounding)"

# 3. Compare before/after
# - Count generic phrases ("various", "several", "many")
# - Check citation density (references to sources)
# - Verify domain-specific terminology
# - Assess factual accuracy against transcript
```

**Expected Improvements:**
- ❌ Before: "There are several important AWS services for data engineering..."
- ✅ After: "As noted in exam guide Task 1.1, S3, Glue, and Athena form the core data engineering stack..."

---

## Tier 2: RAG Context Structuring (High Impact)

**Impact:** Very High
**Effort:** Medium (4-6 hours)
**Files Changed:** 2 (base.py, embeddings.py)
**Lines Added:** ~80
**Cost:** $0

### Architecture Changes

#### Before (Current):
```
RAG Retrieval → Flat Concatenation → {knowledge_base_context}
                                              ↓
                            "=== EXAM GUIDE ===\n[Source 1]...\n=== TRANSCRIPT ===\n[Source 2]..."
```

#### After (Tier 2):
```
RAG Retrieval → Structured Formatting → {knowledge_base_context}
                                              ↓
                    "### Domain: X | Source: Y | Relevance: 0.92\n**Objective**: Z\n{text}\n---"
```

### Code Changes

#### 1. Update base.py:_format_combined_context()

**File:** `presgen-assess/src/knowledge/base.py`

**Location:** Lines 186-211

```python
def _format_combined_context(self, context_results: List[Dict]) -> str:
    """Format retrieved context into a coherent string for LLM consumption.

    Tier 2 Enhancement: Add semantic structure with domain tags, relevance scores,
    and learning objective alignment for better LLM comprehension.
    """
    if not context_results:
        return ""

    from src.common.config import settings

    # Check if Tier 2 features are enabled
    enable_domain_tags = getattr(settings, 'rag_enable_domain_tags', False)
    include_relevance = getattr(settings, 'rag_include_relevance_scores', False)
    relevance_threshold = getattr(settings, 'rag_relevance_threshold', 0.75)

    formatted_sections = []

    # Group by source type for better organization
    exam_guides = [r for r in context_results if r["source_type"] == "exam_guide"]
    transcripts = [r for r in context_results if r["source_type"] == "transcript"]

    def format_chunk(result: Dict, index: int, source_type: str) -> str:
        """Format a single chunk with Tier 2 structure."""
        # Calculate relevance score (inverse of distance)
        # ChromaDB uses cosine distance (0 = identical, 2 = opposite)
        distance = result.get("distance", 1.0)
        relevance = max(0.0, min(1.0, 1.0 - (distance / 2.0)))  # Normalize to 0-1

        # Skip low-relevance chunks if threshold enabled
        if relevance < relevance_threshold:
            return ""

        metadata = result.get("metadata", {})
        content = result["content"]

        # Extract domain/topic from metadata (if available)
        domain = metadata.get("domain", metadata.get("exam_domain", "General"))
        topic = metadata.get("topic", "")
        learning_objective = metadata.get("learning_objective", "")
        task_id = metadata.get("exam_guide_task", "")

        # Build structured header
        if enable_domain_tags:
            header_parts = [f"### Domain: {domain}"]
            header_parts.append(f"Source: {source_type}")

            if include_relevance:
                header_parts.append(f"Relevance: {relevance:.2f}")

            header = " | ".join(header_parts)

            # Add metadata lines
            metadata_lines = []
            if learning_objective:
                metadata_lines.append(f"**Learning Objective**: {learning_objective}")
            if topic:
                metadata_lines.append(f"**Topic**: {topic}")
            if task_id:
                metadata_lines.append(f"**Exam Task**: {task_id}")

            # Add citation
            citation = result.get("citation", f"{source_type.title()} Source {index}")
            metadata_lines.append(f"**Citation**: {citation}")

            # Combine into structured block
            structured_block = [
                header,
                *metadata_lines,
                "",  # Blank line before content
                content,
                "---"  # Separator
            ]
            return "\n".join(structured_block)
        else:
            # Fallback to original format (Tier 1)
            citation = result.get("citation", f"{source_type.title()} Source {index}")
            return f"\n[Source {index}: {citation}]\n{content}"

    # Format exam guide content
    if exam_guides:
        if enable_domain_tags:
            formatted_sections.append("## OFFICIAL EXAM GUIDE CONTENT\n")
        else:
            formatted_sections.append("=== OFFICIAL EXAM GUIDE CONTENT ===")

        for i, result in enumerate(exam_guides[:3], 1):  # Limit to top 3
            chunk_formatted = format_chunk(result, i, "exam_guide")
            if chunk_formatted:  # Only add if passed relevance threshold
                formatted_sections.append(chunk_formatted)

    # Format transcript content
    if transcripts:
        if enable_domain_tags:
            formatted_sections.append("\n## COURSE TRANSCRIPT CONTENT\n")
        else:
            formatted_sections.append("\n\n=== COURSE TRANSCRIPT CONTENT ===")

        for i, result in enumerate(transcripts[:3], 1):  # Limit to top 3
            chunk_formatted = format_chunk(result, i, "transcript")
            if chunk_formatted:
                formatted_sections.append(chunk_formatted)

    return "\n".join(formatted_sections)
```

#### 2. Update embeddings.py:_generate_citation()

**File:** `presgen-assess/src/knowledge/embeddings.py`

**Location:** Lines 200-211

```python
def _generate_citation(self, metadata: Dict, source_type: str) -> str:
    """Generate a proper citation for source attribution.

    Tier 2 Enhancement: Include domain/topic information in citations
    for better context tracking.
    """
    document_name = metadata.get("document_name", "Unknown Document")
    chunk_index = metadata.get("chunk_index", 0)
    page_number = metadata.get("source_page", "Unknown")

    # Tier 2: Add domain/topic if available
    domain = metadata.get("domain", metadata.get("exam_domain"))
    topic = metadata.get("topic")

    if source_type == "exam_guide":
        citation = f"Exam Guide: {document_name} (Section {chunk_index}, Page {page_number})"
        if domain:
            citation += f" [Domain: {domain}]"
        return citation

    elif source_type == "transcript":
        citation = f"Course Transcript: {document_name} (Segment {chunk_index})"
        if domain and topic:
            citation += f" [Domain: {domain}, Topic: {topic}]"
        elif domain:
            citation += f" [Domain: {domain}]"
        return citation

    else:
        return f"Source: {document_name} (Chunk {chunk_index})"
```

#### 3. Update config.py with Tier 2 settings

**File:** `presgen-assess/src/common/config.py`

**Location:** Add after line 94 (rag_source_citation_required)

```python
    # RAG Context Configuration (Tier 2)
    rag_retrieval_k_per_section: int = int(os.getenv("RAG_RETRIEVAL_K_PER_SECTION", "3"))
    rag_max_total_chunks: int = int(os.getenv("RAG_MAX_TOTAL_CHUNKS", "15"))
    rag_relevance_threshold: float = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.75"))

    rag_enable_domain_tags: bool = os.getenv("RAG_ENABLE_DOMAIN_TAGS", "false").lower() == "true"
    rag_include_relevance_scores: bool = os.getenv("RAG_INCLUDE_RELEVANCE_SCORES", "false").lower() == "true"
    rag_chunk_compression: bool = os.getenv("RAG_CHUNK_COMPRESSION", "false").lower() == "true"

    rag_transcript_weight: float = float(os.getenv("RAG_TRANSCRIPT_WEIGHT", "0.6"))
    rag_exam_guide_weight: float = float(os.getenv("RAG_EXAM_GUIDE_WEIGHT", "0.4"))
```

#### 4. Update workflows.py to respect new limits

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`

**Location:** Lines 2715-2722 (inside _format_prompt_template)

```python
            # Tier 2: Respect configured chunk limits
            max_chunks = getattr(settings, 'rag_max_total_chunks', 15)
            k_per_query = getattr(settings, 'rag_retrieval_k_per_section', 3)

            # Adjust k based on number of queries to stay under max_chunks
            num_queries = min(len(queries), 3)
            k_adjusted = min(k_per_query, max_chunks // num_queries) if num_queries > 0 else k_per_query

            logger.info(f"🔍 Starting RAG retrieval with certification_id='{rag_certification_id}', queries={queries[:3]}, k={k_adjusted}")

            for query in queries[:3]:  # Top 3 learning objectives
                try:
                    logger.info(f"🔍 Calling RAG for query: '{query}'")
                    result = await rag_kb.retrieve_context_for_assessment(
                        query=query,
                        certification_id=rag_certification_id,
                        k=k_adjusted,  # Use adjusted k
                        balance_sources=True
                    )
```

### Enable Tier 2

**Update .env:**

```bash
# Enable Tier 2 features
RAG_ENABLE_DOMAIN_TAGS=true
RAG_INCLUDE_RELEVANCE_SCORES=true
RAG_RELEVANCE_THRESHOLD=0.75
RAG_MAX_TOTAL_CHUNKS=15
RAG_RETRIEVAL_K_PER_SECTION=5
```

### Testing Tier 2

```bash
# 1. Restart application to load new config
# (if using Docker: docker-compose restart presgen-assess)

# 2. Generate presentation with Tier 2 enabled
# Check logs for structured context

# 3. Verify context format in logs
tail -f logs/workflow_*.log | grep -A 20 "knowledge_base_context"

# Expected output:
# ### Domain: Data Engineering | Source: transcript | Relevance: 0.94
# **Learning Objective**: Understand core Data Engineering principles
# **Topic**: Data Storage Solutions
# **Citation**: Course Transcript: AWS ML Module 3 (Segment 42)
#
# Amazon S3 provides eleven nines of durability...
# ---

# 4. Compare quality metrics
# - Measure domain-specific term frequency
# - Check citation accuracy (references match sources)
# - Assess slide relevance to learning objectives
```

---

## Tier 3: Model Upgrade Path (Optional)

**Impact:** Medium-High
**Effort:** Low (2-3 hours)
**Files Changed:** 2 (llm_service.py, config.py)
**Lines Added:** ~60
**Cost:** $0.004/course (mini) → $0.008/course (haiku) or $0.068/course (gpt-4o)

### Architecture: Model Selection Strategy

```python
# Configuration-driven model selection
if quality_score < 70:
    COMPOSITION_MODEL = "claude-3-5-haiku-20241022"  # Better reasoning, 200K context
elif quality_score < 80 AND budget_allows:
    COMPOSITION_MODEL = "gpt-4o"  # Best quality, highest cost
else:
    COMPOSITION_MODEL = "gpt-4o-mini"  # Fast, cheap, good enough
```

### Code Changes

#### 1. Add Model Configuration

**File:** `presgen-assess/.env`

```bash
# ============================================
# LLM Model Configuration (Tier 3)
# ============================================

# Assessment Generation (keep fast/cheap)
ASSESSMENT_MODEL=gpt-4o-mini
ASSESSMENT_PROVIDER=openai

# Presentation Composition (upgrade for quality)
COMPOSITION_MODEL=gpt-4o-mini              # Options: gpt-4o-mini | claude-3-5-haiku-20241022 | gpt-4o
COMPOSITION_PROVIDER=openai                # Options: openai | anthropic
COMPOSITION_MAX_TOKENS=8000                # Max tokens for presentation JSON output

# Anthropic API (if using Claude)
ANTHROPIC_API_KEY=sk-ant-xxxxx             # Required if COMPOSITION_PROVIDER=anthropic

# Model Fallback Strategy
ENABLE_MODEL_FALLBACK=true                 # Fall back to gpt-4o-mini if primary fails
FALLBACK_MODEL=gpt-4o-mini
```

#### 2. Update config.py

**File:** `presgen-assess/src/common/config.py`

```python
    # LLM Model Configuration (Tier 3)
    assessment_model: str = os.getenv("ASSESSMENT_MODEL", "gpt-4o-mini")
    assessment_provider: str = os.getenv("ASSESSMENT_PROVIDER", "openai")

    composition_model: str = os.getenv("COMPOSITION_MODEL", "gpt-4o-mini")
    composition_provider: str = os.getenv("COMPOSITION_PROVIDER", "openai")
    composition_max_tokens: int = int(os.getenv("COMPOSITION_MAX_TOKENS", "8000"))

    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")

    enable_model_fallback: bool = os.getenv("ENABLE_MODEL_FALLBACK", "true").lower() == "true"
    fallback_model: str = os.getenv("FALLBACK_MODEL", "gpt-4o-mini")
```

#### 3. Update llm_service.py

**File:** `presgen-assess/src/services/llm_service.py`

**Add after line 14:**

```python
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic  # Add to requirements.txt: anthropic>=0.34.0
```

**Update __init__ method (lines 20-26):**

```python
class LLMService:
    """Service for OpenAI LLM integration with RAG context enhancement.

    Tier 3 Enhancement: Multi-provider support (OpenAI + Anthropic) with
    separate models for assessment (fast/cheap) vs composition (quality).
    """

    def __init__(self):
        """Initialize LLM clients for assessment and composition."""
        # Assessment client (always OpenAI gpt-4o-mini for speed/cost)
        self.assessment_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.assessment_model = settings.assessment_model

        # Composition client (configurable provider)
        self.composition_model = settings.composition_model
        self.composition_provider = settings.composition_provider

        if self.composition_provider == "anthropic":
            if not settings.anthropic_api_key:
                logger.warning("⚠️ ANTHROPIC_API_KEY not set, falling back to OpenAI")
                self.composition_client = self.assessment_client
                self.composition_provider = "openai"
                self.composition_model = settings.fallback_model
            else:
                self.composition_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                logger.info(f"✅ Composition client initialized: Anthropic {self.composition_model}")
        else:
            self.composition_client = self.assessment_client
            logger.info(f"✅ Composition client initialized: OpenAI {self.composition_model}")

        self.knowledge_base = RAGKnowledgeBase()
        self.token_usage = {"total_tokens": 0, "total_cost": 0.0}
```

**Add new method for provider-agnostic completion:**

```python
    async def _complete_with_provider(
        self,
        provider: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8000,
        temperature: float = 0.2
    ) -> Tuple[str, Dict]:
        """Provider-agnostic LLM completion.

        Args:
            provider: "openai" or "anthropic"
            model: Model identifier
            system_prompt: System role/instructions
            user_prompt: User message
            max_tokens: Max tokens for response
            temperature: Sampling temperature

        Returns:
            Tuple of (response_text, usage_stats)
        """
        if provider == "anthropic":
            # Anthropic Messages API
            try:
                response = await self.composition_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )

                content = response.content[0].text
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
                return content, usage

            except Exception as e:
                logger.error(f"❌ Anthropic API error: {e}")
                if settings.enable_model_fallback:
                    logger.info(f"🔄 Falling back to {settings.fallback_model}")
                    return await self._complete_with_provider(
                        "openai", settings.fallback_model, system_prompt, user_prompt, max_tokens, temperature
                    )
                raise

        else:
            # OpenAI Chat Completions API
            try:
                response = await self.composition_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
                return content, usage

            except Exception as e:
                logger.error(f"❌ OpenAI API error: {e}")
                raise
```

**Update generate_refined_course_outline (lines 357-400):**

```python
    async def generate_refined_course_outline(
        self,
        *,
        recommended_course: Dict[str, Any],
        presentation_prompt: Optional[str],
        rag_context: str,
        rag_citations: List[Dict[str, Any]],
        gap_analysis: Dict[str, Any],
        assessment_results: Dict[str, Any],
        target_slide_count: int
    ) -> Dict[str, Any]:
        """Regenerate course outline using existing recommendations and RAG context.

        Tier 3 Enhancement: Use composition_model (potentially upgraded) instead of
        assessment_model for better quality presentation generation.
        """

        # Build prompt...
        prompt = self._build_refined_outline_prompt(
            recommended_course=recommended_course,
            presentation_prompt=presentation_prompt,
            rag_context=rag_context,
            gap_analysis=gap_analysis,
            assessment_results=assessment_results,
            target_slide_count=target_slide_count
        )

        system_prompt = presentation_prompt or self._get_default_presentation_system_prompt()

        # Log request
        self._log_llm_event(
            "refined_outline_request",
            {
                "model": self.composition_model,
                "provider": self.composition_provider,
                "slide_count": target_slide_count,
                "rag_context_chars": len(rag_context),
                "prompt_chars": len(prompt)
            }
        )

        # Call LLM with provider abstraction
        try:
            content, usage = await self._complete_with_provider(
                provider=self.composition_provider,
                model=self.composition_model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                max_tokens=settings.composition_max_tokens,
                temperature=0.2
            )

            # Parse JSON response
            outline = json.loads(content)

            # Add metadata
            outline["rag_citations"] = rag_citations
            outline["model_used"] = self.composition_model
            outline["provider"] = self.composition_provider
            outline["token_usage"] = usage

            self._log_llm_event(
                "refined_outline_response",
                {
                    "success": True,
                    "model": self.composition_model,
                    "section_count": len(outline.get("sections", [])),
                    "tokens": usage
                }
            )

            return outline

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response from {self.composition_model}: {e}")
            return {"success": False, "error": f"Invalid JSON from LLM: {str(e)}"}

        except Exception as e:
            logger.error(f"❌ LLM completion failed: {e}")
            return {"success": False, "error": str(e)}
```

### Testing Tier 3

**Test Matrix:**

| Model | Provider | Expected Quality | Cost/Course | Test Command |
|-------|----------|------------------|-------------|--------------|
| gpt-4o-mini (baseline) | openai | 60% | $0.004 | `COMPOSITION_MODEL=gpt-4o-mini` |
| claude-3-5-haiku | anthropic | 75% | $0.008 | `COMPOSITION_MODEL=claude-3-5-haiku-20241022` |
| gpt-4o | openai | 85% | $0.068 | `COMPOSITION_MODEL=gpt-4o` |

**Test Procedure:**

```bash
# 1. Test gpt-4o-mini (baseline)
export COMPOSITION_MODEL=gpt-4o-mini
export COMPOSITION_PROVIDER=openai
# Generate presentation, record quality score

# 2. Test Claude 3.5 Haiku
export COMPOSITION_MODEL=claude-3-5-haiku-20241022
export COMPOSITION_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-xxxxx
# Generate same presentation, compare quality

# 3. Test GPT-4o (if budget allows)
export COMPOSITION_MODEL=gpt-4o
export COMPOSITION_PROVIDER=openai
# Generate same presentation, compare quality

# 4. Evaluate results
python3 << 'EOF'
# Compare presentations:
# - Domain-specific terminology density
# - Citation accuracy
# - Factual correctness (manual review)
# - Slide coherence
# - Learner value (subjective)
EOF
```

---

## Tier 4: Domain-Aware Ingestion (Future Enhancement)

**Impact:** Very High (but diminishing returns)
**Effort:** High (1-2 weeks)
**Files Changed:** 5+ (new classifier, updated ingestion, retrieval)
**Lines Added:** ~200+
**Cost:** +$0.50 per transcript upload (one-time)

**Note:** This is a **future enhancement** - not required for initial quality improvement. Document architecture but defer implementation until Tier 1-3 results are evaluated.

### Architecture Overview

```
Upload Transcript
    ↓
Parse Exam Guide Taxonomy → {domains, topics, tasks}
    ↓
Chunk Transcript (800 chars)
    ↓
FOR EACH chunk:
    ↓
    LLM Classify Chunk → {primary_domain, secondary_domains, topic, skills, confidence}
        Prompt: "Given this exam taxonomy and transcript chunk, classify the chunk..."
        Model: gpt-4o-mini (fast, cheap)
        Cost: ~$0.001 per chunk
    ↓
    Store in ChromaDB with enhanced metadata:
        {
            "certification_id": "aws-ml-specialty",
            "primary_domain": "Data Engineering",
            "primary_domain_id": "domain_1",
            "secondary_domains": ["Model Development"],
            "topic": "Data Storage Solutions",
            "topic_id": "topic_1.1",
            "skills": ["Identify data sources", "Choose storage solutions"],
            "exam_guide_tasks": ["Task 1.1", "Task 1.2"],
            "classification_confidence": 0.94,
            "keywords": ["S3", "data lake", "storage"]
        }
    ↓
END FOR
    ↓
Transcript Indexed with Domain Structure
    ↓
Generate Course Request
    ↓
Retrieve with hierarchical filters:
    - Filter by primary_domain = course.exam_domain
    - Filter by topic IN learning_objectives
    - Filter by exam_guide_tasks related to gaps
    ↓
Return ONLY domain-relevant chunks (5-10 chunks instead of 15-20)
    ↓
Compose Presentation with highly focused context
```

### Benefits

| Metric | Tier 3 | Tier 4 (Domain-Aware) | Improvement |
|--------|--------|----------------------|-------------|
| Chunks retrieved | 15 | 6 | 60% reduction |
| Token usage | 15K | 6K | 60% reduction |
| Relevance precision | 75% | 90% | +20% |
| Cross-domain noise | 25% | 5% | 80% reduction |
| Generation cost | $0.008 | $0.006 | 25% savings |

### Implementation Sketch

**New File:** `presgen-assess/src/knowledge/domain_classifier.py`

```python
"""LLM-based domain classification for transcript chunks."""

import json
import logging
from typing import Dict, List, Optional

from openai import AsyncOpenAI
from src.common.config import settings

logger = logging.getLogger(__name__)


class DomainClassifier:
    """Classify transcript chunks using exam guide taxonomy."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # Fast, cheap for classification

    async def classify_chunk(
        self,
        chunk_text: str,
        exam_taxonomy: Dict,
        certification_id: str
    ) -> Dict:
        """Classify a transcript chunk into domain/topic/skill categories.

        Args:
            chunk_text: Text chunk to classify
            exam_taxonomy: Parsed exam guide structure
            certification_id: Certification identifier

        Returns:
            Classification metadata dict
        """
        # Build classification prompt
        prompt = self._build_classification_prompt(chunk_text, exam_taxonomy)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_classifier_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500,
                response_format={"type": "json_object"}
            )

            classification = json.loads(response.choices[0].message.content)

            # Add certification_id
            classification["certification_id"] = certification_id

            return classification

        except Exception as e:
            logger.error(f"❌ Classification failed: {e}")
            return self._get_fallback_classification(certification_id)

    def _build_classification_prompt(self, chunk_text: str, taxonomy: Dict) -> str:
        """Build prompt for chunk classification."""
        return f"""
# Exam Guide Taxonomy

{json.dumps(taxonomy, indent=2)}

# Transcript Chunk to Classify

{chunk_text}

# Task

Classify this transcript chunk according to the exam taxonomy above.

Return JSON with:
{{
  "primary_domain": "Exact domain name from taxonomy",
  "primary_domain_id": "domain_X ID from taxonomy",
  "confidence": 0.0-1.0,
  "secondary_domains": ["Other relevant domains if cross-cutting"],
  "topic": "Specific topic within primary domain",
  "topic_id": "topic_X.Y ID from taxonomy",
  "skills": ["Relevant skills from taxonomy this chunk addresses"],
  "exam_guide_tasks": ["Task IDs like Task 1.1"],
  "keywords": ["Key technical terms in this chunk"],
  "reasoning": "Brief explanation of classification"
}}

If chunk doesn't clearly fit any domain, use "General" with confidence < 0.5.
"""

    def _get_classifier_system_prompt(self) -> str:
        """System prompt for classification."""
        return """You are an exam taxonomy classifier. Your job is to accurately categorize transcript chunks according to a provided certification exam structure.

Be precise:
- Match domain/topic names exactly as they appear in taxonomy
- Only use secondary_domains if content truly spans multiple domains
- Include task IDs only if chunk directly addresses that task
- Set confidence < 0.7 if classification is uncertain
- Extract 3-5 key technical terms as keywords"""

    def _get_fallback_classification(self, certification_id: str) -> Dict:
        """Fallback classification if LLM fails."""
        return {
            "certification_id": certification_id,
            "primary_domain": "General",
            "primary_domain_id": "domain_0",
            "confidence": 0.5,
            "secondary_domains": [],
            "topic": "Uncategorized",
            "topic_id": "topic_0.0",
            "skills": [],
            "exam_guide_tasks": [],
            "keywords": [],
            "reasoning": "Classification failed, using fallback"
        }


async def classify_transcript_batch(
    chunks: List[str],
    exam_taxonomy: Dict,
    certification_id: str
) -> List[Dict]:
    """Classify multiple chunks efficiently."""
    classifier = DomainClassifier()

    classifications = []
    for i, chunk in enumerate(chunks):
        logger.info(f"📝 Classifying chunk {i+1}/{len(chunks)}")
        classification = await classifier.classify_chunk(chunk, exam_taxonomy, certification_id)
        classifications.append(classification)

    return classifications
```

**Updated Ingestion Flow** (base.py):

```python
async def ingest_with_domain_classification(
    self,
    certification_id: str,
    transcript_files: List[Path],
    exam_guide_taxonomy: Dict
) -> Dict:
    """Enhanced ingestion with domain classification (Tier 4).

    Args:
        certification_id: Certification identifier
        transcript_files: List of transcript file paths
        exam_guide_taxonomy: Parsed exam guide structure

    Returns:
        Ingestion result with classification stats
    """
    from src.knowledge.domain_classifier import classify_transcript_batch

    all_chunks = []
    all_metadata = []

    for transcript_file in transcript_files:
        # Process document
        chunks, base_metadata = await self.document_processor.process_document(
            document_path=transcript_file,
            certification_id=certification_id,
            content_classification="transcript"
        )

        # Classify chunks
        logger.info(f"🔍 Classifying {len(chunks)} chunks from {transcript_file.name}")
        classifications = await classify_transcript_batch(chunks, exam_guide_taxonomy, certification_id)

        # Merge base metadata with classifications
        for i, (chunk, base_meta, classification) in enumerate(zip(chunks, base_metadata, classifications)):
            enhanced_metadata = {
                **base_meta,
                **classification,
                "chunk_index": i,
                "document_name": transcript_file.name
            }
            all_chunks.append(chunk)
            all_metadata.append(enhanced_metadata)

    # Store in ChromaDB
    success = await self.vector_manager.store_document_chunks(
        chunks=all_chunks,
        metadata=all_metadata,
        content_classification="transcript"
    )

    # Calculate classification stats
    high_confidence = sum(1 for m in all_metadata if m.get("confidence", 0) >= 0.8)
    domain_distribution = {}
    for m in all_metadata:
        domain = m.get("primary_domain", "Unknown")
        domain_distribution[domain] = domain_distribution.get(domain, 0) + 1

    return {
        "success": success,
        "total_chunks": len(all_chunks),
        "high_confidence_classifications": high_confidence,
        "classification_accuracy": high_confidence / len(all_chunks) if all_chunks else 0,
        "domain_distribution": domain_distribution,
        "certification_id": certification_id
    }
```

**Updated Retrieval** (embeddings.py):

```python
async def retrieve_by_domain_hierarchy(
    self,
    query: str,
    certification_id: str,
    target_domain: str,
    target_topics: Optional[List[str]] = None,
    k: int = 5
) -> List[Dict]:
    """Retrieve chunks with hierarchical domain filtering (Tier 4).

    Args:
        query: Semantic search query
        certification_id: Certification identifier
        target_domain: Primary domain filter
        target_topics: Optional topic filters
        k: Number of results to return

    Returns:
        List of relevant chunks with metadata
    """
    # Build metadata filter
    where_filter = {
        "certification_id": certification_id,
        "$or": [
            {"primary_domain": target_domain},
            {"secondary_domains": {"$contains": target_domain}}
        ]
    }

    if target_topics:
        where_filter["$and"] = [
            where_filter,
            {"topic": {"$in": target_topics}}
        ]

    # Semantic search with metadata filter
    results = self.transcripts_collection.query(
        query_texts=[query],
        n_results=k * 2,  # Over-retrieve for re-ranking
        where=where_filter
    )

    # Re-rank by confidence + relevance
    scored_results = []
    for i, doc in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]

        # Combined score: 70% semantic relevance + 30% classification confidence
        relevance = 1.0 - (distance / 2.0)  # Normalize cosine distance
        confidence = metadata.get("classification_confidence", 0.5)
        combined_score = (relevance * 0.7) + (confidence * 0.3)

        scored_results.append({
            "content": doc,
            "source_type": "transcript",
            "metadata": metadata,
            "distance": distance,
            "relevance": relevance,
            "combined_score": combined_score,
            "id": results["ids"][0][i]
        })

    # Sort by combined score and return top-k
    scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
    return scored_results[:k]
```

### Tier 4 Cost Analysis

**One-Time Costs (Per Transcript Upload):**
```
500 chunks × $0.001/classification = $0.50 per transcript
10 transcripts per certification = $5.00 total
```

**Ongoing Savings (Per Course Generation):**
```
Before: 15 chunks × 800 words = 12K words ≈ 16K tokens
After: 6 chunks × 800 words = 4.8K words ≈ 6.4K tokens

Token reduction: 60%
Cost savings: $0.008 → $0.006 per course (25% reduction)

Payback: $5 investment / $0.002 savings = 2,500 courses to break even
```

**ROI Timeline:**
- Low volume (<100 courses/month): Not worth it
- Medium volume (100-500 courses/month): Break even in 5-25 months
- High volume (>500 courses/month): Break even in <5 months

**Recommendation:** Defer Tier 4 until:
1. Course generation volume > 100/month
2. Tier 1-3 quality improvements plateau
3. Budget allows for upfront investment

---

## Implementation Checklist

### Tier 1: Prompt Enhancement (1-2 hours)

- [ ] **Update CLEANED_CERTIFICATION_PROMPT.md**
  - [ ] Add enhanced system role with quality rubric
  - [ ] Add internal quality checklist
  - [ ] Add context structure interpretation guide
  - [ ] Add grounding requirements
  - [ ] Update design framework with filtering hierarchy
  - [ ] Add example output with metadata
  - [ ] Version bump to v2.0

- [ ] **Update .env file**
  - [ ] Add RAG configuration variables (declarative)
  - [ ] Document Tier 2 feature flags (disabled by default)

- [ ] **Update certification profile prompt (database)**
  - [ ] Load updated prompt via UI
  - [ ] Verify prompt saved correctly
  - [ ] Test with existing workflow

- [ ] **Testing**
  - [ ] Generate test presentation with existing course
  - [ ] Compare before/after quality metrics
  - [ ] Check for citation improvements
  - [ ] Verify domain-specific terminology usage
  - [ ] Document quality score improvement

### Tier 2: RAG Context Structuring (4-6 hours)

- [ ] **Update src/knowledge/base.py**
  - [ ] Modify `_format_combined_context()` method
  - [ ] Add structured formatting with domain tags
  - [ ] Add relevance score filtering
  - [ ] Add metadata extraction (domain, topic, objective)
  - [ ] Add semantic boundary markers (---)
  - [ ] Test with existing retrieval

- [ ] **Update src/knowledge/embeddings.py**
  - [ ] Modify `_generate_citation()` method
  - [ ] Include domain/topic in citations
  - [ ] Test citation generation

- [ ] **Update src/common/config.py**
  - [ ] Add Tier 2 configuration fields
  - [ ] Add validation for numeric ranges
  - [ ] Test config loading

- [ ] **Update src/service/api/v1/endpoints/workflows.py**
  - [ ] Modify `_format_prompt_template()` chunk limit logic
  - [ ] Respect RAG_MAX_TOTAL_CHUNKS
  - [ ] Adjust k_per_query dynamically
  - [ ] Test with different configurations

- [ ] **Enable Tier 2 in .env**
  - [ ] Set RAG_ENABLE_DOMAIN_TAGS=true
  - [ ] Set RAG_INCLUDE_RELEVANCE_SCORES=true
  - [ ] Set RAG_RELEVANCE_THRESHOLD=0.75
  - [ ] Restart application

- [ ] **Testing**
  - [ ] Generate presentation with Tier 2 enabled
  - [ ] Verify structured context in logs
  - [ ] Check relevance filtering (low-relevance chunks excluded)
  - [ ] Compare quality vs Tier 1
  - [ ] Measure token usage reduction

### Tier 3: Model Upgrade (2-3 hours)

- [ ] **Update requirements.txt**
  - [ ] Add `anthropic>=0.34.0` (if using Claude)

- [ ] **Update src/common/config.py**
  - [ ] Add composition_model configuration
  - [ ] Add composition_provider configuration
  - [ ] Add anthropic_api_key field
  - [ ] Add fallback configuration

- [ ] **Update src/services/llm_service.py**
  - [ ] Add AsyncAnthropic import
  - [ ] Update `__init__` to initialize both clients
  - [ ] Add `_complete_with_provider()` method
  - [ ] Update `generate_refined_course_outline()` to use composition client
  - [ ] Add fallback logic

- [ ] **Update .env file**
  - [ ] Add COMPOSITION_MODEL configuration
  - [ ] Add COMPOSITION_PROVIDER configuration
  - [ ] Add ANTHROPIC_API_KEY (if using Claude)
  - [ ] Add fallback settings

- [ ] **Testing**
  - [ ] Test with gpt-4o-mini (baseline)
  - [ ] Test with claude-3-5-haiku (if budget allows)
  - [ ] Test with gpt-4o (if budget allows)
  - [ ] Compare quality across models
  - [ ] Measure cost per course
  - [ ] Document ROI analysis

### Tier 4: Domain-Aware Ingestion (Future - 1-2 weeks)

- [ ] **Design exam taxonomy schema**
  - [ ] Define JSON structure for domains/topics/tasks
  - [ ] Create parser for existing exam guides
  - [ ] Validate taxonomy completeness

- [ ] **Create src/knowledge/domain_classifier.py**
  - [ ] Implement DomainClassifier class
  - [ ] Build classification prompts
  - [ ] Add batch classification support
  - [ ] Add error handling and fallbacks

- [ ] **Update src/knowledge/base.py**
  - [ ] Add `ingest_with_domain_classification()` method
  - [ ] Integrate with DomainClassifier
  - [ ] Update metadata structure
  - [ ] Test with sample transcript

- [ ] **Update src/knowledge/embeddings.py**
  - [ ] Add `retrieve_by_domain_hierarchy()` method
  - [ ] Implement re-ranking logic
  - [ ] Add metadata filtering support
  - [ ] Test hierarchical retrieval

- [ ] **Update ingestion UI/API**
  - [ ] Add taxonomy upload endpoint
  - [ ] Add progress tracking for classification
  - [ ] Update ingestion response schema

- [ ] **Testing**
  - [ ] Classify test transcript
  - [ ] Verify classification accuracy (manual review sample)
  - [ ] Test hierarchical retrieval
  - [ ] Compare quality vs Tier 3
  - [ ] Measure cost per upload

---

## Testing Strategy

### Test Scenarios

#### Scenario 1: Baseline Comparison

**Goal:** Establish baseline quality metrics

**Procedure:**
1. Select existing "Data Engineering" recommended course
2. Generate presentation with current system (pre-Tier 1)
3. Manual quality evaluation:
   - Count generic phrases ("various", "several", "important")
   - Check citation density (references per slide)
   - Assess domain-specific terminology usage
   - Verify factual accuracy against source transcripts
   - Rate slide relevance to learning objectives (1-5 scale)
4. Automated metrics:
   - Token usage (input + output)
   - Generation time (seconds)
   - Cost per course
   - Chunk count used
5. Document baseline scores

**Expected Baseline:**
```
Generic phrase count: 15-20 per presentation
Citation density: 0-2 citations per slide
Domain terminology: 40-50% of technical terms
Factual accuracy: 70-80%
Relevance score: 2.5/5 (50%)
Token usage: 60K+ input tokens
Cost: $0.004/course
```

#### Scenario 2: Tier 1 Improvement

**Goal:** Validate prompt enhancement impact

**Procedure:**
1. Update CLEANED_CERTIFICATION_PROMPT.md with Tier 1 changes
2. Regenerate same "Data Engineering" course
3. Compare metrics against baseline:
   - Generic phrases (expect 40-50% reduction)
   - Citations (expect 2-3x increase)
   - Domain terminology (expect 10-15% increase)
   - Factual accuracy (manual review)
   - Relevance score (expect 3.0-3.5/5)
4. Document improvements

**Expected Tier 1:**
```
Generic phrase count: 8-10 (-50%)
Citation density: 2-4 citations per slide (+100-200%)
Domain terminology: 50-60% (+10-15%)
Factual accuracy: 75-85%
Relevance score: 3.0-3.5/5 (60-70%)
Token usage: 60K (no change)
Cost: $0.004 (no change)
```

#### Scenario 3: Tier 2 Improvement

**Goal:** Validate RAG restructuring impact

**Procedure:**
1. Enable Tier 2 features in .env
2. Regenerate same course with structured context
3. Compare metrics against Tier 1:
   - Token usage (expect 40-60% reduction)
   - Relevance score (expect 3.5-4.0/5)
   - Context utilization (check if high-relevance chunks used)
   - Citation accuracy (references match sources)
4. Log analysis:
   - Verify structured context format
   - Check relevance filtering (chunks < 0.75 excluded)
   - Confirm domain tag matching

**Expected Tier 2:**
```
Generic phrase count: 5-7 (-40% from Tier 1)
Citation density: 3-5 citations per slide (+25-50%)
Domain terminology: 60-70% (+10-15%)
Factual accuracy: 80-90%
Relevance score: 3.5-4.0/5 (70-80%)
Token usage: 20-30K (-50-65%)
Cost: $0.003-0.004 (-25% if smaller model suffices)
```

#### Scenario 4: Tier 3 Model Comparison

**Goal:** Quantify model upgrade ROI

**Procedure:**
1. Generate same course with 3 models:
   - gpt-4o-mini (baseline)
   - claude-3-5-haiku
   - gpt-4o (if budget allows)
2. Blind quality evaluation (hide model identity):
   - 3 reviewers rate each presentation (1-5 scale)
   - Average scores
   - Measure inter-rater reliability
3. Calculate cost-quality ratio:
   - Quality score / cost per course
   - Identify best ROI model

**Expected Tier 3:**
```
gpt-4o-mini:
  - Quality: 3.5/5 (70%)
  - Cost: $0.004
  - ROI: 875 quality points per dollar

claude-3-5-haiku:
  - Quality: 3.75-4.0/5 (75-80%)
  - Cost: $0.008
  - ROI: 469-500 quality points per dollar

gpt-4o:
  - Quality: 4.25-4.5/5 (85-90%)
  - Cost: $0.068
  - ROI: 63-66 quality points per dollar
```

### Automated Testing

**Unit Tests:**

```python
# tests/test_rag_context_structuring.py

import pytest
from src.knowledge.base import RAGKnowledgeBase

@pytest.mark.asyncio
async def test_format_combined_context_tier2():
    """Test Tier 2 structured context formatting."""
    kb = RAGKnowledgeBase()

    # Mock context results
    context_results = [
        {
            "content": "Amazon S3 provides eleven nines of durability...",
            "source_type": "transcript",
            "metadata": {
                "domain": "Data Engineering",
                "topic": "Data Storage",
                "learning_objective": "Choose appropriate storage solutions",
                "exam_guide_task": "Task 1.1"
            },
            "distance": 0.15,  # High relevance (1.0 - 0.15/2 = 0.925)
            "citation": "Course Transcript: AWS ML Module 3 (Segment 42)"
        }
    ]

    # Format context with Tier 2 enabled
    formatted = kb._format_combined_context(context_results)

    # Assertions
    assert "### Domain: Data Engineering" in formatted
    assert "Source: transcript" in formatted
    assert "Relevance: 0.9" in formatted  # Rounded
    assert "**Learning Objective**: Choose appropriate storage solutions" in formatted
    assert "---" in formatted  # Separator

@pytest.mark.asyncio
async def test_relevance_filtering():
    """Test that low-relevance chunks are filtered out."""
    kb = RAGKnowledgeBase()

    context_results = [
        {"content": "High relevance", "distance": 0.2, ...},  # 0.90 relevance
        {"content": "Low relevance", "distance": 0.8, ...},   # 0.60 relevance
    ]

    # With threshold 0.75
    formatted = kb._format_combined_context(context_results)

    assert "High relevance" in formatted
    assert "Low relevance" not in formatted
```

### Regression Testing

**Pre-deployment Checklist:**

- [ ] Existing workflows continue to work with Tier 1 changes
- [ ] No breaking changes to API responses
- [ ] Database schema unchanged
- [ ] Backward compatibility with old certification prompts
- [ ] Performance regression check (generation time ≤ baseline)
- [ ] Cost regression check (no unexpected cost increases)

---

## Key Learnings & Recommendations

### Learnings from Phase 10 Investigation

#### 1. RAG Retrieval Works Correctly

**Finding:** The semantic search accurately identifies relevant chunks based on learning objectives.

**Evidence:**
- ChromaDB queries return contextually relevant passages
- Relevance scores (cosine distance) correlate with manual relevance assessment
- Source balancing (exam guide vs transcript) works as intended

**Implication:** The problem is NOT with retrieval quality, but with how retrieved content is delivered to the LLM.

#### 2. Context Formatting is Critical for Small Models

**Finding:** gpt-4o-mini and similar small models struggle with unstructured long-context inputs.

**Evidence from Analysis:**
```
"gpt-4o-mini (a small multimodal model) treats it as a long unrelated blob,
so relevance filtering in Step 1 of your prompt ('Primary filter: {skill_name}') fails."
```

**Key Insight:** Small models need semantic scaffolding:
- Clear section boundaries (markdown headers)
- Metadata tags (domain, topic, relevance)
- Explicit relevance scores
- Compressed content (<200 words per chunk)

**Why:** Small models have limited attention span (~16K effective tokens) and weak long-range reasoning.

#### 3. Prompt Directives > Model Size (Up to a Point)

**Finding:** Enhanced prompts with quality rubrics significantly improve small model output.

**Evidence:** Analysis recommendation:
```
"Append before the generation instructions: Quality Checklist
Small LLMs improve drastically when given evaluation checklists.
This increases factual alignment by 10–20% without extra calls."
```

**Threshold:** Prompts can improve quality from 40% → 60-70%, but plateau beyond that. For 80%+ quality, model upgrades necessary.

#### 4. Token Budget Management is Essential

**Finding:** Exceeding effective attention window degrades quality more than model limitations.

**Evidence:**
```
"Context window: 128K tokens
Effective attention: ~16K tokens for middle content
Your input: ~60K tokens → most of the transcript is silently dropped"
```

**Best Practice:** Prefer structured, compressed context over raw, voluminous context.

**Formula:**
```
Quality = f(Context_Relevance × Context_Structure / Token_Count)

NOT: Quality = f(Total_Context_Size)
```

#### 5. Two-Stage Workflows Are Powerful but Complex

**Finding:** Separating summarization (Stage A) from composition (Stage B) improves quality but adds complexity.

**Trade-offs:**
- **Pro:** Allows using cheap model for compression, quality model for generation
- **Pro:** Reduces token usage by 60-80%
- **Con:** Adds latency (two sequential LLM calls)
- **Con:** Increases error surface (two points of failure)
- **Con:** Harder to debug (which stage introduced error?)

**Recommendation:** Start with single-stage (Tier 1-2), only add two-stage if quality plateaus.

#### 6. Domain-Aware Ingestion Has Diminishing Returns

**Finding:** Pre-classifying chunks by domain/topic improves precision but requires upfront investment.

**Cost-Benefit:**
```
Investment: $5 per certification (one-time)
Savings: $0.002 per course (ongoing)
Break-even: 2,500 courses

For low-volume use cases (<100 courses/month), ROI is poor.
For high-volume (>500 courses/month), ROI is excellent.
```

**Recommendation:** Defer Tier 4 until:
1. Course generation volume justifies investment
2. Tier 1-3 quality improvements prove insufficient
3. Budget allows for experimental features

---

### Model Comparison & Recommendations

#### Model Evaluation Criteria

| Model | Context | Speed | Cost | Reasoning | Instruction Following | Best For |
|-------|---------|-------|------|-----------|----------------------|----------|
| **gpt-4o-mini** | 128K | Fast | $0.75/1M | Weak | Good | Assessments, summaries |
| **claude-3.5-haiku** | 200K | Very Fast | $1.50/1M | Medium | Excellent | Structured output, technical content |
| **gpt-4o** | 128K | Medium | $12.50/1M | Strong | Excellent | Complex reasoning, high-stakes content |
| **claude-3.5-sonnet** | 200K | Medium | $15/1M | Very Strong | Excellent | Research, analysis, writing |

#### Use Case Recommendations

##### For Assessment Generation (Current: gpt-4o-mini ✅)

**Keep gpt-4o-mini** - No change needed.

**Rationale:**
- Multiple-choice questions don't require deep reasoning
- Fast generation (200-300ms) improves UX
- Cost-effective ($0.001/assessment)
- Quality is adequate (70-80% accuracy)

##### For Presentation Composition (Current: gpt-4o-mini ⚠️)

**Tier 1-2: Stick with gpt-4o-mini**
- Implement prompt enhancements first
- Add context structuring
- Measure quality improvement
- **Expected outcome:** 40% → 70% quality

**Tier 3a: Upgrade to claude-3.5-haiku** (Recommended if Tier 2 < 75%)
- **Cost:** +$0.004/course (+100%)
- **Quality:** 70% → 75-80% (+7-14%)
- **Speed:** 2-3x faster than gpt-4o-mini
- **ROI:** Best value for incremental quality improvement

**Pros:**
- ✅ 200K context (vs 128K) reduces truncation risk
- ✅ Strong at structured output (JSON formatting)
- ✅ Excellent instruction following (adheres to rubrics)
- ✅ Good at technical content (AWS/ML terminology)
- ✅ Fast generation (150-200ms)

**Cons:**
- ❌ Requires Anthropic API integration
- ❌ 2x cost vs gpt-4o-mini
- ❌ Different API format (requires abstraction layer)

**When to choose:**
- Budget allows $0.008/course
- Tier 2 quality = 70-75% (good but not excellent)
- Need faster generation (latency sensitive)
- Already using Anthropic for other services

**Tier 3b: Upgrade to gpt-4o** (Only if quality critical)
- **Cost:** +$0.064/course (+1600%)
- **Quality:** 70% → 85%+ (+21%)
- **Speed:** Slower than mini/haiku
- **ROI:** Poor unless high-value courses

**Pros:**
- ✅ Best reasoning capabilities
- ✅ Strong long-context comprehension
- ✅ Excellent factual accuracy
- ✅ No new API integration needed

**Cons:**
- ❌ 17x cost vs gpt-4o-mini
- ❌ 8x cost vs claude-3.5-haiku
- ❌ Slower generation (400-600ms)
- ❌ Overkill for most use cases

**When to choose:**
- Budget allows $0.068/course
- Quality requirements > 85% (regulatory/compliance)
- High-value courses (enterprise/premium)
- Tier 2 + haiku still insufficient (<80%)

##### For RAG Chunk Summarization (Future Two-Stage Workflow)

**Use gpt-4o-mini** - Fast, cheap, adequate for compression.

**Rationale:**
- Summarization is simple task (no reasoning required)
- Need speed to minimize latency
- Cost-effective (processes 15-20 chunks per course)
- Quality bar is low (just need coherent 150-word summary)

##### Cost-Benefit Summary

**Annual Cost Comparison** (1,000 courses/month = 12,000 courses/year):

| Configuration | Assessment Model | Composition Model | Total Cost/Year | Avg Quality |
|---------------|------------------|-------------------|----------------|-------------|
| **Current (Baseline)** | gpt-4o-mini | gpt-4o-mini | $60 | 60% |
| **Tier 1-2 (Recommended)** | gpt-4o-mini | gpt-4o-mini | $60 | 70-75% |
| **Tier 3a (Best Value)** | gpt-4o-mini | claude-3.5-haiku | $108 (+$48) | 75-80% |
| **Tier 3b (Premium)** | gpt-4o-mini | gpt-4o | $828 (+$768) | 85%+ |

**ROI Analysis:**

```
Tier 3a (Haiku):
- Investment: +$48/year
- Quality gain: +5-10%
- Worth it if: Quality issues cost >$48/year in user dissatisfaction

Tier 3b (GPT-4o):
- Investment: +$768/year
- Quality gain: +15-25%
- Worth it if: Quality issues cost >$768/year OR compliance mandates high accuracy
```

---

### Alternative Models (Future Consideration)

#### Google Gemini 2.0 Flash

**Specs:**
- Context: 1M tokens (largest available)
- Speed: Very fast
- Cost: $0.075 input / $0.30 output per 1M tokens
- Reasoning: Medium (between mini and 4o)

**Pros:**
- ✅ Massive context window (can handle entire transcripts)
- ✅ Very cheap (cheaper than gpt-4o-mini)
- ✅ Fast generation
- ✅ Good at multimodal (images + text)

**Cons:**
- ❌ Inconsistent quality (varies by task)
- ❌ Weaker instruction following vs Claude/GPT
- ❌ Requires Google Cloud integration
- ❌ Less proven for technical content

**When to consider:**
- Need to process very long documents (>100K tokens)
- Budget extremely constrained
- Already using Google Cloud infrastructure

#### Meta Llama 3.1 70B (Self-Hosted)

**Specs:**
- Context: 128K tokens
- Speed: Depends on hardware (typically 50-200ms)
- Cost: $0 (after infrastructure)
- Reasoning: Medium-strong

**Pros:**
- ✅ Zero per-request cost
- ✅ Full data privacy (no external API)
- ✅ Customizable (can fine-tune)
- ✅ Strong open-source community

**Cons:**
- ❌ High infrastructure cost ($500-2000/month for GPU)
- ❌ Maintenance burden (model updates, scaling)
- ❌ Break-even requires high volume (>10K courses/month)
- ❌ Quality typically 5-10% below GPT-4o/Claude

**When to consider:**
- Very high volume (>10K courses/month)
- Data privacy requirements prohibit external APIs
- Have ML engineering team for model operations
- Long-term commitment (infrastructure investment)

---

### Best Practices Going Forward

#### 1. Implement Incrementally

**Don't:** Implement all tiers at once
**Do:** Implement Tier 1 → test → Tier 2 → test → decide on Tier 3

**Rationale:** Diminishing returns + compounding complexity. Each tier has different ROI:
- Tier 1: High ROI (0 cost, 50% improvement)
- Tier 2: High ROI (2 days work, 25% improvement)
- Tier 3: Medium ROI (3 hours work, 2x cost, 13% improvement)
- Tier 4: Low ROI (2 weeks work, $5 upfront, 6% improvement)

#### 2. Measure Everything

**Metrics to Track:**
- Quality score (manual review, 1-5 scale)
- Citation density (citations per slide)
- Domain-specific terminology (% of technical terms)
- Token usage (input + output)
- Cost per course
- Generation time (seconds)
- User feedback (if available)

**Dashboard:**
```
┌─────────────────────────────────────────────────────────────┐
│ Presentation Quality Dashboard                              │
├─────────────────────────────────────────────────────────────┤
│ Tier          │ Quality │ Cost/Course │ Tokens │ Time      │
│───────────────│─────────│─────────────│────────│───────────│
│ Baseline      │  60%    │  $0.004     │  60K   │  3.5s     │
│ Tier 1        │  70%    │  $0.004     │  60K   │  3.5s     │
│ Tier 2        │  75%    │  $0.003     │  25K   │  2.8s     │
│ Tier 3 (haiku)│  78%    │  $0.008     │  25K   │  2.1s     │
│ Tier 3 (gpt4o)│  86%    │  $0.068     │  25K   │  4.2s     │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Prompt Engineering First, Model Upgrades Second

**Principle:** Exhaust prompt optimization before spending on better models.

**Rationale:**
- Prompt changes are free
- Model upgrades have ongoing costs
- A great prompt on a small model often beats a mediocre prompt on a large model

**Example:**
```
Bad prompt + gpt-4o = 75% quality, $0.068 cost
Great prompt + gpt-4o-mini = 70% quality, $0.004 cost

5% quality improvement costs $0.064 (1600% cost increase)
```

#### 4. Context Structure Beats Context Volume

**Principle:** Prefer 10 well-structured chunks over 50 raw chunks.

**Rationale:**
- Small models can't synthesize large unstructured inputs
- Token limits punish verbose context
- Relevance filtering reduces noise

**Formula:**
```
Effective_Context = Structure_Quality × Relevance_Precision × Chunk_Count^0.5

NOT: Effective_Context = Chunk_Count
```

**Example:**
```
Option A: 50 chunks, flat concatenation, no filtering
  - Total tokens: 60K
  - Model uses: ~16K (26%)
  - Quality: 60%

Option B: 10 chunks, structured, relevance ≥0.75
  - Total tokens: 12K
  - Model uses: ~12K (100%)
  - Quality: 75%
```

#### 5. Universal Design (Avoid Certification Lock-In)

**Principle:** All enhancements must work for ANY learning domain, not just certifications.

**Examples:**
- ✅ "Learning domain" → Works for: certs, onboarding, compliance, sales training
- ❌ "Exam tasks" → Only works for: certifications
- ✅ "Source transcripts" → Works for: any video/audio content
- ❌ "Exam guide" → Only works for: certifications

**Implementation:**
```python
# BAD (certification-specific)
metadata = {
    "exam_domain": "Data Engineering",
    "exam_task": "Task 1.1",
    "certification_id": "aws-ml-specialty"
}

# GOOD (universal)
metadata = {
    "learning_domain": "Data Engineering",  # Could be "Sales Techniques", "Compliance Rules", etc.
    "learning_objective": "Choose appropriate storage",
    "content_collection": "aws-ml-specialty"  # Could be "onboarding-v2", "gdpr-training", etc.
}
```

---

## Cost-Benefit Analysis

### Investment Summary

| Tier | Effort (Hours) | One-Time Cost | Ongoing Cost/Course | Quality Gain |
|------|---------------|---------------|---------------------|--------------|
| **Tier 1** | 1-2 | $0 | $0 | +50% (40→60%) |
| **Tier 2** | 4-6 | $0 | $0 | +25% (60→75%) |
| **Tier 3a (Haiku)** | 2-3 | $0 | +$0.004 | +7% (75→80%) |
| **Tier 3b (GPT-4o)** | 2-3 | $0 | +$0.064 | +13% (75→85%) |
| **Tier 4** | 80-160 | $5/cert | -$0.002 | +6% (85→90%) |

### ROI Calculation

**Scenario: 100 courses generated per month**

#### Tier 1 + 2 (Recommended Minimum)
```
Investment:
  - Development time: 6-8 hours
  - Developer cost: $0 (in-house)
  - One-time cost: $0

Returns:
  - Quality improvement: 40% → 75% (+88%)
  - User satisfaction: Higher (fewer complaints)
  - Token usage: -40% (60K → 36K tokens)
  - Generation speed: +20% faster (less context to process)

Payback: Immediate (no cost)

Annual value (assuming $10/hour saved per improved course):
  - 1,200 courses × 88% better × $10/hour = $10,560/year
```

#### Tier 3a: Claude 3.5 Haiku (Optional Upgrade)
```
Investment:
  - Development time: 2-3 hours (one-time)
  - API integration: Anthropic SDK
  - One-time cost: $0

Ongoing costs:
  - 100 courses/month × $0.004 extra = $0.40/month
  - Annual: $4.80/year

Returns:
  - Quality improvement: 75% → 80% (+7%)
  - Generation speed: 2-3x faster
  - User satisfaction: Marginal improvement

Payback:
  - Break-even if quality improvement saves >$4.80/year
  - At 100 courses/month, quality issues likely cost >>$4.80
  - ROI: Positive if users value speed + 5% quality boost

Annual value (assuming $1/course for 5% quality gain):
  - 1,200 courses × 5% × $1/course = $60/year
  - Net value: $60 - $4.80 = $55.20/year
  - ROI: 1,150%
```

#### Tier 3b: GPT-4o (High-End Upgrade)
```
Investment:
  - Development time: 2-3 hours (same as Tier 3a)
  - No new API needed (OpenAI already integrated)
  - One-time cost: $0

Ongoing costs:
  - 100 courses/month × $0.064 extra = $6.40/month
  - Annual: $76.80/year

Returns:
  - Quality improvement: 75% → 85% (+13%)
  - Generation speed: Slower (400-600ms vs 200-300ms)
  - User satisfaction: High improvement

Payback:
  - Break-even if quality improvement saves >$76.80/year
  - At 100 courses/month, must value quality at $0.64/course
  - ROI: Positive if high-stakes content (compliance, premium)

Annual value (assuming $2/course for 10% quality gain):
  - 1,200 courses × 10% × $2/course = $240/year
  - Net value: $240 - $76.80 = $163.20/year
  - ROI: 212%

However:
  - Most users unlikely to perceive 10% quality difference
  - Slower generation may hurt UX
  - Recommendation: Only for premium/enterprise tier
```

#### Tier 4: Domain-Aware Ingestion (Future)
```
Investment:
  - Development time: 80-160 hours
  - Developer cost: $8,000-16,000 (at $100/hour)
  - One-time classification: $5/certification × 10 certs = $50
  - Total: $8,050-16,050

Ongoing costs:
  - 100 courses/month × (-$0.002) savings = -$0.20/month
  - Annual savings: -$2.40/year (positive!)

Ongoing classification:
  - New transcripts: $0.50/transcript
  - ~5 new transcripts/year = $2.50/year
  - Net savings: $2.40 - $2.50 = -$0.10/year (slight cost)

Returns:
  - Quality improvement: 85% → 90% (+6%)
  - Precision improvement: 75% → 90% (+20%)
  - Token usage: -60% (better filtering)

Payback:
  - Quality value: 1,200 courses × 5% × $2/course = $120/year
  - Development cost: $8,000-16,000
  - Break-even: 67-133 years (!!)
  - ROI: Negative unless volume >>100 courses/month

Revised calculation at 1,000 courses/month:
  - Quality value: 12,000 courses × 5% × $2/course = $1,200/year
  - Break-even: 6.7-13.3 years
  - ROI: Still poor

Revised calculation at 10,000 courses/month:
  - Quality value: 120,000 courses × 5% × $2/course = $12,000/year
  - Break-even: 0.67-1.33 years
  - ROI: 50-75% annual return (good!)

Conclusion: Only viable at enterprise scale (>5,000 courses/month)
```

### Recommended Investment Path

**Phase 1: Immediate (Weeks 1-2)**
- ✅ Implement Tier 1 (1-2 hours)
- ✅ Implement Tier 2 (4-6 hours)
- ✅ Test and measure improvements
- **Investment:** ~8 hours developer time
- **Expected outcome:** 40% → 75% quality

**Phase 2: Evaluation (Week 3)**
- ✅ Analyze Tier 1+2 results
- ✅ Gather user feedback
- ✅ Calculate actual quality improvement
- **Decision point:** Is 75% quality sufficient?

**Phase 3a: If quality < 75% (Week 4)**
- ✅ Implement Tier 3a (Claude 3.5 Haiku)
- ✅ Test with production workload
- ✅ Monitor cost/quality metrics
- **Investment:** ~3 hours + $0.004/course

**Phase 3b: If quality < 80% AND high-value use case (Week 4)**
- ✅ Implement Tier 3b (GPT-4o) as opt-in
- ✅ Offer as "Premium Quality" tier to users
- ✅ Charge $0.50/course to cover costs
- **Investment:** ~3 hours + $0.068/course

**Phase 4: Future (6-12 months out)**
- ⏸️ Defer Tier 4 until volume justifies investment
- ⏸️ Re-evaluate when course generation > 5,000/month
- ⏸️ Consider if quality plateau requires fundamental improvements

---

## Conclusion

**Phase 11 provides a clear, incremental path to dramatically improve presentation quality with minimal risk and investment.**

**Key Takeaways:**

1. **Root Cause Identified:** Unstructured RAG context delivery, not retrieval quality
2. **Tier 1+2 Sufficient:** 88% quality improvement for ~8 hours work and $0 cost
3. **Model Upgrades Optional:** Only needed if Tier 2 < 75% quality
4. **Best ROI:** Claude 3.5 Haiku (+$4.80/year for +7% quality)
5. **Domain Classification:** Defer until enterprise scale (>5K courses/month)
6. **Universal Design:** All enhancements work for ANY learning domain

**Next Steps:**

1. Review and approve plan
2. Update project status docs
3. Begin Tier 1 implementation (1-2 hours)
4. Test and iterate
5. Proceed to Tier 2 based on results

---

**Document Version:** 1.0
**Last Updated:** October 14, 2025
**Owner:** PresGen-Assess Development Team
**Status:** Ready for Implementation
