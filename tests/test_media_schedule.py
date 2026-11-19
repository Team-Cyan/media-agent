from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from test_media_runtime import media_config

from media_agent.media_import.config import BackgroundSchedule, ScanSchedule
from media_agent.media_import.runtime import build_engine
from media_agent.media_import.schedule import background_window_open, claim_slot, latest_slot


def ts(value):
    return datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp()


def test_calendar_boundaries_and_dst(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    assert latest_slot(ScanSchedule(cron="0 9 * * 1"), ts("2026-11-17T00:00")) == ts(
        "2026-11-16T09:00"
    )
    assert latest_slot(ScanSchedule(cron="0 0 31 * *"), ts("2026-03-01T00:00")) == ts(
        "2026-01-31T00:00"
    )
    monkeypatch.setenv("TZ", "America/New_York")
    spring = ScanSchedule(cron="30 2 * * *")
    assert latest_slot(spring, ts("2026-03-08T12:00")) == ts("2026-03-07T07:30")
    fall = ScanSchedule(cron="30 1 * * *")
    assert latest_slot(fall, ts("2026-11-01T07:00")) == ts("2026-11-01T05:30")


def test_config_validation():
    with pytest.raises(ValidationError):
        ScanSchedule(cron="0 0 * * *", timezone="not/a-zone")
    with pytest.raises(ValidationError):
        ScanSchedule(cron="x" * 257)


def test_activation_restart_missed_and_manual_completion(tmp_path):
    path, _, _ = media_config(tmp_path)
    engine, _ = build_engine(path)
    schedule = ScanSchedule(cron="0 * * * *")
    names = [p.name for p in engine.profiles()]
    assert names
    assert not claim_slot(engine.store, schedule, names, ts("2026-01-01T00:00"))
    assert claim_slot(engine.store, schedule, names, ts("2026-01-01T03:15"))
    # Persisted claim survives a new engine and prevents retries after failure.
    restarted, _ = build_engine(path)
    assert not claim_slot(restarted.store, schedule, names, ts("2026-01-01T03:59"))
    with restarted.store._connect() as conn:
        for name in names:
            conn.execute(
                "INSERT INTO media_scan_runs(profile,started,completed,status) "
                "VALUES(?,?,?,'complete')",
                (name, ts("2026-01-01T04:01"), ts("2026-01-01T04:02")),
            )
    assert not claim_slot(restarted.store, schedule, names, ts("2026-01-01T04:05"))
    assert claim_slot(restarted.store, schedule, names, ts("2026-01-01T05:00"))
    changed = ScanSchedule(cron="0 0 * * *")
    assert not claim_slot(restarted.store, changed, names, ts("2026-01-02T01:00"))
    assert claim_slot(restarted.store, changed, names, ts("2026-01-03T00:00"))


def test_worker_uses_calendar_and_forces_scan(tmp_path, monkeypatch):
    import yaml

    from media_agent.config import atomic_write_text
    from media_agent.config_views import load_view
    from media_agent.media_import import worker

    path, _, _ = media_config(tmp_path)
    raw = yaml.safe_load(path.read_text())
    raw["deployment"] = {"source_id": "calendar-fixture"}
    raw["media_import"]["scan_schedule"] = {
        "cron": "15 * * * *",
        "timezone": "UTC",
    }
    atomic_write_text(path, yaml.safe_dump(raw))
    assert (
        load_view(path, "media", require_identity=True).config.media_import.scan_schedule.cron
        == "15 * * * *"
    )
    now = [ts("2026-01-01T00:10")]
    runs = []
    monkeypatch.setattr(worker.time, "time", lambda: now[0])
    monkeypatch.setattr(worker.time, "sleep", lambda _: now.__setitem__(0, now[0] + 600))
    monkeypatch.setattr(worker, "process_one", lambda *a, **kw: None)
    monkeypatch.setattr(
        worker,
        "run_engine",
        lambda *a, **kw: runs.append((kw["scan"], kw["force"])) or {"status": "complete"},
    )
    worker.serve(path, max_cycles=3)
    assert runs == [(False, False), (True, True), (False, False)]


@pytest.mark.parametrize(
    "expression",
    [
        "@daily",
        "R * * * *",
        "0 0 * * * *",
        "0 0 L * *",
        "0 0 * * ?",
        "0 0 31 2 *",
        "0 0 * * 1#2",
        "*/0 * * * *",
        "jan * * * *",
    ],
)
def test_invalid_cron_is_disabled(expression):
    from media_agent.cron_schedule import is_cron_enabled, next_cron_slot, validate_cron

    schedule = ScanSchedule(cron=expression)
    assert not is_cron_enabled(expression)
    assert latest_slot(schedule, ts("2026-01-01T00:00")) is None
    assert next_cron_slot(expression, "UTC", ts("2026-01-01T00:00")) is None
    with pytest.raises(ValueError):
        validate_cron(expression)


def test_cron_hash_and_conjunctive_days_and_second_fold(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    hashed = ScanSchedule(cron="H(0-30)/5 H * * *")
    assert latest_slot(hashed, ts("2026-11-17T00:00")) == latest_slot(
        hashed, ts("2026-11-17T00:00")
    )
    both = ScanSchedule(cron="0 0 1 * 1")
    assert latest_slot(both, ts("2026-06-02T00:00")) == ts("2026-06-01T00:00")
    monkeypatch.setenv("TZ", "America/New_York")
    repeated = ScanSchedule(cron="30 1 * * *")
    assert latest_slot(repeated, ts("2026-11-01T06:15")) == ts("2026-11-01T05:30")
    assert ScanSchedule().cron is None


def test_next_cron_slot_respects_dst():
    from media_agent.cron_schedule import next_cron_slot

    assert next_cron_slot("30 2 * * *", "America/New_York", ts("2026-03-08T06:00")) == ts(
        "2026-03-09T06:30"
    )
    assert next_cron_slot("30 1 * * *", "America/New_York", ts("2026-11-01T06:15")) == ts(
        "2026-11-02T06:30"
    )


def test_invalid_schedule_never_claims_and_preview(tmp_path):
    from media_agent.cron_schedule import next_cron_slots

    path, _, _ = media_config(tmp_path)
    engine, _ = build_engine(path)
    names = [p.name for p in engine.profiles()]
    schedule = ScanSchedule(cron="-")
    assert not claim_slot(engine.store, schedule, names, ts("2026-01-01T00:00"))
    assert not claim_slot(engine.store, schedule, names, ts("2026-01-02T00:00"))
    assert next_cron_slots("-", "UTC", ts("2026-01-01T00:00")) == []
    assert next_cron_slots("0 * * * *", "UTC", ts("2026-01-01T00:10")) == [
        ts("2026-01-01T01:00"),
        ts("2026-01-01T02:00"),
    ]


def test_pending_batches_resume_after_yield_without_another_inventory(tmp_path, monkeypatch):
    from media_agent.media_import.runtime import run_engine

    path, source, _ = media_config(tmp_path)
    for name in ("one.mkv", "two.mkv", "three.mkv"):
        (source / name).write_bytes(b"video")
    engine, _ = build_engine(path)
    engine.config.work_batch_size = 1
    inventory_calls = []
    original_inventory = engine.inventory

    def inventory(profile):
        inventory_calls.append(profile.name)
        return original_inventory(profile)

    monkeypatch.setattr(engine, "inventory", inventory)
    processed = []
    monkeypatch.setattr(
        engine, "process_source", lambda profile, item: processed.append(item["id"])
    )
    result = run_engine(engine, path, force=True, enrichment=False, should_yield=lambda: True)
    assert result["status"] == "yielded"
    assert processed == []
    with engine.store._connect() as conn:
        conn.execute("UPDATE media_source_files SET stable_count=2")
    for _ in range(3):
        result = run_engine(engine, path, scan=False, drain_pending=True, enrichment=False)
        assert result["status"] == "complete"
    assert len(set(processed)) == 3
    assert inventory_calls == ["movie"]


def test_pending_drain_checks_roots_and_yields_for_commands(tmp_path, monkeypatch):
    from media_agent.media_import.runtime import run_engine

    path, source, _ = media_config(tmp_path)
    (source / "one.mkv").write_bytes(b"video")
    engine, _ = build_engine(path)
    engine.scan("movie", force=True, should_yield=lambda: True)
    with engine.store._connect() as conn:
        conn.execute("UPDATE media_source_files SET stable_count=2")
    processed = []
    monkeypatch.setattr(
        engine, "process_source", lambda profile, item: processed.append(item["id"])
    )
    assert (
        run_engine(
            engine,
            path,
            scan=False,
            drain_pending=True,
            enrichment=False,
            should_yield=lambda: True,
        )["status"]
        == "yielded"
    )
    assert not processed
    (source / ".media-volume").unlink()
    run_engine(engine, path, scan=False, drain_pending=True, enrichment=False)
    assert not processed


def test_idle_pending_check_does_not_touch_media_roots(tmp_path, monkeypatch):
    from media_agent.media_import.runtime import run_engine

    path, source, _ = media_config(tmp_path)
    (source / "one.mkv").write_bytes(b"video")
    engine, _ = build_engine(path)
    engine.scan("movie", force=True, should_yield=lambda: True)
    monkeypatch.setattr(engine, "health", lambda *_: pytest.fail("idle root touched"))
    monkeypatch.setattr(engine, "inventory", lambda *_: pytest.fail("idle inventory"))
    for _ in range(2):
        assert (
            run_engine(engine, path, scan=False, drain_pending=True, enrichment=False)["status"]
            == "complete"
        )
    with engine.store._connect() as conn:
        row = conn.execute("SELECT id FROM media_source_files").fetchone()
        conn.execute("UPDATE media_source_files SET stable_count=2,status='imported'")
        conn.execute(
            "INSERT INTO media_import_jobs(source_id,revision,status,updated) "
            "VALUES(?,1,'imported',0)",
            (row[0],),
        )
    assert (
        run_engine(engine, path, scan=False, drain_pending=True, enrichment=False)["status"]
        == "complete"
    )


def test_pending_gate_includes_recovery_records(tmp_path):
    from media_agent.media_import.runtime import has_pending_work

    path, _, _ = media_config(tmp_path)
    engine, _ = build_engine(path)
    engine.config.import_policy = "execute"
    profile = engine.profile("movie")
    assert not has_pending_work(engine, profile)
    with engine.store._connect() as conn:
        conn.execute("INSERT INTO media_variant_switches VALUES('v','key','{}','pending',0)")
    assert has_pending_work(engine, profile)
    with engine.store._connect() as conn:
        conn.execute("DELETE FROM media_variant_switches")
        conn.execute(
            "INSERT INTO media_extra_attachments VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "s",
                1,
                "fingerprint",
                "parent",
                '{"source_profile":"movie"}',
                "target",
                "artifact",
                "temporary",
                0,
            ),
        )
    assert has_pending_work(engine, profile)


def test_background_window_activation_restart_expiry_and_invalid(tmp_path):
    path, _, _ = media_config(tmp_path)
    engine, _ = build_engine(path)
    schedule = BackgroundSchedule(cron="0 * * * *", window_minutes=20)
    assert not background_window_open(engine.store, schedule, ts("2026-01-01T00:05"))
    assert background_window_open(engine.store, schedule, ts("2026-01-01T01:15"))
    restarted, _ = build_engine(path)
    assert not background_window_open(restarted.store, schedule, ts("2026-01-01T01:20"))
    assert not background_window_open(restarted.store, schedule, ts("2026-01-01T02:30"))
    invalid = BackgroundSchedule(cron="-")
    assert not background_window_open(restarted.store, invalid, ts("2026-01-01T03:00"))
    assert not background_window_open(restarted.store, invalid, ts("2026-01-01T04:00"))
    assert background_window_open(restarted.store, None, ts("2026-01-01T04:00"))
    with pytest.raises(ValidationError):
        BackgroundSchedule(window_minutes=0)


def test_inventory_only_defers_processing_and_reconcile_until_drain(tmp_path, monkeypatch):
    from media_agent.media_import.runtime import run_engine

    path, source, _ = media_config(tmp_path)
    (source / "one.mkv").write_bytes(b"video")
    engine, _ = build_engine(path)
    calls = []
    monkeypatch.setattr(engine, "recover", lambda *a, **k: calls.append("recover") or False)
    monkeypatch.setattr(engine, "process_source", lambda *a: calls.append("source"))
    monkeypatch.setattr(engine, "reconcile", lambda *a: calls.append("reconcile"))
    run_engine(engine, path, force=True, inventory_only=True, drain_pending=False, enrichment=False)
    assert calls == []
    with engine.store._connect() as conn:
        conn.execute("UPDATE media_source_files SET stable_count=2")
    run_engine(
        engine, path, scan=False, drain_pending=True, enrichment=False, reconcile_pending=True
    )
    assert "recover" in calls and "source" in calls and "reconcile" in calls
    calls.clear()
    run_engine(
        engine, path, scan=False, drain_pending=True, enrichment=False, reconcile_pending=True
    )
    assert "reconcile" not in calls


def test_window_closing_during_inventory_prevents_background_admission(tmp_path, monkeypatch):
    from media_agent.media_import.runtime import run_engine

    path, _, _ = media_config(tmp_path)
    engine, _ = build_engine(path)
    closed = [False]
    profiles = engine.profiles()
    profiles.append(profiles[0].model_copy(update={"name": "second"}))
    monkeypatch.setattr(engine, "profiles", lambda: profiles)
    seen = []

    def scan(name, **kwargs):
        assert kwargs["inventory_only"]
        seen.append(name)
        closed[0] = True
        return {"profile": name, "status": "complete"}

    monkeypatch.setattr(engine, "scan", scan)
    for method in ("health", "recover", "process_pending", "reconcile"):
        monkeypatch.setattr(engine, method, lambda *a, **k: pytest.fail("background admitted"))
    monkeypatch.setattr(
        "media_agent.media_import.artwork.PosterJobs.run",
        lambda *a, **k: pytest.fail("poster admitted"),
    )
    result = run_engine(
        engine,
        path,
        scan=True,
        inventory_only=True,
        drain_pending=True,
        reconcile_pending=True,
        should_yield=lambda: closed[0],
    )
    assert result["status"] == "yielded"
    assert seen == ["movie", "second"]
    assert [item["profile"] for item in result["scans"]] == seen


def test_closed_background_worker_still_runs_inventory_only(tmp_path, monkeypatch):
    import yaml

    from media_agent.config import atomic_write_text
    from media_agent.media_import import worker

    path, _, _ = media_config(tmp_path)
    raw = yaml.safe_load(path.read_text())
    raw["deployment"] = {"source_id": "background-fixture"}
    raw["media_import"]["background_schedule"] = {"cron": "-"}
    atomic_write_text(path, yaml.safe_dump(raw))
    runs = []
    monkeypatch.setattr(worker, "process_one", lambda *a, **kw: None)
    monkeypatch.setattr(
        worker, "run_engine", lambda *a, **kw: runs.append(kw) or {"status": "complete"}
    )
    worker.serve(path, max_cycles=1)
    assert runs[0]["scan"] and runs[0]["inventory_only"]
    assert not runs[0]["drain_pending"] and not runs[0]["enrichment"]


def test_manual_subtitles_does_not_open_background_or_run_posters(tmp_path, monkeypatch):
    from media_agent.media_import import worker
    from media_agent.media_import.commands import submit

    path, _, _ = media_config(tmp_path)
    submit(path, "subtitles")
    calls = []
    monkeypatch.setattr(
        worker, "run_engine", lambda *a, **kw: calls.append(kw) or {"status": "complete"}
    )
    monkeypatch.setattr(
        worker, "background_window_open", lambda *a: pytest.fail("global window opened")
    )
    assert worker.process_one(path)["status"] == "complete"
    assert calls[0]["refresh"] and not calls[0]["scan"] and not calls[0]["posters"]
