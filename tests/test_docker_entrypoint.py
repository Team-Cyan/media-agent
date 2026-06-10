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
