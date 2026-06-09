from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from media_agent.cli import main


def test_import_run_once_dry_run_plans_movie_without_linking(tmp_path, capsys) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.1080p.BluRay.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)

    exit_code = main(
        [
            "import-run-once",
            "--config",
            str(config),
            "--state-dir",
            str(state_dir),
            "--json",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["planned"] == 1
    assert output["executed"] == 0
    planned_target = target / "Arrival (2016)" / "Arrival (2016).mkv"
    assert not planned_target.exists()

    audit = [json.loads(line) for line in (state_dir / "audit.jsonl").read_text().splitlines()]
    assert audit[0]["operation"] == "plan"
    assert audit[0]["source_path"] == str(movie)
    assert audit[0]["target_path"] == str(planned_target)
    assert audit[0]["result"] == "planned"

    with sqlite3.connect(state_dir / "state.db") as db:
        rows = db.execute("select source_path, target_path, status from import_actions").fetchall()
    assert rows == [(str(movie), str(planned_target), "planned")]


def test_import_run_once_execute_creates_hardlink_and_audit(tmp_path, capsys) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.1080p.BluRay.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)

    exit_code = main(
        [
            "import-run-once",
            "--config",
            str(config),
            "--state-dir",
            str(state_dir),
            "--execute",
            "--json",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["planned"] == 1
    assert output["executed"] == 1
    linked = target / "Arrival (2016)" / "Arrival (2016).mkv"
    assert linked.exists()
    assert linked.read_bytes() == b"movie"
    assert os.stat(movie).st_ino == os.stat(linked).st_ino

    audit = [json.loads(line) for line in (state_dir / "audit.jsonl").read_text().splitlines()]
    assert [row["operation"] for row in audit] == ["plan", "execute"]
    assert audit[-1]["result"] == "linked"


def test_import_run_once_plans_tv_episode(tmp_path, capsys) -> None:
    source = tmp_path / "downloads" / "tv"
    target = tmp_path / "media" / "TV"
    state_dir = tmp_path / "state"
    episode = source / "Breaking.Bad.S01E01.Pilot.mkv"
    episode.parent.mkdir(parents=True)
    episode.write_bytes(b"episode")
    config = _write_config(tmp_path, source, target, profile_type="tv")

    exit_code = main(
        [
            "import-run-once",
            "--config",
            str(config),
            "--state-dir",
            str(state_dir),
            "--json",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["planned"] == 1
    planned = target / "Breaking Bad" / "Season 01" / "Breaking Bad - S01E01 - Pilot.mkv"
    audit = [json.loads(line) for line in (state_dir / "audit.jsonl").read_text().splitlines()]
    assert audit[0]["target_path"] == str(planned)


def _write_config(
    tmp_path: Path,
    source: Path,
    target: Path,
    *,
    profile_type: str = "movie",
) -> Path:
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
  - name: {profile_type}
    type: {profile_type}
    enabled: true
    source: {source}
    target: {target}
    link:
      mode: hardlink
      allow_symlink_fallback: true
    naming:
      collection_folders: true
      movie_folder_template: "{{title}} ({{year}})"
      movie_file_template: "{{title}} ({{year}}){{extension}}"
      series_folder_template: "{{series_title}}"
      season_folder_template: "Season {{season:02d}}"
      episode_file_template: >-
        {{series_title}} - S{{season:02d}}E{{episode:02d}} -
        {{episode_title}}{{extension}}
""",
        encoding="utf-8",
    )
    return config
