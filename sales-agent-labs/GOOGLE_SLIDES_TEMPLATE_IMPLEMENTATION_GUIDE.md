# Google Slides Template Implementation Guide for Presgen

**Project**: Presgen Core & Data
**Version**: 1.0
**Last Updated**: October 24, 2025

---

## Executive Summary

This guide explains how to implement **Google Slides templates** in Presgen Core and Presgen Data. Templates allow you to:
- Apply consistent branding (colors, fonts, logos)
- Use pre-designed layouts for different slide types
- Copy existing presentations as starting points
- Leverage Google's built-in themes and layouts

---

## Current State Analysis

### What Presgen Does Now

**Your current implementation** (`src/agent/slides_google.py`):
1. Creates a **blank presentation** from scratch
2. Adds **BLANK slides** with custom text boxes
3. Manually positions all elements (text, images, bullets)
4. No use of Google Slides' built-in layouts or themes

**Code Example**:
```python
# src/agent/slides_google.py:158
def create_presentation(title: str) -> Dict[str, Any]:
    pres = slides.presentations().create(body={"title": title}).execute()
    # This creates a blank presentation with NO template
```

```python
# src/agent/slides_google.py:193
"slideLayoutReference": {"predefinedLayout": "BLANK"}
# All slides use BLANK layout, then manually add text boxes
```

### Why This Matters

**Without Templates**:
❌ Every presentation looks generic (default Google Slides style)
❌ No branding or custom colors
❌ Manual positioning for every element
❌ Inconsistent styling across decks

**With Templates**:
✅ Professional branded presentations
✅ Consistent look and feel
✅ Faster generation (leverage existing layouts)
✅ Client-ready output

---

## Three Approaches to Templates

### Approach 1: Copy an Existing Presentation (Easiest)

**Best For**: Quick branding, existing template decks, client-specific styles

**How It Works**:
1. Create a "master template" presentation in Google Slides (manually or via URL)
2. Use Google Drive API to **copy** the template
3. Replace placeholders with generated content
4. Keep original slides as reference

**Pros**:
- ✅ Easiest to implement (one API call)
- ✅ Preserves all formatting, themes, and layouts
- ✅ Supports custom fonts, logos, backgrounds
- ✅ Non-technical users can create templates

**Cons**:
- ❌ Requires template presentation ID for each style
- ❌ Placeholder replacement can be tricky
- ❌ Template must be maintained separately

**Implementation**:

```python
# src/agent/slides_google.py - Add this function

def create_presentation_from_template(
    template_id: str,
    title: str,
    copy_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Copy an existing presentation to use as a template.

    Args:
        template_id: Google Slides presentation ID to copy
        title: Title for placeholder replacement
        copy_title: Name for the copied presentation (defaults to title)

    Returns:
        Copied presentation metadata with new presentationId
    """
    creds = _load_credentials()
    drive = _drive_service(creds)

    copy_title = copy_title or f"{title} - Generated"

    try:
        # Copy the template presentation
        copied_file = drive.files().copy(
            fileId=template_id,
            body={"name": copy_title}
        ).execute()

        new_pres_id = copied_file["id"]
        log.info(
            "Copied template %s to new presentation %s (%s)",
            template_id,
            copy_title,
            new_pres_id
        )

        # Optional: Replace placeholder text
        slides_service = _slides_service(creds)
        pres = slides_service.presentations().get(
            presentationId=new_pres_id
        ).execute()

        # Replace {{TITLE}} placeholder if it exists
        replace_requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": "{{TITLE}}", "matchCase": False},
                    "replaceText": title
                }
            },
            {
                "replaceAllText": {
                    "containsText": {"text": "{{DATE}}", "matchCase": False},
                    "replaceText": time.strftime("%B %d, %Y")
                }
            }
        ]

        slides_service.presentations().batchUpdate(
            presentationId=new_pres_id,
            body={"requests": replace_requests}
        ).execute()

        return pres

    except HttpError as e:
        _log_http_error("create_presentation_from_template", e)
        raise
```

