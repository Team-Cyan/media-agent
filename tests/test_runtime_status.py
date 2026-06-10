from __future__ import annotations

import json
import time

from media_agent.cli import main


def test_runtime_status_reports_paths_without_secret_values(tmp_path, capsys) -> None:
    config = tmp_path / "config.yaml"
    state_dir = tmp_path / "state"
    heartbeat = tmp_path / "heartbeat.json"
    secret = tmp_path / "secret.txt"
    secret.write_text("do-not-print", encoding="utf-8")
    config.write_text(
        f"""
mode: semi_auto
tmdb:
  api_key_ref: {secret}
profiles:
  - name: movies
    type: movie
    source: {tmp_path / "downloads"}
    target: {tmp_path / "media"}
""",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "runtime-status",
            "--config",
            str(config),
            "--state-dir",
            str(state_dir),
            "--heartbeat-file",
            str(heartbeat),
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["state_db"].endswith("state.db")
    assert payload["audit_jsonl"].endswith("audit.jsonl")
    assert payload["heartbeat_file"] == str(heartbeat)
    assert "do-not-print" not in json.dumps(payload)


def test_healthcheck_rejects_stale_heartbeat(tmp_path, capsys) -> None:
    config = tmp_path / "config.yaml"
    heartbeat = tmp_path / "heartbeat.json"
    config.write_text(
        f"""
tmdb:
  api_key_ref: {tmp_path / "missing"}
profiles:
  - name: movies
    type: movie
    source: {tmp_path / "downloads"}
    target: {tmp_path / "media"}
""",
        encoding="utf-8",
    )
    heartbeat.write_text(json.dumps({"ts": time.time() - 3600}), encoding="utf-8")

    exit_code = main(
        [
            "healthcheck",
            "--config",
            str(config),
            "--heartbeat-file",
            str(heartbeat),
            "--max-staleness-minutes",
            "10",
        ]
    )

    assert exit_code == 1
    assert "stale heartbeat" in capsys.readouterr().err


def test_import_schedule_once_writes_heartbeat(tmp_path, capsys) -> None:
    source = tmp_path / "downloads"
    target = tmp_path / "media"
    state_dir = tmp_path / "state"
    heartbeat = tmp_path / "heartbeat.json"
    movie = source / "Arrival.2016.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
tmdb:
  api_key_ref: {tmp_path / "missing"}
scheduler:
  interval_minutes: 30
  execute: false
profiles:
  - name: movies
    type: movie
    source: {source}
    target: {target}
""",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "import-schedule",
            "--config",
            str(config),
            "--state-dir",
            str(state_dir),
            "--heartbeat-file",
            str(heartbeat),
            "--once",
            "--json",
        ]
    )

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    heartbeat_payload = json.loads(heartbeat.read_text(encoding="utf-8"))
    assert summary["planned"] == 1
    assert heartbeat_payload["summary"]["planned"] == 1
    assert heartbeat_payload["ok"] is True
