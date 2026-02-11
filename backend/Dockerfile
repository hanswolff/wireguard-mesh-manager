# Use Python 3.11 slim image as base
FROM python:3.11-slim AS backend

LABEL maintainer="devops@wireguard-mesh-manager.org" \
      version="1.0" \
      description="WireGuard Mesh Manager Backend" \
      org.opencontainers.image.source="https://github.com/wireguard-mesh-manager/wireguard-mesh-manager"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONHASHSEED=random \
    # Security hardening
    PYTHONNOUSERSITE=1 \
    PYTHONOPTIMIZE=1 \
    # Enable pip caching for faster rebuilds
    PIP_CACHE_DIR=/root/.cache/pip

# Create a non-root user
RUN groupadd -r wmm && useradd -r -g wmm wmm

# Set work directory
WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        ca-certificates \
        dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && find /usr/share/man -type f -delete \
    && find /usr/share/doc -type f -delete \
    && find /usr/share/info -type f -delete

# Copy project configuration and dependency locks first for better caching
COPY pyproject.toml requirements.lock.txt requirements.txt ./

# Install Python dependencies from the lock file
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.lock.txt

# Copy application code
COPY . .

# Install the application package
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install .

# Create data directory and set permissions
RUN mkdir -p /app/data && \
    chown -R wmm:wmm /app && \
    chmod 700 /app/data

# Volume for pip cache (share with host for faster rebuilds)
VOLUME ["/root/.cache/pip"]

USER wmm

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
