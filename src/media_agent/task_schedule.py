"""In-memory claimed-slot bookkeeping for the serialized scheduler."""

from dataclasses import dataclass, field

from media_agent.cron_schedule import latest_cron_slot, next_cron_slot, runtime_timezone

_HASHES = {
    "pt": b"scheduler-cycle",
    "maintenance": b"scheduler-maintenance",
    "intent": b"scheduler-intent",
}


@dataclass
class TaskSchedule:
    """Observe configuration without replaying slots predating observation."""

    keys: dict[str, tuple[str | None, str]] = field(default_factory=dict)
    since: dict[str, float] = field(default_factory=dict)
    guard_due: float | None = None
    legacy_due_at: float | None = None

    def observe(self, scheduler: object, now: float) -> set[str]:
        expressions = {
            "pt": scheduler.cron,
            "maintenance": scheduler.maintenance_cron,
            "intent": scheduler.intent_search_cron,
        }
        due: set[str] = set()
        zone = runtime_timezone()
        for task, expression in expressions.items():
            key = (expression, zone)
            if self.keys.get(task) != key:
                self.keys[task] = key
                self.since[task] = now
                continue
            if expression is None:
                continue
            slot = latest_cron_slot(expression, zone, now, hash_id=_HASHES[task])
            if slot is not None and slot > self.since[task]:
                due.add(task)
                self.since[task] = slot
        if "pt" in due and scheduler.maintenance_cron is None:
            due.add("maintenance")
        return due

    def next_slot(self, scheduler: object, now: float) -> float | None:
        zone = runtime_timezone()
        slots = [
            next_cron_slot(expression, zone, now, hash_id=_HASHES[task])
            for task, expression in (
                ("pt", scheduler.cron),
                ("maintenance", scheduler.maintenance_cron),
                ("intent", scheduler.intent_search_cron),
            )
            if expression is not None
        ]
        return min((slot for slot in slots if slot is not None), default=None)
