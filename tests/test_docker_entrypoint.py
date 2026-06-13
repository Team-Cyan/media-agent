from __future__ import annotations

from pathlib import Path


def test_entrypoint_allows_runtime_modes() -> None:
    entrypoint = Path("docker/entrypoint.sh").read_text(encoding="utf-8")

    for mode in (
        "healthcheck",
        "config-check",
        "runtime-status",
        "import-run-once",
        "import-schedule",
        "web",
    ):
        assert mode in entrypoint


def test_entrypoint_starts_web_sidecar_for_scheduler() -> None:
    entrypoint = Path("docker/entrypoint.sh").read_text(encoding="utf-8")

    assert "MEDIA_AGENT_WEB_ENABLED" in entrypoint
    assert "media-agent web" in entrypoint
    assert "media-agent \"$mode\"" in entrypoint


def test_entrypoint_can_print_startup_runtime_status() -> None:
    entrypoint = Path("docker/entrypoint.sh").read_text(encoding="utf-8")

    assert "MEDIA_AGENT_STARTUP_STATUS" in entrypoint
    assert "media-agent runtime-status" in entrypoint
    assert '--heartbeat-file "${MEDIA_AGENT_HEARTBEAT_FILE:-}"' in entrypoint
