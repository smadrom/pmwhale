import { Database } from "bun:sqlite";
import { extname, isAbsolute, relative, resolve } from "node:path";

const PORT = Number(process.env.PORT ?? 5178);
const DB_PATH = process.env.DB_PATH ?? "/data/pmwhale.db";
const DIST = resolve(process.env.DIST_DIR ?? resolve(import.meta.dir, "dist"));

const db = new Database(DB_PATH, { readonly: true });
db.exec("PRAGMA busy_timeout = 3000;");

const SECURITY_HEADERS = {
  "content-security-policy":
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; " +
    "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  "cross-origin-resource-policy": "same-origin",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
};

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: {
      ...SECURITY_HEADERS,
      "content-type": "application/json; charset=utf-8",
    },
  });

class HttpError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

function boundedInteger(
  raw: string | null,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  if (raw === null) return fallback;
  if (!/^\d+$/.test(raw)) throw new HttpError(400, "invalid integer query parameter");
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < minimum)
    throw new HttpError(400, "integer query parameter is out of range");
  return Math.min(value, maximum);
}

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
  let decoded: string;
  try {
    decoded = decodeURIComponent(pathname).replace(/\\/g, "/");
  } catch {
    throw new HttpError(400, "invalid URL encoding");
  }
  if (decoded.includes("\0")) throw new HttpError(400, "invalid path");

  const requested = resolve(DIST, decoded === "/" ? "index.html" : decoded.replace(/^\/+/, ""));
  const fromRoot = relative(DIST, requested);
  if (fromRoot.startsWith("..") || isAbsolute(fromRoot))
    throw new HttpError(404, "not found");

  let file = Bun.file(requested);
  if (!(await file.exists()) && !extname(decoded)) file = Bun.file(resolve(DIST, "index.html"));
  if (!(await file.exists()))
    return new Response("not found", {
      status: 404,
      headers: SECURITY_HEADERS,
    });
  return new Response(file, { headers: SECURITY_HEADERS });
}

Bun.serve({
  port: PORT,
  hostname: "0.0.0.0",
  async fetch(req) {
    const url = new URL(req.url);
    const p = url.pathname;
    try {
      if (req.method !== "GET" && req.method !== "HEAD")
        return json({ error: "method not allowed" }, 405);
      if (p === "/api/health") return json({ ok: true });
      if (p === "/api/stats") return json(getStats());
      if (p === "/api/wallets") {
        const limit = boundedInteger(url.searchParams.get("limit"), 25, 1, 200);
        const minPos = boundedInteger(url.searchParams.get("min_positions"), 10, 1, 10_000);
        return json({ wallets: getWallets(limit, minPos) });
      }
      const tm = p.match(/^\/api\/wallets\/(0x[0-9a-fA-F]{40})\/trades$/);
      if (tm) {
        const limit = boundedInteger(url.searchParams.get("limit"), 50, 1, 500);
        return json({ trades: getWalletTrades(tm[1], limit) });
      }
      if (p.startsWith("/api/")) return json({ error: "not found" }, 404);
      return await serveStatic(p);
    } catch (error: unknown) {
      if (error instanceof HttpError) return json({ error: error.message }, error.status);
      console.error("request failed", error);
      return json({ error: "internal server error" }, 500);
    }
  },
});

console.log(`pmwhale-ui listening on http://0.0.0.0:${PORT}`);
