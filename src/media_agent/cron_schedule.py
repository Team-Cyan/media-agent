"""Shared Jenkins-style five-field cron validation and calendar evaluation."""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import CroniterBadCronError, CroniterBadDateError, croniter

DEFAULT_HASH_ID = b"media-agent-schedule"
# Jenkins core: numeric values, lists, ranges, steps and stable hashed fields.
_PART = re.compile(r"(?:\*|[0-9]+(?:-[0-9]+)?|H(?:\([0-9]+-[0-9]+\))?)(?:/[0-9]+)?\Z")


def runtime_timezone() -> str:
    """Resolve the timezone supplied by the host to this process."""
    configured = os.environ.get("TZ", "").removeprefix(":")
    localtime = Path("/etc/localtime").resolve().as_posix().partition("/zoneinfo/")[2]
    for candidate in (configured, localtime, "UTC"):
        try:
            ZoneInfo(candidate)
        except (ValueError, ZoneInfoNotFoundError):
            continue
        return candidate
    return "UTC"


def validate_cron(expression, *, hash_id=DEFAULT_HASH_ID):
    if not isinstance(expression, str) or len(expression) > 256:
        raise ValueError("cron must be a string of at most 256 characters")
    if "\n" in expression or "\r" in expression:
        raise ValueError("cron must be a single line")
    fields = expression.split()
    if len(fields) != 5 or any(
        not all(_PART.fullmatch(part) for part in field.split(",")) for field in fields
    ):
        raise ValueError("cron must have five numeric fields using *, lists, ranges, steps or H")
    try:
        iterator = croniter(
            expression,
            datetime.now(),
            hash_id=hash_id,
            day_or=False,
            max_years_between_matches=8,
        )
        iterator.get_next(datetime)
    except CroniterBadCronError, CroniterBadDateError, ValueError, KeyError:
        raise ValueError("invalid cron or no matching date within eight years") from None


def is_cron_enabled(expression, *, hash_id=DEFAULT_HASH_ID):
    """Invalid, impossible, and absent expressions disable automation."""
    try:
        validate_cron(expression, hash_id=hash_id)
    except ValueError:
        return False
    return True


def latest_cron_slot(expression, timezone, now, *, hash_id=DEFAULT_HASH_ID):
    """Find latest slot, skipping local clock gaps and choosing fold 0 on repeats."""
    if not is_cron_enabled(expression, hash_id=hash_id):
        return None
    zone = ZoneInfo(timezone)
    local = datetime.fromtimestamp(now, zone)
    naive = local.replace(tzinfo=None)
    # During the second fold, earlier UTC slots may have a later wall time.
    if local.fold:
        naive += local.replace(fold=0).utcoffset() - local.utcoffset()
    iterator = croniter(
        expression,
        naive + timedelta(microseconds=1),
        hash_id=hash_id,
        day_or=False,
        max_years_between_matches=8,
    )
    # A skipped civil day can contain 1440 minutely slots.
    for _ in range(3000):
        try:
            candidate = iterator.get_prev(datetime)
        except CroniterBadDateError:
            return None
        stamp = candidate.replace(tzinfo=zone, fold=0).timestamp()
        if stamp <= now and datetime.fromtimestamp(stamp, zone).replace(tzinfo=None) == candidate:
            return stamp
    return None


def next_cron_slot(expression, timezone, now, *, hash_id=DEFAULT_HASH_ID):
    """Return the next UTC epoch slot, skipping gaps and second-fold occurrences."""
    if not is_cron_enabled(expression, hash_id=hash_id):
        return None
    zone = ZoneInfo(timezone)
    local = datetime.fromtimestamp(now, zone)
    iterator = croniter(
        expression,
        local.replace(tzinfo=None),
        hash_id=hash_id,
        day_or=False,
        max_years_between_matches=8,
    )
    for _ in range(3000):
        try:
            candidate = iterator.get_next(datetime)
        except CroniterBadDateError:
            return None
        stamp = candidate.replace(tzinfo=zone, fold=0).timestamp()
        if stamp > now and datetime.fromtimestamp(stamp, zone).replace(tzinfo=None) == candidate:
            return stamp
    return None


def next_cron_slots(expression, timezone, now, count=2, *, hash_id=DEFAULT_HASH_ID):
    """Return up to count strictly future UTC epoch slots."""
    if not 0 <= count <= 100:
        raise ValueError("count must be between 0 and 100")
    slots = []
    for _ in range(count):
        slot = next_cron_slot(expression, timezone, now, hash_id=hash_id)
        if slot is None:
            break
        slots.append(slot)
        now = slot
    return slots
