# src/mcp_lab/orchestrator.py
from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Environment variable for cache control with development mode support
def _get_cache_setting():
    # Option C: Auto-disable cache in development mode
    dev_mode = os.getenv("NODE_ENV") == "development" or os.getenv("PRESGEN_DEV_MODE", "false").lower() == "true"
    if dev_mode:
        return False

    # Otherwise use explicit setting or default to true for production
    return os.getenv("PRESGEN_USE_CACHE", "true").lower() == "true"

PRESGEN_USE_CACHE = _get_cache_setting()

from .rpc_client import MCPClient, ToolError
from src.common.cache import get as cache_get, set as cache_set, llm_key, imagen_key
from src.common.jsonlog import jlog

log = logging.getLogger("orchestrator")


def _truncate_script(script: str, max_len: int) -> str:
    """
    Intelligently truncate script content to fit slide character limits.
    Tries to break at word boundaries and add ellipsis if truncated.
    """
    if len(script) <= max_len:
        return script
    
    # Find the last space before the limit
    truncated = script[:max_len - 3]  # Leave room for "..."
    last_space = truncated.rfind(' ')
    last_newline = truncated.rfind('\n')
    
    # Break at the latest word/line boundary
    break_point = max(last_space, last_newline)
    if break_point > max_len // 2:  # Only if we don't lose too much content
        return script[:break_point] + "..."
    else:
        return script[:max_len - 3] + "..."


