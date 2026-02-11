# Multi-stage build for production-ready image
FROM node:20-slim AS builder

LABEL maintainer="devops@wireguard-mesh-manager.org" \
      version="1.0" \
      description="WireGuard Mesh Manager Frontend Development" \
      org.opencontainers.image.source="https://github.com/wireguard-mesh-manager/wireguard-mesh-manager"

# Set environment variables for build
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && find /usr/share/man -type f -delete \
    && find /usr/share/doc -type f -delete \
    && find /usr/share/info -type f -delete \
    && groupadd -r wmm && useradd -r -g wmm wmm

# Set work directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies
RUN --mount=type=cache,target=/root/.npm \
    npm ci && npm cache clean --force

# Copy source code
COPY . .

# Build the production bundle
RUN npm run build

# Runtime image
FROM node:20-slim AS production

# Set environment variables for runtime
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    NODE_OPTIONS="--no-deprecation"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && find /usr/share/man -type f -delete \
    && find /usr/share/doc -type f -delete \
    && find /usr/share/info -type f -delete \
    && groupadd -r wmm && useradd -r -g wmm wmm

WORKDIR /app

# Copy built assets
COPY --from=builder --chown=wmm:wmm /app/.next ./.next
COPY --from=builder --chown=wmm:wmm /app/node_modules ./node_modules
COPY --from=builder --chown=wmm:wmm /app/package*.json ./
COPY --from=builder --chown=wmm:wmm /app/public ./public

USER wmm

# Expose port
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "run", "start"]
