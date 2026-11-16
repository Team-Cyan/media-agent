"""Supervise the independent roles that share a single container."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from media_agent.config_views import load_view


@dataclass(frozen=True)
class Child:
    name: str
    argv: list[str]
    env: dict[str, str]


def _enabled_media(config: Path) -> bool:
    return bool(load_view(config, "seed").media_configured)


def _web_enabled(env: Mapping[str, str]) -> bool:
    return env.get("SEED_AGENT_WEB_ENABLED", "false") == "true"


def children(config: Path, env: Mapping[str, str]) -> list[Child]:
    base = dict(env)
    seed_env = {**base, "SEED_AGENT_ROLE": "seed"}
    media_env = {**base, "SEED_AGENT_ROLE": "media"}
    scheduler = ["media-agent", "schedule-run", "--config", str(config)]
    if env.get("SEED_AGENT_EXECUTE", "true") == "true":
        scheduler.append("--execute")
    for key, option in (
        ("SEED_AGENT_MIN_FREE_WINDOW_MINUTES", "--min-free-window-minutes"),
        ("SEED_AGENT_HEARTBEAT_FILE", "--heartbeat-file"),
        ("SEED_AGENT_INTERVAL_MINUTES", "--interval-minutes"),
        ("SEED_AGENT_MAX_CYCLES", "--max-cycles"),
    ):
        if env.get(key):
            scheduler.extend([option, env[key]])
    for key, yes, no in (
        (
            "SEED_AGENT_REQUIRE_KNOWN_FREE_WINDOW",
            "--require-known-free-window",
            "--allow-unknown-free-window",
        ),
        ("SEED_AGENT_PRUNE", "--prune", "--no-prune"),
        ("SEED_AGENT_INTENT", "--intent", "--no-intent"),
        ("SEED_AGENT_INTENT_EXECUTE", "--intent-execute", "--intent-dry-run"),
    ):
        if env.get(key):
            scheduler.append(yes if env[key] == "true" else no)
    result = [Child("scheduler", scheduler, seed_env)]
    if _web_enabled(env):
        result.append(
            Child(
                "web",
                [
                    "media-agent",
                    "web",
                    "--config",
                    str(config),
                    "--host",
                    env.get("SEED_AGENT_WEB_HOST", "0.0.0.0"),
                    "--port",
                    env.get("SEED_AGENT_WEB_PORT", "8765"),
                ],
                seed_env,
            )
        )
    if _enabled_media(config):
        worker = ["media-agent", "media-worker", "--config", str(config)]
        if env.get("SEED_AGENT_MAX_CYCLES"):
            worker.extend(["--max-cycles", env["SEED_AGENT_MAX_CYCLES"]])
        result.append(Child("media-worker", worker, media_env))
    return result


def _reap_adopted(processes: Sequence[tuple[Child, subprocess.Popen[bytes]]]) -> None:
    """Reap descendants adopted by PID 1 without stealing a tracked exit status."""
    if not all(hasattr(os, name) for name in ("waitid", "P_ALL", "WNOWAIT")):
        return
    tracked = {proc.pid: proc for _, proc in processes}
    while True:
        try:
            event = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        except ChildProcessError:
            return
        if event is None:
            return
        if event.si_pid in tracked:
            tracked[event.si_pid].poll()
        else:
            try:
                os.waitpid(event.si_pid, os.WNOHANG)
            except ChildProcessError:
                pass


def supervise(specs: Sequence[Child], *, grace_seconds: float = 15) -> int:
    processes: list[tuple[Child, subprocess.Popen[bytes]]] = []
    received: int | None = None

    def stop(signum: int, _frame: object) -> None:
        nonlocal received
        if received is None:
            received = signum

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    result = 1
    try:
        for spec in specs:
            if received is not None:
                break
            proc = subprocess.Popen(spec.argv, env=spec.env, start_new_session=True)
            processes.append((spec, proc))
        while received is None:
            _reap_adopted(processes)
            for spec, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"{spec.name} exited unexpectedly ({code})", file=sys.stderr, flush=True)
                    return_code = code if code > 0 else 1
                    result = min(return_code, 255)
                    break
            else:
                time.sleep(0.1)
                continue
            break
        if received is not None:
            result = 0
    finally:
        # Signal every owned group even if its leader already exited: descendants may remain.
        shutdown_signal = received or signal.SIGTERM
        for _, proc in processes:
            try:
                os.killpg(proc.pid, shutdown_signal)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + grace_seconds
        # Groups, not just leaders, determine when cleanup is complete.
        while time.monotonic() < deadline:
            _reap_adopted(processes)
            for _, proc in processes:
                proc.poll()
            alive = []
            for _, proc in processes:
                try:
                    os.killpg(proc.pid, 0)
                    alive.append(proc)
                except ProcessLookupError:
                    pass
            if not alive:
                break
            time.sleep(0.1)
        for _, proc in processes:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for _, proc in processes:
            proc.wait()
        _reap_adopted(processes)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return result


def healthcheck(config: Path, env: Mapping[str, str]) -> int:
    # Reuse the existing read-only checks in-process: no service or database initialization.
    import typer

    from media_agent.cli import healthcheck as role_healthcheck

    try:
        media_enabled = _enabled_media(config)
        web_url = None
        if _web_enabled(env):
            host = env.get("SEED_AGENT_WEB_HOST", "0.0.0.0")
            if host in ("0.0.0.0", "::", "[::]"):
                host = "127.0.0.1"
            elif ":" in host and not host.startswith("["):
                host = f"[{host}]"
            web_url = f"http://{host}:{env.get('SEED_AGENT_WEB_PORT', '8765')}/api/health"
        role_healthcheck(
            config=config,
            role="seed",
            heartbeat_file=Path(env["SEED_AGENT_HEARTBEAT_FILE"])
            if env.get("SEED_AGENT_HEARTBEAT_FILE")
            else None,
            max_staleness_minutes=int(env["SEED_AGENT_MAX_STALENESS_MINUTES"])
            if env.get("SEED_AGENT_MAX_STALENESS_MINUTES")
            else None,
            web_health_url=web_url,
        )
        if media_enabled:
            role_healthcheck(
                config=config,
                role="media",
                heartbeat_file=None,
                max_staleness_minutes=None,
                web_health_url=None,
            )
    except typer.Exit as exc:
        return exc.exit_code or 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("run", "healthcheck"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "healthcheck":
            return healthcheck(args.config, os.environ)
        return supervise(children(args.config, os.environ))
    except (OSError, ValueError) as exc:
        print(f"supervisor: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
