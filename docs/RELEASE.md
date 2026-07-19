# Release runbook

## Current status

Target: `v0.1.0` public research preview. The repository is release-candidate
ready only after every open gate below is closed or explicitly accepted by the
maintainer.

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
- GitHub repository audit — repository is private, has no topics, has an outdated
  description, vulnerability alerts are disabled, private vulnerability
  reporting is unavailable, immutable releases are disabled, and protection
  rules cannot be configured on the current private/free setup. Actions are
  enabled with read-only default workflow permissions; current workflow actions
  are pinned to full commit SHAs.
- Docker image build — SKIPPED locally because Docker is unavailable. The CI
  candidate includes a GitHub-hosted job that builds the image, starts it with a
  read-only smoke database, and checks the health and stats endpoints; this gate
  remains open until that job passes remotely.

## Open gates

- Enable GitHub private vulnerability reporting, secret scanning, push
  protection, Dependabot alerts/security updates, and immutable releases.
- Configure branch protection for `main` with the Python and UI CI jobs required.
- Replace the outdated GitHub description, add topics, upload the prepared
  social preview, and change repository visibility to public.
- Obtain green GitHub-hosted CI and CodeQL results on the final commit.
- Obtain a passing GitHub-hosted Docker image build and health check.
- Review third-party API terms and jurisdictional wording for the intended
  audience.

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

Close the repository-setting gates, obtain green CI on the final commit, and
publish `v0.1.0` as a clearly labeled research preview.
