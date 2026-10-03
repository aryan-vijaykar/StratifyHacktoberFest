"""
Shared utilities — helper functions used across the application.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a UUID-based short identifier with optional prefix."""
    uid = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{uid}" if prefix else uid


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division helper that avoids ZeroDivisionError."""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a float value between min and max bounds."""
    return max(min_val, min(max_val, value))


def now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.utcnow().isoformat()


def mask_sensitive(data: Dict[str, Any], keys: Optional[list] = None) -> Dict[str, Any]:
    """Return a copy of a dict with sensitive keys masked (for logging)."""
    sensitive = keys or ["password", "secret", "token", "key", "api_key"]
    return {
        k: "***" if any(s in k.lower() for s in sensitive) else v
        for k, v in data.items()
    }
