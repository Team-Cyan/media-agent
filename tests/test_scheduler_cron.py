from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from media_agent import cli
from media_agent.config import SchedulerConfig


def test_scheduler_cron_configuration_preserves_legacy_and_disabled_values():
    assert SchedulerConfig().cron is None
    assert SchedulerConfig(cron="-", intent_search_cron="", timezone="Asia/Shanghai").cron == "-"
    with pytest.raises(ValueError, match="IANA timezone"):
        SchedulerConfig(timezone="invalid/zone")


def test_cron_wait_does_not_catch_up_and_runs_at_next_slot(monkeypatch):
    scheduler = SchedulerConfig(cron="* * * * *", capacity_guard_interval_seconds=10)
    clock = [datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC).timestamp()]
    waits = []
    monkeypatch.setattr(cli.time, "time", lambda: clock[0])
    def wait(*args, interval_seconds, **kwargs):
        waits.append(interval_seconds)
        clock[0] += interval_seconds
        return None
    monkeypatch.setattr(cli, "_wait_for_next_schedule_cycle", wait)
    monkeypatch.setattr(cli, "load_config", lambda _: SimpleNamespace(scheduler=scheduler))
    assert cli._wait_for_cron_schedule_cycle(Path("config"), scheduler, {}, execute=False,
        lease_heartbeat=SimpleNamespace(ensure_owned=lambda: None), trigger_store=object()) is None
    assert clock[0] == datetime(2026, 1, 1, 0, 1, tzinfo=UTC).timestamp()
    assert waits


def test_disabled_cron_waits_for_manual_trigger(monkeypatch):
    scheduler = SchedulerConfig(cron="-")
    trigger = {"source": "test"}
    monkeypatch.setattr(cli, "_wait_for_next_schedule_cycle", lambda *a, **k: trigger)
    assert cli._wait_for_cron_schedule_cycle(Path("config"), scheduler, {}, execute=False,
        lease_heartbeat=SimpleNamespace(ensure_owned=lambda: None),
        trigger_store=object()) == trigger


@pytest.mark.parametrize(
    ("cron", "zone", "when", "expected"),
    [
        ("0 0 * * *", "UTC", "2026-01-01T00:00:00+00:00", 2881),
        ("0 0 1 * *", "UTC", "2026-01-01T00:00:00+00:00", 84961),
        ("0 2 * * *", "America/New_York", "2026-03-07T07:00:00+00:00", 4261),
    ],
)
def test_second_slot_horizon(cron, zone, when, expected):
    now = datetime.fromisoformat(when).timestamp()
    assert cli._schedule_free_window_safety_minutes(
        interval_minutes=60, configured_minutes=None, cron=cron, timezone=zone, now=now,
    ) == expected


def test_cron_free_window_rechecks_slot_and_ages_observation(monkeypatch):
    from media_agent.models import ScoreBreakdown, TorrentCandidate

    now = datetime(2026, 1, 1, 0, 59, tzinfo=UTC).timestamp()
    candidate = TorrentCandidate(
        site="test", title="test", source_url="https://example.com/1",
        download_url="https://example.com/1.torrent", size_bytes=1,
        seeders=1, leechers=1, discount="free", left_time_minutes=62,
        hr=False, metadata={"schedule_free_observed_at": now},
    )
    item = ScoreBreakdown(candidate_id=candidate.stable_id, score=1, accepted=True,
                          reasons=[], candidate=candidate)
    scheduler = SchedulerConfig(cron="0 * * * *")
    monkeypatch.setattr(cli.time, "time", lambda: now)
    assert cli._cron_free_window_rejection(item, scheduler) is None
    monkeypatch.setattr(cli.time, "time", lambda: now + 61)
    assert "requires" in cli._cron_free_window_rejection(item, scheduler)
    assert "no second future" in cli._cron_free_window_rejection(
        item, SchedulerConfig(cron="-")
    )
    unlimited = candidate.model_copy(update={"left_time_minutes": None,
        "metadata": {"left_time_source": "mteam_api_unlimited"}})
    assert cli._cron_free_window_rejection(item.model_copy(update={"candidate": unlimited}),
                                           SchedulerConfig(cron="-")) is None


@pytest.mark.parametrize("cron", ["0 0 * * *", "-"])
def test_cron_wait_writes_healthy_heartbeat_before_first_cycle(monkeypatch, tmp_path, cron):
    scheduler = SchedulerConfig(cron=cron)
    heartbeat = tmp_path / "heartbeat.json"
    trigger = {"source": "test"}
    def wait(*args, waiting_heartbeat, **kwargs):
        waiting_heartbeat()
        return trigger
    monkeypatch.setattr(cli, "_wait_for_next_schedule_cycle", wait)
    assert cli._wait_for_cron_schedule_cycle(
        Path("config"), scheduler, {}, execute=False,
        lease_heartbeat=SimpleNamespace(ensure_owned=lambda: None), trigger_store=object(),
        heartbeat_file=heartbeat,
    ) == trigger
    assert cli._heartbeat_status(heartbeat, max_staleness_minutes=1)["age_minutes"] < 1
    import json
    assert json.loads(heartbeat.read_text())["phase"] == "waiting"


