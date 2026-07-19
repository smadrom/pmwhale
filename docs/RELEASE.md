# Release runbook

## Current status

`v0.1.0` was published on 2026-07-19 as a public, immutable GitHub release:
<https://github.com/smadrom/pmwhale/releases/tag/v0.1.0>. The annotated tag
resolves to commit `4f1dce7`.

## Completed

- Public code and Git history audited for common secret patterns.
- Maintainer confirmed `sn.one.dev@gmail.com` as an intentional public author
  and security-contact address on 2026-07-19.
- MIT license and GitHub community health files added.
- Python package, offline tests, lockfile workflow, and CI added.
- UI build made reproducible and its server/container hardened.
- Misleading latency/settlement claims removed; placeholder model fails closed.
- A 1280×640 social-preview image under GitHub's 1 MB limit is prepared at
  `.github/social-preview.jpg`.
- The GitHub repository is public with the release description and project
  topics applied.
- Dependabot vulnerability alerts and security updates, secret scanning with
  push protection, private vulnerability reporting, and immutable releases are
  enabled.
- `main` requires an up-to-date branch, pull-request flow, resolved
  conversations, linear history, and all CI and CodeQL contexts. Force pushes
  and branch deletion are disabled.
- GitHub Actions requires full commit-SHA pinning for actions.
- The verified wheel, source distribution, and checksum manifest were published
  in the immutable `v0.1.0` release.

## Verification

CI must repeat these commands on the tagged commit:

```bash
uv sync --extra dev --locked
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build
uv run twine check dist/*
uv run pip-audit

cd ui
bun install --frozen-lockfile
bun run check
bun run licenses
git diff --exit-code -- THIRD_PARTY_LICENSES.txt
bun run licenses:allowlist
bun audit
```

Local release-candidate results on 2026-07-19:

- `uv lock --check` — PASS.
- `ruff format --check` and `ruff check` — PASS on 14 Python files.
- `pytest` — PASS, 11 tests on Python 3.11.15, 3.12.10, 3.13.13, and 3.14.5;
  measured coverage was 70% on each interpreter. CI covers the same supported
  version matrix.
- `uv build` and `twine check dist/*` — PASS for the wheel and source archive.
- The source archive contains the license, community files, documentation,
  compatibility wrappers, tests, and package sources — PASS.
- Fresh execution of `pmwhale-collect --help` from the built wheel — PASS.
- `pip-audit` — PASS for known dependency vulnerabilities; the unpublished
  local `pmwhale` package itself was skipped because it is not on PyPI.
- `bun install --frozen-lockfile`, TypeScript check, and Vite production build —
  PASS. Vite reports a non-blocking bundle-size warning for the roughly 1 MB JS
  chunk.
- `bun audit` — PASS, no known vulnerabilities.
- Local UI runtime — PASS for root, health, and stats; malformed query returned
  400; traversal and missing asset returned 404; security header was present.
- Live public API smoke test — PASS for markets, holders, trades, positions,
  closed positions, activity, trader leaderboard, and CLOB price history. The
  client enforces the documented holders limit of 20 and trades cap of 10,000.
  Wallet values were not logged and responses were not persisted.
- GitHub workflow and Dependabot schema validation — PASS; `zizmor` reported no
  findings; Markdown lint and local Markdown links passed.
- Compose schema validation, Hadolint 2.14.0 with its official SHA-256 verified,
  and pinned multi-architecture Bun image digests — PASS.
- `git fsck --full --strict` — PASS; common credential-pattern scan across Git
  history found no matches.
- Gitleaks 8.30.1 (official release checksum verified) — PASS for all four Git
  commits and the 58-file candidate release tree; the temporary scanner and
  copied audit tree were removed afterward.
- Dependency license inventory — PASS for runtime compatibility: Python runtime
  dependencies are BSD/MIT-family; UI production dependencies are MIT, ISC,
  BSD, Apache-2.0, or 0BSD. Exact UI dependency notices are generated into
  `ui/THIRD_PARTY_LICENSES.txt`, checked for drift in CI, and copied into the
  container. The local private UI package declares MIT.
- The `pmwhale` project name returned 404 from both PyPI and TestPyPI on
  2026-07-19, so it appeared unclaimed at the time of this check. Availability
  is not reserved until a package is uploaded.
- GitHub-hosted CI run
  [29677166322](https://github.com/smadrom/pmwhale/actions/runs/29677166322)
  — PASS on commit `aeb4020` for Python 3.11–3.14, package build, UI, and the
  Docker image build plus container health/stats smoke test.
- CodeQL run
  [29677314348](https://github.com/smadrom/pmwhale/actions/runs/29677314348)
  — PASS on commit `aeb4020` for Python and JavaScript/TypeScript.
- GitHub code-scanning, secret-scanning, and Dependabot alert queues — PASS,
  zero open alerts after the successful CodeQL run.
- Docker remains unavailable locally, but the required GitHub-hosted Docker job
  built the actual image and passed its container smoke test.
- Final GitHub-hosted CI run
  [29677735942](https://github.com/smadrom/pmwhale/actions/runs/29677735942)
  — PASS on tagged commit `4f1dce7`, including the Docker image smoke test.
- Final CodeQL run
  [29677735951](https://github.com/smadrom/pmwhale/actions/runs/29677735951)
  — PASS on tagged commit `4f1dce7` for Python and JavaScript/TypeScript.
- Release workflow run
  [29677801011](https://github.com/smadrom/pmwhale/actions/runs/29677801011)
  — PASS; validated the annotated tag and version, repeated Python checks,
  built both distributions, generated `SHA256SUMS`, and created the draft.
- The downloaded draft assets matched `SHA256SUMS`; the wheel digest is
  `40996f355bb951258ac6a588e3971659de8cbcb558e24df69d099876c79b5a5e`
  and the source archive digest is
  `201645ce1c95f11185f0797f32df673b190f94359f0a22d12e4bec7c1d441c3a`.
  Fresh execution of `pmwhale-collect --help` from that wheel — PASS.
- The public release page identifies `v0.1.0` as latest and immutable; GitHub's
  release API reports `draft=false` and `immutable=true`.

## Open gates

None for `v0.1.0`.

The prepared social preview still needs a manual upload in GitHub Settings; no
supported API is available for that UI-only operation. This does not affect the
source, security posture, build artifacts, or release verification.

## Release procedure

1. Confirm a clean tree and passing checks from the `Verification` section.
2. Move the `Unreleased` changelog entries to `0.1.0 - YYYY-MM-DD` and update the
   comparison links.
3. Confirm `pyproject.toml`, `src/pmwhale/__init__.py`, `ui/package.json`, and
   `CITATION.cff` all contain `0.1.0`.
4. Merge through the protected `main` branch.
5. Create an annotated tag: `git tag -a v0.1.0 -m "pmwhale v0.1.0"`. A signed
   tag may be used after configuring a supported signing key.
6. Push the tag and create a draft GitHub release from it. Attach the verified
   wheel and source distribution from CI.
7. Review generated notes and publish the draft. If enabled, immutable releases
   will lock the tag and assets after publication.
8. Verify installation from the release artifact in a fresh environment, then
   update the `Current status` section.

## Risks

- Public endpoints and response shapes are third-party contracts and can change.
- Ranking output is exploratory and includes open-position cash flows.
- No valid delayed-entry/settlement backtest exists in `v0.1.0`.
- Collected wallet data is public but can become sensitive when enriched.

## Next steps

Upload the prepared social preview through GitHub Settings when a signed-in
browser is available. Continue dependency maintenance, security-alert review,
and review of third-party API terms and jurisdictional wording as ongoing
maintenance responsibilities.
