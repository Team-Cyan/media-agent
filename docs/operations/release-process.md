# Release Process

Keep release-facing metadata aligned before pushing a deployable change:

- `VERSION`
- `CHANGELOG.md`
- `docs/roadmap.md`
- `deploy/unraid/media-agent.xml`
- `docs/operations/unraid-dockerman.md`

## Branch Convention

`main` is the active development branch.

For each medium version line, keep an archival branch:

```text
release/<major>.<minor>
```

Examples:

- `0.1.0` uses `release/0.1`
- `0.2.0` uses `release/0.2`

Do not develop routine work on release branches. They are historical
checkpoints unless a specific hotfix requires one.

## Pre-Push Checklist

Run:

```bash
uv run ruff check .
uv run pytest -q
git diff --check
```

For Unraid-facing changes, also verify:

```bash
uv run python - <<'PY'
import xml.etree.ElementTree as ET
ET.parse("deploy/unraid/media-agent.xml")
print("xml ok")
PY
```

If Docker is available, build locally:

```bash
docker build -t media-agent:local .
```

## Unraid Release Expectations

Before calling a release deployable to Unraid:

1. GHCR image must publish successfully from GitHub Actions.
2. DockerMan template must reference the expected image, WebUI port, icon, and
   healthcheck.
3. `media-agent runtime-status` must not print secret values.
4. Web UI button should open the operational UI.
5. Scheduler heartbeat should update under the mounted runtime state path.
