# media-agent

`media-agent` is a Docker-first media library import tool for NAS and homelab deployments.

It scans completed-download source folders, matches media through TMDB, builds Plex/Jellyfin/Emby-friendly target paths, and links files into media library folders.

The first capability is the media linker/importer:

- movies,
- TV shows,
- anime,
- per-profile source and target folders,
- TMDB-first scraping,
- semi-automatic matching,
- Web UI review for uncertain matches,
- hardlink-first import with optional symlink fallback,
- dry-run-first scheduled scans,
- durable audit and local state.

## Relationship To seed-agent

`seed-agent` owns PT discovery, resource intent search, qBittorrent enqueue, upload strategy, and cleanup decisions.

`media-agent` owns completed-file organization after downloads already exist on disk.

The split is intentional:

- `seed-agent` decides what to download and how to manage PT/downloader policy.
- `media-agent` decides how completed files should appear in Plex/Jellyfin/Emby libraries.

## Current Scope

Version 0.1.0 is a working local import MVP with config validation, source
scanning, filename-based media guesses, dry-run planning, SQLite state, JSONL
audit, and explicit hardlink/symlink execution.

```bash
media-agent import-run-once --config config/config.yaml
media-agent import-schedule --config config/config.yaml --interval-minutes 30
media-agent web --config config/config.yaml --host 0.0.0.0 --port 8775
```

The default behavior must remain dry-run unless execution is explicitly enabled.

Current working commands:

```bash
media-agent config-check --config config/example.yaml
media-agent healthcheck --config config/example.yaml
media-agent runtime-status --config config/example.yaml --state-dir .media-agent
media-agent import-run-once --config config/config.yaml --state-dir .media-agent --json
media-agent import-schedule --config config/config.yaml --state-dir .media-agent --heartbeat-file state/media-agent-heartbeat.json
media-agent import-run-once --config config/config.yaml --state-dir .media-agent --execute
media-agent web --config config/config.yaml --state-dir .media-agent --host 127.0.0.1 --port 8775
```

`import-run-once` uses TMDB when `tmdb.api_key_ref` or
`tmdb.bearer_token_ref` points to a readable local secret file. If TMDB secrets
are absent, it falls back to conservative filename parsing.

## Docker Image

The repository builds and publishes an image, but it does not require a local
Docker Compose deployment.

```bash
docker run --rm \
  -v "$PWD/config:/app/config:ro" \
  -v "$PWD/local:/app/local:ro" \
  -v "$PWD/.media-agent:/app/.media-agent" \
  ghcr.io/team-cyan/media-agent:latest \
  healthcheck --config /app/config/example.yaml
```

Operators can provide their own Compose, Unraid, Kubernetes, or systemd wrapper
outside this repository.

## Import Behavior

`import-run-once` scans enabled profile source folders for common video files,
builds Plex/Jellyfin-friendly target paths, and records every planned action.

Movies:

```text
Arrival.2016.1080p.BluRay.mkv
-> Movies/Arrival (2016)/Arrival (2016).mkv
```

Episodes:

```text
Breaking.Bad.S01E01.Pilot.mkv
-> TV/Breaking Bad/Season 01/Breaking Bad - S01E01 - Pilot.mkv
```

State and audit files:

```text
.media-agent/state.db
.media-agent/audit.jsonl
```

Dry-run is the default. `--execute` creates links and still records audit rows.
Existing target files are not overwritten.

## Example Config

Start from:

```bash
cp config/example.yaml config/config.yaml
```

Keep TMDB credentials in:

```text
local/secrets/tmdb.api-key
local/secrets/tmdb.bearer-token
```

The checked-in config stores only the secret file reference.

## Target Naming Direction

Movies:

```text
Movies/
  Collection Name/
    Movie Title (2024)/
      Movie Title (2024).mkv
```

Shows and anime:

```text
TV/
  Show Title/
    Season 01/
      Show Title - S01E01 - Episode Title.mkv
```

Collection folders are enabled for movie collections. Series folders are always used for TV/anime.

## Safety Defaults

- Dry-run first.
- Never delete source files.
- Do not overwrite target files.
- Do not silently pick low-confidence metadata matches.
- Put uncertain matches in a review queue.
- Prefer hardlink. Allow symlink fallback only when configured.
- Record every planned and executed action in local state/audit.

## Documentation

- [Project Overview](docs/ai/project-overview.md)
- [Roadmap](docs/roadmap.md)
- [Product Boundary Spec](docs/specs/2026-06-09-media-agent-product-boundary.md)
- [Docker Image Runtime](docs/operations/docker-image-runtime.md)
- [Docker Image Publishing](docs/operations/docker-image-publishing.md)
- [Unraid DockerMan Install](docs/operations/unraid-dockerman.md)
- [Session Handoff](docs/operations/session-handoff.md)
