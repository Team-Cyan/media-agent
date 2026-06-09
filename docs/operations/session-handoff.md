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
- Python package bootstrap,
- `media-agent config-check`,
- `media-agent healthcheck`,
- Docker image scaffold and GHCR publishing workflow.

The real import runtime is not implemented yet. `import-run-once`, `import-schedule`,
and `web` are CLI placeholders that validate config and exit with a
not-implemented status.

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
- [ ] Typed config model.
- [ ] TMDB client interface with mocked tests.
- [ ] Source scan model.
- [ ] State and audit initialization.
- [ ] Dry-run import plan generation for movies only.

Then add TV/anime once the path planner and state/audit model are stable.

## Known Risks

- Hardlink behavior depends on filesystem and Docker mount topology.
- Wrong TMDB match can pollute Plex/Jellyfin libraries.
- Anime naming and season offsets are easy to get wrong.
- Symlinks may point to paths the media server cannot resolve if container mount views differ.
- Copy fallback can silently double disk usage and should not be a default v1 behavior.
