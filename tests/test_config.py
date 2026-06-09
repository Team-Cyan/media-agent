from __future__ import annotations

from pathlib import Path

import pytest

from media_agent.config import ConfigError, load_config, validate_config


def test_example_config_is_valid() -> None:
    config = load_config(Path("config/example.yaml"))

    summary = validate_config(config)

    assert summary.profile_count == 3
    assert summary.enabled_profile_count == 3
    assert summary.dry_run_default is True


def test_rejects_invalid_link_mode() -> None:
    config = {
        "tmdb": {"api_key_ref": "local/secrets/tmdb.api-key"},
        "profiles": [
            {
                "name": "movies",
                "type": "movie",
                "source": "/downloads/movies",
                "target": "/media/Movies",
                "link": {"mode": "delete"},
            }
        ],
    }

    with pytest.raises(ConfigError, match="link.mode"):
        validate_config(config)
