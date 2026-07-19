from __future__ import annotations

import sqlite3
from typing import Any

from pmwhale.collect import init_db, seed_wallets, store_trades


class FakeCollectionClient:
    def __init__(self) -> None:
        self.order: str | None = None

    def gamma_markets(
        self,
        limit: int = 50,
        order: str = "volumeNum",
        active: bool = True,
        closed: bool = False,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        self.order = order
        return [{"conditionId": "market-1"}, {"conditionId": None}]

    def holders(self, condition_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "holders": [
                    {"proxyWallet": "0xABC", "amount": "150"},
                    {"proxyWallet": "0xDEF", "amount": "99"},
                    {"proxyWallet": None, "amount": "500"},
                ]
            }
        ]

    def iter_trades(self, user: str, page: int = 500, max_trades: int = 20_000) -> Any:
        return iter(())


def test_store_trades_is_idempotent_and_counts_only_insertions() -> None:
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    trade = {
        "transactionHash": "0xtx",
        "timestamp": 123,
        "conditionId": "condition",
        "asset": "asset",
        "side": "buy",
        "outcome": "Yes",
        "price": "0.4",
        "size": "10",
    }

    assert store_trades(connection, "0xABC", [trade]) == 1
    assert store_trades(connection, "0xABC", [trade]) == 0
    assert connection.execute("SELECT wallet, side, usd FROM trades").fetchone() == (
        "0xabc",
        "BUY",
        4.0,
    )
    connection.close()


def test_store_trades_skips_malformed_rows() -> None:
    connection = sqlite3.connect(":memory:")
    init_db(connection)

    assert (
        store_trades(
            connection,
            "0xabc",
            [
                {"timestamp": "bad"},
                {},
                {"timestamp": 1, "asset": "a", "side": "MINT", "price": 0.5, "size": 1},
                {"timestamp": 2, "asset": "a", "side": "BUY", "price": 1.5, "size": 1},
            ],
        )
        == 0
    )
    connection.close()


def test_seed_wallets_uses_verified_volume_order_and_threshold() -> None:
    client = FakeCollectionClient()

    wallets = seed_wallets(client, n_markets=10, holders_per_market=5, min_amount=100)

    assert client.order == "volumeNum"
    assert wallets == ["0xabc"]
