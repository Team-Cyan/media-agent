#!/usr/bin/env sh
set -eu

mode="${MEDIA_AGENT_MODE:-${1:-healthcheck}}"
config="${MEDIA_AGENT_CONFIG:-/app/config/config.yaml}"
state_dir="${MEDIA_AGENT_STATE_DIR:-/app/.media-agent}"
web_host="${MEDIA_AGENT_WEB_HOST:-0.0.0.0}"
web_port="${MEDIA_AGENT_WEB_PORT:-8775}"

case "$mode" in
  healthcheck|config-check|runtime-status|import-run-once|import-schedule|web)
    if [ "$#" -gt 0 ] && [ "$1" = "$mode" ]; then
      shift
    fi
    if [ "$mode" = "import-schedule" ] && [ "${MEDIA_AGENT_WEB_ENABLED:-false}" = "true" ]; then
      media-agent web \
        --config "$config" \
        --state-dir "$state_dir" \
        --host "$web_host" \
        --port "$web_port" &
    fi
    exec media-agent "$mode" "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
