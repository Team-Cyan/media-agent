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


def _mapping(data: dict[str, Any], key: str, *, required: bool = True) -> dict[str, Any]:
    value = data.get(key)
    if value is None and not required:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value
