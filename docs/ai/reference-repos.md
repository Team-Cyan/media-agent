# Reference Repositories

These projects are references, not implementation templates.

Borrow product boundaries, naming ideas, and operational expectations. Do not copy broad platform scope.

## NAS Media Automation

### MoviePilot

- Source: https://github.com/jxxghp/MoviePilot
- Refer to for:
  - end-to-end NAS workflow coverage,
  - subscription/download/organization separation,
  - Web UI review expectations,
  - media library refresh concepts.
- Do not copy:
  - broad dashboard scope,
  - large plugin system,
  - downloader strategy features that belong in `seed-agent`.

### nas-tools

- Source: https://github.com/NAStool/nas-tools
- Refer to for:
  - NAS user expectations around media organization,
  - source-to-target transfer workflows,
  - naming and library import boundaries.
- Do not copy:
  - all-in-one product shape.

### vertex

- Source: https://github.com/vertex-app/vertex
- Refer to for:
  - PT/NAS product surface ideas,
  - operator ergonomics.
- Do not copy:
  - tracker automation scope into media-agent.

## Anime-Oriented References

### Auto_Bangumi

- Source: https://github.com/EstrellaXD/Auto_Bangumi
- Refer to for:
  - anime season/episode tracking,
  - media-library-friendly organization,
  - source health/status ideas,
  - episode offset handling.
- Do not copy:
  - anime-only assumptions as global rules.

### ani-rss

- Source: https://github.com/wushuo894/ani-rss
- Refer to for:
  - light subscription workflows,
  - Docker-first deployment,
  - clear documentation for non-programmer operators.
- Do not copy:
  - feed acquisition into v1 media-agent unless a later spec explicitly adds it.

### bgmi

- Source: https://github.com/BGmi/BGmi
- Refer to for:
  - episode-oriented content tracking,
  - naming conventions,
  - simple operator flows.

## Design Lessons

- Discovery, download, matching, and organization are separate phases.
- `media-agent` should begin at the organization phase.
- Matching must be conservative and auditable.
- Web UI review is appropriate when multiple metadata candidates are plausible.
- Good Docker volume docs matter because source and target path mapping is the product.
