from __future__ import annotations

import httpx
import pytest

from pmwhale.client import PolyClient


def test_gamma_markets_sends_verified_sort_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["order"] == "volumeNum"
        assert request.url.params["ascending"] == "false"
        return httpx.Response(200, json=[{"conditionId": "one"}])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = PolyClient(client=http_client, sleep=lambda _seconds: None)
        assert client.gamma_markets(limit=1) == [{"conditionId": "one"}]


def test_trader_leaderboard_uses_live_public_endpoint_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/leaderboard"
        assert request.url.params["timePeriod"] == "DAY"
        assert request.url.params["orderBy"] == "PNL"
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = PolyClient(client=http_client, sleep=lambda _seconds: None)
        assert client.trader_leaderboard() == []


def test_transient_status_is_retried() -> None:
    requests = 0
    sleeps: list[float] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = PolyClient(client=http_client, sleep=sleeps.append)
        assert client.trades("0xabc") == []

    assert requests == 2
    assert 0.0 in sleeps


def test_trade_iteration_never_exceeds_requested_maximum() -> None:
    requests: list[tuple[int, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        limit = int(request.url.params["limit"])
        offset = int(request.url.params["offset"])
        requests.append((limit, offset))
        return httpx.Response(200, json=[{"offset": offset + index} for index in range(limit)])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = PolyClient(client=http_client, sleep=lambda _seconds: None)
        trades = list(client.iter_trades("0xabc", page=3, max_trades=5))

    assert len(trades) == 5
    assert requests == [(3, 0), (2, 3)]


def test_public_api_limits_are_validated_before_request() -> None:
    with httpx.Client() as http_client:
        client = PolyClient(client=http_client, sleep=lambda _seconds: None)

        with pytest.raises(ValueError, match="holders limit"):
            client.holders("condition", limit=21)
        with pytest.raises(ValueError, match="max_trades"):
            list(client.iter_trades("0xabc", max_trades=10_001))
        with pytest.raises(ValueError, match="leaderboard limit"):
            client.trader_leaderboard(limit=51)
        with pytest.raises(ValueError, match="leaderboard time period"):
            client.trader_leaderboard(time_period="YEAR")
