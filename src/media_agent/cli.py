from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from media_agent import __version__
from media_agent.config import ConfigError, load_config, parse_config, validate_config
from media_agent.import_runner import run_import_once, summary_to_dict

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

    import_once = subparsers.add_parser("import-run-once", help="scan and plan one import pass")
    add_import_args(import_once)
    import_once.set_defaults(func=run_import_run_once)

    import_schedule = subparsers.add_parser(
        "import-schedule",
        help="run import passes on an interval",
    )
    add_import_args(import_schedule)
    import_schedule.add_argument("--interval-minutes", type=int)
    import_schedule.set_defaults(func=run_import_schedule)

    web = subparsers.add_parser("web", help="web UI placeholder")
    web.add_argument("--config", default=DEFAULT_CONFIG)
    web.set_defaults(func=run_not_implemented)

    return parser


def add_import_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--state-dir",
        default=os.environ.get("MEDIA_AGENT_STATE_DIR", ".media-agent"),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="create links instead of dry-run only",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable summary")


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


def run_import_run_once(args: argparse.Namespace) -> int:
    config = _load_app_config(args.config)
    execute = bool(args.execute or config.scheduler.execute)
    summary = run_import_once(config, state_dir=Path(args.state_dir), execute=execute)
    _print_summary(summary, as_json=args.json)
    return 1 if summary.failed else 0


def run_import_schedule(args: argparse.Namespace) -> int:
    config = _load_app_config(args.config)
    interval = args.interval_minutes or config.scheduler.interval_minutes
    execute = bool(args.execute or config.scheduler.execute)
    while True:
        summary = run_import_once(config, state_dir=Path(args.state_dir), execute=execute)
        _print_summary(summary, as_json=args.json)
        time.sleep(interval * 60)


def _load_and_validate(config_path: str):
    config = load_config(config_path)
    return validate_config(config)


def _load_app_config(config_path: str):
    config = load_config(config_path)
    return parse_config(config)


def _print_summary(summary, *, as_json: bool) -> None:
    payload = summary_to_dict(summary)
    if as_json:
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        "media-agent import summary: "
        f"scanned={summary.scanned} planned={summary.planned} "
        f"executed={summary.executed} skipped={summary.skipped} "
        f"failed={summary.failed} dry_run={summary.dry_run}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
