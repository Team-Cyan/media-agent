from __future__ import annotations

import errno
import json
import os
import re
import sqlite3
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from media_agent.config import AppConfig, ConfigError, ProfileConfig

VIDEO_EXTENSIONS = {
    ".avi",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
    ".wmv",
}


@dataclass(frozen=True)
class MediaGuess:
    media_type: str
    title: str
    year: int | None = None
    series_title: str | None = None
    season: int | None = None
    episode: int | None = None
    episode_title: str | None = None
    confidence: float = 0.7


@dataclass(frozen=True)
class ImportAction:
    profile: str
    media_type: str
    source_path: Path
    target_path: Path
    link_mode: str
    metadata_id: str
    confidence: float


@dataclass(frozen=True)
class ImportSummary:
    scanned: int
    planned: int
    executed: int
    skipped: int
    failed: int
    dry_run: bool


def run_import_once(
    config: AppConfig,
    *,
    state_dir: Path,
    execute: bool,
) -> ImportSummary:
    state = ImportState(state_dir)
    scanned = 0
    planned = 0
    executed = 0
    skipped = 0
    failed = 0

    for profile in config.profiles:
        if not profile.enabled:
            continue
        for source_path in scan_profile(profile):
            scanned += 1
            guess = guess_media(profile, source_path)
            if guess is None:
                skipped += 1
                continue
            action = plan_action(profile, source_path, guess)
            planned += 1
            state.record_plan(action, dry_run=not execute)
            if execute:
                result = execute_action(action, profile)
                state.record_execution(action, result)
                if result == "linked":
                    executed += 1
                elif result == "target_exists":
                    skipped += 1
                else:
                    failed += 1

    return ImportSummary(
        scanned=scanned,
        planned=planned,
        executed=executed,
        skipped=skipped,
        failed=failed,
        dry_run=not execute,
    )


