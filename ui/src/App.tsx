import { useEffect, useState, useCallback } from "react";
import {
  Card,
  Grid,
  Metric,
  Text,
  Title,
  Flex,
  Badge,
  BarList,
  Table,
  TableHead,
  TableHeaderCell,
  TableBody,
  TableRow,
  TableCell,
  Button,
} from "@tremor/react";

type Stats = {
  trades: number;
  wallets: number;
  markets: number;
  first_ts: number | null;
  last_ts: number | null;
};

type Wallet = {
  wallet: string;
  pnl_usd: number;
  n_positions: number;
  winrate: number;
  volume_usd: number;
  n_trades: number;
  sharpe_like: number;
};

const usd = (n: number) =>
  (n < 0 ? "-$" : "$") +
  Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 });

const short = (w: string) => `${w.slice(0, 6)}…${w.slice(-4)}`;

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [wallets, setWallets] = useState<Wallet[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const [s, w] = await Promise.all([
        getJSON<Stats>("/api/stats"),
        getJSON<{ wallets: Wallet[] }>("/api/wallets?limit=25&min_positions=10"),
      ]);
      setStats(s);
      setWallets(w.wallets);
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const spanDays =
    stats?.first_ts && stats?.last_ts
      ? Math.round((stats.last_ts - stats.first_ts) / 86400)
      : 0;

  const pnlList = wallets
    .slice()
    .sort((a, b) => b.pnl_usd - a.pnl_usd)
    .slice(0, 12)
    .map((w) => ({ name: short(w.wallet), value: Math.round(w.pnl_usd) }));

  return (
    <main className="min-h-screen bg-gray-950 text-gray-200 p-6 md:p-10">
      <Flex justifyContent="between" alignItems="center" className="mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-white">
            🐋 pmwhale
            <span className="ml-3 text-sm font-normal text-gray-500">
              Polymarket whale-copy research
            </span>
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Рейтинг кошельков по риск-скорректированной доходности. Данные —
            публичные API Polymarket.
          </p>
        </div>
        <Button variant="secondary" loading={loading} onClick={load}>
          Обновить
        </Button>
      </Flex>

      {err && (
        <Card className="mb-6 ring-red-800 bg-red-950/40">
          <Text className="text-red-300">Ошибка загрузки: {err}</Text>
          <Text className="text-red-400/70 text-xs mt-1">
            Проверь, что API отвечает и pmwhale.db смонтирована.
          </Text>
        </Card>
      )}

      <Grid numItemsSm={2} numItemsLg={4} className="gap-6 mb-8">
        <KpiCard label="Сделок собрано" value={stats?.trades ?? 0} />
        <KpiCard label="Китов (кошельков)" value={stats?.wallets ?? 0} />
        <KpiCard label="Рынков затронуто" value={stats?.markets ?? 0} />
        <KpiCard label="Окно данных, дней" value={spanDays} />
      </Grid>

      <Grid numItemsLg={3} className="gap-6">
        <Card className="bg-gray-900 ring-gray-800">
          <Title className="text-gray-100">Топ по P&L (USD)</Title>
          <Text className="text-gray-500 mb-4 text-xs">
            грубая оценка из потоков сделок — сверяй с /positions
          </Text>
          {pnlList.length ? (
            <BarList data={pnlList} className="mt-2" valueFormatter={usd} />
          ) : (
            <Text className="text-gray-600">нет данных</Text>
          )}
        </Card>

        <Card className="bg-gray-900 ring-gray-800 lg:col-span-2">
          <Flex justifyContent="between" alignItems="center">
            <Title className="text-gray-100">
              Рейтинг китов (sharpe-подобная метрика)
            </Title>
            <Badge color="blue">{wallets.length}</Badge>
          </Flex>
          <Text className="text-gray-500 mb-2 text-xs">
            фильтр: ≥10 позиций. Копировать имеет смысл верхних — стабильных, а не
            крупнейших по объёму.
          </Text>
          <div className="max-h-[520px] overflow-auto">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell className="text-gray-400">Кошелёк</TableHeaderCell>
                  <TableHeaderCell className="text-gray-400 text-right">P&L</TableHeaderCell>
                  <TableHeaderCell className="text-gray-400 text-right">Win</TableHeaderCell>
                  <TableHeaderCell className="text-gray-400 text-right">Поз.</TableHeaderCell>
                  <TableHeaderCell className="text-gray-400 text-right">Сделок</TableHeaderCell>
                  <TableHeaderCell className="text-gray-400 text-right">Sharpe*</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {wallets.map((w) => (
                  <TableRow key={w.wallet} className="border-gray-800">
                    <TableCell>
                      <a
                        href={`https://polymarket.com/profile/${w.wallet}`}
                        target="_blank"
                        rel="noreferrer"
                        className="font-mono text-blue-400 hover:text-blue-300"
                        title={w.wallet}
                      >
                        {short(w.wallet)}
                      </a>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={w.pnl_usd >= 0 ? "text-emerald-400" : "text-red-400"}>
                        {usd(w.pnl_usd)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right text-gray-300">
                      {(w.winrate * 100).toFixed(0)}%
                    </TableCell>
                    <TableCell className="text-right text-gray-400">{w.n_positions}</TableCell>
                    <TableCell className="text-right text-gray-400">{w.n_trades}</TableCell>
                    <TableCell className="text-right text-gray-200 font-medium">
                      {w.sharpe_like.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      </Grid>

      <p className="text-xs text-gray-600 mt-8">
        * sharpe-подобная = средний P&L позиции / его разброс. Research-инструмент,
        не финансовый совет. Реальный сеттлмент и вход после задержки в бэктесте
        ещё не реализованы — см. README.
      </p>
    </main>
  );
}

function KpiCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="bg-gray-900 ring-gray-800">
      <Text className="text-gray-400">{label}</Text>
      <Metric className="text-white mt-1">
        {value.toLocaleString("ru-RU")}
      </Metric>
    </Card>
  );
}
