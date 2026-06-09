# Docker Image Runtime

`media-agent` ships as a Docker image, but this repository does not require a
local Docker Compose deployment.

The image entrypoint exposes the same CLI as the Python package:

```bash
media-agent healthcheck --config /app/config/config.yaml
media-agent config-check --config /app/config/config.yaml
```

The current import runtime supports:

```bash
media-agent import-run-once --config /app/config/config.yaml
media-agent import-schedule --config /app/config/config.yaml
media-agent import-run-once --config /app/config/config.yaml --execute
```

Dry-run is the default. `--execute` is required to create links unless the
operator-local config explicitly enables scheduler execution.

The Web UI command is still a placeholder:

```bash
media-agent web --config /app/config/config.yaml
```

## Container Contract

Expected paths inside a containerized runtime:

- `/app/config`: read-only config directory.
- `/app/local`: read-only local secrets directory.
- `/app/.media-agent`: writable state and audit directory.
- `/downloads`: completed-download source root.
- `/media`: media library target root.

Config paths are container paths, not host paths.

## Safety Defaults

- Execution must remain disabled by default.
- Source downloads must never be deleted.
- Future hardlink, symlink, or copy actions must write audit records.
- Operators can create their own Compose, Unraid, Kubernetes, or systemd wrapper
  outside this repository.
