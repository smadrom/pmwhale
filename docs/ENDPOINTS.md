# Проверенные эндпоинты Polymarket

Всё ниже проверено живыми запросами (июль 2026). Важно: официальная дока
(`docs.polymarket.com`, `llms.txt`) местами описывает пути, которых на боевых
хостах **нет** (напр. `/leaderboard`, `/v1/data/...` отдают 404). Здесь —
только то, что реально отвечает.

## Хосты

| Хост | Назначение | Auth |
|------|-----------|------|
| `https://gamma-api.polymarket.com` | Метаданные рынков | нет |
| `https://data-api.polymarket.com`  | Позиции / сделки / холдеры / активность | нет |
| `https://clob.polymarket.com`      | Ордербук, цены, история цен | публичные ручки без auth |

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

- Ответ: список групп `{ token, holders: [...] }` по каждому исходу-токену.
- Холдер: `proxyWallet`, `amount` (в долях/shares, НЕ USD), `outcomeIndex`.
- Крупнейшие `proxyWallet` = киты этого рынка. Хороший способ сидировать кошельки
  (лучше несуществующего лидерборда).

## Сделки кошелька — Data

`GET /trades?user=<addr>&limit=&offset=`

- Пагинация — через **`offset`** (параметр `before` из доки **игнорируется**).
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

## CLOB — цены (для слиппеджа)

`GET /prices-history?market=<token_id>&interval=1h&fidelity=60` — история цены
исхода. Нужна, чтобы моделировать реальный слиппедж на момент входа в бэктесте.
