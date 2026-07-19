"""Thin client for public, unauthenticated Polymarket APIs."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from types import TracebackType
from typing import Any, Self

import httpx

DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

_MIN_INTERVAL = 0.15
_MAX_RETRIES = 6
MAX_HOLDERS_LIMIT = 20
MAX_TRADES = 10_000
MAX_TRADES_PAGE = 10_000
LEADERBOARD_CATEGORIES = frozenset(
    {
        "OVERALL",
        "POLITICS",
        "SPORTS",
        "ESPORTS",
        "CRYPTO",
        "CULTURE",
        "MENTIONS",
        "WEATHER",
        "ECONOMICS",
        "TECH",
        "FINANCE",
    }
)
LEADERBOARD_TIME_PERIODS = frozenset({"DAY", "WEEK", "MONTH", "ALL"})
LEADERBOARD_ORDER_BY = frozenset({"PNL", "VOL"})
MAX_LEADERBOARD_LIMIT = 50
MAX_LEADERBOARD_OFFSET = 1_000


class PolyClient:
    """Rate-limited HTTP client with bounded retries for transient failures."""

    _RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __init__(
        self,
        timeout: float = 30.0,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._owns_client = client is None
        self._c = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "pmwhale-research/0.1"},
        )
        self._sleep = sleep
        self._last = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < _MIN_INTERVAL:
            self._sleep(_MIN_INTERVAL - elapsed)
        self._last = time.monotonic()

    def _backoff(self, attempt: int, response: httpx.Response | None = None) -> None:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        try:
            seconds = float(retry_after) if retry_after is not None else 2**attempt
        except ValueError:
            seconds = 2**attempt
        self._sleep(min(max(seconds, 0.0), 20.0))

    def _get(self, base: str, path: str, **params: Any) -> Any:
        last_exception: httpx.HTTPError | None = None
        last_response: httpx.Response | None = None
        for attempt in range(_MAX_RETRIES):
            self._throttle()
            try:
                response = self._c.get(f"{base}{path}", params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exception = exc
                self._backoff(attempt)
                continue
            last_response = response
            if response.status_code in self._RETRY_STATUS:
                self._backoff(attempt, response)
                continue
            response.raise_for_status()
            return response.json()

        if last_exception is not None and last_response is None:
            raise last_exception
        if last_response is None:  # pragma: no cover - defensive invariant
            raise RuntimeError("request failed without a response")
        last_response.raise_for_status()
        raise RuntimeError("unreachable")  # pragma: no cover

    def gamma_markets(
        self,
        limit: int = 50,
        order: str = "volumeNum",
        active: bool = True,
        closed: bool = False,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return active markets, largest volume first by default."""
        return self._get(
            GAMMA_API,
            "/markets",
            limit=limit,
            offset=offset,
            order=order,
            ascending="false",
            active=str(active).lower(),
            closed=str(closed).lower(),
        )

    def holders(self, condition_id: str, limit: int = MAX_HOLDERS_LIMIT) -> list[dict[str, Any]]:
        if not 0 <= limit <= MAX_HOLDERS_LIMIT:
            raise ValueError(f"holders limit must be between 0 and {MAX_HOLDERS_LIMIT}")
        return self._get(DATA_API, "/holders", market=condition_id, limit=limit)

    def trades(self, user: str, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        if not 0 <= limit <= MAX_TRADES_PAGE:
            raise ValueError(f"trades limit must be between 0 and {MAX_TRADES_PAGE}")
        if not 0 <= offset <= MAX_TRADES:
            raise ValueError(f"trades offset must be between 0 and {MAX_TRADES}")
        return self._get(DATA_API, "/trades", user=user, limit=limit, offset=offset)

    def iter_trades(
        self,
        user: str,
        page: int = 500,
        max_trades: int = MAX_TRADES,
    ) -> Iterator[dict[str, Any]]:
        if not 1 <= page <= MAX_TRADES_PAGE:
            raise ValueError(f"page must be between 1 and {MAX_TRADES_PAGE}")
        if not 1 <= max_trades <= MAX_TRADES:
            raise ValueError(f"max_trades must be between 1 and {MAX_TRADES}")
        offset = 0
        while offset < max_trades:
            batch = self.trades(user, limit=min(page, max_trades - offset), offset=offset)
            if not batch:
                return
            yield from batch
            if len(batch) < page:
                return
            offset += page

    def positions(self, user: str) -> list[dict[str, Any]]:
        return self._get(DATA_API, "/positions", user=user)

    def closed_positions(self, user: str) -> list[dict[str, Any]]:
        return self._get(DATA_API, "/closed-positions", user=user)

    def activity(
        self,
        user: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return self._get(DATA_API, "/activity", user=user, limit=limit, offset=offset)

    def trader_leaderboard(
        self,
        *,
        category: str = "OVERALL",
        time_period: str = "DAY",
        order_by: str = "PNL",
        limit: int = 25,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if category not in LEADERBOARD_CATEGORIES:
            raise ValueError(f"unsupported leaderboard category: {category}")
        if time_period not in LEADERBOARD_TIME_PERIODS:
            raise ValueError(f"unsupported leaderboard time period: {time_period}")
        if order_by not in LEADERBOARD_ORDER_BY:
            raise ValueError(f"unsupported leaderboard order: {order_by}")
        if not 1 <= limit <= MAX_LEADERBOARD_LIMIT:
            raise ValueError(f"leaderboard limit must be between 1 and {MAX_LEADERBOARD_LIMIT}")
        if not 0 <= offset <= MAX_LEADERBOARD_OFFSET:
            raise ValueError(f"leaderboard offset must be between 0 and {MAX_LEADERBOARD_OFFSET}")
        return self._get(
            DATA_API,
            "/v1/leaderboard",
            category=category,
            timePeriod=time_period,
            orderBy=order_by,
            limit=limit,
            offset=offset,
        )

    def price_history(
        self,
        token_id: str,
        interval: str = "1h",
        fidelity: int = 60,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        return self._get(
            CLOB_API,
            "/prices-history",
            market=token_id,
            interval=interval,
            fidelity=fidelity,
        )

    def close(self) -> None:
        if self._owns_client:
            self._c.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
