# src/common/config.py
from __future__ import annotations

import os
import pathlib
import re
import logging
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Union

import yaml  # pip install pyyaml

log = logging.getLogger("common.config")

# Cache
_CONF: Dict[str, Any] | None = None
# Default search order (first existing wins)
_DEFAULT_PATHS = [
    pathlib.Path(os.getenv("SALES_AGENT_CONFIG", "")),  # explicit override
    pathlib.Path(os.getenv("CONFIG_PATH", "")),  # common alias
    pathlib.Path("config/config.yaml"),
    pathlib.Path("config.yaml"),
]


def _first_existing(paths: Iterable[pathlib.Path]) -> pathlib.Path | None:
    for p in paths:
        if p and p.exists() and p.is_file():  # <-- require file
            return p
    return None


_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand_env_in_str(s: str) -> str:
    """Expand ${VAR_NAME} using os.environ (missing vars -> empty string)."""

    def repl(m: re.Match[str]) -> str:
        var = m.group(1)
        return os.getenv(var, "")

    return _ENV_VAR_PATTERN.sub(repl, s)


def _expand_env(obj: Any) -> Any:
    """
    Recursively expand ${VAR} in all strings contained in obj (dict/list/str).
    Non-strings are returned unchanged.
    """
    if isinstance(obj, str):
        return _expand_env_in_str(obj)
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    return obj


def _load_file(path: pathlib.Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _expand_env(data)


def reload_config() -> Dict[str, Any]:
    """
    Force reload from disk (useful during development).
    Search order:
      1) $SALES_AGENT_CONFIG
      2) $CONFIG_PATH
      3) config/config.yaml
      4) config.yaml
    """
    global _CONF
    path = _first_existing(_DEFAULT_PATHS)
    if not path:
        log.info("No config file found; using empty config")
        _CONF = {}
        return _CONF
    try:
        _CONF = _load_file(path)
        log.debug("Loaded config from %s", path)
        return _CONF
    except Exception as e:
        log.warning("Failed to load config at %s: %s", path, e)
        _CONF = {}
        return _CONF


def get_config() -> Dict[str, Any]:
    """Return cached config; load once if needed."""
    global _CONF
    if _CONF is not None:
        return _CONF
    return reload_config()


_MISSING = object()


def _dig(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    cur: Any = mapping
    for k in keys:
        if not isinstance(cur, Mapping) or k not in cur:
            return _MISSING
        cur = cur[k]
    return cur


def cfg(*keys: str, default: Any = None) -> Any:
    """
    Fetch a nested value: cfg("llm", "model", default="models/gemini-2.0-flash-001")
    - Returns the value if found, even if it's falsy (0, "", False).
    - Returns `default` only when the key path is missing.
    """
    c = get_config()
    val = _dig(c, keys)
    return default if val is _MISSING else val


def require(*keys: str) -> Any:
    """
    Like cfg(), but raises a clear error when the key path is missing.
    Use for must-have settings in production.
    """
    c = get_config()
    val = _dig(c, keys)
    if val is _MISSING:
        path = ".".join(keys)
        raise RuntimeError(f"Missing required config key: {path}")
    return val


# ============================================================================
# Port Configuration Helpers (Standardized 2025-10-04)
# ============================================================================
def get_presgen_assess_port() -> int:
    """Get the port for PresGen-Assess service (default: 8000)."""
    return int(os.getenv("PRESGEN_ASSESS_PORT", "8000"))


def get_presgen_core_port() -> int:
    """Get the port for PresGen-Core service (default: 8080)."""
    return int(os.getenv("PRESGEN_CORE_PORT", "8080"))


def get_presgen_ui_port() -> int:
    """Get the port for PresGen-UI service (default: 3000)."""
    return int(os.getenv("PRESGEN_UI_PORT", "3000"))


def get_presgen_assess_url() -> str:
    """Get the URL for PresGen-Assess service."""
    return os.getenv("PRESGEN_ASSESS_URL", f"http://localhost:{get_presgen_assess_port()}")


def get_presgen_core_url() -> str:
    """Get the URL for PresGen-Core service."""
    return os.getenv("PRESGEN_CORE_URL", f"http://localhost:{get_presgen_core_port()}")


def log_port_configuration():
    """Log the current port configuration (useful for debugging)."""
    log.info("🔧 Service Port Configuration:")
    log.info(f"  📡 PresGen-Assess: {get_presgen_assess_url()} (port {get_presgen_assess_port()})")
    log.info(f"  📡 PresGen-Core: {get_presgen_core_url()} (port {get_presgen_core_port()})")
    log.info(f"  📡 PresGen-UI: port {get_presgen_ui_port()}")
