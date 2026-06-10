# Docker Image Runtime

`media-agent` ships as a Docker image, but this repository does not require a
local Docker Compose deployment.

The image entrypoint exposes the same CLI as the Python package:

```bash
media-agent healthcheck --config /app/config/config.yaml
media-agent config-check --config /app/config/config.yaml
media-agent runtime-status --config /app/config/config.yaml
```

The current import runtime supports:

```bash
media-agent import-run-once --config /app/config/config.yaml
media-agent import-schedule --config /app/config/config.yaml
media-agent import-run-once --config /app/config/config.yaml --execute
media-agent web --config /app/config/config.yaml --host 0.0.0.0 --port 8775
```

Dry-run is the default. `--execute` is required to create links unless the
operator-local config explicitly enables scheduler execution.

For long-running scheduler deployments, use a heartbeat file and healthcheck
staleness guard:

```bash
media-agent import-schedule \
  --config /app/config/config.yaml \
  --heartbeat-file /state/media-agent-heartbeat.json

media-agent healthcheck \
  --config /app/config/config.yaml \
  --heartbeat-file /state/media-agent-heartbeat.json \
  --max-staleness-minutes 90
```

## Container Contract

Expected paths inside a containerized runtime:

- `/app/config`: read-only config directory.
- `/app/local`: read-only local secrets directory.
- `/app/.media-agent`: writable state and audit directory.
- `/state`: optional heartbeat/output directory.
- `/downloads`: completed-download source root.
- `/media`: media library target root.

Config paths are container paths, not host paths.

TMDB credential refs should point to files inside `/app/local` or another
operator-managed secret mount:

```yaml
tmdb:
  api_key_ref: /app/local/secrets/tmdb.api-key
  bearer_token_ref: /app/local/secrets/tmdb.bearer-token
```

## Safety Defaults

- Execution must remain disabled by default.
- Source downloads must never be deleted.
- Future hardlink, symlink, or copy actions must write audit records.
- Operators can create their own Compose, Unraid, Kubernetes, or systemd wrapper
  outside this repository.
