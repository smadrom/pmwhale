# Pull request

## Summary

Describe the problem and the smallest useful solution.

## Evidence boundary

- What is verified?
- What remains assumed, mocked, skipped, or dependent on a live third party?
- For ranking/backtesting changes: how are settlement, latency, slippage, fees,
  look-ahead, and open positions handled?

## Verification

- [ ] `uv run ruff format --check .`
- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv build && uv run twine check dist/*`
- [ ] `cd ui && bun install --frozen-lockfile && bun run check`
- [ ] Documentation and `CHANGELOG.md` updated when behavior changed
- [ ] No secrets, databases, private data, or deanonymization claims added
