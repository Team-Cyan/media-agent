# CI Failure Investigation

Date: 2026-11-15. Initial window: 30 days, then expanded to every retained run
returned by GitHub Actions (392 at inventory). Fifteen failures were identified;
376 successes and one then-running run do not explain those failures.
Run attempt 1 is the retained failed attempt for the entries below. Raw logs and
annotations are retained only in ignored local evidence.

## Confirmed Causes And Fixes

| Run / source | First failing step and evidence | Root cause and correction | Current verification |
| --- | --- | --- | --- |
| [43439028684](https://github.com/Team-Cyan/seed-agent/actions/runs/43439028684), `da91090`, main push, 2026-11-13 | Test: `test_manual_or_modified_poster_is_preserved`, `NotADirectoryError` | Test selected the first directory entry, which can be the volume-marker file. `06412d0` restricts selection to directories; preserves the manual-poster assertion. | Artwork tests and full 1.0 CI pass. |
| [42013711991](https://github.com/Team-Cyan/seed-agent/actions/runs/42013711991), `fbc70f2`, manual archival-branch CI, 2026-11-05 | Test: workflow metadata assertion expected the old literal Docker build command | Revision-bound image verification changed the command; its test lagged. `c795c6a` checks the new revision argument and descriptor-hardlink gate. | Metadata tests and full 1.0 CI pass. |
| [32699648060](https://github.com/Team-Cyan/seed-agent/actions/runs/32699648060), `f296081`, main push, 2026-08-24 | Docker smoke healthcheck: state DB missing | Healthcheck correctly required existing state; the disposable CI fixture had never initialized it. `7b41bcf` adds a fixture initialization container and shared state mount. | Current isolated image initialization and healthcheck pass. |
| [32741419645](https://github.com/Team-Cyan/seed-agent/actions/runs/32741419645), `37756b1`, main push, 2026-08-24 | Docker smoke healthcheck: same missing-state error | A later source revision still had the missing fixture; same correction as above. | Same current smoke path passes. |
| [32785875758](https://github.com/Team-Cyan/seed-agent/actions/runs/32785875758), `7b41bcf`, main push, 2026-08-24 | Fixture initialization: `AttributeError`, string has no `parent` | Initial fixture correction passed a string into the Path-based StateStore API. `7f9eaf7` constructs `Path` explicitly. | Current workflow checks fixture Path construction and runs it in Linux. |

These are actual test/fixture defects, not inferred network flakiness. The two
August missing-fixture runs are repeated failures of the same unresolved path;
the following attempted fix introduced the distinct constructor-type failure.
All corrections predate 1.0 and were retained rather than reimplemented. Focused
artwork/metadata verification during this investigation: 39 passed. The release
also adds a separate demonstrated SQLite-lock safety fix, read-only metrics and
Unicode RSS regressions; those are review findings, not proven historic CI causes.

## Older Failures With Incomplete Evidence

The following logs are no longer downloadable. Check-run annotations were read
for each: the CI cases retain only exit-code-1 errors plus Node action deprecation
warnings. Those warnings are not proof of the failure cause. Several run job lists
have also expired. Source history alone cannot establish the original failing step.

| Run | SHA / date | Retained evidence and disposition |
| --- | --- | --- |
| [29022987035](https://github.com/Team-Cyan/seed-agent/actions/runs/29022987035) | `4e2b915`, 2026-07-09 | CI failure; step unavailable; root cause unconfirmed. |
| [28799485939](https://github.com/Team-Cyan/seed-agent/actions/runs/28799485939) | `5ca6c0e`, 2026-07-06 | Test step failed; assertion output expired; root cause unconfirmed. |
| [28710545862](https://github.com/Team-Cyan/seed-agent/actions/runs/28710545862) | `a0579e2`, 2026-07-04 | Pages deployment; annotation says deployment failed/try later. Service-side or packaging cause cannot be distinguished. Current Pages deployment passes. |
| [26017075465](https://github.com/Team-Cyan/seed-agent/actions/runs/26017075465) | `401b362`, 2026-05-18 | CI exit 1; root cause unconfirmed. |
| [26004449784](https://github.com/Team-Cyan/seed-agent/actions/runs/26004449784) | `40dc374`, 2026-05-17 | CI exit 1; root cause unconfirmed. |
| [25982630694](https://github.com/Team-Cyan/seed-agent/actions/runs/25982630694) | `001e9b0`, 2026-05-17 | CI exit 1; root cause unconfirmed. |
| [25978459288](https://github.com/Team-Cyan/seed-agent/actions/runs/25978459288) | `f71fcdd`, 2026-05-17 | CI exit 1; root cause unconfirmed. |
| [25978402070](https://github.com/Team-Cyan/seed-agent/actions/runs/25978402070) | `b114a3b`, 2026-05-17 | CI exit 1; root cause unconfirmed. |
| [25920300820](https://github.com/Team-Cyan/seed-agent/actions/runs/25920300820) | `6700667`, 2026-05-15 | CI exit 1; root cause unconfirmed. |
| [25919182950](https://github.com/Team-Cyan/seed-agent/actions/runs/25919182950) | `c7deb8e`, 2026-05-15 | CI exit 1; root cause unconfirmed. |

No old workflow was rerun against changed dependencies and presented as its
original cause. No notification setting was changed. Current pinned action
versions address the deprecation warning independently of these unknown errors.
If separately retained failure excerpts exist, they can narrow the older cases;
there is no evidence-backed code fix to invent from the remaining annotations.

## Release Checks

The tested release source is `7c815caf5121e7dffd0b163037f869b234996f9c`.
[CI 43667564751](https://github.com/Team-Cyan/seed-agent/actions/runs/43667564751)
passed all test/lint/audit/Compose/image/hardlink/health gates.
[Pages 43667564496](https://github.com/Team-Cyan/seed-agent/actions/runs/43667564496)
and [main publication 43667833963](https://github.com/Team-Cyan/seed-agent/actions/runs/43667833963)
passed. The immutable annotated `v1.0.0` tag and `release/1.0` branch point to that
source. [GitHub Release 43667928443](https://github.com/Team-Cyan/seed-agent/actions/runs/43667928443)
created the non-draft, non-prerelease release. [Tag publication 43667928478](https://github.com/Team-Cyan/seed-agent/actions/runs/43667928478)
passed. Registry tags `v1.0.0`, `1.0.0` and `1.0` resolve to index
`sha256:ab58eb3170dd7462cabbd6ca00976dd46bdcbac1b45afc0c60425fb7fba87df7`.
Both linux/amd64 and linux/arm64 configs report version 1.0.0 and the tested
revision above. Platform manifests:

- amd64: `sha256:a5cbbc7e954aae1cd662b656bb7cb0099615b4cae36eb2e50823706aa942eb86`
- arm64: `sha256:dc1413b51bccf8b94ca874c129ec4b6d7f284b3b53ed127e37f3b62c6783d84e`

This milestone needed no post-tag behavior fix or tag rewrite. A subsequent
documentation-only main commit records these receipts; the release tag remains
at the tested source. Production was not upgraded.

Published platform images were also pulled by immutable manifest and both passed
hardlink/health smoke checks. Final image-layer/privacy evidence is recorded in the
[release review](2026-11-15-v1-release-review.md#published-image-readback).
