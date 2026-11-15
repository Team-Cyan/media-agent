# 1.0 Release Review

Review date: 2026-11-15. Baseline: `ff8c9e2`. Scope: first stable milestone;
publication receipts are the immutable tag, GitHub Release and exact-revision Actions
runs. This report records bounded review evidence, not an absence-of-bugs guarantee.

## Preservation And Disposition

A separate clean worktree was created from refreshed main. All 27 dirty/untracked
items in the original checkout were inventoried and retained. Four matched main
exactly (CI descriptor/revision checks, filesystem fencing, metadata tests and review
projection); the older engine/worker/tests were superseded by later integrated
source/extras/variant work. The local diagnostic remains private. The remaining
harness, templates, roadmap and old planning proposals are deferred for separate
review; relevant product documentation was refreshed from current code instead of
copying the old branch. No reset, stash, broad staging or production writer ran.
No open PR existed; all seven historical PRs were closed and merged. The source
handoff chat was idle at inventory; the fresh execution chat owns release writes.

## Coverage Matrix

The baseline contains 305 tracked paths. A per-path bucket inventory is retained
locally; all buckets below were included through contracts, implementation and
associated tests/configuration/build review. Tests and historic design documents
are supporting evidence, not independent live acceptance.

| Subsystem | Review focus and evidence | Disposition |
| --- | --- | --- |
| Config, secret refs, models | Strict YAML models, runtime secret resolution, config revisions, portable examples | Reviewed; private fixture account label anonymized |
| Discovery, RSS, M-Team, Torznab | Error/empty distinction, API-key boundaries, deferred tokens, XML parsing, search constraints | Unicode RSS filtering fixed; RSS preserved |
| Scoring, tracker strategy | Free-only farming gates, paid Want distinction, refreshed evidence, expiry/backoff | Existing regression coverage; no new blocker found |
| Downloaders, budgets, cleanup | Category authority, add-only pools, cap gates, latest-state revalidation, delete verification | Existing contracts/regressions; no live mutation |
| Intents and sources | Aliases, terminal/selected protection, atomic search snapshots, claims/renewal, allowlists/cursors | Static review plus automated tests |
| Scheduler | Execute gates, heartbeat, lease renewal, phase ownership and backoff | Automated phase/state evidence; broader fake-provider coverage deferred |
| State, audit, metrics, observability | Native locks, privacy modes, read-only readers, redaction, rotation, backup/restore | SQLite and metrics fixes below |
| CLI, API, auth, Web assets | Optional token, Origin/JSON limits, static paths, revision CAS, operator actions | Trusted-operator boundary retained |
| Media identity, completion, extras, variants | Independent facts, selected-source preservation, source/config/epoch baseline, parent receipts | Reviewed with fixtures; no corpus writers replayed |
| Filesystem, worker, recovery/migration | Descriptor hardlinks, no-follow paths, single writer, lost responses, conservative conflicts | Linux container fence check; existing race/crash tests |
| Subtitles, metadata, artwork | Payload bounds, provider origins/quotas, staged local SRT hashes, shared publisher | Best effort; corpus/client limitations retained |
| Docker, Compose, Unraid, native SQLite shim | Build allowlist, identity drop, role health, templates, revision labels | Compose and local Linux image smoke; no NAS upgrade |
| Tests, dependencies, scripts | Full suite, Ruff, frozen lock, dependency audit, public checker | Required local checks passed |
| Workflows and release automation | Pinned actions, permissions, tested-main publication, tag metadata/notes, concurrency | Exact-head CI/publication verified separately; historical triage below |
| Docs, examples, assets, license, agent routing | Current support matrix, portable install/upgrade, stale handoff, MIT and bundled icon | Refreshed current entrypoints; older specs/plans remain historical |

Independent read-only review covered safety-sensitive paths and the integrated fix
diff. The main owner reviewed evidence, implemented fixes and ran integration checks.

## Findings And Validation

| Severity | Finding | Fix and evidence |
| --- | --- | --- |
| High | Permission helpers opened/closed existing SQLite DB/SHM descriptors, releasing other same-process connections' POSIX locks | Existing regular files use no-follow chmod without opening; first creation closes under exclusive access fence. Isolated subprocess reproduction shows baseline loses writer exclusion in DELETE/WAL and fixed code retains both. Regression and symlink tests added. |
| Medium | Metrics GET constructed a writable, initializing StateStore | Read-only URI/query-only store, no schema initialization; regression asserts no DDL/DML. |
| Medium | ASCII-only RSS tokens rejected exact non-Latin titles | Unicode whole-token matching; regression rejects title/year/season/episode drift in three scripts. |
| Medium | Current public docs/fixtures retained personal deployment/corpus descriptions | Current account label and corpus specifics removed; public docs now retain only generic bounded evidence. Historical copies remain; no history rewrite was authorized or performed. |
| Low | README and handoff described obsolete product phases and mixed local/deployed acceptance | Current support matrix, upgrade guide and versioned roadmap replace stale entrypoint claims. |

