FROM node:22-slim AS base

WORKDIR /app

# Install dependencies
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# Build stage
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Build args for runtime config baked into the image
ARG NUXT_PUBLIC_API_BASE
ARG NUXT_PUBLIC_PAYPAL_CLIENT_ID

ENV NUXT_PUBLIC_API_BASE=$NUXT_PUBLIC_API_BASE
ENV NUXT_PUBLIC_PAYPAL_CLIENT_ID=$NUXT_PUBLIC_PAYPAL_CLIENT_ID
ENV NODE_ENV=production

RUN npm run build

# Production stage — only the built output
FROM node:22-slim AS final

WORKDIR /app

RUN groupadd --system --gid 1000 nuxt && \
    useradd nuxt --uid 1000 --gid 1000 --create-home --shell /bin/bash

COPY --chown=nuxt:nuxt --from=build /app/.output ./output

USER 1000:1000

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

EXPOSE 3000

CMD ["node", "output/server/index.mjs"]
