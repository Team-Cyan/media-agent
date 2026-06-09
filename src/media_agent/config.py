from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_PROFILE_TYPES = {"movie", "tv", "anime"}
VALID_LINK_MODES = {"hardlink", "symlink"}


@dataclass(frozen=True)
class ConfigSummary:
    profile_count: int
    enabled_profile_count: int
    dry_run_default: bool


@dataclass(frozen=True)
class LinkConfig:
    mode: str = "hardlink"
    allow_symlink_fallback: bool = False


@dataclass(frozen=True)
class NamingConfig:
    collection_folders: bool = False
    movie_folder_template: str = "{title} ({year})"
    movie_file_template: str = "{title} ({year}){extension}"
    series_folder_template: str = "{series_title}"
    season_folder_template: str = "Season {season:02d}"
    episode_file_template: str = (
        "{series_title} - S{season:02d}E{episode:02d} - {episode_title}{extension}"
    )


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    type: str
    enabled: bool
    source: Path
    target: Path
    link: LinkConfig
    naming: NamingConfig


@dataclass(frozen=True)
class SchedulerConfig:
    interval_minutes: int = 30
    execute: bool = False


@dataclass(frozen=True)
class AppConfig:
    mode: str
    tmdb_api_key_ref: str
    tmdb_bearer_token_ref: str | None
    tmdb_language: str
    scheduler: SchedulerConfig
    profiles: tuple[ProfileConfig, ...]


class ConfigError(ValueError):
    """Raised when a media-agent config file is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config file does not exist: {config_path}")
    if not config_path.is_file():
        raise ConfigError(f"config path is not a file: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ConfigError("config root must be a mapping")
    return loaded


def validate_config(config: dict[str, Any]) -> ConfigSummary:
    tmdb = _mapping(config, "tmdb")
    if not tmdb.get("api_key_ref"):
        raise ConfigError("tmdb.api_key_ref is required")

    scheduler = _mapping(config, "scheduler", required=False)
    execute = bool(scheduler.get("execute", False))

    profiles = config.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ConfigError("profiles must be a non-empty list")

    enabled_count = 0
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            raise ConfigError(f"profiles[{index}] must be a mapping")
        _validate_profile(profile, index)
        if profile.get("enabled", True):
            enabled_count += 1

    return ConfigSummary(
        profile_count=len(profiles),
        enabled_profile_count=enabled_count,
        dry_run_default=not execute,
    )


def parse_config(config: dict[str, Any]) -> AppConfig:
    validate_config(config)
    tmdb = _mapping(config, "tmdb")
    scheduler = _mapping(config, "scheduler", required=False)
    profiles = tuple(_parse_profile(profile) for profile in config["profiles"])
    return AppConfig(
        mode=str(config.get("mode", "semi_auto")),
        tmdb_api_key_ref=str(tmdb["api_key_ref"]),
        tmdb_bearer_token_ref=(
            str(tmdb["bearer_token_ref"]) if tmdb.get("bearer_token_ref") else None
        ),
        tmdb_language=str(tmdb.get("language", "en-US")),
        scheduler=SchedulerConfig(
            interval_minutes=int(scheduler.get("interval_minutes", 30)),
            execute=bool(scheduler.get("execute", False)),
        ),
        profiles=profiles,
    )


def _validate_profile(profile: dict[str, Any], index: int) -> None:
    prefix = f"profiles[{index}]"
    for key in ("name", "type", "source", "target"):
        if not profile.get(key):
            raise ConfigError(f"{prefix}.{key} is required")

    profile_type = profile["type"]
    if profile_type not in VALID_PROFILE_TYPES:
        raise ConfigError(f"{prefix}.type must be one of: {', '.join(sorted(VALID_PROFILE_TYPES))}")

    link = _mapping(profile, "link", required=False)
    link_mode = link.get("mode", "hardlink")
    if link_mode not in VALID_LINK_MODES:
        valid_modes = ", ".join(sorted(VALID_LINK_MODES))
        raise ConfigError(f"{prefix}.link.mode must be one of: {valid_modes}")


def _parse_profile(profile: dict[str, Any]) -> ProfileConfig:
    link = _mapping(profile, "link", required=False)
    naming = _mapping(profile, "naming", required=False)
    return ProfileConfig(
        name=str(profile["name"]),
        type=str(profile["type"]),
        enabled=bool(profile.get("enabled", True)),
        source=Path(str(profile["source"])),
        target=Path(str(profile["target"])),
        link=LinkConfig(
            mode=str(link.get("mode", "hardlink")),
            allow_symlink_fallback=bool(link.get("allow_symlink_fallback", False)),
        ),
        naming=NamingConfig(
            collection_folders=bool(naming.get("collection_folders", False)),
            movie_folder_template=str(
                naming.get("movie_folder_template", "{title} ({year})")
            ),
            movie_file_template=str(
                naming.get("movie_file_template", "{title} ({year}){extension}")
            ),
            series_folder_template=str(naming.get("series_folder_template", "{series_title}")),
            season_folder_template=str(naming.get("season_folder_template", "Season {season:02d}")),
            episode_file_template=str(
                naming.get(
                    "episode_file_template",
                    "{series_title} - S{season:02d}E{episode:02d} - "
                    "{episode_title}{extension}",
                )
            ),
        ),
    )


def _mapping(data: dict[str, Any], key: str, *, required: bool = True) -> dict[str, Any]:
    value = data.get(key)
    if value is None and not required:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value
