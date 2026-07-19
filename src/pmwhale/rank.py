"""Rank collected wallets using an explicitly approximate cash-flow metric."""

from __future__ import annotations

import argparse
import math
import sqlite3
from collections import defaultdict
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import TypedDict

DEFAULT_DB = Path("pmwhale.db")


class WalletStats(TypedDict):
    wallet: str
    pnl_usd: float
    n_positions: int
    winrate: float
    volume_usd: float
    n_trades: int
    sharpe_like: float


def wallet_stats(connection: sqlite3.Connection) -> list[WalletStats]:
    """Approximate wallet statistics from trade cash flows.

    Open positions and settlement are not marked to market. These values are for
    candidate exploration only, not a statement of realized performance.
    """
    rows = connection.execute(
        "SELECT wallet, asset, side, usd FROM trades ORDER BY wallet, asset, timestamp"
    ).fetchall()

    position_cash_flow: dict[tuple[str, str], float] = defaultdict(float)
    volume: dict[str, float] = defaultdict(float)
    trade_count: dict[str, int] = defaultdict(int)

    for wallet, asset, side, usd in rows:
        cash = float(usd or 0)
        key = (str(wallet), str(asset))
        volume[str(wallet)] += cash
        trade_count[str(wallet)] += 1
        position_cash_flow[key] += cash if side == "SELL" else -cash

    returns: dict[str, list[float]] = defaultdict(list)
    for (wallet, _asset), cash_flow in position_cash_flow.items():
        returns[wallet].append(cash_flow)

    output: list[WalletStats] = []
    for wallet, cash_flows in returns.items():
        total = sum(cash_flows)
        wins = sum(value > 0 for value in cash_flows)
        count = len(cash_flows)
        mean = total / count if count else 0.0
        standard_deviation = (
            math.sqrt(sum((value - mean) ** 2 for value in cash_flows) / count)
            if count > 1
            else 0.0
        )
        output.append(
            {
                "wallet": wallet,
                "pnl_usd": round(total, 2),
                "n_positions": count,
                "winrate": round(wins / count, 3) if count else 0.0,
                "volume_usd": round(volume[wallet], 2),
                "n_trades": trade_count[wallet],
                "sharpe_like": round(mean / standard_deviation, 3)
                if standard_deviation > 0
                else 0.0,
            }
        )
    return output


def ranked_wallets(
    connection: sqlite3.Connection,
    min_positions: int = 20,
) -> list[WalletStats]:
    ranked = [row for row in wallet_stats(connection) if row["n_positions"] >= min_positions]
    ranked.sort(key=lambda row: (row["sharpe_like"], row["winrate"]), reverse=True)
    return ranked


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite input path")
    parser.add_argument("--min-positions", type=int, default=20)
    parser.add_argument("--limit", type=int, default=25)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.min_positions <= 0 or args.limit <= 0:
        parser.error("--min-positions and --limit must be positive")
    if not args.db.is_file():
        parser.error(f"database does not exist: {args.db}")

    with closing(sqlite3.connect(args.db)) as connection:
        ranked = ranked_wallets(connection, args.min_positions)

    print("WARNING: approximate cash-flow ranking; open positions are not marked to market.")
    print(f"{'wallet':44} {'cash$':>10} {'win':>5} {'pos':>5} {'score':>7}")
    for row in ranked[: args.limit]:
        print(
            f"{row['wallet']:44} {row['pnl_usd']:>10.0f} {row['winrate']:>5.2f} "
            f"{row['n_positions']:>5} {row['sharpe_like']:>7.2f}"
        )


if __name__ == "__main__":
    main()
