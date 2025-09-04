from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict


def parse_duration(s: str) -> timedelta:
    s = s.strip().lower()
    if s.endswith("ms"):
        return timedelta(milliseconds=int(s[:-2]))
    if s.endswith("s"):
        return timedelta(seconds=int(s[:-1]))
    if s.endswith("m"):
        return timedelta(minutes=int(s[:-1]))
    if s.endswith("h"):
        return timedelta(hours=int(s[:-1]))
    if s.endswith("d"):
        return timedelta(days=int(s[:-1]))
    raise ValueError("Unsupported duration")


class SLAService:
    async def apply(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target", "15m")
        deadline = datetime.now(timezone.utc) + parse_duration(target)
        # In real implementation, persist deadline and schedule checks
        return {"deadline": deadline.isoformat(), "target": target}
