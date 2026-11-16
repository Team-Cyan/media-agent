"""Initialize an isolated no-network fixture, then exec the real PID1 app.

Run only in a disposable candidate image; no host business state is mounted.
The controller checks app-healthcheck, process identity and graceful stop.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def main():
    root = Path("/tmp/single-container-smoke")
    root.mkdir()
    os.chown(root, 1000, 100)
    os.setgid(100)
    os.setuid(1000)
    config = root / "config.yaml"
    raw = yaml.safe_load(Path("/checks/example.yaml").read_text())
    raw.update(
        {
            "tracker_sites": [],
            "download_client": None,
            "deployment": {"source_id": "isolated-linux-supervisor-smoke"},
            "scheduler": {
                "tracker_backfill_enabled": False,
                "prune_enabled": False,
                "intent_enabled": False,
            },
            "media_import": {"enabled": True, "profiles": [], "interval_seconds": 1},
        }
    )
    raw["want_sources"] = {}
    config.write_text(yaml.safe_dump(raw))
    from media_agent.media_import.runtime import build_engine
    from media_agent.state import StateStore

    build_engine(config, initialize=True)
    StateStore(root / ".seed-agent/state.db")
    os.environ.update(
        SEED_AGENT_CONFIG=str(config),
        SEED_AGENT_HEARTBEAT_FILE=str(root / "state/schedule-heartbeat.json"),
        SEED_AGENT_EXECUTE="false",
        SEED_AGENT_WEB_ENABLED="true",
        SEED_AGENT_WEB_HOST="0.0.0.0",
        SEED_AGENT_WEB_PORT="8765",
    )
    os.execv("/app/docker/entrypoint.sh", ["/app/docker/entrypoint.sh"])


if __name__ == "__main__":
    main()
