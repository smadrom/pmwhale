# Contributing to pmwhale

Thanks for helping make this research reproducible and less misleading.

## Before opening a change

- Use an issue for substantial behavior or data-model changes.
- Never commit API credentials, collected databases, wallet profiles, or other
  personal data.
- Keep claims narrower than the evidence. A mocked API test is not a live API
  verification, and historical fit is not out-of-sample performance.
- Changes to ranking or backtesting must document look-ahead, settlement,
  latency, fee, and slippage assumptions.

## Development setup

```bash
uv sync --extra dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
uv build

cd ui
bun install --frozen-lockfile
bun run check
bun run licenses
bun run licenses:allowlist
```

Python tests must stay offline and deterministic. Put sanitized API examples in
fixtures rather than calling production services from CI.

Commit `ui/THIRD_PARTY_LICENSES.txt` whenever a production UI dependency changes;
CI regenerates it and rejects drift or licenses outside the current permissive
allowlist.

## Pull requests

1. Keep the change focused and add tests for observable behavior.
2. Update the README, endpoint notes, changelog, or release runbook when public
   behavior or evidence boundaries change.
3. Run the commands above and report any skipped check in the pull request.
4. Use clear commit messages; Conventional Commit prefixes such as `fix:`,
   `feat:`, `docs:`, and `test:` are welcome but not required.

By contributing, you agree that your contribution is licensed under the MIT
License and that you will follow the [Code of Conduct](CODE_OF_CONDUCT.md).
