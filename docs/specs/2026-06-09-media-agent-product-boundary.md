# Media Agent Product Boundary

Date: 2026-06-09

## Goal

Build `media-agent` as a standalone Docker-first media library import tool.

The project organizes completed media files into Plex/Jellyfin/Emby-friendly library folders using TMDB metadata and hardlink/symlink actions.

## Split From seed-agent

All features built before this split stay in `seed-agent`:

- PT discovery,
- Want List ingestion,
- tracker search,
- M-Team API integration,
- qBittorrent enqueue,
- upload strategy,
- cleanup policy,
- Docker/Unraid surfaces for PT automation.

All media organization features described here belong in `media-agent`:

- source folder scanning,
- TMDB matching,
- movie/TV/anime naming,
- collection and season folder creation,
- hardlink/symlink import,
- media import review queue,
- media import audit.

## V1 Feature Scope

### Media Types

V1 supports:

- movies,
- TV shows,
- anime.

Each media type is configured through profiles. Profiles have independent source and target folders.

### Scheduling

The import workflow is not a downloader-completion hook.

It runs as:

- manual `import-run-once`,
- scheduled `import-schedule`,
- optional Web UI triggered scan.

### Metadata

TMDB is the primary metadata provider.

The TMDB API key must be loaded from a secret reference such as:

```yaml
tmdb:
  api_key_ref: local/secrets/tmdb.api-key
```

Future metadata sources may be added only behind explicit provider interfaces.

### Matching Mode

Matching is semi-automatic.

- High-confidence matches can produce import plans automatically.
- Lower-confidence matches enter review.
- Review should show several candidate TMDB matches in the Web UI.
- User selections should persist so future scans do not ask the same question again.

### Naming

Movies use TMDB movie metadata. When collection folders are enabled and TMDB provides collection data, movies go under a collection root.

Example:

```text
Movies/
  Marvel Cinematic Universe/
    Iron Man (2008)/
      Iron Man (2008).mkv
```

If no collection is available:

```text
Movies/
  Arrival (2016)/
    Arrival (2016).mkv
```

TV and anime use TMDB TV metadata and always use series root plus season subfolder.

Example:

```text
TV/
  Breaking Bad/
    Season 01/
      Breaking Bad - S01E01 - Pilot.mkv
```

Anime follows the same structure by default:

```text
Anime/
  Frieren Beyond Journey's End/
    Season 01/
      Frieren Beyond Journey's End - S01E01 - The Journey's End.mkv
```

### Link Mode

V1 should prefer hardlinks.

Supported planned modes:

- `hardlink`
- `symlink`
- `copy` only if explicitly added later

`hardlink` may allow symlink fallback if configured.

No mode deletes the source file.

### Web UI

The Web UI should be small and operational:

- scan status,
- pending review items,
- TMDB candidate choices,
- import preview,
- executed import history,
- source/target health.

It should not become a large dashboard-first product in v1.

## Safety Requirements

- Dry-run is the default.
- Execution requires explicit operator action.
- Never delete source downloads.
- Never overwrite target files by default.
- Never silently choose a low-confidence metadata match.
- Record planned and executed actions.
- Redact secrets in logs, audit, and Web UI.
- Keep local source/target paths out of committed docs and public examples unless they are generic placeholders.
- Detect path traversal and normalize paths before file operations.
- Treat cross-device hardlink failure as expected, not as a crash.

## State And Audit

Expected local durable files:

- `.media-agent/state.db`
- `.media-agent/audit.jsonl`

State should track:

- scan candidates,
- metadata matches,
- review decisions,
- import plans,
- executed imports,
- source/target conflict status.

Audit should record:

- operation type,
- source path,
- target path,
- media type,
- TMDB id,
- link mode,
- dry-run vs execute,
- result,
- error summary.

## Configuration Shape

The initial config should follow this shape:

```yaml
mode: semi_auto
tmdb:
  api_key_ref: local/secrets/tmdb.api-key
matching:
  auto_plan_min_confidence: 0.85
  review_min_confidence: 0.55
  max_review_choices: 5
profiles:
  - name: movies
    type: movie
    source: /downloads/movies
    target: /media/Movies
    link:
      mode: hardlink
      allow_symlink_fallback: true
    naming:
      collection_folders: true
  - name: tv
    type: tv
    source: /downloads/tv
    target: /media/TV
  - name: anime
    type: anime
    source: /downloads/anime
    target: /media/Anime
```

## Non-Goals

Do not build these in v1:

- PT discovery,
- tracker search,
- download strategy,
- torrent cleanup,
- source file deletion,
- broad plugin system,
- all-in-one MoviePilot clone,
- hidden automatic copy fallback.

## Open Design Questions

- Whether TMDB collection folder names should be raw TMDB names or operator-overridable aliases.
- How to infer season/episode from filenames before TMDB matching.
- Whether subtitle and sidecar files should be linked in v1 or deferred.
- Whether Plex refresh should ship in v1 or after import history is stable.
