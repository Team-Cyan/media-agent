from __future__ import annotations

import json
import sqlite3
import threading
import urllib.error
import urllib.request
from pathlib import Path

from media_agent.cli import main
from media_agent.web import build_status, render_config_page, render_dashboard, run_web_server


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
    assert status["review_items"][0]["title"] == "Arrival"
    assert status["review_items"][0]["status"] == "pending"


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
    assert "Runtime Status" in html
    assert 'href="/config"' in html
    assert "Pending Review" in html
    assert "Recent Actions" in html
    assert "TMDB API Access" not in html


def test_render_config_page_contains_config_controls_without_status_tables() -> None:
    html = render_config_page(config_text="profiles: []\n")

    assert "Configuration" in html
    assert 'href="/status"' in html
    assert "Validate" in html
    assert "TMDB API Access" in html
    assert "API 读访问令牌 / Read Access Token" in html
    assert "API 密钥 / API Key" in html
    assert "Fallback only" in html
    assert "Run dry scan" not in html
    assert "Recent Actions" not in html


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
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=5) as response:
            body = response.read().decode()
        assert "Runtime Status" in body
        assert "TMDB API Access" not in body

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


def test_web_server_reads_and_writes_config(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
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
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/config", timeout=5) as response:
            page = response.read().decode()
        assert "Configuration" in page
        assert "TMDB API Access" in page
        assert "Runtime Status" in page
        assert "Run dry scan" not in page

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/config", timeout=5) as response:
            body = response.read().decode()
        assert "profiles:" in body

        new_config = body.replace("Movies", "Films")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/config",
            data=new_config.encode(),
            method="POST",
            headers={"Content-Type": "application/x-yaml"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["ok"] is True
        assert "Films" in config.read_text(encoding="utf-8")
    finally:
        server.shutdown()
        server.server_close()


def test_web_server_validates_config_without_writing(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    config = _write_config(tmp_path, source, target)
    original = config.read_text(encoding="utf-8")
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
        draft_config = original.replace("Movies", "Films")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/config/validate",
            data=draft_config.encode(),
            method="POST",
            headers={"Content-Type": "application/x-yaml"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload == {
            "ok": True,
            "summary": {"dry_run_default": True, "enabled_profiles": 1, "profiles": 1},
        }
        assert config.read_text(encoding="utf-8") == original
    finally:
        server.shutdown()
        server.server_close()


def test_web_server_rejects_invalid_config(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    config = _write_config(tmp_path, source, target)
    original = config.read_text(encoding="utf-8")
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/config",
            data=b"profiles: []",
            method="POST",
            headers={"Content-Type": "application/x-yaml"},
        )
        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read())
            assert exc.code == 400
            assert payload["ok"] is False
        else:
            raise AssertionError("invalid config was accepted")
        assert config.read_text(encoding="utf-8") == original
    finally:
        server.shutdown()
        server.server_close()


def test_web_server_writes_tmdb_secrets_to_configured_refs(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    api_key = tmp_path / "secrets" / "tmdb.api-key"
    bearer = tmp_path / "secrets" / "tmdb.bearer-token"
    config = _write_config(tmp_path, source, target, api_key=api_key, bearer=bearer)
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
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/secrets",
            data=json.dumps({"api_key": "abc", "bearer_token": "def"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["ok"] is True
        assert api_key.read_text(encoding="utf-8") == "abc"
        assert bearer.read_text(encoding="utf-8") == "def"
    finally:
        server.shutdown()
        server.server_close()


def test_web_server_selects_review_candidate(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Unknown.Movie.mkv"
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
    with sqlite3.connect(state_dir / "state.db") as db:
        review_id = db.execute("select id from review_items").fetchone()[0]
        db.execute(
            """
            insert into review_candidates (
                review_item_id, rank, metadata_id, title, year, confidence, raw_json
            ) values (?, 1, 'tmdb:movie:603', 'The Matrix', 1999, 0.9, '{}')
            """,
            (review_id,),
        )

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
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/review-items/{review_id}/select",
            data=json.dumps({"metadata_id": "tmdb:movie:603"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["ok"] is True
        with sqlite3.connect(state_dir / "state.db") as db:
            item_status = db.execute(
                "select status from review_items where id = ?",
                (review_id,),
            ).fetchone()[0]
            decision = db.execute(
                "select selected_metadata_id, title from review_decisions"
            ).fetchone()
        assert item_status == "selected"
        assert decision == ("tmdb:movie:603", "The Matrix")
    finally:
        server.shutdown()
        server.server_close()


def _write_config(
    tmp_path: Path,
    source: Path,
    target: Path,
    *,
    api_key: Path | None = None,
    bearer: Path | None = None,
) -> Path:
    config = tmp_path / "config.yaml"
    api_key = api_key or tmp_path / "missing"
    bearer = bearer or tmp_path / "missing-bearer"
    config.write_text(
        f"""
mode: semi_auto
tmdb:
  api_key_ref: {api_key}
  bearer_token_ref: {bearer}
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
