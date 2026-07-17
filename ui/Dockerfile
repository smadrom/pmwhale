# --- build stage: собираем React-фронт через Vite ---
FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json ./
RUN bun install
COPY . .
RUN bun run build

# --- runtime stage: только bun + собранный dist + сервер ---
# bun:sqlite и node:path встроены в bun, node_modules в рантайме не нужны.
FROM oven/bun:1-slim AS run
WORKDIR /app
ENV PORT=5178 \
    DB_PATH=/data/pmwhale.db \
    DIST_DIR=/app/dist
COPY --from=build /app/dist ./dist
COPY server.ts ./
EXPOSE 5178
CMD ["bun", "server.ts"]
