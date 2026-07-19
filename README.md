# pmwhale

[![CI](https://github.com/smadrom/pmwhale/actions/workflows/ci.yml/badge.svg)](https://github.com/smadrom/pmwhale/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](pyproject.toml)

Research tools for testing hypotheses about copying large public Polymarket
wallets. The project collects public API data into SQLite, produces an
exploratory wallet ranking, and includes a local dashboard.

[Русская версия](docs/README.ru.md)

> [!WARNING]
> `pmwhale` is an early research preview, not a trading system. The current
> ranking is an approximation from trade cash flows. The backtest does not yet
> model delayed entry or authoritative settlement and refuses to run by default.
> Do not use its placeholder output for financial decisions.

## Status

| Component | Status | Evidence boundary |
| --- | --- | --- |
| Public API client | Working | Unit-tested request and retry behavior |
| SQLite collector | Working | Offline tests; live APIs are excluded from CI |
| Wallet ranking | Exploratory | Open positions are not marked to market |
| Dashboard | Working | Type-checked and production-built in CI |
| Copy backtest | Not valid yet | Latency and settlement are absent |

All network access is read-only and unauthenticated. No database or collected
wallet dataset is shipped in the repository.

## Quick start

The recommended development setup uses [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/smadrom/pmwhale.git
cd pmwhale
uv sync --extra dev
uv run pmwhale-collect --help
```

Plain `pip` also works:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
```

Python 3.11 or newer is required.

## Usage

Collect candidate wallets and public trades into `pmwhale.db`:

```bash
uv run pmwhale-collect \
  --markets 40 \
  --holders 20 \
  --min-amount 100 \
  --max-trades 10000
```

Create an exploratory ranking:

```bash
uv run pmwhale-rank --db pmwhale.db --min-positions 20 --limit 25
```

Legacy root scripts (`python collect.py`, `python rank.py`, and
`python backtest.py`) remain as compatibility entry points.

The backtest command intentionally fails closed. Its development-only
`--allow-placeholder-model` flag acknowledges that results are invalid and are
emitted with `model_valid: false` and `latency_applied: false`.

## Dashboard

The dashboard requires [Bun 1.3.14](https://bun.sh/) and an existing database.

```bash
cd ui
bun install --frozen-lockfile
bun run build

# Terminal 1: API and built UI on http://127.0.0.1:5178
DB_PATH=../pmwhale.db bun run start

# Terminal 2, optional Vite development server
bun run dev
```

On PowerShell, set the database path with
`$env:DB_PATH = "../pmwhale.db"` before `bun run start`.

Docker Compose binds the service to localhost and mounts the database read-only:

```bash
cd ui
docker compose up --build
```

Set `PMWHALE_DB` when the database is not at `../pmwhale.db`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/pmwhale/client.py` | Public Gamma, Data, and CLOB API client |
| `src/pmwhale/collect.py` | Candidate discovery and SQLite collection |
| `src/pmwhale/rank.py` | Exploratory cash-flow ranking |
| `src/pmwhale/backtest.py` | Fail-closed placeholder model |
| `ui/` | Bun API server and React dashboard |
| `tests/` | Offline Python tests |
| `docs/ENDPOINTS.md` | Observed public endpoint notes |
| `docs/RELEASE.md` | Maintainer release runbook and readiness record |

## Known research gaps

Before the project can claim a valid copy-strategy backtest, it needs:

1. authoritative market settlement from closed positions or on-chain resolution;
2. delayed entry prices from timestamped CLOB data;
3. order-book depth rather than constant slippage;
4. strictly time-split wallet selection to remove look-ahead bias;
5. position-based realized P&L for ranking and an out-of-sample evaluation.

Contributions that close these gaps need fixtures, tests, and a clear statement
of what was verified. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Responsible use

Prediction-market access and data use may be restricted by your jurisdiction or
by third-party terms. You are responsible for checking the rules that apply to
you. Public wallet addresses can still be sensitive when combined with other
data; do not commit collected databases, deanonymize users, or publish personal
profiles.

This software is provided for research and education, without warranty. It is
not financial, legal, tax, or investment advice, and it is not affiliated with
or endorsed by Polymarket.

## Community and security

- Bugs and proposals: [GitHub Issues](https://github.com/smadrom/pmwhale/issues)
- Usage questions: [SUPPORT.md](SUPPORT.md)
- Vulnerability reports: [SECURITY.md](SECURITY.md)
- Community expectations: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE) © 2026 pmwhale contributors.

License texts for third-party packages bundled into the dashboard are preserved
in [`ui/THIRD_PARTY_LICENSES.txt`](ui/THIRD_PARTY_LICENSES.txt).
