from __future__ import annotations

from typing import Dict, List


def get_cors_config(settings) -> Dict[str, List[str] | int]:
    allow_origins = getattr(settings, "allowed_origins", ["*"])
    return {
        "allow_origins": allow_origins,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Request-ID"],
        "max_age": 600,
    }
