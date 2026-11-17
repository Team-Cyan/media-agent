from datetime import UTC, datetime

from media_agent.config import SchedulerConfig
from media_agent.task_schedule import TaskSchedule


def test_independent_slots_are_claimed_once_without_startup_catchup() -> None:
    scheduler = SchedulerConfig(
        cron="-", maintenance_cron="* * * * *", intent_search_cron="* * * * *"
    )
    clock = TaskSchedule()
    now = datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC).timestamp()
    assert clock.observe(scheduler, now) == set()
    assert clock.observe(scheduler, now + 30) == {"maintenance", "intent"}
    assert clock.observe(scheduler, now + 31) == set()
    changed = scheduler.model_copy(update={"intent_search_cron": "*/2 * * * *"})
    assert clock.observe(changed, now + 90) == {"maintenance"}


def test_maintenance_inherits_pt_slot_when_absent() -> None:
    scheduler = SchedulerConfig(cron="* * * * *")
    clock = TaskSchedule()
    now = datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC).timestamp()
    assert clock.observe(scheduler, now) == set()
    assert clock.observe(scheduler, now + 30) == {"pt", "maintenance"}