**Configuration** (add to `config.yaml`):
```yaml
slides:
  templates:
    corporate: "1ABC123_corporate_template_id"
    creative: "1XYZ789_creative_template_id"
    minimal: "1DEF456_minimal_template_id"
  default_template: "corporate"
```

**Usage in Orchestrator**:
```python
# src/mcp_lab/orchestrator.py
from src.common.config import load_config

config = load_config()
template_id = config["slides"]["templates"].get(
    template_style,  # from user input
    config["slides"]["templates"][config["slides"]["default_template"]]
)

pres = create_presentation_from_template(
    template_id=template_id,
    title=title
)
```

---

### Approach 2: Use Predefined Layouts (Moderate)

**Best For**: Standard Google Slides layouts, theme-based styling, no custom templates

**How It Works**:
1. Create presentation with a **theme** applied
2. Use Google's built-in layouts: `TITLE_AND_BODY`, `TITLE_ONLY`, `SECTION_HEADER`, etc.
3. Leverage placeholders that come with layouts
4. Apply theme colors and fonts

**Pros**:
- ✅ No external template file needed
- ✅ Uses Google's semantic layouts (better for accessibility)
- ✅ Placeholders automatically positioned
- ✅ Easy to switch themes

**Cons**:
- ❌ Limited to Google's predefined layouts
- ❌ Less customization than copying templates
- ❌ Theme must be specified upfront

**Available Predefined Layouts**:
```python
# Google Slides API predefined layouts
LAYOUTS = {
    "BLANK": "Blank slide with no placeholders",
    "TITLE": "Title slide with title and subtitle placeholders",
    "TITLE_AND_BODY": "Title at top, body text below",
    "TITLE_AND_TWO_COLUMNS": "Title with two-column layout",
    "TITLE_ONLY": "Title placeholder only",
    "SECTION_HEADER": "Section break with title",
    "CAPTION_ONLY": "Caption text only",
    "BIG_NUMBER": "Large number with caption",
    "ONE_COLUMN_TEXT": "Single text column",
    "MAIN_POINT": "Main point with subtitle"
}
```

**Implementation**:

```python
# src/agent/slides_google.py - Modify existing functions

def create_presentation_with_theme(
    title: str,
    theme_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a presentation with a specific theme applied.

    Args:
        title: Presentation title
        theme_id: Optional Google Slides theme ID (e.g., "BEACH", "MODERN_WRITER")

    Returns:
        Presentation metadata
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    body = {"title": title}

    # If theme_id provided, apply it
    # Note: Themes must be copied from public Google templates first
    # or use presentation.pages[0].slideProperties.masterObjectId

    try:
        pres = slides.presentations().create(body=body).execute()
        pres_id = pres["presentationId"]

        # If theme specified, apply it via replaceAllShapesWithImage or similar
        # Google Slides API doesn't directly support theme_id in create()
        # You need to copy a themed template instead (see Approach 1)

        log.info("Created presentation with title: %s", title)
        return pres

    except HttpError as e:
        _log_http_error("create_presentation_with_theme", e)
        raise


def add_slide_with_layout(
    presentation_id: str,
    layout: str = "TITLE_AND_BODY",
    title: str = "",
    body_text: str = ""
) -> str:
    """
    Add a slide using a predefined layout and populate placeholders.

    Args:
        presentation_id: Existing presentation ID
        layout: One of the predefined layout types
        title: Text for title placeholder
        body_text: Text for body placeholder

    Returns:
        Created slide's objectId
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    slide_id = _gen_id("slide")

    requests = [
        {
            "createSlide": {
                "objectId": slide_id,
                "slideLayoutReference": {
                    "predefinedLayout": layout  # Use built-in layout
                }
            }
        }
    ]

    try:
        # Create the slide with layout
        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()

        # Fetch the slide to find placeholder object IDs
        pres = slides.presentations().get(
            presentationId=presentation_id
        ).execute()

        # Find the created slide
        created_slide = None
        for s in pres.get("slides", []):
            if s.get("objectId") == slide_id:
                created_slide = s
                break

        if not created_slide:
            log.warning("Could not find created slide %s", slide_id)
            return slide_id

        # Find placeholders by type
        title_placeholder_id = None
        body_placeholder_id = None

        for element in created_slide.get("pageElements", []):
            placeholder = element.get("shape", {}).get("placeholder", {})
            placeholder_type = placeholder.get("type")

            if placeholder_type == "TITLE" or placeholder_type == "CENTERED_TITLE":
                title_placeholder_id = element.get("objectId")
            elif placeholder_type == "BODY" or placeholder_type == "SUBTITLE":
                body_placeholder_id = element.get("objectId")

        # Insert text into placeholders
        text_requests = []

        if title_placeholder_id and title:
            text_requests.append({
                "insertText": {
                    "objectId": title_placeholder_id,
                    "text": title,
                    "insertionIndex": 0
                }
            })

        if body_placeholder_id and body_text:
            text_requests.append({
                "insertText": {
                    "objectId": body_placeholder_id,
                    "text": body_text,
                    "insertionIndex": 0
                }
            })

        if text_requests:
            slides.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": text_requests}
            ).execute()

        log.info("Added slide with layout %s: %s", layout, slide_id)
        return slide_id

    except HttpError as e:
        _log_http_error("add_slide_with_layout", e)
        raise
```

