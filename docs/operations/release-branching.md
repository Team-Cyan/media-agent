# Release Branching

`main` is the active development branch.

For each medium version line, create an archival branch named:

```text
release/<major>.<minor>
```

Examples:

- `0.1.0` uses `release/0.1`.
- `0.2.0` uses `release/0.2`.
- `1.0.0` uses `release/1.0`.

Release branches are for historical checkpoints and hotfix reference. Normal
work continues on `main`.

## Current Rule

When a medium version is ready to preserve:

```bash
git branch release/<major>.<minor> main
git push origin main release/<major>.<minor>
```

Do not switch long-running work onto release branches unless a specific hotfix
requires it.
