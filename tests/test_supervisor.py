from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from media_agent import supervisor


def test_role_selection_and_environment(monkeypatch, tmp_path):
    class View:
        media_configured = False

    monkeypatch.setattr(supervisor, "load_view", lambda *args: View())
    env = {
        "SEED_AGENT_ROLE": "media",
        "SEED_AGENT_WEB_ENABLED": "true",
        "SEED_AGENT_EXECUTE": "false",
        "SEED_AGENT_PRUNE": "true",
        "SEED_AGENT_INTENT": "false",
        "SEED_AGENT_INTENT_EXECUTE": "true",
        "SEED_AGENT_REQUIRE_KNOWN_FREE_WINDOW": "false",
        "SEED_AGENT_INTERVAL_MINUTES": "5",
        "SEED_AGENT_HEARTBEAT_FILE": "/tmp/h b",
    }
    specs = supervisor.children(tmp_path / "config.yaml", env)
    assert [s.name for s in specs] == ["scheduler", "web"]
    args = specs[0].argv
    assert "--execute" not in args
    assert all(
        x in args
        for x in ("--prune", "--no-intent", "--intent-execute", "--allow-unknown-free-window")
    )
    assert args[args.index("--heartbeat-file") + 1] == "/tmp/h b"
    assert all(s.env["SEED_AGENT_ROLE"] == "seed" for s in specs)
    View.media_configured = True
    specs = supervisor.children(tmp_path / "config.yaml", env)
    assert specs[-1].name == "media-worker"
    assert specs[-1].env["SEED_AGENT_ROLE"] == "media"


def test_healthcheck_runs_roles_in_process(monkeypatch, tmp_path):
    import media_agent.cli

    calls = []
    monkeypatch.setattr(supervisor, "_enabled_media", lambda path: True)
    monkeypatch.setattr(media_agent.cli, "healthcheck", lambda **kwargs: calls.append(kwargs))
    assert supervisor.healthcheck(tmp_path / "config", {"SEED_AGENT_WEB_ENABLED": "true"}) == 0
    assert [call["role"] for call in calls] == ["seed", "media"]
    assert calls[0]["web_health_url"] == "http://127.0.0.1:8765/api/health"
    calls.clear()
    monkeypatch.setattr(supervisor, "_enabled_media", lambda path: False)
    assert supervisor.healthcheck(tmp_path / "config", {}) == 0
    assert len(calls) == 1 and calls[0]["web_health_url"] is None


def _wait_for(path: Path):
    deadline = time.monotonic() + 10
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert path.exists()


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT])
def test_forward_signal_and_reap(tmp_path, signum):
    ready = tmp_path / "ready"
    stopped = tmp_path / "stopped"
    script = (
        "import pathlib,signal,time,sys; "
        "signal.signal(int(sys.argv[3]), lambda *_: "
        "(pathlib.Path(sys.argv[2]).touch(),sys.exit(0))); "
        "pathlib.Path(sys.argv[1]).touch(); time.sleep(60)"
    )
    runner = (
        "import os,sys; from media_agent.supervisor import Child,supervise; "
        "spec=Child('test',[sys.executable,'-c',*sys.argv[1:]],dict(os.environ)); "
        "raise SystemExit(supervise([spec],grace_seconds=2))"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", runner, script, str(ready), str(stopped), str(signum)]
    )
    try:
        _wait_for(ready)
        proc.send_signal(signum)
        assert proc.wait(timeout=5) == 0
        assert stopped.exists()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_unexpected_success_stops_sibling(tmp_path):
    ready = tmp_path / "ready"
    stopped = tmp_path / "stopped"
    slow = (
        "import pathlib,signal,time,sys; signal.signal(signal.SIGTERM,lambda *_: "
        "(pathlib.Path(sys.argv[2]).touch(),sys.exit(0))); "
        "pathlib.Path(sys.argv[1]).touch(); time.sleep(60)"
    )
    dying = (
        "import pathlib,time,sys; p=pathlib.Path(sys.argv[1]);\n"
        "while not p.exists(): time.sleep(.02)"
    )
    specs = [
        supervisor.Child(
            "sibling", [sys.executable, "-c", slow, str(ready), str(stopped)], dict(os.environ)
        ),
        supervisor.Child("exits", [sys.executable, "-c", dying, str(ready)], dict(os.environ)),
    ]
    assert supervisor.supervise(specs, grace_seconds=2) != 0
    assert stopped.exists()


def test_disabled_media_reads_config_without_creating_state(tmp_path):
    config = tmp_path / "config.yaml"
    example = Path(__file__).resolve().parents[1] / "config" / "example.yaml"
    config.write_text(example.read_text())
    assert not supervisor._enabled_media(config)
    assert not (tmp_path / ".media-import").exists()
    assert not (tmp_path / ".seed-agent").exists()


def test_shutdown_signals_descendant_group(tmp_path):
    ready = tmp_path / "descendant-ready"
    stopped = tmp_path / "descendant-stopped"
    descendant = (
        "import pathlib,signal,sys,time; "
        "signal.signal(signal.SIGTERM,lambda *_: (pathlib.Path(sys.argv[2]).touch(),sys.exit(0))); "
        "pathlib.Path(sys.argv[1]).touch(); time.sleep(60)"
    )
    parent = (
        "import signal,subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c',sys.argv[1],*sys.argv[2:]]); "
        "signal.signal(signal.SIGTERM,lambda *_: (p.wait(timeout=2),sys.exit(0))); "
        "time.sleep(60)"
    )
    exit_after_ready = (
        "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]);\n"
        "while not p.exists(): time.sleep(.02)"
    )
    specs = [
        supervisor.Child(
            "parent",
            [sys.executable, "-c", parent, descendant, str(ready), str(stopped)],
            dict(os.environ),
        ),
        supervisor.Child(
            "exits", [sys.executable, "-c", exit_after_ready, str(ready)], dict(os.environ)
        ),
    ]
    assert supervisor.supervise(specs, grace_seconds=3) != 0
    assert stopped.exists()
