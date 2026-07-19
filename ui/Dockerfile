ARG BUN_VERSION=1.3.14

FROM oven/bun:${BUN_VERSION}@sha256:e10577f0db68676a7024391c6e5cb4b879ebd17188ab750cf10024a6d700e5c4 AS build
WORKDIR /app
COPY ui/package.json ui/bun.lock ./
RUN bun install --frozen-lockfile
COPY ui/ ./
RUN bun run build

FROM oven/bun:${BUN_VERSION}-slim@sha256:d56a2534ffd262e92c12fd3249d3924d296d97086da773f821d7d0477435ea04 AS run
WORKDIR /app
ENV PORT=5178 \
    DB_PATH=/data/pmwhale.db \
    DIST_DIR=/app/dist
LABEL org.opencontainers.image.source="https://github.com/smadrom/pmwhale" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.description="Local dashboard for pmwhale research data"
COPY --from=build --chown=bun:bun /app/dist ./dist
COPY --chown=bun:bun ui/server.ts ./
COPY --chown=bun:bun LICENSE ./
COPY --chown=bun:bun ui/THIRD_PARTY_LICENSES.txt ./
USER bun
EXPOSE 5178
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["bun", "-e", "fetch('http://127.0.0.1:5178/api/health').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]
CMD ["bun", "server.ts"]
