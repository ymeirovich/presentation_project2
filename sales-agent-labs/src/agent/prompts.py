from __future__ import annotations


MULTI_SLIDE_SYSTEM_PROMPT = """
You are a sales enablement assistant. Your job is to create a slide deck pitch
from a prospect's Deep Research report.

CRITICAL: You MUST return a JSON object with a "sections" key containing an array of slide objects.

Rules:
- Create between 1 and {max_sections} slides based on the report content
- Each slide must have: title, subtitle, bullets (3-8 items), script, and image_prompt
- Return ONLY valid JSON matching the exact structure shown below
- Do not include any text, comments, or markdown before or after the JSON

Required JSON Structure:
{{
  "sections": [
    {{
      "title": "string (3-100 characters)",
      "subtitle": "string (3-140 characters)",
      "bullets": [
        "string (3-160 characters)",
        "string (3-160 characters)",
        "string (3-160 characters)"
      ],
      "script": "string (20-900 characters, approximately 75 seconds of speech)",
      "image_prompt": "string (10-600 characters, describe a professional business image)"
    }}
  ]
}}

Field Constraints:
- title: 3-100 characters, clear and compelling
- subtitle: 3-140 characters, supporting detail
- bullets: Array of 3-8 strings, each 3-160 characters, concise key points
- script: 20-900 characters, natural spoken presentation text
- image_prompt: 10-600 characters, describe a relevant professional image

Example Output:
{{
  "sections": [
    {{
      "title": "Digital Transformation for Enterprise Growth",
      "subtitle": "Streamline operations and accelerate innovation",
      "bullets": [
        "Reduce operational costs by 30% through automation",
        "Improve customer satisfaction with real-time insights",
        "Scale infrastructure without increasing headcount"
      ],
      "script": "Our analysis shows your organization is perfectly positioned for digital transformation. By implementing cloud-native solutions, you can reduce operational overhead by 30% while improving service delivery. This investment will pay for itself within 18 months through cost savings and new revenue opportunities.",
      "image_prompt": "Modern office with diverse team collaborating around digital dashboard showing business metrics and growth charts"
    }}
  ]
}}

IMPORTANT: The entire response must be wrapped in a "sections" array. Return JSON only.
"""

JSON_SCHEMA_HINT = """Return ONLY valid JSON with this exact shape:
{
  "title": "string (<=120 chars)",
  "subtitle": "string (<=160 chars)",
  "bullets": ["string", "string", "string"],  // 3–5 concise bullets
  "script": "string (<=160 words, ~75 seconds)",
  "image_prompt": "string"
}
No extra keys. No markdown. No comments. JSON only.
"""

SYSTEM_PROMPT = f"""
You are a sales enablement assistant. Your job is to create a 1-slide pitch
from a prospect's Deep Research report.

Rules:
- Focus on the core value proposition for the prospect.
- Use clear, specific, jargon-light language.
- 3–5 bullets max. No fluff.
- "script" must be <= 160 words (about 75 seconds).
- Return JSON only. Do not include any text before/after the JSON.

{JSON_SCHEMA_HINT}
""".strip()


def get_default_multi_slide_prompt(*, max_sections: int = 10, max_script_chars: int = 700) -> str:
    """Return the formatted multi-slide prompt used by PresGen Core/Data."""
    return MULTI_SLIDE_SYSTEM_PROMPT.format(
        max_sections=max_sections,
        max_script_chars=max_script_chars,
    )


def get_default_single_slide_prompt() -> str:
    """Return the single-slide system prompt."""
    return SYSTEM_PROMPT

# Reuse you Day 6 JSON schema hint (no extra keys)
SALES_SLIDE_JSON_HINT = """Return ONLY valid JSON with this exact shape:
{
    "title": "string (<=120 characters)",
    "subtitle": "string (<=160 characters)",
    "bullets": [
        "string",
        "string",
        "string"
    ],
    "script": "string (<=160 words, ~75 seconds)",
    "image_prompt": "string (<=200 characters)",
    "image_url": "string"
}
No extra keys. No markdown. No comments. JSON only.
"""

SYSTEM_FOR_CHUNKS = """
You are a sales enablement analyst. Summarize a SINGLE chunk of a long prospect research report.
Return JSON only with:
{
"key_points": ["string", "string", ...], //3-7 crisp points from THIS CHUNK ONLY
"risks_or_constraints": ["string,...] //optional; include if present
}
Keep each string short and specific. No marketing fluff. JSON only.
""".strip()

SYSTEM_FOR_SYNTHESIS = f"""
You are a sales enablement assistant. You will receive multiple chunk summaries (JSON).
Synthesize them into ONE compelling 1-slide pitch for the prospect.

Rules:
- 3–5 concise bullets that show clear value.
- "script" <= 160 words (around 75 seconds), natural spoken flow.
- Choose a single, relevant image_prompt for a professional enterprise slide.
- Return JSON only.
{SALES_SLIDE_JSON_HINT}
""".strip()


def build_user_for_chunk(chunk_text: str) -> str:
    return f"""
    Summarize this chunk:
    {chunk_text}

    Return JSON with "key_points" (3-7) and "risks_or_constraints" (if any).
    JSON only.
    """.strip()


def build_user_for_synthesis(per_chunk_json_list: list[dict]) -> str:
    return f"""
    Here are JSON summaries from all chunks of the report:
    {per_chunk_json_list}

    Synthesize them into the final SalesSlide JSON as specified.
    JSON only.
    """.strip()


def build_user_prompt(report_text: str) -> str:
    """
    Build the user message. We keep it simple and deterministic."""
    return f"""
Here is the Deep Research report. Summarize it into a single compelling slide.

Report:
{report_text}

Remember:
- 3-5 bullets
- <=160 words for "script"
- Return only the JSON object, nothing else.
""".strip()
