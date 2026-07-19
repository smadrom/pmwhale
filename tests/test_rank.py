from __future__ import annotations

import sqlite3

from pmwhale.collect import init_db, store_trades
from pmwhale.rank import ranked_wallets, wallet_stats


def test_wallet_stats_are_explicit_cash_flow_approximations() -> None:
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    wallet = "0xabc"
    store_trades(
        connection,
        wallet,
        [
            {
                "transactionHash": "1",
                "timestamp": 1,
                "asset": "a",
                "side": "BUY",
                "price": 0.4,
                "size": 10,
            },
            {
                "transactionHash": "2",
                "timestamp": 2,
                "asset": "a",
                "side": "SELL",
                "price": 0.7,
                "size": 10,
            },
            {
                "transactionHash": "3",
                "timestamp": 3,
                "asset": "b",
                "side": "BUY",
                "price": 0.2,
                "size": 10,
            },
        ],
    )

    stats = wallet_stats(connection)

    assert stats == [
        {
            "wallet": wallet,
            "pnl_usd": 1.0,
            "n_positions": 2,
            "winrate": 0.5,
            "volume_usd": 13.0,
            "n_trades": 3,
            "sharpe_like": 0.2,
        }
    ]
    assert ranked_wallets(connection, min_positions=3) == []
    connection.close()