def scan_profile(profile: ProfileConfig) -> Iterable[Path]:
    if not profile.source.exists():
        return ()
    if profile.source.is_file():
        files = (profile.source,)
    else:
        files = profile.source.rglob("*")
    return (
        path
        for path in sorted(files)
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def guess_media(profile: ProfileConfig, source_path: Path) -> MediaGuess | None:
    if profile.type == "movie":
        return _guess_movie(source_path)
    if profile.type in {"tv", "anime"}:
        return _guess_episode(profile.type, source_path)
    return None


def plan_action(profile: ProfileConfig, source_path: Path, guess: MediaGuess) -> ImportAction:
    extension = source_path.suffix
    if guess.media_type == "movie":
        if guess.year is None:
            return _fallback_action(profile, source_path, guess)
        folder = profile.naming.movie_folder_template.format(title=guess.title, year=guess.year)
        filename = profile.naming.movie_file_template.format(
            title=guess.title,
            year=guess.year,
            edition="",
            extension=extension,
        )
        target_path = profile.target / sanitize_path_part(folder) / sanitize_path_part(filename)
        metadata_id = f"local:movie:{guess.title}:{guess.year}"
    else:
        if guess.season is None or guess.episode is None or guess.series_title is None:
            return _fallback_action(profile, source_path, guess)
        series = profile.naming.series_folder_template.format(series_title=guess.series_title)
        season = profile.naming.season_folder_template.format(season=guess.season)
        episode_title = guess.episode_title or f"Episode {guess.episode:02d}"
        filename = profile.naming.episode_file_template.format(
            series_title=guess.series_title,
            season=guess.season,
            episode=guess.episode,
            episode_title=episode_title,
            extension=extension,
        )
        target_path = (
            profile.target
            / sanitize_path_part(series)
            / sanitize_path_part(season)
            / sanitize_path_part(filename)
        )
        metadata_id = (
            f"local:{guess.media_type}:{guess.series_title}:"
            f"s{guess.season}e{guess.episode}"
        )

    return ImportAction(
        profile=profile.name,
        media_type=guess.media_type,
        source_path=source_path,
        target_path=target_path,
        link_mode=profile.link.mode,
        metadata_id=metadata_id,
        confidence=guess.confidence,
    )


def execute_action(action: ImportAction, profile: ProfileConfig) -> str:
    if action.target_path.exists():
        return "target_exists"
    action.target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if action.link_mode == "symlink":
            action.target_path.symlink_to(action.source_path)
        else:
            os.link(action.source_path, action.target_path)
        return "linked"
    except OSError as exc:
        if (
            action.link_mode == "hardlink"
            and profile.link.allow_symlink_fallback
            and exc.errno == errno.EXDEV
        ):
            action.target_path.symlink_to(action.source_path)
            return "linked"
        return f"failed:{exc.errno or exc.__class__.__name__}"


def sanitize_path_part(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in {"", ".", ".."}:
        raise ConfigError(f"unsafe empty path segment generated from: {value!r}")
    return cleaned


class ImportState:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.state_dir / "audit.jsonl"
        self.db_path = self.state_dir / "state.db"
        self._init_db()

    def record_plan(self, action: ImportAction, *, dry_run: bool) -> None:
        self._record_action(action, status="planned", dry_run=dry_run)
        self._append_audit(action, operation="plan", result="planned", dry_run=dry_run)

    def record_execution(self, action: ImportAction, result: str) -> None:
        self._record_action(action, status=result, dry_run=False)
        self._append_audit(action, operation="execute", result=result, dry_run=False)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                create table if not exists import_actions (
                    id integer primary key autoincrement,
                    created_at real not null,
                    profile text not null,
                    media_type text not null,
                    source_path text not null,
                    target_path text not null,
                    metadata_id text not null,
                    link_mode text not null,
                    confidence real not null,
                    dry_run integer not null,
                    status text not null
                )
                """
            )

    def _record_action(self, action: ImportAction, *, status: str, dry_run: bool) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                """
                insert into import_actions (
                    created_at, profile, media_type, source_path, target_path,
                    metadata_id, link_mode, confidence, dry_run, status
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    action.profile,
                    action.media_type,
                    str(action.source_path),
                    str(action.target_path),
                    action.metadata_id,
                    action.link_mode,
                    action.confidence,
                    int(dry_run),
                    status,
                ),
            )

    def _append_audit(
        self,
        action: ImportAction,
        *,
        operation: str,
        result: str,
        dry_run: bool,
    ) -> None:
        record = {
            "ts": time.time(),
            "operation": operation,
            "profile": action.profile,
            "media_type": action.media_type,
            "source_path": str(action.source_path),
            "target_path": str(action.target_path),
            "metadata_id": action.metadata_id,
            "link_mode": action.link_mode,
            "dry_run": dry_run,
            "result": result,
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def summary_to_dict(summary: ImportSummary) -> dict[str, object]:
    return asdict(summary)


def _guess_movie(source_path: Path) -> MediaGuess | None:
    stem = source_path.stem
    match = re.search(r"(19\d{2}|20\d{2})", stem)
    if not match:
        return MediaGuess(media_type="movie", title=_clean_title(stem), confidence=0.45)
    year = int(match.group(1))
    title = _clean_title(stem[: match.start()])
    return MediaGuess(media_type="movie", title=title, year=year, confidence=0.72)


def _guess_episode(media_type: str, source_path: Path) -> MediaGuess | None:
    stem = source_path.stem
    match = re.search(r"[Ss](\d{1,2})[ ._-]*[Ee](\d{1,3})", stem)
    if not match:
        return None
    series_title = _clean_title(stem[: match.start()])
    episode_title = _clean_title(stem[match.end() :]) or f"Episode {int(match.group(2)):02d}"
    return MediaGuess(
        media_type=media_type,
        title=series_title,
        series_title=series_title,
        season=int(match.group(1)),
        episode=int(match.group(2)),
        episode_title=episode_title,
        confidence=0.7,
    )


def _fallback_action(profile: ProfileConfig, source_path: Path, guess: MediaGuess) -> ImportAction:
    target_path = profile.target / "_Review" / sanitize_path_part(source_path.name)
    return ImportAction(
        profile=profile.name,
        media_type=guess.media_type,
        source_path=source_path,
        target_path=target_path,
        link_mode=profile.link.mode,
        metadata_id=f"local:review:{source_path.stem}",
        confidence=guess.confidence,
    )


def _clean_title(value: str) -> str:
    cleaned = re.sub(r"[._-]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title()
