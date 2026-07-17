// Bun-сервер: API поверх pmwhale.db (bun:sqlite) + раздача собранного фронта.
// Один порт, один процесс. DB монтируется в контейнер только на чтение.
import { Database } from "bun:sqlite";
import { join, normalize } from "node:path";

const PORT = Number(process.env.PORT ?? 5178);
const DB_PATH = process.env.DB_PATH ?? "/data/pmwhale.db";
const DIST = process.env.DIST_DIR ?? join(import.meta.dir, "dist");

const db = new Database(DB_PATH, { readonly: true });
db.exec("PRAGMA busy_timeout = 3000;"); // сбор может писать в БД параллельно

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });

function getStats() {
  const t = db.query("SELECT COUNT(*) c FROM trades").get() as { c: number };
  const w = db
    .query("SELECT COUNT(DISTINCT wallet) c FROM trades")
    .get() as { c: number };
  const m = db
    .query("SELECT COUNT(DISTINCT market) c FROM trades")
    .get() as { c: number };
  const span = db
    .query("SELECT MIN(timestamp) a, MAX(timestamp) b FROM trades")
    .get() as { a: number | null; b: number | null };
  return {
    trades: t.c,
    wallets: w.c,
    markets: m.c,
    first_ts: span.a,
    last_ts: span.b,
  };
}

const RANK_SQL = `
WITH pos AS (
  SELECT wallet, asset,
         SUM(CASE side WHEN 'SELL' THEN usd ELSE -usd END) AS pnl
  FROM trades GROUP BY wallet, asset
),
agg AS (
  SELECT wallet,
         COUNT(*)                              AS n_positions,
         SUM(pnl)                              AS pnl_usd,
         SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins,
         AVG(pnl)                              AS mean_pnl,
         AVG(pnl * pnl)                        AS mean_sq
  FROM pos GROUP BY wallet
),
vol AS (
  SELECT wallet, SUM(usd) AS volume_usd, COUNT(*) AS n_trades
  FROM trades GROUP BY wallet
)
SELECT a.wallet, a.pnl_usd, a.n_positions, a.wins, a.mean_pnl, a.mean_sq,
       v.volume_usd, v.n_trades
FROM agg a JOIN vol v ON v.wallet = a.wallet
WHERE a.n_positions >= ?1
`;

function getWallets(limit: number, minPositions: number) {
  const rows = db.query(RANK_SQL).all(minPositions) as Array<{
    wallet: string;
    pnl_usd: number;
    n_positions: number;
    wins: number;
    mean_pnl: number;
    mean_sq: number;
    volume_usd: number;
    n_trades: number;
  }>;
  const out = rows.map((r) => {
    const variance = Math.max(0, r.mean_sq - r.mean_pnl * r.mean_pnl);
    const sd = Math.sqrt(variance);
    return {
      wallet: r.wallet,
      pnl_usd: r.pnl_usd,
      n_positions: r.n_positions,
      winrate: r.n_positions ? r.wins / r.n_positions : 0,
      volume_usd: r.volume_usd,
      n_trades: r.n_trades,
      sharpe_like: sd > 0 ? r.mean_pnl / sd : 0,
    };
  });
  out.sort(
    (a, b) => b.sharpe_like - a.sharpe_like || b.winrate - a.winrate,
  );
  return out.slice(0, limit);
}

function getWalletTrades(addr: string, limit: number) {
  return db
    .query(
      "SELECT timestamp, market, side, price, size, usd FROM trades " +
        "WHERE wallet = ?1 ORDER BY timestamp DESC LIMIT ?2",
    )
    .all(addr.toLowerCase(), limit);
}

async function serveStatic(pathname: string): Promise<Response> {
  const rel = pathname === "/" ? "/index.html" : pathname;
  // защита от path traversal
  const safe = normalize(join(DIST, rel)).replace(/^(\.\.[/\\])+/, "");
  let file = Bun.file(safe);
  if (!(await file.exists())) file = Bun.file(join(DIST, "index.html")); // SPA fallback
  if (!(await file.exists()))
    return new Response("UI не собран (нет dist/). Запусти `bun run build`.", {
      status: 404,
    });
  return new Response(file);
}

Bun.serve({
  port: PORT,
  hostname: "0.0.0.0",
  async fetch(req) {
    const url = new URL(req.url);
    const p = url.pathname;
    try {
      if (p === "/api/health") return json({ ok: true, db: DB_PATH });
      if (p === "/api/stats") return json(getStats());
      if (p === "/api/wallets") {
        const limit = Math.min(200, Number(url.searchParams.get("limit") ?? 25));
        const minPos = Number(url.searchParams.get("min_positions") ?? 10);
        return json({ wallets: getWallets(limit, minPos) });
      }
      const tm = p.match(/^\/api\/wallets\/(0x[0-9a-fA-F]+)\/trades$/);
      if (tm) {
        const limit = Math.min(500, Number(url.searchParams.get("limit") ?? 50));
        return json({ trades: getWalletTrades(tm[1], limit) });
      }
      if (p.startsWith("/api/")) return json({ error: "not found" }, 404);
      return await serveStatic(p);
    } catch (e: any) {
      return json({ error: String(e?.message ?? e) }, 500);
    }
  },
});

console.log(`pmwhale-ui on http://0.0.0.0:${PORT}  (db=${DB_PATH})`);
