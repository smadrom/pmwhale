# pmwhale

`pmwhale` — исследовательский набор инструментов для проверки гипотез о
копировании крупных публичных кошельков Polymarket. Он собирает публичные данные
в SQLite, строит разведочный рейтинг кошельков и показывает локальный dashboard.

> **Важно:** это ранний research preview, а не торговая система. Рейтинг пока
> оценивает денежные потоки сделок без переоценки открытых позиций. Бэктест не
> учитывает реальную задержку входа и достоверный сеттлмент, поэтому по умолчанию
> отказывается запускаться. Его placeholder-результаты нельзя использовать для
> финансовых решений.

## Быстрый старт

```bash
git clone https://github.com/smadrom/pmwhale.git
cd pmwhale
uv sync --extra dev

uv run pmwhale-collect --markets 40 --holders 50 --min-amount 100
uv run pmwhale-rank --db pmwhale.db --min-positions 20
```

Нужен Python 3.11+. Без `uv` можно создать обычный `venv` и выполнить
`python -m pip install -e .`.

Старые команды `python collect.py`, `python rank.py` и `python backtest.py`
оставлены как совместимые точки входа.

## Dashboard

```bash
cd ui
bun install --frozen-lockfile
bun run build

# Linux/macOS
DB_PATH=../pmwhale.db bun run start

# или Docker Compose, порт доступен только на localhost
docker compose up --build
```

В PowerShell перед запуском используй
`$env:DB_PATH = "../pmwhale.db"`.

## Что ещё нужно для валидного бэктеста

1. Фактический исход рынка из закрытых позиций или on-chain resolution.
2. Цена входа после задержки из исторических CLOB-данных.
3. Слиппедж по глубине стакана, а не константа.
4. Отбор кошельков только по данным до тестового периода.
5. Реализованный P&L из позиций и out-of-sample проверка.

Проект работает только с публичными API без авторизации и не включает собранную
базу. Не коммить базы, не деанонимизируй владельцев адресов и не публикуй
персональные профили.

Использование prediction markets может ограничиваться правилами площадки и
законами твоей юрисдикции. Это не финансовый, юридический или налоговый совет.
Проект не связан с Polymarket и не одобрен им.

Основная документация, правила участия и релизный статус находятся в
[README](../README.md), [CONTRIBUTING](../CONTRIBUTING.md) и
[docs/RELEASE.md](RELEASE.md).
