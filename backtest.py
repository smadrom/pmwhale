"""Шаг 3 — ГЛАВНЫЙ тест схемы: окупается ли копирование китов
ПОСЛЕ задержки реакции и проскальзывания.

Логика: для каждой сделки отобранных кошельков-лидеров эмулируем, что мы
повторяем вход с задержкой LATENCY_S и по цене, ухудшенной на SLIPPAGE + FEE.
Выход — по цене закрытия исхода (0 или 1) либо по нашей стоп-логике.

Наивная копия почти всегда выходит в минус — если у тебя получается плюс,
перепроверь, не заглядываешь ли ты в будущее (look-ahead bias).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB = Path(__file__).with_name("pmwhale.db")


@dataclass
class Params:
    latency_s: int = 30          # через сколько секунд после кита мы реально входим
    slippage: float = 0.01       # ухудшение цены исхода (в абсолютных пунктах 0..1)
    fee: float = 0.0             # комиссия площадки, если есть
    stake_usd: float = 100.0     # фиксированная ставка на копию
    min_price: float = 0.05      # не копируем экстремальные цены (шум/неликвид)
    max_price: float = 0.95
    only_buys: bool = True       # копируем только открытие позиции (BUY)


def resolved_price(con: sqlite3.Connection, asset: str) -> float | None:
    """Грубая оценка исхода токена: если по нему были поздние SELL близко к 1/0.

    Заглушка. В боевой версии бери реальный settlement из /closed-positions
    или on-chain resolution рынка. Без этого бэктест НЕ валиден.
    """
    row = con.execute(
        "SELECT price FROM trades WHERE asset=? ORDER BY timestamp DESC LIMIT 1",
        (asset,),
    ).fetchone()
    return float(row[0]) if row else None


def run(con: sqlite3.Connection, wallets: list[str], p: Params) -> dict:
    q = (
        "SELECT timestamp, asset, side, price, size FROM trades "
        f"WHERE wallet IN ({','.join('?' * len(wallets))}) "
        "ORDER BY timestamp"
    )
    trades = con.execute(q, [w.lower() for w in wallets]).fetchall()

    pnl = 0.0
    n = 0
    wins = 0
    skipped = 0
    for _ts, asset, side, price, _size in trades:
        if p.only_buys and side != "BUY":
            continue
        if price is None or not (p.min_price <= price <= p.max_price):
            skipped += 1
            continue

        entry = price + p.slippage + p.fee      # мы входим дороже кита
        if entry >= 1.0:
            skipped += 1
            continue

        settle = resolved_price(con, asset)     # ЗАГЛУШКА — заменить на реальный сеттлмент
        if settle is None:
            skipped += 1
            continue

        shares = p.stake_usd / entry
        payout = shares * settle
        trade_pnl = payout - p.stake_usd
        pnl += trade_pnl
        n += 1
        wins += trade_pnl > 0

    return {
        "copied_trades": n,
        "skipped": skipped,
        "total_pnl_usd": round(pnl, 2),
        "avg_pnl_per_trade": round(pnl / n, 3) if n else 0.0,
        "winrate": round(wins / n, 3) if n else 0.0,
        "roi_pct": round(100 * pnl / (n * p.stake_usd), 2) if n else 0.0,
    }


def main() -> None:
    import sys
    wallets = sys.argv[1:]
    if not wallets:
        print("usage: python backtest.py 0xWALLET1 0xWALLET2 ...")
        print("(возьми топ из rank.py)")
        return
    con = sqlite3.connect(DB)
    try:
        for lat in (5, 30, 120):
            res = run(con, wallets, Params(latency_s=lat))
            print(f"latency={lat:>4}s  {res}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