**Usage**:
```python
# Instead of current BLANK approach:
slide_id = add_slide_with_layout(
    presentation_id=pres_id,
    layout="TITLE_AND_BODY",
    title="Market Analysis",
    body_text="• Revenue up 25%\n• Customer satisfaction: 4.8/5\n• Market share increased"
)
```

---

### Approach 3: Master Slide Manipulation (Advanced)

**Best For**: Full control over themes, custom layouts, programmatic template generation

**How It Works**:
1. Create presentation
2. Fetch `masters` (theme/template definitions)
3. Modify master slide properties (colors, fonts, layouts)
4. Create slides referencing modified masters

**Pros**:
- ✅ Complete control over themes
- ✅ Programmatic template generation
- ✅ No external files needed
- ✅ Can create custom layouts

**Cons**:
- ❌ Most complex implementation
- ❌ Requires deep understanding of Slides API
- ❌ Fragile (API changes can break it)
- ❌ Not recommended for MVP

**Implementation Sketch** (not recommended for now):
```python
def create_custom_master_slide(presentation_id: str, theme_colors: dict):
    """
    Modify the master slide to apply custom branding.
    This is VERY complex and not recommended for most use cases.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    pres = slides.presentations().get(presentationId=presentation_id).execute()

    # Find the master slides
    masters = pres.get("masters", [])
    if not masters:
        log.warning("No masters found in presentation")
        return

    master_id = masters[0].get("objectId")

    # Update master slide colors
    requests = [
        {
            "updatePageProperties": {
                "objectId": master_id,
                "pageProperties": {
                    "colorScheme": {
                        "colors": [
                            {"type": "ACCENT1", "color": {"rgbColor": theme_colors["accent1"]}},
                            {"type": "DARK1", "color": {"rgbColor": theme_colors["dark1"]}},
                            # ... more colors
                        ]
                    }
                },
                "fields": "colorScheme"
            }
        }
    ]

    slides.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests}
    ).execute()
```

**Verdict**: Skip this for now. Use Approach 1 (copy template) or Approach 2 (predefined layouts).

---

## Recommended Implementation Strategy

### Phase 1: Copy Template (Quick Win)

**Timeline**: 1 day

**Steps**:
1. Create 3 template presentations manually in Google Slides:
   - Corporate (blue theme, professional)
   - Creative (colorful, modern)
   - Minimal (clean, simple)

