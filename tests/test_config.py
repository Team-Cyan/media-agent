from __future__ import annotations

from pathlib import Path

import pytest

from media_agent.config import ConfigError, load_config, parse_config, validate_config


def test_example_config_is_valid() -> None:
    config = load_config(Path("config/example.yaml"))

    summary = validate_config(config)

    assert summary.profile_count == 3
    assert summary.enabled_profile_count == 3
    assert summary.dry_run_default is True


def test_parses_matching_config() -> None:
    config = load_config(Path("config/example.yaml"))

    parsed = parse_config(config)

    assert parsed.matching.auto_plan_min_confidence == 0.85
    assert parsed.matching.review_min_confidence == 0.55
    assert parsed.matching.max_review_choices == 5


def test_rejects_invalid_matching_threshold_order() -> None:
    config = {
        "tmdb": {"api_key_ref": "local/secrets/tmdb.api-key"},
        "matching": {
            "auto_plan_min_confidence": 0.4,
            "review_min_confidence": 0.8,
            "max_review_choices": 5,
        },
        "profiles": [
            {
                "name": "movies",
                "type": "movie",
                "source": "/downloads/movies",
                "target": "/media/Movies",
            }
        ],
    }

    with pytest.raises(ConfigError, match="auto_plan_min_confidence"):
        validate_config(config)


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
