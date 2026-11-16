from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_unified_modes_use_supervisor_after_identity_guard(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "args"
    python = bin_dir / "python"
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGS_LOG"\n')
    python.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("SEED_AGENT_")}
    env.update(PATH=f"{bin_dir}:{env['PATH']}", ARGS_LOG=str(log))
    entrypoint = Path(__file__).resolve().parents[1] / "docker" / "entrypoint.sh"
    for arguments, mode in (([], "run"), (["app-healthcheck"], "healthcheck")):
        subprocess.run(["sh", str(entrypoint), *arguments], env=env, check=True)
        assert log.read_text().splitlines() == [
            "-m",
            "media_agent.supervisor",
            mode,
            "--config",
            "/app/config/config.yaml",
        ]