2. Add placeholder text: `{{TITLE}}`, `{{DATE}}`, `{{COMPANY}}`

3. Implement `create_presentation_from_template()` function

4. Update `orchestrate()` to accept `template_id` parameter

5. Expose template selection in Web UI (dropdown)

**Configuration**:
```yaml
# config.yaml
slides:
  templates:
    corporate: "1ABC123_google_slides_id"
    creative: "1XYZ789_google_slides_id"
    minimal: "1DEF456_google_slides_id"
  default_template: "corporate"

  # Placeholder replacements
  placeholders:
    - "{{TITLE}}"
    - "{{DATE}}"
    - "{{COMPANY}}"
```

**Frontend Changes** (`presgen-ui/src/components/CoreForm.tsx`):
```tsx
// Add template selector
<Select value={templateStyle} onValueChange={setTemplateStyle}>
  <SelectTrigger>
    <SelectValue placeholder="Select template" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="corporate">Corporate</SelectItem>
    <SelectItem value="creative">Creative</SelectItem>
    <SelectItem value="minimal">Minimal</SelectItem>
  </SelectContent>
</Select>
```

### Phase 2: Use Predefined Layouts (Better)

**Timeline**: 2 days

**Steps**:
1. Implement `add_slide_with_layout()` function

2. Map Presgen slide types to Google layouts:
   - Title slide → `TITLE`
   - Content slide → `TITLE_AND_BODY`
   - Data slide → `TITLE_ONLY` (manual image placement)
   - Section break → `SECTION_HEADER`

3. Update `add_bullets_and_script()` to use layouts instead of BLANK

4. Add placeholder detection and population

**Slide Type Mapping**:
```python
# src/agent/slides_google.py

SLIDE_TYPE_TO_LAYOUT = {
    "title": "TITLE",
    "content": "TITLE_AND_BODY",
    "data": "TITLE_ONLY",
    "section": "SECTION_HEADER",
    "blank": "BLANK"
}

def create_slide_by_type(
    presentation_id: str,
    slide_type: str,
    content: dict
) -> str:
    """
    Create a slide using appropriate layout for the content type.
    """
    layout = SLIDE_TYPE_TO_LAYOUT.get(slide_type, "TITLE_AND_BODY")

    return add_slide_with_layout(
        presentation_id=presentation_id,
        layout=layout,
        title=content.get("title", ""),
        body_text="\n".join(content.get("bullets", []))
    )
```

### Phase 3: Template Management System (Future)

**Timeline**: 1 week

**Features**:
- Template gallery in Web UI
- Upload custom templates
- Template preview thumbnails
- Per-user template library
- Template versioning

---

## Best Practices & Rules

### Rule 1: Always Use Template IDs, Not URLs

**Wrong**:
```python
template = "https://docs.google.com/presentation/d/1ABC123/edit"
```

**Right**:
```python
template_id = "1ABC123"  # Extract ID from URL
```

### Rule 2: Handle Missing Templates Gracefully

```python
def get_template_id(template_name: str) -> str:
    config = load_config()
    templates = config.get("slides", {}).get("templates", {})

    template_id = templates.get(template_name)

    if not template_id:
        log.warning(
            "Template '%s' not found, using default",
            template_name
        )
        return templates.get(
            config["slides"]["default_template"],
            None  # Will create blank if even default missing
        )

    return template_id
```

### Rule 3: Verify Template Permissions

Templates must be:
- ✅ Readable by the service account or OAuth user
- ✅ Copyable (Drive API needs copy permission)
- ✅ Shared with "Anyone with the link" (easiest) or specific accounts

**Test Template Access**:
```python
def verify_template_access(template_id: str) -> bool:
    """Check if template is accessible before using it."""
    creds = _load_credentials()
    drive = _drive_service(creds)

    try:
        file_metadata = drive.files().get(
            fileId=template_id,
            fields="id,name,permissions"
        ).execute()

        log.info("Template '%s' is accessible", file_metadata["name"])
        return True

    except HttpError as e:
        log.error("Cannot access template %s: %s", template_id, e)
        return False
```

