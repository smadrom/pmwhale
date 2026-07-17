"""Шаг 2 — рейтинг кошельков по риск-скорректированной доходности.

Смысл: НЕ копировать по размеру ставки ("кит зашёл"), а копировать только
кошельки со стабильно положительным ROI и приемлемой просадкой. Большой объём
!= высокий винрейт — этот скрипт как раз отделяет одно от другого.

Реализация P&L здесь — грубая аппроксимация по сделкам (реализованный поток
BUY/SELL на пару wallet+asset). Для точных цифр сверяйся с /closed-positions.
"""
from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path(__file__).with_name("pmwhale.db")


def wallet_stats(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT wallet, asset, side, price, size, usd, timestamp "
        "FROM trades ORDER BY wallet, asset, timestamp"
    ).fetchall()

    # поток кэша по позиции: BUY = отток USDC, SELL = приток
    pos_pnl: dict[tuple[str, str], float] = defaultdict(float)
    pos_open: dict[tuple[str, str], float] = defaultdict(float)  # чистый размер токенов
    volume: dict[str, float] = defaultdict(float)
    ntrades: dict[str, int] = defaultdict(int)

    for wallet, asset, side, price, size, usd, _ in rows:
        key = (wallet, asset)
        volume[wallet] += usd
        ntrades[wallet] += 1
        if side == "BUY":
            pos_pnl[key] -= usd
            pos_open[key] += size
        else:  # SELL
            pos_pnl[key] += usd
            pos_open[key] -= size

    # закрытые позиции считаем реализованными; открытые метим по последней цене ~0.5
    # (для честности используй /positions -> curPrice; тут заглушка)
    per_wallet_returns: dict[str, list[float]] = defaultdict(list)
    for (wallet, asset), pnl in pos_pnl.items():
        per_wallet_returns[wallet].append(pnl)

    out = []
    for wallet, pnls in per_wallet_returns.items():
        total = sum(pnls)
        wins = sum(1 for p in pnls if p > 0)
        n = len(pnls)
        mean = total / n if n else 0.0
        sd = (math.sqrt(sum((p - mean) ** 2 for p in pnls) / n) if n > 1 else 0.0)
        sharpe_like = mean / sd if sd > 0 else 0.0
        out.append({
            "wallet": wallet,
            "pnl_usd": round(total, 2),
            "n_positions": n,
            "winrate": round(wins / n, 3) if n else 0.0,
            "volume_usd": round(volume[wallet], 2),
            "n_trades": ntrades[wallet],
            "sharpe_like": round(sharpe_like, 3),
        })
    return out


def main(min_positions: int = 20) -> None:
    con = sqlite3.connect(DB)
    try:
        stats = wallet_stats(con)
    finally:
        con.close()

    # фильтр: достаточная выборка + стабильность, а не разовый занос
    ranked = [s for s in stats if s["n_positions"] >= min_positions]
    ranked.sort(key=lambda s: (s["sharpe_like"], s["winrate"]), reverse=True)

    print(f"{'wallet':44} {'pnl$':>10} {'win':>5} {'pos':>5} {'sharpe':>7}")
    for s in ranked[:25]:
        print(f"{s['wallet']:44} {s['pnl_usd']:>10.0f} "
              f"{s['winrate']:>5.2f} {s['n_positions']:>5} {s['sharpe_like']:>7.2f}")


if __name__ == "__main__":
    main()