def orchestrate(
    report_text: str,
    *,
    client_request_id: Optional[str] = None,
    slide_count: int = 3,
    use_cache: bool = False,
    cache_ttl_secs: Optional[float] = 36000.0,
    llm_model: str = "models/gemini-2.0-flash-001",
    imagen_model: str = "imagegeneration@006",
    imagen_size: str = "1280x720",
) -> Dict[str, Any]:
    """
    Flow:
      1) llm.summarize -> sections[] (or single slide fields)
      2) For each section up to slide_count (≤ N):
           image.generate (best effort, cached)
           slides.create (first creates deck; rest append via presentation_id)
    """
    jlog(
        log,
        logging.INFO,
        event="** orchestrate_begin **",
        slide_count=slide_count,
        req_id=client_request_id,
    )
    req_id = client_request_id or str(uuid.uuid4())
    jlog(
        log,
        logging.INFO,
        event="orchestrate_begin 2",
        slide_count=slide_count,
        req_id=client_request_id,
    )

    # ----------------------------
    # 1) LLM summarize (with cache)
    # ----------------------------
    # Cap the hint sensibly (don’t force N, just allow up to N)
    max_sections_hint = max(1, min(10, slide_count))

    # include the hint in the cache key so different requested sizes don’t collide
    llm_cache_key = (
        llm_key(report_text, 5, 700, llm_model) + f":msec={max_sections_hint}"
    )
    # still in orchestrate()
    jlog(
        log,
        logging.INFO,
        event="summarize_call",
        max_sections=max_sections_hint,
        max_bullets=5,
        max_script_chars=700,
        req_id=req_id,
    )

    def _call_llm() -> Dict[str, Any]:
        with MCPClient() as client:
            s = client.call(
                "llm.summarize",
                {
                    "report_text": report_text,
                    "max_bullets": 5,
                    "max_script_chars": 700,
                    # ✅ correct: “no more than N”, tool may return fewer
                    "max_sections": max_sections_hint,
                },
                req_id=req_id,
            )
            # 🔧 Debug log instead of print to avoid JSON serialization issues
            jlog(
                log,
                logging.DEBUG,
                event="llm_summarize_raw_result",
                sections_count=len(s.get("sections", [])),
                req_id=req_id,
                result_keys=list(s.keys()) if isinstance(s, dict) else []
            )
            return s

    if use_cache:
        cached = cache_get("llm_summarize", llm_cache_key, ttl_secs=cache_ttl_secs)
        if cached:
            jlog(
                log,
                logging.INFO,
                event="cache_hit",
                layer="llm.summarize",
                req_id=req_id,
            )
            s = cached
        else:
            s = _call_llm()
            cache_set("llm_summarize", llm_cache_key, s)
            jlog(
                log,
                logging.INFO,
                event="cache_miss_store",
                layer="llm.summarize",
                req_id=req_id,
            )
    else:
        s = _call_llm()

    # Normalize to sections[]
    sections = s.get("sections")
    if not isinstance(sections, list):
        sections = [
            {
                "title": s.get("title") or "Untitled",
                "subtitle": s.get("subtitle"),
                "bullets": s.get("bullets") or [],
                "script": s.get("script") or "",
                "image_prompt": s.get("image_prompt"),
            }
        ]

    jlog(
        log,
        logging.INFO,
        event="summarize_result",
        received_sections=len(sections),
        req_id=req_id,
    )

    jlog(
        log,
        logging.INFO,
        event="section_cap",
        requested=slide_count,
        will_use=min(slide_count, len(sections)),
        req_id=req_id,
    )

    jlog(
        log,
        logging.INFO,
        event="sections_debug",
        count=len(sections),
        titles=[(sec.get("title") or "")[:60] for sec in sections],
    )

    # Never fabricate slides; use at most slide_count
    desired = max(1, min(10, slide_count))
    actual = min(desired, len(sections))
    if actual < desired:
        jlog(
            log,
            logging.INFO,
            event="fewer_sections_than_requested",
            requested=desired,
            received=len(sections),
            will_create=actual,
            req_id=req_id,
        )
    # pad sections to reach desired count (simple, safe)
    # if len(sections) < desired:
    #     last = sections[-1] if sections else {"title":"Overview","bullets":[],"script":""}
    #     for i in range(desired - len(sections)):
    #         sections.append({
    #             "title": f"{last.get('title','Section')} (cont. {i+1})",
    #             "subtitle": last.get("subtitle"),
    #             "bullets": (last.get("bullets") or [])[:3],  # trim
    #             "script": (last.get("script") or "")[:700],
    #             "image_prompt": last.get("image_prompt"),
    #         })
    if actual == 0:
        return {
            "presentation_id": None,
            "url": None,
            "created_slides": 0,
            "first_slide_id": None,
        }

    # ---------------------------------
    # 2) For each section (≤ N): build
    # ---------------------------------
    created_pres_id: Optional[str] = None
    deck_url: Optional[str] = None
    first_slide_id: Optional[str] = None

    for idx, sec in enumerate(sections[:actual], start=1):
        per_slide_id = f"{req_id}#s{idx}"

        # 2a) Best-effort image (with cache)
        image_url: Optional[str] = None
        image_drive_file_id: Optional[str] = None
        image_local_path: Optional[str] = None
        image_prompt = sec.get("image_prompt")

        def _imagen_call() -> Dict[str, Any]:
            with MCPClient() as client:
                return client.call(
                    "image.generate",
                    {
                        "prompt": image_prompt,
                        "aspect": "16:9",
                        "size": imagen_size,
                        "safety_tier": "default",
                        "return_drive_link": True,
                    },
                    req_id=per_slide_id,
                )

        if image_prompt:
            try:
                if use_cache:
                    ikey = imagen_key(
                        image_prompt, "16:9", imagen_size, imagen_model, True
                    )
                    icached = cache_get("imagen", ikey, ttl_secs=cache_ttl_secs)
                    if icached and (
                        icached.get("image_url") or icached.get("drive_file_id")
                    ):
                        jlog(
                            log,
                            logging.INFO,
                            event="cache_hit",
                            layer="image.generate",
                            req_id=per_slide_id,
                        )
                        raw_image_url = icached.get("image_url")
                        image_drive_file_id = icached.get("drive_file_id")
                        
                        # Ensure cached image_url is a string, not bytes
                        if isinstance(raw_image_url, bytes):
                            jlog(log, logging.ERROR, event="cached_image_url_is_bytes", 
                                 req_id=per_slide_id, bytes_length=len(raw_image_url))
                            image_url = None  # Don't use bytes as URL
                        else:
                            image_url = raw_image_url
                    else:
                        try:
                            g = _imagen_call()
                            # Check if result contains any bytes objects
                            if any(isinstance(v, bytes) for v in (g.values() if isinstance(g, dict) else [])):
                                jlog(log, logging.ERROR, event="imagen_result_contains_bytes", req_id=per_slide_id)
                                # Clean the result
                                g = {k: ("<bytes_removed>" if isinstance(v, bytes) else v) 
                                     for k, v in g.items()} if isinstance(g, dict) else g
                            jlog(
                                log,
                                logging.INFO,
                                event="image_generate_raw",
                                req_id=per_slide_id,
                                result_keys=list(g.keys()) if isinstance(g, dict) else [],
                                has_image_url=bool(g.get("image_url") or g.get("url")),
                                has_drive_file_id=bool(g.get("drive_file_id")),
                                has_local_path=bool(g.get("local_path"))
                            )
                            raw_image_url = g.get("image_url") or g.get("url")
                            image_drive_file_id = g.get("drive_file_id")
                            image_local_path = g.get("local_path")
                            
                            # Ensure image_url is a string, not bytes
                            if isinstance(raw_image_url, bytes):
                                jlog(log, logging.ERROR, event="image_url_is_bytes", 
                                     req_id=per_slide_id, bytes_length=len(raw_image_url))
                                image_url = None  # Don't use bytes as URL
                            else:
                                image_url = raw_image_url
                            cache_set(
                                "imagen",
                                ikey,
                                {
                                    "image_url": image_url,
                                    "drive_file_id": image_drive_file_id,
                                },
                            )
                            jlog(
                                log,
                                logging.INFO,
                                event="cache_miss_store",
                                layer="image.generate",
                                req_id=per_slide_id,
                            )
                        except Exception as e:
                            jlog(
                                log,
                                logging.WARNING,
                                event="image_generate_failed",
                                req_id=per_slide_id,
                                error=str(e),
                                fallback="proceeding_without_image"
                            )
                            # Continue without image - set all image variables to None
                            image_url = None
                            image_drive_file_id = None
                            image_local_path = None
                else:
                    try:
                        g = _imagen_call()
                        # Check if result contains any bytes objects  
                        if any(isinstance(v, bytes) for v in (g.values() if isinstance(g, dict) else [])):
                            jlog(log, logging.ERROR, event="imagen_result_contains_bytes_no_cache", req_id=per_slide_id)
                            # Clean the result
                            g = {k: ("<bytes_removed>" if isinstance(v, bytes) else v) 
                                 for k, v in g.items()} if isinstance(g, dict) else g
                        raw_image_url = g.get("image_url") or g.get("url")
                        image_drive_file_id = g.get("drive_file_id")
                        image_local_path = g.get("local_path")
                        
                        # Ensure image_url is a string, not bytes
                        if isinstance(raw_image_url, bytes):
                            jlog(log, logging.ERROR, event="image_url_is_bytes_no_cache", 
                                 req_id=per_slide_id, bytes_length=len(raw_image_url))
                            image_url = None  # Don't use bytes as URL
                        else:
                            image_url = raw_image_url
                    except Exception as e:
                        jlog(
                            log,
                            logging.WARNING,
                            event="image_generate_failed_no_cache",
                            req_id=per_slide_id,
                            error=str(e),
                            fallback="proceeding_without_image"
                        )
                        # Continue without image - set all image variables to None
                        image_url = None
                        image_drive_file_id = None
                        image_local_path = None

                if not (image_url or image_drive_file_id or image_local_path):
                    jlog(
                        log,
                        logging.WARNING,
                        event="image_generate_no_usable_fields",
                        req_id=per_slide_id,
                        keys=list(g.keys()) if "g" in locals() else [],
                    )
            except ToolError as e:
                jlog(
                    log,
                    logging.WARNING,
                    event="image_generate_failed",
                    req_id=per_slide_id,
                    err=str(e),
                )

        # 2b) Create or append slide
        slide_params: Dict[str, Any] = {
            "client_request_id": per_slide_id,  # idempotency per slide
            "title": sec.get("title") or "Untitled",
            "subtitle": sec.get("subtitle"),
            "bullets": sec.get("bullets") or [],
            "script": sec.get("script") or "",
            "share_image_public": True,
            "aspect": "16:9",
            "use_cache": use_cache,  # Pass through cache setting
        }
        if image_url:
            slide_params["image_url"] = image_url
        elif image_drive_file_id:
            slide_params["image_drive_file_id"] = image_drive_file_id
        elif image_local_path:
            slide_params["image_local_path"] = image_local_path

        if created_pres_id:
            slide_params["presentation_id"] = created_pres_id  # append mode

        # Validate slide_params for bytes objects before sending to MCP server
        bytes_keys = []
        for key, value in slide_params.items():
            if isinstance(value, bytes):
                jlog(log, logging.ERROR, event="slide_params_contains_bytes", 
                     key=key, bytes_length=len(value), req_id=per_slide_id)
                bytes_keys.append(key)
        
        # Remove bytes objects to prevent JSON serialization error
        for key in bytes_keys:
            del slide_params[key]
            
        if bytes_keys:
            jlog(log, logging.WARNING, event="removed_bytes_from_slide_params", 
                 removed_keys=bytes_keys, req_id=per_slide_id)
        
        # Debug log slide params safely
        safe_params = {k: v for k, v in slide_params.items() if not isinstance(v, bytes)}
        safe_params['has_image_url'] = bool(slide_params.get('image_url'))
        safe_params['has_image_drive_file_id'] = bool(slide_params.get('image_drive_file_id'))
        safe_params['has_image_local_path'] = bool(slide_params.get('image_local_path'))
        
        jlog(
            log,
            logging.DEBUG,
            event="slide_params_debug",
            slide_index=idx,
            req_id=per_slide_id,
            slide_params=safe_params
        )

        with MCPClient() as client:
            try:
                jlog(log, logging.INFO, event="slides_create_attempt", 
                     req_id=per_slide_id, slide_index=idx, presentation_id=created_pres_id)
                create_res = client.call(
                    "slides.create", slide_params, req_id=per_slide_id, timeout=120.0
                )
                jlog(log, logging.INFO, event="slides_create_success", 
                     req_id=per_slide_id, result_keys=list(create_res.keys()))
            except TimeoutError as e:
                jlog(
                    log,
                    logging.ERROR,
                    event="slides_create_timeout",
                    req_id=per_slide_id,
                    err=str(e),
                    slide_params_keys=list(slide_params.keys()),
                    timeout=120.0
                )
                # continue; record a placeholder so we still finish the deck
                continue
            except Exception as e:
                import traceback
                jlog(
                    log,
                    logging.ERROR,
                    event="slides_create_exception",
                    req_id=per_slide_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    stack_trace=traceback.format_exc(),
                    slide_params_keys=list(slide_params.keys())
                )
                # Re-raise this exception since it's likely a critical error
                raise
        if idx == 1:
            created_pres_id = create_res.get("presentation_id") or created_pres_id
            deck_url = create_res.get("url") or deck_url
            first_slide_id = create_res.get("slide_id") or first_slide_id

        jlog(
            log,
            logging.INFO,
            event="slide_ok",
            req_id=per_slide_id,
            idx=idx,
            presentation_id=created_pres_id,
            slide_id=create_res.get("slide_id"),
        )

    result = {
        "presentation_id": created_pres_id,
        "url": deck_url,
        "created_slides": actual,
        "first_slide_id": first_slide_id,
    }

    jlog(
        log,
        logging.INFO,
        event="orchestrate_ok",
        req_id=req_id,
        presentation_id=created_pres_id,
        url=deck_url,
        created_slides=actual,
        result_dict=result,
    )

    return result