### Rule 4: Clean Up Placeholder Text

```python
def replace_all_placeholders(
    presentation_id: str,
    replacements: dict
):
    """
    Replace all placeholder text in presentation.

    Args:
        presentation_id: Presentation ID
        replacements: Dict of {placeholder: value}
            Example: {"{{TITLE}}": "Q4 Results", "{{DATE}}": "Oct 24, 2025"}
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    requests = []

    for placeholder, value in replacements.items():
        requests.append({
            "replaceAllText": {
                "containsText": {"text": placeholder, "matchCase": False},
                "replaceText": value
            }
        })

    if requests:
        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()

        log.info("Replaced %d placeholders", len(requests))
```

### Rule 5: Preserve Template Slides as Examples

When copying a template, optionally:
- Keep first slide as example (don't delete)
- Or delete template slides after copying structure

```python
def remove_template_example_slides(
    presentation_id: str,
    keep_first_n: int = 1
):
    """
    Remove template example slides, keeping only the first N.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    pres = slides.presentations().get(presentationId=presentation_id).execute()

    slide_ids = [s["objectId"] for s in pres.get("slides", [])]

    # Keep first N slides (usually title slide), delete rest
    to_delete = slide_ids[keep_first_n:]

    if not to_delete:
        return

    requests = [
        {"deleteObject": {"objectId": sid}}
        for sid in to_delete
    ]

    slides.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests}
    ).execute()

    log.info("Removed %d template example slides", len(to_delete))
```

### Rule 6: Cache Template Metadata

Don't fetch template info on every generation:

```python
# src/common/template_cache.py

import json
from pathlib import Path

TEMPLATE_CACHE = Path("out/state/template_cache.json")

def cache_template_info(template_id: str, metadata: dict):
    """Cache template metadata to avoid repeated API calls."""
    cache = {}

    if TEMPLATE_CACHE.exists():
        cache = json.loads(TEMPLATE_CACHE.read_text())

    cache[template_id] = {
        "name": metadata.get("name"),
        "master_id": metadata.get("masters", [{}])[0].get("objectId"),
        "slide_count": len(metadata.get("slides", [])),
        "cached_at": time.time()
    }

    TEMPLATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_CACHE.write_text(json.dumps(cache, indent=2))

def get_cached_template_info(template_id: str) -> dict | None:
    """Retrieve cached template metadata."""
    if not TEMPLATE_CACHE.exists():
        return None

    cache = json.loads(TEMPLATE_CACHE.read_text())
    return cache.get(template_id)
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Template Not Found Error

**Error**:
```
HttpError 404: File not found: 1ABC123
```

**Cause**: Template ID is wrong or template not shared with service account

**Solution**:
```python
# Always verify template access first
if not verify_template_access(template_id):
    log.warning("Falling back to blank presentation")
    return create_presentation(title)  # Fallback to blank
```

### Pitfall 2: Placeholders Not Replaced

**Issue**: `{{TITLE}}` still appears in final presentation

**Cause**: Placeholder text is in a table cell, grouped object, or master slide

**Solution**:
```python
# Use recursive replacement for nested objects
requests = [
    {
        "replaceAllText": {
            "containsText": {"text": "{{TITLE}}", "matchCase": False},
            "replaceText": title,
            "pageObjectIds": []  # Empty = all pages including masters
        }
    }
]
```

### Pitfall 3: Layout Placeholders Not Detected

**Issue**: `add_slide_with_layout()` can't find title/body placeholders

**Cause**: Layout may not have placeholders, or they're nested in groups

**Solution**:
```python
def find_placeholder_recursive(element: dict, placeholder_type: str) -> str | None:
    """Recursively search for placeholder in element tree."""
    # Check if this element is the placeholder
    placeholder = element.get("shape", {}).get("placeholder", {})
    if placeholder.get("type") == placeholder_type:
        return element.get("objectId")

    # Check grouped elements
    for child in element.get("group", {}).get("children", []):
        result = find_placeholder_recursive(child, placeholder_type)
        if result:
            return result

    return None
```

### Pitfall 4: Template Permissions Revoked

**Issue**: Template works locally but fails in production

**Cause**: Template shared with personal account but not service account

**Solution**:
```yaml
# .env
TEMPLATE_SHARING_MODE=public  # or 'domain' or 'specific'

# If 'specific', template must grant permission to:
# presgen-sa@your-project.iam.gserviceaccount.com
```

### Pitfall 5: Slow Template Copying

**Issue**: Copying large templates takes 5-10 seconds

**Cause**: Drive API copy operation is synchronous

**Solution**:
```python
# Use async copy for large templates (future enhancement)
async def copy_template_async(template_id: str, title: str):
    # Implement async Drive API calls
    pass
```

---

## Testing Checklist

### Unit Tests

```python
# tests/test_templates.py

def test_create_from_template():
    """Test template copying works."""
    template_id = "1ABC123_test_template"
    pres = create_presentation_from_template(template_id, "Test Deck")

    assert pres["presentationId"]
    assert pres["title"] == "Test Deck - Generated"

def test_placeholder_replacement():
    """Test placeholders are replaced."""
    template_id = "1ABC123_with_placeholders"
    pres = create_presentation_from_template(template_id, "Q4 Results")

    # Verify {{TITLE}} was replaced
    slides_service = _slides_service(_load_credentials())
    pres_data = slides_service.presentations().get(
        presentationId=pres["presentationId"]
    ).execute()

    # Check no placeholders remain
    presentation_text = extract_all_text(pres_data)
    assert "{{TITLE}}" not in presentation_text

def test_layout_detection():
    """Test predefined layout detection."""
    pres = create_presentation("Test")
    slide_id = add_slide_with_layout(
        pres["presentationId"],
        layout="TITLE_AND_BODY",
        title="Test Title",
        body_text="Test Body"
    )

    assert slide_id
    # Verify placeholders were populated
```

### Integration Tests

1. **Manual Template Test**:
   - Create template in Google Slides UI
   - Add to `config.yaml`
   - Run: `python -m src.mcp_lab examples/report_demo.txt --template corporate`
   - Verify: Generated deck uses corporate template

2. **Web UI Test**:
   - Select "Creative" template in dropdown
   - Generate presentation
   - Verify: Deck uses creative styling

3. **Fallback Test**:
   - Set invalid template ID in config
   - Generate presentation
   - Verify: Falls back to blank presentation with warning log

---

## Production Deployment Considerations

### 1. Template Storage

**Option A: Hard-coded IDs** (simplest)
```yaml
# config.yaml
slides:
  templates:
    corporate: "1ABC123"
```

**Option B: Database** (scalable)
```sql
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    google_slides_id VARCHAR(100),
    owner_user_id INT,
    is_public BOOLEAN,
    created_at TIMESTAMP
);
```

**Option C: Google Drive Folder** (organized)
```python
# Store all templates in a specific Drive folder
TEMPLATE_FOLDER_ID = "0ABCxyz_folder_id"

