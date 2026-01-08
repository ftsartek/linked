# syntax=docker.io/docker/dockerfile-upstream:1.19.0
FROM debian:trixie-slim

# Set persistent environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    UV_PYTHON_INSTALL_DIR=/opt/uv \
    UV_CACHE_DIR=/var/cache/uv

# Supercronic for cron jobs (runs in foreground, no root required)
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.41/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=f70ad28d0d739a96dc9e2087ae370c257e79b8d7 \
    SUPERCRONIC=supercronic-linux-amd64

# Application directories
ENV DATA_DIR=/var/lib/linked/preseed \
    IMAGE_CACHE_DIR=/var/cache/linked/images

# Data volume
VOLUME /var/lib/linked

# Set up working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic
RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy application files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY static/preseed/curated/ ./static/preseed/curated/
COPY migrations/ ./migrations/

# Copy configuration files
COPY supervisord.conf /var/www/.supervisord.conf
COPY crontab /var/www/.crontab
COPY entrypoint.sh /entrypoint.sh

# Create virtual environment, sync dependencies, and set up directories
RUN uv sync --frozen && \
    mkdir -p /var/lib/linked/preseed/sde /var/cache/linked/images /var/cache/uv /var/run/supervisor && \
    chown -R www-data:www-data /var/lib/linked /var/cache/linked /var/cache/uv /opt/uv /app /var/run/supervisor /etc/linked && \
    chmod +x /entrypoint.sh

ENV PATH=/app/.venv/bin:$PATH

EXPOSE 8000

USER www-data

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/linked/supervisord.conf"]
