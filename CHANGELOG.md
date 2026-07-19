# Changelog

All notable changes to this project will be documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-19

### Added

- Installable `pmwhale` Python package and command-line entry points.
- Offline unit tests, linting, package builds, and UI checks in CI.
- Reproducible Python and Bun lockfiles.
- MIT license, contribution guide, code of conduct, security policy, support
  guide, issue forms, pull request template, and release runbook.
- Reproducible third-party UI license notices and a repository social-preview
  asset.

### Changed

- Collector now requests the verified `volumeNum` market order.
- Collector enforces current Data API limits for holders and trade pagination;
  the API client includes the live `/v1/leaderboard` endpoint.
- Trade insertion reports only newly stored rows and skips malformed records.
- UI server validates paths and query parameters, limits error disclosure, adds
  browser security headers, and runs as a non-root read-only container.
- Research limitations are prominent in the README and command output.
- Dependabot uses the native `uv` and `bun` package ecosystems.

### Security

- Placeholder backtest now fails closed unless the user explicitly acknowledges
  that latency and authoritative settlement are missing.
- Repository history was checked for common credential patterns before release.

[Unreleased]: https://github.com/smadrom/pmwhale/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/smadrom/pmwhale/releases/tag/v0.1.0