@pytest.mark.asyncio
async def test_enqueue_rechecks_guard_before_each_download():
    from media_agent.actions.qb import enqueue_candidates
    from media_agent.config import CategoryPolicyConfig
    from media_agent.models import ScoreBreakdown, TorrentCandidate

    candidate = TorrentCandidate(
        site="test", title="test", source_url="https://example.com/1",
        download_url="https://example.com/1.torrent", size_bytes=1,
        seeders=1, leechers=1, discount="free", hr=False,
    )
    item = ScoreBreakdown(candidate_id=candidate.stable_id, score=1, accepted=True,
                          reasons=[], candidate=candidate)
    class Downloader:
        async def add_url(self, *args, **kwargs):
            raise AssertionError("must not enqueue a rejected candidate")
    policy = CategoryPolicyConfig(name="seed", mode="mutable", budget_pool="downloads",
                                  delete_enabled=True, over_budget_behavior="add_paused")
    decisions = await enqueue_candidates(
        [item], Downloader(), policy, True,
        cron_guard=lambda _: "cron execute safety unavailable: no second future scheduler slot",
    )
    assert decisions[0].action == "qb.enqueue.rejected"
    assert "no second future" in decisions[0].reason


@pytest.mark.asyncio
async def test_cron_intent_free_release_rejected_before_token(tmp_path):
    from media_agent.actions.intent import _score_breakdown_from_ranked, add_intent, enqueue_intent
    from media_agent.config import CategoryPolicyConfig
    from media_agent.models import RankedRelease, ReleaseCandidate
    from media_agent.state import StateStore

    store = StateStore(tmp_path / "state.db")
    intent, _ = add_intent("Example 2026", store)
    release = ReleaseCandidate(
        release_id="test:1", site="test", title="Example 2026",
        source_url="https://example.com/1", download_url="mteam-api://torrent/1",
        size_bytes=1, seeders=1, leechers=1, discount="free",
        metadata={"download_url_source": "mteam_api_deferred"},
    )
    store.save_ranked_releases([RankedRelease(
        intent_id=intent.intent_id, release=release, score=90, confidence=0.9,
        accepted=True, confirmation_required=False, reasons=[], risks=[],
    )])
    async def resolver(_release):
        raise AssertionError("must not fetch a token without free-window evidence")
    policy = CategoryPolicyConfig(name="seed", mode="mutable", budget_pool="downloads",
                                  delete_enabled=True, over_budget_behavior="add_paused")
    _, _, decisions = await enqueue_intent(
        intent.intent_id, store, object(), policy, True, release_resolver=resolver,
        release_id=release.release_id, cron_guard=cli._scheduled_intent_cron_guard,
    )
    assert decisions[0].action == "qb.enqueue.rejected"
    assert "fresh free-window evidence" in decisions[0].reason
    assert cli._scheduled_intent_cron_guard(
        _score_breakdown_from_ranked(RankedRelease(
            intent_id=intent.intent_id, release=release.model_copy(update={"discount": "normal"}),
            score=90, confidence=0.9, accepted=True, confirmation_required=False,
            reasons=[], risks=[],
        ))
    ) is None


def test_disabled_cron_refreshes_heartbeat_with_short_guard(monkeypatch, tmp_path):
    scheduler = SchedulerConfig(cron="-", capacity_guard_interval_seconds=10)
    clock = [0.0]
    writes = []
    monkeypatch.setattr(cli.time, "time", lambda: clock[0])
    monkeypatch.setattr(cli, "_write_heartbeat", lambda *a, **k: writes.append(clock[0]))
    monkeypatch.setattr(cli, "load_config", lambda _: SimpleNamespace(scheduler=scheduler))
    def wait(*args, interval_seconds, **kwargs):
        clock[0] += interval_seconds
        return {"source": "test"} if clock[0] >= 100 else None
    monkeypatch.setattr(cli, "_wait_for_next_schedule_cycle", wait)
    cli._wait_for_cron_schedule_cycle(
        Path("config"), scheduler, {}, execute=False, heartbeat_file=tmp_path / "heartbeat",
        lease_heartbeat=SimpleNamespace(ensure_owned=lambda: None), trigger_store=object(),
    )
    assert clock[0] >= 100
    assert len(writes) >= 9
    assert max(b - a for a, b in zip(writes, writes[1:], strict=False)) <= 30

def test_task_and_media_slots_inherit_container_timezone(monkeypatch):
    from media_agent.media_import.config import ScanSchedule
    from media_agent.media_import.schedule import latest_slot
    from media_agent.task_schedule import TaskSchedule

    monkeypatch.setenv("TZ", "Asia/Shanghai")
    previous = 15 * 3600
    slot = 19 * 3600  # 03:00 the following day in Asia/Shanghai.
    task = TaskSchedule()
    scheduler = SchedulerConfig(
        cron="0 3 * * *",
        maintenance_cron="0 3 * * *",
        intent_search_cron="0 3 * * *",
        timezone="UTC",
    )
    assert task.observe(scheduler, previous) == set()
    assert task.next_slot(scheduler, previous) == slot
    assert task.observe(scheduler, slot) == {"pt", "maintenance", "intent"}
    assert latest_slot(ScanSchedule(cron="0 3 * * *", timezone="UTC"), slot) == slot
