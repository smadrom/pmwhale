"""Collect public Polymarket trades into a local SQLite database."""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from pmwhale.client import MAX_HOLDERS_LIMIT, MAX_TRADES, PolyClient

DEFAULT_DB = Path("pmwhale.db")


class CollectionClient(Protocol):
    def gamma_markets(
        self,
        limit: int = 50,
        order: str = "volumeNum",
        active: bool = True,
        closed: bool = False,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def holders(
        self,
        condition_id: str,
        limit: int = MAX_HOLDERS_LIMIT,
    ) -> list[dict[str, Any]]: ...

    def iter_trades(
        self,
        user: str,
        page: int = 500,
        max_trades: int = MAX_TRADES,
    ) -> Any: ...


def init_db(connection: sqlite3.Connection) -> None:
    """Create the v1 database schema if it does not exist."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS trades (
            wallet     TEXT NOT NULL,
            tx_hash    TEXT NOT NULL DEFAULT '',
            timestamp  INTEGER NOT NULL,
            market     TEXT,
            asset      TEXT NOT NULL,
            side       TEXT,
            outcome    TEXT,
            price      REAL,
            size       REAL,
            usd        REAL,
            PRIMARY KEY (wallet, tx_hash, asset, timestamp)
        );
        CREATE INDEX IF NOT EXISTS ix_trades_wallet ON trades(wallet);
        CREATE INDEX IF NOT EXISTS ix_trades_ts     ON trades(timestamp);
        PRAGMA user_version = 1;
        """
    )


def store_trades(
    connection: sqlite3.Connection,
    wallet: str,
    rows: Sequence[dict[str, Any]],
) -> int:
    """Store valid trades and return the number of newly inserted rows."""
    inserted = 0
    for trade in rows:
        asset = trade.get("asset") or trade.get("tokenId")
        side = str(trade.get("side") or "").upper()
        try:
            timestamp = int(trade["timestamp"])
            price = float(trade["price"])
            size = float(trade["size"])
        except (KeyError, TypeError, ValueError):
            continue
        if not asset or side not in {"BUY", "SELL"} or not (0 <= price <= 1) or size < 0:
            continue

        transaction_hash = trade.get("transactionHash") or trade.get("tx_hash")
        if not transaction_hash:
            transaction_hash = (
                f"missing:{timestamp}:{side}:{price:.12g}:{size:.12g}:{trade.get('outcome') or ''}"
            )

        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO trades
                (wallet, tx_hash, timestamp, market, asset, side, outcome, price, size, usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                wallet.lower(),
                str(transaction_hash),
                timestamp,
                trade.get("conditionId") or trade.get("market"),
                str(asset),
                side,
                trade.get("outcome"),
                price,
                size,
                price * size,
            ),
        )
        inserted += max(cursor.rowcount, 0)
    return inserted


def seed_wallets(
    client: CollectionClient,
    n_markets: int,
    holders_per_market: int,
    min_amount: float,
) -> list[str]:
    """Find candidate wallets among holders of the largest active markets."""
    markets = client.gamma_markets(limit=n_markets, order="volumeNum")
    print(f"Markets by volume: {len(markets)}")
    seen: set[str] = set()
    for market in markets:
        condition_id = market.get("conditionId")
        if not condition_id:
            continue
        try:
            groups = client.holders(str(condition_id), limit=holders_per_market)
        except Exception as exc:  # one unavailable market must not stop a collection
            print(f"  holders failed {str(condition_id)[:10]}: {type(exc).__name__}")
            continue
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            holders = group.get("holders", [])
            if not isinstance(holders, list):
                continue
            for holder in holders:
                if not isinstance(holder, dict):
                    continue
                wallet = holder.get("proxyWallet")
                try:
                    amount = float(holder.get("amount", 0) or 0)
                except (TypeError, ValueError):
                    continue
                if wallet and amount >= min_amount:
                    seen.add(str(wallet).lower())
    return sorted(seen)


def collect(
    db_path: Path,
    *,
    n_markets: int = 40,
    holders_per_market: int = MAX_HOLDERS_LIMIT,
    min_amount: float = 100.0,
    max_trades: int = MAX_TRADES,
) -> tuple[int, int]:
    """Run collection and return ``(wallet_count, failed_wallet_count)``."""
    connection = sqlite3.connect(db_path)
    init_db(connection)
    try:
        with PolyClient() as client:
            wallets = seed_wallets(client, n_markets, holders_per_market, min_amount)
            print(f"Unique candidate wallets (amount >= {min_amount}): {len(wallets)}")
            failed = 0
            for index, wallet in enumerate(wallets, 1):
                total = 0
                try:
                    for trade in client.iter_trades(wallet, max_trades=max_trades):
                        total += store_trades(connection, wallet, [trade])
                    connection.commit()
                    print(f"[{index}/{len(wallets)}] {wallet}: +{total} trades")
                except Exception as exc:  # preserve partial public data for this wallet
                    connection.commit()
                    failed += 1
                    print(
                        f"[{index}/{len(wallets)}] {wallet}: FAILED {type(exc).__name__} "
                        f"(partial +{total})"
                    )
            print(f"Done. Failed wallets: {failed}/{len(wallets)}")
            return len(wallets), failed
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite output path")
    parser.add_argument("--markets", type=int, default=40, help="number of markets to seed")
    parser.add_argument(
        "--holders",
        type=int,
        default=MAX_HOLDERS_LIMIT,
        help=f"holders requested per market (maximum {MAX_HOLDERS_LIMIT})",
    )
    parser.add_argument("--min-amount", type=float, default=100.0, help="minimum holder shares")
    parser.add_argument(
        "--max-trades",
        type=int,
        default=MAX_TRADES,
        help=f"safety cap per wallet (maximum {MAX_TRADES})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.markets <= 0 or args.holders <= 0 or args.max_trades <= 0:
        raise SystemExit("--markets, --holders and --max-trades must be positive")
    if args.holders > MAX_HOLDERS_LIMIT:
        raise SystemExit(f"--holders cannot exceed the API maximum of {MAX_HOLDERS_LIMIT}")
    if args.max_trades > MAX_TRADES:
        raise SystemExit(f"--max-trades cannot exceed the API maximum of {MAX_TRADES}")
    if args.min_amount < 0:
        raise SystemExit("--min-amount cannot be negative")
    collect(
        args.db,
        n_markets=args.markets,
        holders_per_market=args.holders,
        min_amount=args.min_amount,
        max_trades=args.max_trades,
    )


if __name__ == "__main__":
    main()