def list_available_templates():
    drive = _drive_service(_load_credentials())
    results = drive.files().list(
        q=f"'{TEMPLATE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.presentation'",
        fields="files(id, name, thumbnailLink)"
    ).execute()

    return results.get("files", [])
```

### 2. Template Versioning

```python
# Add version suffix to template names
templates:
  corporate_v1: "1ABC123"
  corporate_v2: "1XYZ789"

# Or use Drive API to track versions
def get_template_version(template_id: str) -> int:
    drive = _drive_service(_load_credentials())
    file = drive.files().get(
        fileId=template_id,
        fields="version"
    ).execute()

    return int(file.get("version", 1))
```

### 3. Multi-Tenant Templates

```python
# Different templates per customer
templates:
  acme_corp:
    corporate: "1ABC_acme"
    creative: "1XYZ_acme"

  globex:
    corporate: "1DEF_globex"
    minimal: "1GHI_globex"

def get_customer_template(customer_id: str, style: str):
    config = load_config()
    customer_templates = config["slides"]["templates"].get(customer_id, {})

    return customer_templates.get(
        style,
        config["slides"]["templates"]["default"][style]  # Fallback
    )
```

---

## Example: Full Implementation

```python
# src/agent/slides_google.py - Complete template integration

def create_presentation_smart(
    title: str,
    template_id: Optional[str] = None,
    template_name: Optional[str] = None,
    placeholders: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Smart presentation creation with template support.

    Args:
        title: Presentation title
        template_id: Specific template ID to copy
        template_name: Template name from config (e.g., "corporate")
        placeholders: Dict of placeholder replacements

    Returns:
        Presentation metadata
    """
    # Determine template to use
    if not template_id and template_name:
        template_id = get_template_id(template_name)

    # If template specified, use it
    if template_id:
        if verify_template_access(template_id):
            pres = create_presentation_from_template(
                template_id=template_id,
                title=title
            )

            # Replace placeholders
            if placeholders:
                default_placeholders = {
                    "{{TITLE}}": title,
                    "{{DATE}}": time.strftime("%B %d, %Y")
                }
                default_placeholders.update(placeholders)

                replace_all_placeholders(
                    pres["presentationId"],
                    default_placeholders
                )

            return pres
        else:
            log.warning("Template %s not accessible, creating blank", template_id)

    # Fallback to blank presentation
    return create_presentation(title)


# src/mcp/tools/slides.py - Update to accept template

def slides_create(
    title: str,
    sections: list[dict],
    template_name: str = "default",  # NEW PARAMETER
    **kwargs
) -> dict:
    """Create slides from sections using specified template."""

    # Create presentation with template
    pres = create_presentation_smart(
        title=title,
        template_name=template_name
    )

    pres_id = pres["presentationId"]

    # Add slides using template's layout style
    for section in sections:
        add_slide_with_layout(
            presentation_id=pres_id,
            layout="TITLE_AND_BODY",  # Or detect from template
            title=section["title"],
            body_text="\n".join(section["bullets"])
        )

    return {
        "presentation_id": pres_id,
        "url": f"https://docs.google.com/presentation/d/{pres_id}/edit"
    }
```

---

## Summary & Next Steps

### Recommended Approach: Copy Template (Approach 1)

**Why**:
- Easiest to implement (1 day)
- Non-technical users can create templates
- Full control over branding
- Works with existing Presgen code

**Implementation Steps**:
1. ✅ Create 3 template presentations manually
2. ✅ Add `create_presentation_from_template()` function
3. ✅ Update `config.yaml` with template IDs
4. ✅ Add template selector to Web UI
5. ✅ Test with real presentations

**Estimated Time**: 1 day

### Future Enhancement: Predefined Layouts (Approach 2)

**When**: After MVP launch, if users request more layout variety

**Benefits**:
- Better accessibility (semantic layouts)
- No template maintenance
- More flexible slide types

**Estimated Time**: 2 days

---

## Resources

- [Google Slides API - Presentations](https://developers.google.com/slides/api/reference/rest/v1/presentations)
- [Google Slides API - Layouts](https://developers.google.com/slides/api/reference/rest/v1/presentations.pages#Layout)
- [Predefined Layouts Reference](https://developers.google.com/slides/api/reference/rest/v1/presentations.pages#PredefinedLayout)
- [Drive API - Copy Files](https://developers.google.com/drive/api/v3/reference/files/copy)

**Status**: This guide provides everything needed to implement Google Slides templates in Presgen. Start with Approach 1 (copy template) for quickest results.
