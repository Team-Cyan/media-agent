# Session Handoff

Date: 2026-06-09

## Current State

`media-agent` was created as a new standalone local repo at:

```text
/Users/lancer/projects/media-agent
```

The repo currently contains:

- project documentation and AI routing docs,
- config examples,
- Python package and CLI runtime,
- `media-agent config-check`,
- `media-agent healthcheck`,
- working `media-agent import-run-once`,
- filename-based movie and episode path planning,
- SQLite state and JSONL audit output,
- explicit hardlink/symlink execution with dry-run default,
- Docker image scaffold and GHCR publishing workflow.

`import-schedule` loops over the same import pass. `web` is still a placeholder
that validates config and exits with a not-implemented status.

## Decision Summary

- Project name: `media-agent`.
- First capability: media library import/linking.
- `seed-agent` keeps all previous PT/downloader/search/Wanted List strategy functionality.
- `media-agent` owns the newly discussed completed-media organization flow.
- Metadata source: TMDB first.
- Matching behavior: semi-automatic.
- Review UI should list several TMDB candidates when confidence is not high enough.
- Movies, TV, and anime are all in v1 scope.
- Each type/profile can specify independent source and target folders.
- The workflow runs as a scheduled task, not a download-completion hook.
- Series movies should support collection root folders with movie subfolders.
- Series TV/anime should use show root folders with season subfolders.

## Important Boundary

Do not implement PT selection, tracker search, qB enqueue strategy, or torrent cleanup here.

Those remain in:

```text
/Users/lancer/projects/seed-agent
```

## Recommended Next Session Start

1. Read `AGENTS.md`.
2. Read `docs/ai/project-overview.md`.
3. Read `docs/specs/2026-06-09-media-agent-product-boundary.md`.
4. Check `docs/roadmap.md` for the next implementation slice.

## Suggested First Implementation Slice

Keep the first real import slice narrow:

- [x] Python package bootstrap.
- [x] Basic config validation.
- [x] Typed config model.
- [x] Source scan model.
- [x] State and audit initialization.
- [x] Dry-run import plan generation for movies and TV episodes.
- [x] Explicit hardlink/symlink execution.
- [ ] TMDB client interface with mocked tests.
- [ ] Review queue for ambiguous filename or TMDB matches.
- [ ] Anime fixture coverage.

Next slices should add TMDB-backed matching, review queue behavior, and anime
fixture coverage without widening into downloader automation.

## Known Risks

- Hardlink behavior depends on filesystem and Docker mount topology.
- Wrong TMDB match can pollute Plex/Jellyfin libraries.
- Anime naming and season offsets are easy to get wrong.
- Symlinks may point to paths the media server cannot resolve if container mount views differ.
- Copy fallback can silently double disk usage and should not be a default v1 behavior.
