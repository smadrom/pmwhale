from __future__ import annotations

import sqlite3

import pytest

from pmwhale.backtest import Params, main, run_placeholder
from pmwhale.collect import init_db, store_trades


def test_placeholder_result_carries_validity_flags() -> None:
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    wallet = "0x" + "a" * 40
    store_trades(
        connection,
        wallet,
        [
            {
                "transactionHash": "1",
                "timestamp": 1,
                "asset": "a",
                "side": "BUY",
                "price": 0.5,
                "size": 10,
            },
            {
                "transactionHash": "2",
                "timestamp": 2,
                "asset": "a",
                "side": "SELL",
                "price": 1.0,
                "size": 10,
            },
        ],
    )

    result = run_placeholder(connection, [wallet], Params())
    connection.close()

    assert result["model_valid"] is False
    assert result["latency_applied"] is False
    assert result["copied_trades"] == 1
    assert result["total_pnl_usd"] == 96.08


def test_cli_refuses_placeholder_model_without_acknowledgement(tmp_path) -> None:
    db_path = tmp_path / "pmwhale.db"
    connection = sqlite3.connect(db_path)
    init_db(connection)
    connection.close()

    with pytest.raises(SystemExit) as exc_info:
        main(["0x" + "a" * 40, "--db", str(db_path)])

    assert exc_info.value.code == 2
