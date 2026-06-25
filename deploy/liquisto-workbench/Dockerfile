FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY apps/liquisto-workbench/package.json apps/liquisto-workbench/package-lock.json ./apps/liquisto-workbench/
RUN npm ci --prefix apps/liquisto-workbench

COPY apps/liquisto-workbench ./apps/liquisto-workbench
RUN npm run --prefix apps/liquisto-workbench build

FROM node:22-bookworm-slim AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=build /app/apps/liquisto-workbench/.next/standalone ./
COPY --from=build /app/apps/liquisto-workbench/.next/static ./.next/static
COPY --from=build /app/apps/liquisto-workbench/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
