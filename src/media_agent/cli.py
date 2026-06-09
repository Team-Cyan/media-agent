from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from media_agent import __version__
from media_agent.config import ConfigError, load_config, validate_config

DEFAULT_CONFIG = os.environ.get("MEDIA_AGENT_CONFIG", "config/config.yaml")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"media-agent: config error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="media-agent")
    parser.add_argument("--version", action="version", version=f"media-agent {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    healthcheck = subparsers.add_parser(
        "healthcheck",
        help="validate runtime config and state path",
    )
    healthcheck.add_argument("--config", default=DEFAULT_CONFIG)
    healthcheck.add_argument(
        "--state-dir",
        default=os.environ.get("MEDIA_AGENT_STATE_DIR", ".media-agent"),
    )
    healthcheck.set_defaults(func=run_healthcheck)

    config_check = subparsers.add_parser("config-check", help="validate a config file")
    config_check.add_argument("--config", default=DEFAULT_CONFIG)
    config_check.set_defaults(func=run_config_check)

    for command in ("import-run-once", "import-schedule", "web"):
        future = subparsers.add_parser(command, help=f"{command} placeholder")
        future.add_argument("--config", default=DEFAULT_CONFIG)
        future.set_defaults(func=run_not_implemented)

    return parser


def run_healthcheck(args: argparse.Namespace) -> int:
    summary = _load_and_validate(args.config)
    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(state_dir, os.W_OK):
        raise ConfigError(f"state dir is not writable: {state_dir}")

    print(
        json.dumps(
            {
                "ok": True,
                "version": __version__,
                "profiles": summary.profile_count,
                "enabled_profiles": summary.enabled_profile_count,
                "dry_run_default": summary.dry_run_default,
                "state_dir": str(state_dir),
            },
            sort_keys=True,
        )
    )
    return 0


def run_config_check(args: argparse.Namespace) -> int:
    summary = _load_and_validate(args.config)
    print(
        json.dumps(
            {
                "ok": True,
                "profiles": summary.profile_count,
                "enabled_profiles": summary.enabled_profile_count,
                "dry_run_default": summary.dry_run_default,
            },
            sort_keys=True,
        )
    )
    return 0


def run_not_implemented(args: argparse.Namespace) -> int:
    _load_and_validate(args.config)
    print(
        "media-agent runtime command is scaffolded but not implemented yet; "
        "use config-check or healthcheck for bootstrap validation.",
        file=sys.stderr,
    )
    return 64


def _load_and_validate(config_path: str):
    config = load_config(config_path)
    return validate_config(config)


if __name__ == "__main__":
    raise SystemExit(main())
