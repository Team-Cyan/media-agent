from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from media_agent.cli import main
from media_agent.web import build_status, render_dashboard, run_web_server


def test_build_status_reads_state(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)

    assert (
        main(
            [
                "import-run-once",
                "--config",
                str(config),
                "--state-dir",
                str(state_dir),
                "--json",
            ]
        )
        == 0
    )

    status = build_status(state_dir)

    assert status["counts"]["planned"] == 1
    assert status["recent_actions"][0]["target_path"].endswith("Arrival (2016).mkv")
    assert status["review_items"] == []


def test_render_dashboard_contains_operational_controls() -> None:
    html = render_dashboard(
        {
            "counts": {"planned": 1, "linked": 0, "pending_review": 2},
            "recent_actions": [],
            "review_items": [],
        }
    )

    assert "Run dry scan" in html
    assert "Run execute" in html
    assert "Pending Review" in html


def test_web_server_serves_status_and_runs_scan(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)

    server = run_web_server(
        config_path=config,
        state_dir=state_dir,
        host="127.0.0.1",
        port=0,
        once=True,
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as response:
            status = json.loads(response.read())
        assert status["counts"]["planned"] == 0

        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/import-run-once",
            data=b"",
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
        assert payload["planned"] == 1

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as response:
            status = json.loads(response.read())
        assert status["counts"]["planned"] == 1
    finally:
        server.shutdown()
        server.server_close()


def _write_config(tmp_path: Path, source: Path, target: Path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
mode: semi_auto
tmdb:
  api_key_ref: local/secrets/tmdb.api-key
scheduler:
  interval_minutes: 30
  execute: false
profiles:
  - name: movies
    type: movie
    enabled: true
    source: {source}
    target: {target}
    link:
      mode: hardlink
      allow_symlink_fallback: true
    naming:
      movie_folder_template: "{{title}} ({{year}})"
      movie_file_template: "{{title}} ({{year}}){{extension}}"
""",
        encoding="utf-8",
    )
    return config
