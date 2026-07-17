"""Шаг 1 — сбор данных.

Берём топ кошельков с лидерборда, тянем всю их историю сделок,
складываем в локальный SQLite. Дальше на этих данных считаем рейтинг и бэктест.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from client import PolyClient

DB = Path(__file__).with_name("pmwhale.db")


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS trades (
            wallet     TEXT NOT NULL,
            tx_hash    TEXT,
            timestamp  INTEGER NOT NULL,
            market     TEXT,
            asset      TEXT,           -- token_id исхода
            side       TEXT,           -- BUY / SELL
            outcome    TEXT,
            price      REAL,           -- цена исхода в USDC (0..1)
            size       REAL,           -- размер в токенах (= долларов при price)
            usd        REAL,           -- price*size, для фильтра "китов"
            PRIMARY KEY (wallet, tx_hash, asset, timestamp)
        );
        CREATE INDEX IF NOT EXISTS ix_trades_wallet ON trades(wallet);
        CREATE INDEX IF NOT EXISTS ix_trades_ts     ON trades(timestamp);
        """
    )


def store_trades(con: sqlite3.Connection, wallet: str, rows: list[dict]) -> int:
    n = 0
    for t in rows:
        price = float(t.get("price", 0) or 0)
        size = float(t.get("size", 0) or 0)
        con.execute(
            "INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                wallet.lower(),
                t.get("transactionHash") or t.get("tx_hash"),
                int(t["timestamp"]),
                t.get("conditionId") or t.get("market"),
                t.get("asset") or t.get("tokenId"),
                (t.get("side") or "").upper(),
                t.get("outcome"),
                price,
                size,
                price * size,
            ),
        )
        n += 1
    return n


def seed_wallets(pc: PolyClient, n_markets: int, holders_per_market: int,
                 min_amount: float) -> list[str]:
    """Собрать кошельки-китов из топ-холдеров крупнейших активных рынков."""
    markets = pc.gamma_markets(limit=n_markets, order="volume")
    print(f"Рынков по объёму: {len(markets)}")
    seen: set[str] = set()
    for m in markets:
        cond = m.get("conditionId")
        if not cond:
            continue
        try:
            groups = pc.holders(cond, limit=holders_per_market)
        except Exception as e:  # рынок без холдеров/ошибка — пропускаем
            print(f"  holders fail {cond[:10]}: {type(e).__name__}")
            continue
        for g in groups:
            for h in g.get("holders", []):
                w = h.get("proxyWallet")
                if w and float(h.get("amount", 0) or 0) >= min_amount:
                    seen.add(w.lower())
    return sorted(seen)


def main(n_markets: int = 40, holders_per_market: int = 50,
         min_amount: float = 100.0) -> None:
    con = sqlite3.connect(DB)
    init_db(con)
    pc = PolyClient()
    try:
        wallets = seed_wallets(pc, n_markets, holders_per_market, min_amount)
        print(f"Уникальных китов (amount>={min_amount}): {len(wallets)}")
        for i, w in enumerate(wallets, 1):
            total = 0
            for t in pc.iter_trades(w):
                total += store_trades(con, w, [t])
            con.commit()
            print(f"[{i}/{len(wallets)}] {w}: +{total} сделок")
    finally:
        pc.close()
        con.close()


if __name__ == "__main__":
    main()
