"""Pure cron previews: no task submission, provider calls, or filesystem traversal."""

import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from media_agent.cron_schedule import is_cron_enabled, next_cron_slots, runtime_timezone

HASH_IDS = {
    "media": b"media-import-scan",
    "scheduler": b"scheduler-cycle",
    "intent": b"scheduler-intent",
    "maintenance": b"scheduler-maintenance",
    "background": b"media-import-background",
}


def preview_schedule(payload, *, now=None, inherit_timezone=False):
    allowed = {"kind", "cron", "timezone", "window_minutes"}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError("expected kind, cron and timezone")
    duration = payload.get("window_minutes", 120)
    if type(duration) is not int or not 1 <= duration <= 1440:
        raise ValueError("window_minutes must be an integer between 1 and 1440")
    kind = payload.get("kind", "media")
    expression = payload.get("cron")
    timezone = runtime_timezone()
    if not inherit_timezone:
        timezone = payload.get("timezone", timezone)
    if kind not in HASH_IDS:
        raise ValueError("unknown schedule kind")
    if expression is not None and (not isinstance(expression, str) or len(expression) > 256):
        raise ValueError("cron must be a string of at most 256 characters")
    if not isinstance(timezone, str):
        raise ValueError("timezone must be an IANA timezone")
    try:
        zone = ZoneInfo(timezone)
    except ValueError, ZoneInfoNotFoundError:
        raise ValueError("timezone must be an available IANA timezone") from None
    hash_id = HASH_IDS[kind]
    enabled = is_cron_enabled(expression, hash_id=hash_id)
    slots = next_cron_slots(
        expression, timezone, time.time() if now is None else now, hash_id=hash_id
    )
    result = {
        "enabled": enabled,
        "timezone": timezone,
        "next_runs": [datetime.fromtimestamp(slot, zone).isoformat() for slot in slots],
        "message": "scheduled" if enabled else "invalid cron; automatic execution disabled",
    }
    if kind == "background":
        result["window_minutes"] = duration
        result["window_ends"] = [
            datetime.fromtimestamp(slot + duration * 60, zone).isoformat() for slot in slots
        ]
    return result