Local checks: 1,417 passed, one platform-specific skip; Ruff, frozen dependency audit
and public repository hygiene passed. Compose resolves. The Linux arm64 candidate
image reports version 1.0.0, passes descriptor-hardlink source-replacement fencing
under UID/GID 1000:100, and passes example-config healthcheck. A native-lock probe
also verifies external writers remain blocked before/after an independent store
connection. The full suite uses fixtures rather than production providers/downloaders.

## Privacy And Distribution Audit

- Gitleaks 8.30.1 scanned 249 reachable commits (including local refs, a superset
  of fetched public refs). A location-only scanner inspected 2,818 historical
  blobs for private paths/identities/corpus details and credential signatures.
- Secret candidates were audited as test redaction data or a static client
  protocol-signing constant, distinct from account API keys/cookies. No account
  credential exposure was confirmed. This is classification evidence, not proof
  of credential inactivity or exhaustive absence of secrets.
- Historical personal labels, home paths and corpus summaries remain reachable.
  New distributable content is sanitized; no remote rewrite, credential rotation,
  artifact deletion or evidence destruction was performed.
- Public issue/PR/review/comment/release authored text was scanned. Expected public
  account/actor metadata is distinct from private operational configuration.
- All 62 completed runs and 24 accessible artifacts in the initial 30-day window
  were downloaded. Logs and build-record strings were scanned; candidates were
  fixture/protocol material. Build records include ephemeral CI network endpoints
  and old public source/fixture labels. Binary/protobuf strings are a bounded view,
  not a decoder proving every nested field safe. Earlier/expired surfaces are a gap.
- Only empty local markers are tracked; runtime config/state/secrets are excluded
  from Docker context. Dockerfile uses explicit COPY inputs rather than copying
  the checkout. Candidate image history, metadata and saved layers are checked
  separately: 18 saved layers, 42,867 entries and 23,076 text files were checked.
  Two home-path matches were third-party documentation/metadata examples, not
  operator runtime values; no runtime config/state path was included. Binary
  semantics and third-party package behavior are not a complete supply-chain attestation.

Raw results, locations and receipts stay ignored/local. Historical privacy cleanup
can be proposed separately; existing public history is not silently rewritten.

## Remaining Limits And Future Work

No supported-path critical/high finding remains after these fixes and verification.
Real-provider behavior and client playback were not exercised by this release
review. Full-library subtitle delivery, archive/retiming support, metadata corpus
recall and broad fake-provider scheduling acceptance remain bounded future work.
See the roadmap for candidate 1.1/1.2 and potential compatibility-breaking 2.0 work.
Production remains on the separately recorded prior release until an explicitly
reviewed deployment; this release does not switch sources or mutate the library.

## Publication And Historical CI Receipts

The release source is `7c815caf5121e7dffd0b163037f869b234996f9c`.
[CI](https://github.com/Team-Cyan/seed-agent/actions/runs/43667564751),
[main image publication](https://github.com/Team-Cyan/seed-agent/actions/runs/43667833963),
[tag publication](https://github.com/Team-Cyan/seed-agent/actions/runs/43667928478) and
[GitHub Release](https://github.com/Team-Cyan/seed-agent/releases/tag/v1.0.0)
all succeeded. The immutable annotated tag and archival `release/1.0` branch
resolve to that source. Both linux/amd64 and linux/arm64 configs report the exact
revision and version 1.0.0. Registry `1.0.0`, `v1.0.0` and `1.0` share index
`sha256:ab58eb3170dd7462cabbd6ca00976dd46bdcbac1b45afc0c60425fb7fba87df7`.

[Historical CI investigation](2026-11-15-ci-failure-investigation.md) inventories
all 15 retained failures, confirms five causes/fixes from logs and reports ten
older evidence gaps explicitly. An expanded final scan of 71 accessible run-log
directories found no Gitleaks candidates. No failure-mail settings or test/security
checks were disabled. The subsequent report commit is documentation-only;
release tag and source remain immutable. Production was not upgraded.

## Published Image Readback

Both immutable platform manifests were pulled and tested after publication.
Descriptor-hardlink checks under UID/GID 1000:100 and example healthcheck passed
for arm64 and amd64 (the latter executed through local platform emulation, with
native amd64 also covered by release CI). Saved-layer inspection covered 18 layers
per platform: 42,767 arm64 entries / 23,075 text files and 42,679 amd64 entries /
22,978 text files. The two home-path signatures per image were third-party
Perl/package documentation examples; no application runtime configuration/state
path or high-confidence account token/private-key signature was found. These
bounded signatures do not prove arbitrary binary contents safe.
