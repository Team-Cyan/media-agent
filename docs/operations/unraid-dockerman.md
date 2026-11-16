# Unraid DockerMan Install

This guide is for operators who want `media-agent` to look and behave like a
normal Unraid-managed Docker app instead of a standalone Compose project.

## Why This Path Exists

Docker Compose is enough to run `media-agent`, but Unraid DockerMan gives you:

- template-backed edit and rebuild actions,
- container lifecycle controls in the main Docker page,
- remote image update checks when the image is published to GHCR,
- simpler operator ergonomics for a long-lived NAS service.

## Published Image

DockerMan should point to:

- `ghcr.io/team-cyan/media-agent:latest`

That image is published from GitHub Actions on pushes to `main`.

## Single-Root Host Layout

The Unraid template retains the existing appdata root:

- `/mnt/user/appdata/seed-agent` -> `/workspace`

Inside that root, keep:

```text
/mnt/user/appdata/seed-agent/
└── runtime/
    ├── config/
    │   └── config.yaml
    ├── local/
    │   ├── inbox/
    │   └── secrets/
    ├── .seed-agent/
    ├── .media-import/
    └── state/
```

That keeps the Unraid mapping surface simple while preserving the repository's
expected config-relative secret paths.

## Secrets Stay On Disk

The DockerMan template intentionally does not expose M-Team or qBittorrent
credentials as template text fields.

Keep secrets as local files under:

- `/mnt/user/appdata/seed-agent/runtime/local/secrets/mteam-api-key.txt`
- `/mnt/user/appdata/seed-agent/runtime/local/secrets/qbittorrent.yaml`

That keeps credentials out of the template XML and still lets the app
load them through the checked-in config file at:

- `/workspace/runtime/config/config.yaml`

DockerMan also mounts one common source and library parent at `/media`; the runtime config resolves `local/secrets/...` relative to
that mounted root.

## Template

Copy or import:

- `deploy/unraid/media-agent.xml`

Recommended user-visible defaults:

- `Network=bridge`
- restart policy `on-failure:5`
- `SEED_AGENT_MODE=app`
- `SEED_AGENT_CONFIG=/workspace/runtime/config/config.yaml`
- `SEED_AGENT_HEARTBEAT_FILE=/workspace/runtime/state/schedule-heartbeat.json`
- `SEED_AGENT_EXECUTE=true`
- Configure scheduler interval, free-window safety, prune, tracker backfill,
  and Intent execution in YAML or the Web UI. The DockerMan template does not
  define scheduler policy environment overrides.
- `SEED_AGENT_STARTUP_STATUS=true`
- `SEED_AGENT_WEB_ENABLED=true`
- `SEED_AGENT_WEB_HOST=0.0.0.0`
- `SEED_AGENT_WEB_PORT=8765`
- WebUI host port `8765` mapped to container port `8765/tcp`

The app supervises scheduler, enabled Web UI and the media worker when configured.
Set the common media parent to an existing host directory and configure source and
library below `/media`. Avoid nested mounts: separate binds can cause hardlink
`EXDEV`. This RW mount does not provide kernel-enforced source read-only protection;
verify real hardlink and root identity behavior before production. The unified
container can access downloader and media credentials, so separate process/container
credential isolation is no longer provided. No Docker socket is required.

Before starting with media configured, explicitly initialize new media state with
`media-agent media-state-init --config /workspace/runtime/config/config.yaml` in a
one-off container using the same mounts. Preserve existing state, stop and drain the
legacy worker, and follow [Media Import](media-import.md) for migration; never run
it alongside the unified app. Initialization does not replay scans.

## Runtime Visibility

Inspect the redacted runtime status to confirm the version, configuration,
credential-file visibility and state paths.

Run this from the Unraid Docker console:

```sh
media-agent runtime-status \
  --config /workspace/runtime/config/config.yaml \
  --heartbeat-file /workspace/runtime/state/schedule-heartbeat.json \
  --max-staleness-minutes 90
```

For the same health check used by DockerMan, run:

```sh
/app/docker/entrypoint.sh app-healthcheck
```

It checks seed state and heartbeat, the enabled Web endpoint, and media health
when media is configured. Docker health alone does not restart a container; the
supervisor exits on a child failure so the bounded restart policy can apply.

The heartbeat JSON now includes the package version and config path in addition
to cycle, interval, execution mode, accepted/enqueued counts, and the last error
field. If Unraid's log viewer looks empty, inspect the mounted file directly:

```sh
cat /workspace/runtime/state/schedule-heartbeat.json
```

## Updating The Container

After the container is installed through DockerMan, keep it managed by the
Unraid template system.

Use the Docker page's normal **Update** / **Apply Update** action when GHCR has
a new `latest` image. Do not update a template-managed install with manual
`docker rm && docker run` commands. Manual recreation can detach the running
container from DockerMan's template metadata, which makes the Unraid UI treat it
like a third-party container and can hide normal up-to-date status.

If a command-line repair is needed on the Unraid host, prefer DockerMan's own
template rebuild/update script so the recreated container keeps the managed
label:

```sh
/usr/local/emhttp/plugins/dynamix.docker.manager/scripts/update_container media-agent
```

Afterward, confirm the container still has:

```text
net.unraid.docker.managed=dockerman
```

Also confirm Docker kept the scheduler restart policy:

```sh
docker inspect media-agent --format '{{json .HostConfig.RestartPolicy}}'
```

Expected:

```json
{"Name":"on-failure","MaximumRetryCount":5}
```

If repeated `latest` pulls leave old `ghcr.io/team-cyan/media-agent:<none>`
images behind, remove only unused media-agent dangling images. Avoid broad
`docker system prune` operations on a NAS host.

## WebUI Button

`media-agent` exposes the settings Web UI on container port `8765` when
`SEED_AGENT_WEB_ENABLED=true`.

The DockerMan template maps host port `8765` to container port `8765/tcp` and
sets:

```text
SEED_AGENT_WEB_ENABLED=true
SEED_AGENT_WEB_HOST=0.0.0.0
SEED_AGENT_WEB_PORT=8765
WebUI=http://[IP]:[PORT:8765]
```

If the Web UI is exposed beyond a trusted local network, add
`SEED_AGENT_WEB_TOKEN` to the DockerMan template. Non-empty values require
write/search/enqueue `POST` calls to include `X-Seed-Agent-Token` or
`Authorization: Bearer`.

If the Docker page shows the container as healthy but the WebUI button opens an
unavailable page, check these live facts before changing application config:

```sh
docker port media-agent
docker inspect media-agent --format '{{json .NetworkSettings.Ports}}'
docker inspect media-agent --format '{{index .Config.Labels "net.unraid.docker.webui"}}'
docker exec media-agent media-agent --version
docker exec media-agent media-agent runtime-status \
  --config /workspace/runtime/config/config.yaml \
  --heartbeat-file /workspace/runtime/state/schedule-heartbeat.json \
  --max-staleness-minutes 90
```

A healthy scheduler with `ports={}` means the image updated, but the installed
DockerMan template did not publish the Web UI port. Update the template from
`deploy/unraid/media-agent.xml`, then use Unraid's **Apply Update** action or:

```sh
/usr/local/emhttp/plugins/dynamix.docker.manager/scripts/update_container media-agent
```

After the rebuild, `docker port media-agent` should show a `8765/tcp` mapping.