def _stable_request_id(report_text: str) -> str:
    h = hashlib.sha256(report_text.encode("utf-8")).hexdigest()[:16]
    return f"req-{h}"


def orchestrate_many(
    items: Iterable[Tuple[str, str]],
    *,
    sleep_between_secs: float = 0.0,
    slide_count: int = 1,
) -> List[Dict[str, Any]]:
    item_list: List[Tuple[str, str]] = list(items)

    results: List[Dict[str, Any]] = []
    for idx, (name, text) in enumerate(item_list, start=1):
        req_id = _stable_request_id(text)
        jlog(
            log,
            logging.INFO,
            event="batch_item_start",
            idx=idx,
            name=name,
            req_id=req_id,
        )
        try:
            res = orchestrate(text, client_request_id=req_id, slide_count=slide_count)
            results.append(
                {
                    "name": name,
                    "request_id": req_id,
                    "presentation_id": res.get("presentation_id"),
                    "url": res.get("url"),
                    "created_slides": res.get("created_slides"),
                    "ok": True,
                    "error": None,
                }
            )
            jlog(
                log,
                logging.INFO,
                event="batch_item_ok",
                idx=idx,
                name=name,
                req_id=req_id,
                url=res.get("url"),
            )
        except Exception as e:
            results.append(
                {
                    "name": name,
                    "request_id": req_id,
                    "presentation_id": None,
                    "url": None,
                    "created_slides": 0,
                    "ok": False,
                    "error": str(e),
                }
            )
            jlog(
                log,
                logging.ERROR,
                event="batch_item_fail",
                idx=idx,
                name=name,
                req_id=req_id,
                err=str(e),
            )

        if sleep_between_secs > 0 and idx < len(item_list):
            time.sleep(sleep_between_secs)

    ok_count = sum(1 for r in results if r["ok"])
    jlog(
        log,
        logging.INFO,
        event="batch_summary",
        total=len(item_list),
        ok=ok_count,
        fail=len(results) - ok_count,
    )
    return results


