"""Run the legacy placeholder model only after explicit acknowledgement."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

DEFAULT_DB = Path("pmwhale.db")
WALLET_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class Params:
    slippage: float = 0.01
    fee: float = 0.0
    stake_usd: float = 100.0
    min_price: float = 0.05
    max_price: float = 0.95
    only_buys: bool = True


class BacktestResult(TypedDict):
    model_valid: bool
    latency_applied: bool
    copied_trades: int
    skipped: int
    total_pnl_usd: float
    avg_pnl_per_trade: float
    winrate: float
    roi_pct: float


def placeholder_exit_price(connection: sqlite3.Connection, asset: str) -> float | None:
    """Return the last observed trade price, which is *not* a settlement price."""
    row = connection.execute(
        "SELECT price FROM trades WHERE asset = ? ORDER BY timestamp DESC LIMIT 1",
        (asset,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def run_placeholder(
    connection: sqlite3.Connection,
    wallets: Sequence[str],
    params: Params,
) -> BacktestResult:
    """Run the old invalid model for development comparisons.

    The result is always marked invalid because entry latency is not modeled and
    the last observed trade is not guaranteed to be a resolved outcome.
    """
    if not wallets:
        trades: list[tuple[int, str, str, float | None, float | None]] = []
    else:
        placeholders = ",".join("?" for _ in wallets)
        trades = connection.execute(
            "SELECT timestamp, asset, side, price, size FROM trades "
            f"WHERE wallet IN ({placeholders}) ORDER BY timestamp",
            [wallet.lower() for wallet in wallets],
        ).fetchall()

    pnl = 0.0
    copied = 0
    wins = 0
    skipped = 0
    for _timestamp, asset, side, price, _size in trades:
        if params.only_buys and side != "BUY":
            continue
        if price is None or not (params.min_price <= price <= params.max_price):
            skipped += 1
            continue

        entry = float(price) + params.slippage + params.fee
        if entry >= 1.0:
            skipped += 1
            continue

        exit_price = placeholder_exit_price(connection, asset)
        if exit_price is None:
            skipped += 1
            continue

        trade_pnl = params.stake_usd / entry * exit_price - params.stake_usd
        pnl += trade_pnl
        copied += 1
        wins += trade_pnl > 0

    return {
        "model_valid": False,
        "latency_applied": False,
        "copied_trades": copied,
        "skipped": skipped,
        "total_pnl_usd": round(pnl, 2),
        "avg_pnl_per_trade": round(pnl / copied, 3) if copied else 0.0,
        "winrate": round(wins / copied, 3) if copied else 0.0,
        "roi_pct": round(100 * pnl / (copied * params.stake_usd), 2) if copied else 0.0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wallets", nargs="+", help="0x-prefixed proxy wallet addresses")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite input path")
    parser.add_argument("--slippage", type=float, default=0.01)
    parser.add_argument("--fee", type=float, default=0.0)
    parser.add_argument("--stake", type=float, default=100.0)
    parser.add_argument(
        "--allow-placeholder-model",
        action="store_true",
        help="acknowledge that latency and settlement are not modeled",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    invalid_wallets = [wallet for wallet in args.wallets if not WALLET_RE.fullmatch(wallet)]
    if invalid_wallets:
        parser.error(f"invalid wallet address: {invalid_wallets[0]}")
    if not args.db.is_file():
        parser.error(f"database does not exist: {args.db}")
    if args.stake <= 0 or args.slippage < 0 or args.fee < 0:
        parser.error("--stake must be positive; --slippage and --fee cannot be negative")
    if not args.allow_placeholder_model:
        parser.error(
            "refusing to report misleading performance: the current model does not apply "
            "latency or real settlement; pass --allow-placeholder-model only for development"
        )

    print("WARNING: INVALID PLACEHOLDER MODEL — do not use these results for decisions.")
    with closing(sqlite3.connect(args.db)) as connection:
        result = run_placeholder(
            connection,
            args.wallets,
            Params(slippage=args.slippage, fee=args.fee, stake_usd=args.stake),
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
