#!/usr/bin/env sh
set -eu

mode="${MEDIA_AGENT_MODE:-${1:-healthcheck}}"

case "$mode" in
  healthcheck|config-check|runtime-status|import-run-once|import-schedule|web)
    if [ "$#" -gt 0 ] && [ "$1" = "$mode" ]; then
      shift
    fi
    exec media-agent "$mode" "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
