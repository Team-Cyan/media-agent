# Unraid DockerMan Install

This guide is for operators who want `media-agent` to behave like a normal
Unraid-managed Docker app.

## Published Image

DockerMan should point to:

- `ghcr.io/team-cyan/media-agent:latest`

That image is published from GitHub Actions on pushes to `main`.

## Single-Root Host Layout

The Unraid template mounts one appdata folder:

- `/mnt/user/appdata/media-agent` -> `/workspace`

Inside that root, keep:

```text
/mnt/user/appdata/media-agent/
└── runtime/
    ├── config/
    │   └── config.yaml
    ├── local/
    │   └── secrets/
    │       ├── tmdb.api-key
    │       └── tmdb.bearer-token
    ├── .media-agent/
    └── state/
```

The template also maps:

- `/mnt/user/downloads` -> `/downloads`
- `/mnt/user/media` -> `/media`

Use container paths in `config.yaml`.

## Secrets Stay On Disk

Do not put TMDB tokens in DockerMan text fields.

Store them under:

```text
/mnt/user/appdata/media-agent/runtime/local/secrets/tmdb.api-key
/mnt/user/appdata/media-agent/runtime/local/secrets/tmdb.bearer-token
```

Then reference them from runtime config:

```yaml
tmdb:
  api_key_ref: /workspace/runtime/local/secrets/tmdb.api-key
  bearer_token_ref: /workspace/runtime/local/secrets/tmdb.bearer-token
```

## Template

Copy or import:

- `deploy/unraid/media-agent.xml`

Recommended defaults:

- `Network=bridge`
- restart policy `unless-stopped`
- `MEDIA_AGENT_MODE=import-schedule`
- `MEDIA_AGENT_CONFIG=/workspace/runtime/config/config.yaml`
- `MEDIA_AGENT_STATE_DIR=/workspace/runtime/.media-agent`
- `MEDIA_AGENT_HEARTBEAT_FILE=/workspace/runtime/state/media-agent-heartbeat.json`
- `MEDIA_AGENT_EXECUTE=false` until plans have been reviewed
- `MEDIA_AGENT_STARTUP_STATUS=true`
- `MEDIA_AGENT_WEB_ENABLED=true`
- `MEDIA_AGENT_WEB_HOST=0.0.0.0`
- `MEDIA_AGENT_WEB_PORT=8775`
- WebUI host port `8775` mapped to container port `8775/tcp`
- DockerMan icon URL uses the direct PNG asset at
  `docs/assets/media-agent-icon.png`.

## Runtime Visibility

Every non-healthcheck container start can print one redacted `runtime-status`
JSON line to Docker logs when `MEDIA_AGENT_STARTUP_STATUS=true`.

From the Unraid Docker console:

```sh
media-agent runtime-status \
  --config /workspace/runtime/config/config.yaml \
  --state-dir /workspace/runtime/.media-agent \
  --heartbeat-file /workspace/runtime/state/media-agent-heartbeat.json
```

For heartbeat checks:

```sh
media-agent healthcheck \
  --config /workspace/runtime/config/config.yaml \
  --heartbeat-file /workspace/runtime/state/media-agent-heartbeat.json \
  --max-staleness-minutes 90
```

Inspect the heartbeat directly when needed:

```sh
cat /workspace/runtime/state/media-agent-heartbeat.json
```

## WebUI Button

The DockerMan template maps host port `8775` to container port `8775/tcp` and
sets:

```text
MEDIA_AGENT_WEB_HOST=0.0.0.0
MEDIA_AGENT_WEB_PORT=8775
WebUI=http://[IP]:[PORT:8775]
```

If the Docker page shows the container as healthy but the WebUI button fails,
check:

```sh
docker port media-agent
docker inspect media-agent --format '{{json .NetworkSettings.Ports}}'
docker inspect media-agent --format '{{index .Config.Labels "net.unraid.docker.webui"}}'
docker exec media-agent media-agent --version
docker exec media-agent media-agent runtime-status \
  --config /workspace/runtime/config/config.yaml \
  --state-dir /workspace/runtime/.media-agent \
  --heartbeat-file /workspace/runtime/state/media-agent-heartbeat.json
```

If `ports={}` is empty, update the installed template from
`deploy/unraid/media-agent.xml`, then use Unraid's **Apply Update** action or:

```sh
/usr/local/emhttp/plugins/dynamix.docker.manager/scripts/update_container media-agent
```

After rebuild, `docker port media-agent` should show an `8775/tcp` mapping.

## Update Discipline

Keep DockerMan installs managed through the template system. Avoid replacing a
template-managed container with manual `docker rm && docker run`, because that
can detach it from DockerMan metadata and hide normal update status.
