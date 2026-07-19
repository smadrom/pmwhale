# Проверенные эндпоинты Polymarket

Всё ниже последний раз проверялось живыми запросами 19 июля 2026 года.
CI проекта намеренно не обращается к production API, поэтому перед релизом,
который зависит от свежих контрактов, нужен ручной smoke test. Здесь описаны
контракты, которые реально отвечали во время последней проверки.

## Хосты

| Хост | Назначение | Auth |
| --- | --- | --- |
| `https://gamma-api.polymarket.com` | Метаданные рынков | нет |
| `https://data-api.polymarket.com` | Сделки, позиции, аналитика | нет |
| `https://clob.polymarket.com` | Ордербук и цены | публичное чтение |

## Рынки — Gamma

`GET /markets`

- Сортировка: **`order=volumeNum`** (или `liquidityNum`, `volume24hr`).
  ⚠️ `order=volume` **молча не сортирует** — частая ловушка.
- `active=true&closed=false&ascending=false&limit=&offset=`
- Ключевые поля: `conditionId`, `clobTokenIds` (JSON-строка со списком token_id
  исходов), `volumeNum`, `liquidityNum`, `outcomes`, `outcomePrices`,
  `lastTradePrice`, `endDate`.

## Холдеры рынка — Data

`GET /holders?market=<conditionId>&limit=`

- `limit` ограничен значением `20`.
- Ответ: список групп `{ token, holders: [...] }` по каждому исходу-токену.
- Холдер: `proxyWallet`, `amount` (в долях/shares, НЕ USD), `outcomeIndex`.
- Крупнейшие `proxyWallet` = киты этого рынка. Это альтернативная выборка для
  исследования, не зависящая от готового лидерборда.

## Сделки кошелька — Data

`GET /trades?user=<addr>&limit=&offset=`

- Пагинация — через **`offset`** (параметр `before` из доки **игнорируется**).
- Максимальное значение `offset` — `10000`; коллектор ограничивает историю
  тем же числом сделок на кошелёк.
- Свежие первыми. Поля: `proxyWallet`, `side` (`BUY`/`SELL`, верхний регистр),
  `asset` (token_id), `conditionId`, `size` (shares), `price` (0..1),
  `timestamp` (unix, сек), `outcome`, `outcomeIndex`, `transactionHash`.
- ⚠️ Может вернуть `[]` даже у кошелька с открытыми позициями (не все холдеры —
  активные тейкеры). Для P&L опирайся на позиции, ниже.

## Позиции кошелька — Data

`GET /positions?user=<addr>` — открытые
`GET /closed-positions?user=<addr>` — закрытые/реализованные

- Готовый P&L без реконструкции: `realizedPnl`, `cashPnl`, `percentPnl`,
  `avgPrice`, `curPrice`, `initialValue`, `currentValue`, `totalBought`,
  `redeemable`.
- Это точнее для рейтинга кошельков, чем суммирование потоков из `/trades`.

## Активность кошелька — Data

`GET /activity?user=<addr>&limit=` — хронологическая лента (сделки/минты/сплиты/
редимы). Валидный JSON-список; для нулевого адреса — `[]`.

## Лидерборд трейдеров — Data

`GET /v1/leaderboard?timePeriod=ALL&orderBy=PNL&limit=25&offset=0`

- Рабочий публичный endpoint для рейтинга по P&L или объёму.
- Допустимы `limit=1..50`, `offset=0..1000`; период по умолчанию — `DAY`, для
  all-time выборки нужно явно передать `timePeriod=ALL`.
- Текущий коллектор намеренно сидирует кандидатов из холдеров крупнейших рынков,
  а не доверяет готовому рейтингу как выборке для бэктеста.

## CLOB — цены (для слиппеджа)

`GET /prices-history?market=<token_id>&interval=1h&fidelity=60` — история цены
исхода. Нужна, чтобы моделировать реальный слиппедж на момент входа в бэктесте.
Текущий ответ CLOB имеет форму `{ "history": [{ "t": ..., "p": ... }, ...] }`.