def orchestrate_mixed(
    report_text: str,
    *,
    slide_count: int = 3,
    dataset_id: str | None = None,
    data_questions: list[str] | None = None,
    sheet: str | None = None,
    client_request_id: str | None = None,
    use_cache: bool = PRESGEN_USE_CACHE,
) -> dict:
    pres_id: Optional[str] = None
    deck_url: Optional[str] = None
    total_created = 0
    
    # Smart slide allocation: respect user's total slide count request
    n_data_questions = len(data_questions or [])
    has_data = bool(dataset_id and data_questions)
    
    if has_data:
        # Use all requested data questions, but respect total slide count
        data_slides_max = min(n_data_questions, slide_count)
        narrative_slides = max(0, slide_count - data_slides_max)
    else:
        data_slides_max = 0
        narrative_slides = slide_count
    
    jlog(
        log,
        logging.INFO,
        event="orchestrate_mixed_begin",
        slide_count=slide_count,
        has_data=has_data,
        n_data_questions=n_data_questions,
        data_slides_allocated=data_slides_max if has_data else 0,
        narrative_slides_allocated=narrative_slides,
        req_id=client_request_id,
    )
    
    # Create narrative slides first (if any)
    if narrative_slides > 0:
        try:
            jlog(log, logging.INFO, event="orchestrate_mixed_narrative_begin", 
                 narrative_slides=narrative_slides, req_id=client_request_id)
            base = orchestrate(
                report_text,
                client_request_id=client_request_id,
                slide_count=narrative_slides,
                use_cache=use_cache,
            )
            pres_id = pres_id or base.get("presentation_id")
            deck_url = deck_url or base.get("url")
            total_created += base.get("created_slides") or 0
            jlog(log, logging.INFO, event="orchestrate_mixed_narrative_success", 
                 created_slides=base.get("created_slides"), pres_id=pres_id, 
                 has_url=bool(deck_url), req_id=client_request_id)
        except Exception as e:
            import traceback
            jlog(log, logging.ERROR, event="orchestrate_mixed_narrative_failed", 
                 error=str(e), error_type=type(e).__name__, 
                 stack_trace=traceback.format_exc(), req_id=client_request_id)
            # Don't continue with data slides if narrative creation failed
            raise

    # Create data slides (limited by allocation)
    if dataset_id and data_questions:
        with MCPClient() as mcp:
            # Only process up to the allocated number of data slides
            questions_to_process = data_questions[:data_slides_max] if has_data else data_questions
            for i, q in enumerate(questions_to_process, 1):
                per_slide_id = f"{(client_request_id or _stable_request_id(q))}#dq{i}"
                jlog(
                    log,
                    logging.INFO,
                    event="mixed_data_q_begin",
                    idx=i,
                    req_id=per_slide_id,
                    question=q,
                    dataset_id=dataset_id,
                    sheet=sheet,
                )

                # 1) Run the data query (fallback to text-only slide on failure)
                try:
                    jlog(
                        log,
                        logging.INFO,
                        event="data_query_call_begin",
                        req_id=per_slide_id,
                        question=q,
                        dataset_id=dataset_id,
                    )
                    dq = mcp.call(
                        "data.query",
                        {
                            "dataset_id": dataset_id,
                            "question": q,
                            "sheet": sheet,
                            "req_id": per_slide_id,  # Pass through the request ID
                        },
                        req_id=per_slide_id,
                        timeout=90.0,  # Explicit timeout for data queries
                    )
                    jlog(
                        log,
                        logging.INFO,
                        event="data_query_call_complete",
                        req_id=per_slide_id,
                        has_chart=bool(dq.get("chart_png_path")),
                        has_bullets=len(dq.get("bullets", [])),
                    )
                    jlog(
                        log,
                        logging.INFO,
                        event="data_query_ok",
                        req_id=per_slide_id,
                        has_chart=bool(dq.get("chart_png_path")),
                    )
                except Exception as e:
                    jlog(
                        log,
                        logging.ERROR,
                        event="data_query_failed",
                        req_id=per_slide_id,
                        q=q,
                        err=str(e),
                    )
                    # create a minimal payload so downstream never sees None
                    dq = {
                        "insights": [f"Could not compute: {q}"],
                        "chart_png_path": None,
                        "table_md": "",
                    }

                # 2) Build slide params
                params: Dict[str, Any] = {
                    "client_request_id": per_slide_id,
                    "presentation_id": pres_id,  # None on first slide → tool will create deck
                    "title": q,
                    "bullets": dq.get("bullets") or dq.get("insights") or [],  # NEW: Use MVP bullets first, fallback to insights
                    "script": _truncate_script(dq.get("table_md") or "", 690),
                    "aspect": "16:9",
                    "share_image_public": True,
                    "use_cache": use_cache,  # NEW: Pass through use_cache parameter
                }
                if dq.get("chart_png_path"):
                    params["image_local_path"] = dq["chart_png_path"]

                # 3) Create the slide (never read `res` unless set)
                slide_res = None
                try:
                    jlog(
                        log,
                        logging.INFO,
                        event="slides_create_begin",
                        req_id=per_slide_id,
                        has_local_image=bool(params.get("image_local_path")),
                        image_path=params.get("image_local_path", "none"),
                        use_cache=use_cache,
                        bullets_count=len(params.get("bullets", [])),
                    )
                    slide_res = mcp.call(
                        "slides.create", params
                    )  # timeout handled per-method
                    pres_id = pres_id or slide_res.get("presentation_id")
                    deck_url = deck_url or slide_res.get("url")
                    total_created += 1
                    jlog(
                        log,
                        logging.INFO,
                        event="data_slide_ok",
                        req_id=per_slide_id,
                        slide_id=slide_res.get("slide_id"),
                    )
                except TimeoutError as e:
                    jlog(
                        log,
                        logging.ERROR,
                        event="slides_create_timeout",
                        req_id=per_slide_id,
                        err=str(e),
                    )
                    # Retry without image if timeout occurred
                    if params.get("image_local_path") or params.get("image_drive_file_id") or params.get("image_url"):
                        jlog(log, logging.INFO, event="slides_create_retry_no_image", req_id=per_slide_id)
                        retry_params = {k: v for k, v in params.items() 
                                      if k not in ["image_local_path", "image_drive_file_id", "image_url"]}
                        try:
                            slide_res = mcp.call("slides.create", retry_params, timeout=180.0)
                            pres_id = pres_id or slide_res.get("presentation_id")
                            deck_url = deck_url or slide_res.get("url")
                            total_created += 1
                            jlog(log, logging.INFO, event="data_slide_ok_retry", req_id=per_slide_id, 
                                 slide_id=slide_res.get("slide_id"))
                        except Exception as retry_e:
                            jlog(log, logging.ERROR, event="slides_create_retry_failed", 
                                 req_id=per_slide_id, err=str(retry_e))
                except Exception as e:
                    jlog(
                        log,
                        logging.ERROR,
                        event="data_slide_fail",
                        req_id=per_slide_id,
                        err=str(e),
                    )
    
    jlog(
        log,
        logging.INFO,
        event="orchestrate_mixed_complete",
        requested_slides=slide_count,
        narrative_slides=narrative_slides,
        data_slides_allocated=data_slides_max if has_data else 0,
        total_created=total_created,
        pres_id=pres_id,
        url=deck_url,
    )
    
    return {
        "presentation_id": pres_id,
        "url": deck_url,
        "created_slides": total_created,
    }
