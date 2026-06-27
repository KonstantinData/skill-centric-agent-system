FROM node:22-bookworm-slim AS build

WORKDIR /app

COPY apps/khh-workbench/package.json apps/khh-workbench/package-lock.json ./apps/khh-workbench/
RUN npm ci --prefix apps/khh-workbench

COPY apps/khh-workbench ./apps/khh-workbench
RUN npm run --prefix apps/khh-workbench build

FROM node:22-bookworm-slim AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=build /app/apps/khh-workbench/.next/standalone ./
COPY --from=build /app/apps/khh-workbench/.next/static ./.next/static
COPY --from=build /app/apps/khh-workbench/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
