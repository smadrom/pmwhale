"""Тонкий клиент к публичным API Polymarket (без авторизации).

Data API  — позиции/сделки/активность/лидерборд по кошелькам.
CLOB API  — цены и история цен рынков (нужно для честного слиппеджа в бэктесте).

Ничего приватного: только чтение публичных данных.
"""
from __future__ import annotations

import time
from typing import Any, Iterator

import httpx

DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"

# Вежливый rate-limit, чтобы не ловить 429. Подкрути под свои серваки/прокси.
_MIN_INTERVAL = 0.15


class PolyClient:
    def __init__(self, timeout: float = 30.0):
        self._c = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "pmwhale-research/0.1"},
        )
        self._last = 0.0

    def _throttle(self) -> None:
        dt = time.monotonic() - self._last
        if dt < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - dt)
        self._last = time.monotonic()

    def _get(self, base: str, path: str, **params: Any) -> Any:
        self._throttle()
        for attempt in range(5):
            r = self._c.get(f"{base}{path}", params=params)
            if r.status_code == 429:  # backoff на rate-limit
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()

    # ---- Gamma API (рынки) ---------------------------------------------
    def gamma_markets(self, limit: int = 50, order: str = "volumeNum",
                      active: bool = True, closed: bool = False,
                      offset: int = 0) -> list[dict]:
        """Активные рынки, по умолчанию сортировка по объёму (крупнейшие).

        ВАЖНО: рабочее поле сортировки — 'volumeNum'/'liquidityNum'/'volume24hr',
        а НЕ 'volume' (последнее молча не сортирует).
        """
        return self._get(
            GAMMA_API, "/markets",
            limit=limit, offset=offset, order=order, ascending="false",
            active=str(active).lower(), closed=str(closed).lower(),
        )

    # ---- Data API -------------------------------------------------------
    def holders(self, condition_id: str, limit: int = 100) -> list[dict]:
        """Топ-холдеры рынка по каждому исходу-токену.

        Возвращает [{token, holders:[{proxyWallet, amount, outcomeIndex,...}]}].
        Крупнейшие proxyWallet = киты этого рынка.
        """
        return self._get(DATA_API, "/holders", market=condition_id, limit=limit)

    def trades(self, user: str, limit: int = 500, offset: int = 0) -> list[dict]:
        """Сделки (fills) кошелька, свежие первыми. Пагинация через offset."""
        return self._get(DATA_API, "/trades", user=user, limit=limit, offset=offset)

    def iter_trades(self, user: str, page: int = 500, max_trades: int = 20000) -> Iterator[dict]:
        """Все сделки кошелька через offset-пагинацию (с потолком безопасности)."""
        offset = 0
        while offset < max_trades:
            batch = self.trades(user, limit=page, offset=offset)
            if not batch:
                return
            yield from batch
            if len(batch) < page:
                return
            offset += page

    def positions(self, user: str) -> list[dict]:
        return self._get(DATA_API, "/positions", user=user)

    def closed_positions(self, user: str) -> list[dict]:
        return self._get(DATA_API, "/closed-positions", user=user)

    # ---- CLOB API -------------------------------------------------------
    def price_history(self, token_id: str, interval: str = "1h",
                      fidelity: int = 60) -> list[dict]:
        """История цены токена-исхода — опорная цена для расчёта слиппеджа."""
        return self._get(CLOB_API, "/prices-history",
                         market=token_id, interval=interval, fidelity=fidelity)

    def close(self) -> None:
        self._c.close()
