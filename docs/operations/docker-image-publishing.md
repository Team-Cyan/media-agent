# Docker Image Publishing

The GitHub workflow publishes multi-architecture images to:

```text
ghcr.io/team-cyan/media-agent
```

## Release Inputs

- `VERSION` is the image version source.
- Tags named `v*` must match `VERSION`.
- `main` publishes `latest`, branch, and short SHA tags.

## Local Build

```bash
docker build -t media-agent:local .
docker run --rm \
  -v "$PWD/config:/app/config:ro" \
  -v "$PWD/.media-agent:/app/.media-agent" \
  media-agent:local healthcheck --config /app/config/example.yaml
```

## Required Repository Settings

The workflow uses `GITHUB_TOKEN` with `packages: write`. No extra package token
is required for normal GHCR publishing from this repository.
